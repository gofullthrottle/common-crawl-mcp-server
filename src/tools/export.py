"""Export and integration tools for Common Crawl MCP Server.

This module provides tools for exporting query results to various formats
and managing datasets.
"""

import csv
import io
import json
import logging
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

import httpx
import jsonlines
from jinja2 import Template
from pydantic import BaseModel, Field
from warcio.warcwriter import WARCWriter

logger = logging.getLogger(__name__)


# Database configuration
DB_PATH = Path("./data/commoncrawl.db")

# Database schema
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS datasets (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    records_count INTEGER DEFAULT 0,
    metadata JSON
);

CREATE TABLE IF NOT EXISTS dataset_records (
    id TEXT PRIMARY KEY,
    dataset_id TEXT NOT NULL,
    data JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dataset_id) REFERENCES datasets (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS investigation_sessions (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    state JSON NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dataset_records_dataset_id ON dataset_records(dataset_id);
CREATE INDEX IF NOT EXISTS idx_investigation_sessions_created_at ON investigation_sessions(created_at DESC);
"""


# Pydantic Models
class ExportResult(BaseModel):
    """Result of export operation."""

    output_path: str = Field(..., description="Path to the exported file")
    format: str = Field(..., description="Export format (csv, jsonl, warc)")
    records_exported: int = Field(..., description="Number of records successfully exported")
    file_size_bytes: int = Field(..., description="Size of the output file in bytes")
    duration_seconds: float = Field(..., description="Time taken to export")
    errors: list[str] = Field(default_factory=list, description="List of errors encountered")


class Dataset(BaseModel):
    """Saved dataset information."""

    id: str = Field(..., description="UUID of the dataset")
    name: str = Field(..., description="Unique name for the dataset")
    description: str = Field(..., description="Description of the dataset")
    created_at: datetime = Field(..., description="When the dataset was created")
    records_count: int = Field(..., description="Number of records in the dataset")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class DatasetRecord(BaseModel):
    """Individual record in a dataset."""

    id: str = Field(..., description="UUID of the record")
    dataset_id: str = Field(..., description="UUID of the parent dataset")
    data: dict[str, Any] = Field(..., description="Record data as JSON")
    created_at: datetime = Field(..., description="When the record was created")


# Helper functions for CSV export
def _flatten_dict(d: dict, parent_key: str = "", sep: str = ".") -> dict:
    """Flatten nested dictionary.

    Args:
        d: Dictionary to flatten
        parent_key: Parent key for nested keys
        sep: Separator for nested keys

    Returns:
        Flattened dictionary

    Example:
        >>> _flatten_dict({"a": {"b": 1, "c": 2}})
        {"a.b": 1, "a.c": 2}
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(_flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def _extract_fields(record: dict) -> list[str]:
    """Extract all field names from a record, including nested ones.

    Args:
        record: Dictionary record

    Returns:
        List of field names in flattened form
    """
    flattened = _flatten_dict(record)
    return list(flattened.keys())


# Export functions
async def export_to_csv(
    data: list[dict[str, Any]],
    output_path: str,
    *,
    fields: Optional[list[str]] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> ExportResult:
    """Export data to CSV format with streaming.

    Args:
        data: List of dictionaries to export
        output_path: Path to output CSV file
        fields: Optional list of fields to export (auto-detected if not provided)
        progress_callback: Optional callback for progress updates (current, total)

    Returns:
        ExportResult with export statistics

    Example:
        >>> data = [{"url": "https://example.com", "title": "Example"}]
        >>> result = await export_to_csv(data, "output.csv")
        >>> print(f"Exported {result.records_exported} records")
    """
    start_time = time.time()
    errors = []

    # Auto-detect fields from first record if not specified
    if fields is None and data:
        fields = _extract_fields(data[0])

    # Stream write
    output_path_obj = Path(output_path)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)

    with output_path_obj.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()

        for i, record in enumerate(data):
            try:
                flattened = _flatten_dict(record)
                # Fill in missing fields with empty strings
                row = {field: flattened.get(field, "") for field in fields}
                writer.writerow(row)

                if progress_callback and (i + 1) % 100 == 0:
                    progress_callback(i + 1, len(data))
            except Exception as e:
                errors.append(f"Row {i}: {str(e)}")

    file_size = output_path_obj.stat().st_size
    duration = time.time() - start_time

    return ExportResult(
        output_path=str(output_path),
        format="csv",
        records_exported=len(data) - len(errors),
        file_size_bytes=file_size,
        duration_seconds=round(duration, 2),
        errors=errors,
    )


async def export_to_jsonl(
    data: list[dict[str, Any]],
    output_path: str,
    *,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> ExportResult:
    """Export data to JSONL format with streaming.

    JSONL (JSON Lines) format writes each record as a separate line of JSON,
    making it ideal for streaming and processing large datasets.

    Args:
        data: List of dictionaries to export
        output_path: Path to output JSONL file
        progress_callback: Optional callback for progress updates (current, total)

    Returns:
        ExportResult with export statistics

    Example:
        >>> data = [
        ...     {"url": "https://example.com", "meta": {"title": "Example"}},
        ...     {"url": "https://test.com", "meta": {"title": "Test"}},
        ... ]
        >>> result = await export_to_jsonl(data, "output.jsonl")
        >>> print(f"Exported {result.records_exported} records in {result.duration_seconds}s")
    """
    start_time = time.time()
    errors = []

    output_path_obj = Path(output_path)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)

    with jsonlines.open(output_path_obj, mode="w") as writer:
        for i, record in enumerate(data):
            try:
                writer.write(record)

                if progress_callback and (i + 1) % 100 == 0:
                    progress_callback(i + 1, len(data))
            except Exception as e:
                errors.append(f"Record {i}: {str(e)}")

    file_size = output_path_obj.stat().st_size
    duration = time.time() - start_time

    return ExportResult(
        output_path=str(output_path),
        format="jsonl",
        records_exported=len(data) - len(errors),
        file_size_bytes=file_size,
        duration_seconds=round(duration, 2),
        errors=errors,
    )


# Database initialization
def _init_database() -> None:
    """Initialize the database schema if it doesn't exist."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.executescript(SCHEMA_SQL)
    conn.commit()
    conn.close()


# Dataset management functions
async def create_dataset(
    name: str,
    description: str,
    data: list[dict[str, Any]],
    *,
    metadata: Optional[dict[str, Any]] = None,
) -> Dataset:
    """Create a named dataset from query results.

    Args:
        name: Unique name for the dataset
        description: Description of the dataset
        data: List of records to store
        metadata: Optional additional metadata

    Returns:
        Dataset: Created dataset information

    Raises:
        sqlite3.IntegrityError: If dataset name already exists
    """
    # Initialize database
    _init_database()

    # Generate IDs and timestamp
    dataset_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc)

    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Insert dataset
        cursor.execute(
            """INSERT INTO datasets (id, name, description, records_count, metadata, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                dataset_id,
                name,
                description,
                len(data),
                json.dumps(metadata or {}),
                created_at.isoformat(),
            ),
        )

        # Insert records
        for record_data in data:
            record_id = str(uuid.uuid4())
            cursor.execute(
                """INSERT INTO dataset_records (id, dataset_id, data, created_at)
                   VALUES (?, ?, ?, ?)""",
                (
                    record_id,
                    dataset_id,
                    json.dumps(record_data),
                    created_at.isoformat(),
                ),
            )

        conn.commit()

    except Exception as e:
        conn.rollback()
        raise e

    finally:
        conn.close()

    return Dataset(
        id=dataset_id,
        name=name,
        description=description,
        created_at=created_at,
        records_count=len(data),
        metadata=metadata or {},
    )


async def get_dataset(name: str) -> Optional[Dataset]:
    """Retrieve dataset by name.

    Args:
        name: Name of the dataset to retrieve

    Returns:
        Dataset if found, None otherwise
    """
    # Initialize database
    _init_database()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    row = cursor.execute(
        "SELECT id, name, description, created_at, records_count, metadata FROM datasets WHERE name = ?",
        (name,),
    ).fetchone()

    conn.close()

    if not row:
        return None

    return Dataset(
        id=row[0],
        name=row[1],
        description=row[2],
        created_at=datetime.fromisoformat(row[3]),
        records_count=row[4],
        metadata=json.loads(row[5]),
    )


async def get_dataset_records(dataset_id: str) -> list[dict[str, Any]]:
    """Retrieve all records from a dataset.

    Args:
        dataset_id: UUID of the dataset

    Returns:
        List of record data dictionaries
    """
    # Initialize database
    _init_database()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    rows = cursor.execute(
        "SELECT data FROM dataset_records WHERE dataset_id = ? ORDER BY created_at",
        (dataset_id,),
    ).fetchall()

    conn.close()

    return [json.loads(row[0]) for row in rows]


async def get_all_datasets() -> list[Dataset]:
    """Retrieve all datasets.

    Returns:
        List of all datasets ordered by creation date (newest first)
    """
    # Initialize database
    _init_database()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    rows = cursor.execute(
        """SELECT id, name, description, created_at, records_count, metadata
           FROM datasets ORDER BY created_at DESC"""
    ).fetchall()

    conn.close()

    return [
        Dataset(
            id=row[0],
            name=row[1],
            description=row[2],
            created_at=datetime.fromisoformat(row[3]),
            records_count=row[4],
            metadata=json.loads(row[5]),
        )
        for row in rows
    ]


async def get_dataset_by_id(dataset_id: str) -> Optional[Dataset]:
    """Retrieve dataset by ID.

    Args:
        dataset_id: UUID of the dataset

    Returns:
        Dataset if found, None otherwise
    """
    # Initialize database
    _init_database()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    row = cursor.execute(
        """SELECT id, name, description, created_at, records_count, metadata
           FROM datasets WHERE id = ?""",
        (dataset_id,),
    ).fetchone()

    conn.close()

    if not row:
        return None

    return Dataset(
        id=row[0],
        name=row[1],
        description=row[2],
        created_at=datetime.fromisoformat(row[3]),
        records_count=row[4],
        metadata=json.loads(row[5]),
    )


async def export_warc_subset(
    urls: list[str],
    crawl_id: str,
    output_path: str,
    *,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> ExportResult:
    """Export WARC records for specified URLs.

    This function queries the CDX API to locate WARC files for the given URLs,
    then downloads the relevant WARC records and combines them into a single
    output WARC file.

    Args:
        urls: List of URLs to export
        crawl_id: Common Crawl crawl ID (e.g., "CC-MAIN-2024-10")
        output_path: Path to output WARC file
        progress_callback: Optional callback(current, total) for progress tracking

    Returns:
        ExportResult with export statistics and any errors

    Note:
        This function may have limited functionality due to S3 access restrictions.
        It attempts to download WARC records via HTTP fallback when S3 access fails.
    """
    from ..core.cc_client import CDXClient

    start_time = time.time()
    errors = []
    records_written = 0

    # Ensure output directory exists
    output_path_obj = Path(output_path)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)

    # Initialize CDX client
    cdx_client = CDXClient()

    # Create HTTP client for downloading WARC records
    http_client = httpx.AsyncClient(timeout=60.0)

    try:
        # Open output WARC file
        with output_path_obj.open("wb") as output_file:
            writer = WARCWriter(output_file, gzip=True)

            # Process each URL
            for i, url in enumerate(urls):
                try:
                    logger.info(f"Processing URL {i+1}/{len(urls)}: {url}")

                    # Query CDX for this URL
                    index_records = await cdx_client.search_index(
                        query=url,
                        crawl_id=crawl_id,
                        limit=1,
                        match_type="exact",
                    )

                    if not index_records:
                        error_msg = f"URL not found in index: {url}"
                        logger.warning(error_msg)
                        errors.append(error_msg)
                        if progress_callback:
                            progress_callback(i + 1, len(urls))
                        continue

                    # Get the first (most recent) record
                    record = index_records[0]

                    # Construct WARC download URL
                    # Common Crawl provides HTTP access to WARC files
                    warc_url = f"https://data.commoncrawl.org/{record.filename}"

                    # Download the specific WARC record using byte range
                    # The CDX index provides offset and length
                    headers = {
                        "Range": f"bytes={record.offset}-{record.offset + record.length - 1}"
                    }

                    logger.debug(
                        f"Downloading WARC record from {warc_url} "
                        f"(offset={record.offset}, length={record.length})"
                    )

                    response = await http_client.get(warc_url, headers=headers)
                    response.raise_for_status()

                    warc_data = response.content

                    # Write the WARC record directly to output
                    # The downloaded data is already in WARC format
                    output_file.write(warc_data)
                    records_written += 1

                    logger.info(
                        f"Successfully exported WARC record for {url} " f"({len(warc_data)} bytes)"
                    )

                except httpx.HTTPError as e:
                    error_msg = f"HTTP error downloading {url}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                except Exception as e:
                    error_msg = f"Error processing {url}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)

                # Call progress callback
                if progress_callback:
                    progress_callback(i + 1, len(urls))

    finally:
        await http_client.aclose()
        await cdx_client.close()

    # Calculate statistics
    duration = time.time() - start_time
    file_size = output_path_obj.stat().st_size if output_path_obj.exists() else 0

    logger.info(
        f"WARC export complete: {records_written}/{len(urls)} records exported "
        f"in {duration:.2f}s, {file_size:,} bytes"
    )

    return ExportResult(
        output_path=str(output_path),
        format="warc",
        records_exported=records_written,
        file_size_bytes=file_size,
        duration_seconds=round(duration, 2),
        errors=errors,
    )


class ReportResult(BaseModel):
    """Result of report generation.

    Attributes:
        output_path: Path to the generated report file
        report_type: Type of report generated
        format: Output format (markdown or html)
        sections_count: Number of sections in the report
        file_size_bytes: Size of the generated file in bytes
    """

    output_path: str = Field(..., description="Path to generated report")
    report_type: str = Field(..., description="Type of report")
    format: str = Field(..., description="Output format (markdown or html)")
    sections_count: int = Field(..., description="Number of sections in report")
    file_size_bytes: int = Field(..., description="File size in bytes")


# Template for Domain Analysis Report
DOMAIN_ANALYSIS_TEMPLATE = """# Domain Analysis Report: {{ domain }}

**Generated:** {{ timestamp }}

## Overview
- **Total Pages Analyzed:** {{ format_number(pages_analyzed) }}
- **Crawl:** {{ crawl_id }}
{% if timeframe %}
- **Analysis Timeframe:** {{ timeframe }}
{% endif %}

## Technologies Detected
{% if technologies %}
{% for tech, adoption in technologies.items() %}
- **{{ tech }}**: {{ "%.1f"|format(adoption) }}% adoption
{% endfor %}
{% else %}
No technologies detected.
{% endif %}

## Link Graph
{% if link_graph %}
- **Total Pages:** {{ format_number(link_graph.total_pages) }}
- **Total Links:** {{ format_number(link_graph.total_links) }}
{% if link_graph.avg_links_per_page is defined %}
- **Average Links per Page:** {{ "%.1f"|format(link_graph.avg_links_per_page) }}
{% endif %}

### Hub Pages (Top 10)
{% if link_graph.hub_pages %}
{% for page, inbound in link_graph.hub_pages[:10] %}
{{ loop.index }}. {{ page }} ({{ format_number(inbound) }} inbound links)
{% endfor %}
{% else %}
No hub pages identified.
{% endif %}
{% else %}
Link graph data not available.
{% endif %}

## Security Headers
{% if security_headers %}
- **Security Score:** {{ security_score }}/100
- **Headers Adoption:**
{% for header, adoption in security_headers.items() %}
  - {{ header }}: {{ "%.1f"|format(adoption) }}%
{% endfor %}

### Recommendations
{% if recommendations %}
{% for rec in recommendations %}
- {{ rec }}
{% endfor %}
{% else %}
No specific recommendations.
{% endif %}
{% else %}
Security header data not available.
{% endif %}

## Summary
This report analyzed {{ format_number(pages_analyzed) }} pages from {{ domain }} during crawl {{ crawl_id }}.
{% if technologies %}
The domain uses {{ technologies|length }} different technologies across its pages.
{% endif %}
{% if link_graph and link_graph.hub_pages %}
The link graph analysis identified {{ link_graph.hub_pages|length }} key hub pages that serve as important navigation points.
{% endif %}

---
*Report generated by Common Crawl MCP Server*
"""


# Template for Tech Stack Report
TECH_STACK_TEMPLATE = """# Technology Stack Report: {{ domain }}

**Generated:** {{ timestamp }}

## Overview
- **Domain:** {{ domain }}
- **Crawl:** {{ crawl_id }}
- **Pages Analyzed:** {{ format_number(pages_analyzed) }}
- **Technologies Found:** {{ total_technologies }}
{% if analysis_date %}
- **Analysis Date:** {{ analysis_date }}
{% endif %}

## Technology Breakdown by Category
{% if categories %}
{% for category, techs in categories.items() %}

### {{ category }}
{% for tech, details in techs.items() %}
- **{{ tech }}**
  - Pages using this: {{ format_number(details.count) }}
  - Adoption rate: {{ "%.1f"|format(details.percentage) }}%
{% if details.version is defined %}
  - Version detected: {{ details.version }}
{% endif %}
{% endfor %}
{% endfor %}
{% else %}
No categorized technology data available.
{% endif %}

## Most Popular Technologies
{% if top_technologies %}
{% for tech in top_technologies[:15] %}
{{ loop.index }}. **{{ tech.name }}** ({{ tech.category }})
   - Used on {{ format_number(tech.page_count) }} pages ({{ "%.1f"|format(tech.adoption_percentage) }}%)
{% if tech.version is defined %}
   - Version: {{ tech.version }}
{% endif %}
{% endfor %}
{% else %}
No technology ranking available.
{% endif %}

## Technology Stack Analysis
{% if stack_analysis %}

### Frontend Technologies
{% if stack_analysis.frontend %}
{% for tech in stack_analysis.frontend %}
- {{ tech }}
{% endfor %}
{% else %}
No frontend technologies detected.
{% endif %}

### Backend Technologies
{% if stack_analysis.backend %}
{% for tech in stack_analysis.backend %}
- {{ tech }}
{% endfor %}
{% else %}
No backend technologies detected.
{% endif %}

### Analytics & Marketing
{% if stack_analysis.analytics %}
{% for tech in stack_analysis.analytics %}
- {{ tech }}
{% endfor %}
{% else %}
No analytics technologies detected.
{% endif %}
{% endif %}

## Adoption Trends
{% if adoption_trends %}
{% for trend, value in adoption_trends.items() %}
- {{ trend }}: {{ value }}
{% endfor %}
{% endif %}

## Summary
The technology stack analysis of {{ domain }} reveals a diverse set of {{ total_technologies }} technologies across {{ format_number(pages_analyzed) }} pages.
{% if categories %}
Technologies are distributed across {{ categories|length }} categories, providing insights into the domain's technical architecture.
{% endif %}

---
*Report generated by Common Crawl MCP Server*
"""


def _format_number(value) -> str:
    """Format large numbers with thousand separators.

    Args:
        value: Integer value to format

    Returns:
        Formatted string with commas (e.g., "1,000,000")
    """
    if value is None:
        return "N/A"
    try:
        return f"{int(value):,}"
    except (ValueError, TypeError):
        return str(value)


async def generate_report(
    report_type: str,
    data: dict[str, Any],
    output_path: str,
    *,
    format: str = "markdown",
) -> ReportResult:
    """Generate formatted report from analysis data.

    This function creates comprehensive reports in Markdown or HTML format
    from Common Crawl analysis data. It supports multiple report types
    with custom templates.

    Args:
        report_type: Type of report to generate. Supported types:
            - "domain_analysis": Comprehensive domain overview
            - "tech_stack": Technology stack analysis
        data: Dictionary containing report data specific to report_type
        output_path: Path where the report will be saved
        format: Output format, either "markdown" or "html" (default: "markdown")

    Returns:
        ReportResult object containing report metadata and statistics

    Raises:
        ValueError: If report_type is not supported
        KeyError: If required data fields are missing
        IOError: If unable to write report file

    Example:
        >>> data = {
        ...     "domain": "example.com",
        ...     "crawl_id": "CC-MAIN-2024-10",
        ...     "pages_analyzed": 1500,
        ...     "technologies": {"React": 45.2, "WordPress": 32.1},
        ...     "link_graph": {
        ...         "total_pages": 1500,
        ...         "total_links": 8942,
        ...         "hub_pages": [("index.html", 234), ("about.html", 198)]
        ...     },
        ...     "security_headers": {"HSTS": 78.5, "CSP": 42.3},
        ...     "security_score": 72
        ... }
        >>> result = await generate_report(
        ...     "domain_analysis",
        ...     data,
        ...     "/tmp/domain_report.md"
        ... )
        >>> print(f"Report saved to {result.output_path}")
    """
    # Select template based on report type
    template_map = {
        "domain_analysis": DOMAIN_ANALYSIS_TEMPLATE,
        "tech_stack": TECH_STACK_TEMPLATE,
    }

    if report_type not in template_map:
        raise ValueError(
            f"Unsupported report type: {report_type}. "
            f"Supported types: {', '.join(template_map.keys())}"
        )

    # Create Jinja2 template with custom filters
    template = Template(template_map[report_type])
    template.globals["format_number"] = _format_number

    # Add timestamp to data
    report_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **data,
    }

    # Render the report
    try:
        rendered = template.render(**report_data)
    except Exception as e:
        raise KeyError(f"Missing required data fields for {report_type}: {e}")

    # Convert to HTML if requested
    if format == "html":
        rendered = _markdown_to_html(rendered, report_type, data.get("domain", "Unknown"))

    # Write to file
    output_path_obj = Path(output_path)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)

    try:
        output_path_obj.write_text(rendered, encoding="utf-8")
    except Exception as e:
        raise IOError(f"Failed to write report to {output_path}: {e}")

    # Count sections (lines starting with ##)
    sections_count = rendered.count("\n## ") + rendered.count("\n### ")

    # Get file size
    file_size = output_path_obj.stat().st_size

    return ReportResult(
        output_path=str(output_path),
        report_type=report_type,
        format=format,
        sections_count=sections_count,
        file_size_bytes=file_size,
    )


def _markdown_to_html(markdown_content: str, report_type: str, domain: str) -> str:
    """Convert Markdown report to HTML with basic styling.

    Args:
        markdown_content: Markdown content to convert
        report_type: Type of report for title
        domain: Domain name for title

    Returns:
        HTML string with basic styling
    """
    # Simple Markdown to HTML conversion
    # In production, you might use a library like markdown or mistune
    html = markdown_content

    # Convert headers
    html = html.replace("\n# ", "\n<h1>").replace("\n## ", "\n<h2>")
    html = html.replace("\n### ", "\n<h3>").replace("\n#### ", "\n<h4>")

    # Add closing tags at line breaks for headers
    lines = html.split("\n")
    html_lines = []
    for line in lines:
        if line.startswith("<h1>"):
            html_lines.append(line + "</h1>")
        elif line.startswith("<h2>"):
            html_lines.append(line + "</h2>")
        elif line.startswith("<h3>"):
            html_lines.append(line + "</h3>")
        elif line.startswith("<h4>"):
            html_lines.append(line + "</h4>")
        elif line.startswith("- "):
            html_lines.append("<li>" + line[2:] + "</li>")
        elif line.startswith("---"):
            html_lines.append("<hr>")
        elif line.startswith("**") and line.endswith("**"):
            html_lines.append("<strong>" + line[2:-2] + "</strong>")
        else:
            html_lines.append("<p>" + line + "</p>" if line.strip() else "")

    html = "\n".join(html_lines)

    # Wrap in full HTML document
    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report_type.replace('_', ' ').title()} - {domain}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
                'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;
            line-height: 1.6;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
            border-bottom: 1px solid #bdc3c7;
            padding-bottom: 5px;
        }}
        h3 {{
            color: #555;
        }}
        strong {{
            color: #2c3e50;
        }}
        li {{
            margin: 5px 0;
        }}
        hr {{
            border: none;
            border-top: 1px solid #bdc3c7;
            margin: 30px 0;
        }}
        p {{
            margin: 10px 0;
        }}
    </style>
</head>
<body>
{html}
</body>
</html>"""

    return full_html


# Export all public functions and models
__all__ = [
    "export_to_csv",
    "export_to_jsonl",
    "create_dataset",
    "get_dataset",
    "get_dataset_records",
    "get_all_datasets",
    "get_dataset_by_id",
    "export_warc_subset",
    "generate_report",
    "Dataset",
    "DatasetRecord",
    "ExportResult",
    "ReportResult",
]
