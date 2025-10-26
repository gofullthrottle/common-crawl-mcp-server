# Wave 1: Export Tools (Phase 6)
**Agents:** 5 parallel agents
**Dependencies:** None - uses existing Pydantic models
**Estimated Time:** 4-6 hours total
**Expected Output:** `src/tools/export.py` with 5 MCP tools + tests

## Agent 1: export_to_csv

### Objective
Create a streaming CSV export tool that converts any Pydantic model results to CSV format.

### Specification

**Function Signature:**
```python
async def export_to_csv(
    data: list[dict[str, Any]],
    output_path: str,
    *,
    fields: Optional[list[str]] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> ExportResult:
    """Export data to CSV format with streaming."""
```

**Pydantic Models:**
```python
class ExportResult(BaseModel):
    """Result of export operation."""
    output_path: str
    format: str
    records_exported: int
    file_size_bytes: int
    duration_seconds: float
    errors: list[str] = []
```

**Requirements:**
1. Use Python's `csv.DictWriter` for streaming
2. Auto-detect fields from first record if not specified
3. Handle nested dictionaries by flattening (e.g., `{"meta": {"title": "X"}}` → `meta.title`)
4. Support progress callbacks every 100 records
5. Handle missing fields gracefully (empty string)
6. Return ExportResult with statistics

**Implementation Pattern:**
```python
import csv
from pathlib import Path
import time

async def export_to_csv(...):
    start_time = time.time()
    errors = []

    # Auto-detect fields
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
                writer.writerow(flattened)

                if progress_callback and (i + 1) % 100 == 0:
                    progress_callback(i + 1, len(data))
            except Exception as e:
                errors.append(f"Row {i}: {str(e)}")

    file_size = output_path_obj.stat().st_size
    duration = time.time() - start_time

    return ExportResult(...)

def _flatten_dict(d: dict, parent_key: str = "", sep: str = ".") -> dict:
    """Flatten nested dictionary."""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(_flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)
```

**MCP Tool Registration:**
```python
@mcp.tool()
async def export_to_csv_tool(
    data: list[dict],
    output_path: str,
    fields: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Export data to CSV format.

    Args:
        data: List of dictionaries to export
        output_path: Path to output CSV file
        fields: Optional list of fields to export (auto-detected if not provided)

    Returns:
        Export statistics and file info
    """
    result = await export_to_csv(data, output_path, fields=fields)
    return result.model_dump()
```

**Testing:**
```python
@pytest.mark.asyncio
async def test_export_to_csv():
    data = [
        {"url": "https://example.com", "title": "Example", "meta": {"description": "Test"}},
        {"url": "https://test.com", "title": "Test", "meta": {"description": "Demo"}},
    ]

    result = await export_to_csv(data, "/tmp/test.csv")

    assert result.records_exported == 2
    assert result.format == "csv"
    assert Path("/tmp/test.csv").exists()

    # Verify CSV content
    with open("/tmp/test.csv") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 2
        assert rows[0]["meta.description"] == "Test"
```

---

## Agent 2: export_to_jsonl

### Objective
Create a streaming JSONL export tool for Pydantic model results.

### Specification

**Function Signature:**
```python
async def export_to_jsonl(
    data: list[dict[str, Any]],
    output_path: str,
    *,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> ExportResult:
    """Export data to JSONL format with streaming."""
```

**Requirements:**
1. Use `jsonlines` library for line-by-line writing
2. Each record on a separate line (JSON Lines format)
3. Support progress callbacks every 100 records
4. Preserve nested structure (no flattening needed)
5. Handle JSON serialization errors gracefully

**Implementation Pattern:**
```python
import jsonlines
from pathlib import Path
import time

async def export_to_jsonl(...):
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
```

**Testing:**
```python
@pytest.mark.asyncio
async def test_export_to_jsonl():
    data = [
        {"url": "https://example.com", "meta": {"title": "Example"}},
        {"url": "https://test.com", "meta": {"title": "Test"}},
    ]

    result = await export_to_jsonl(data, "/tmp/test.jsonl")

    assert result.records_exported == 2
    assert result.format == "jsonl"

    # Verify JSONL content
    with jsonlines.open("/tmp/test.jsonl") as reader:
        rows = list(reader)
        assert len(rows) == 2
        assert rows[0]["meta"]["title"] == "Example"
```

---

## Agent 3: create_dataset

### Objective
Implement SQLite-based dataset storage for saving query results.

### Specification

**Function Signature:**
```python
async def create_dataset(
    name: str,
    description: str,
    data: list[dict[str, Any]],
    *,
    metadata: Optional[dict[str, Any]] = None,
) -> Dataset:
    """Create a named dataset from query results."""
```

**Pydantic Models:**
```python
class Dataset(BaseModel):
    """Saved dataset information."""
    id: str  # UUID
    name: str
    description: str
    created_at: datetime
    records_count: int
    metadata: dict[str, Any] = {}

class DatasetRecord(BaseModel):
    """Individual record in a dataset."""
    id: str
    dataset_id: str
    data: dict[str, Any]
    created_at: datetime
```

**Database Schema:**
```sql
-- src/data/schema.sql
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

CREATE INDEX IF NOT EXISTS idx_dataset_records_dataset_id
ON dataset_records(dataset_id);
```

**Implementation Pattern:**
```python
import sqlite3
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone

# Database path from config
DB_PATH = Path("./data/commoncrawl.db")

async def create_dataset(...):
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    dataset_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create tables if not exist
    cursor.executescript(SCHEMA_SQL)

    # Insert dataset
    cursor.execute(
        """INSERT INTO datasets (id, name, description, records_count, metadata, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (dataset_id, name, description, len(data), json.dumps(metadata or {}), created_at),
    )

    # Insert records
    for record_data in data:
        record_id = str(uuid.uuid4())
        cursor.execute(
            """INSERT INTO dataset_records (id, dataset_id, data, created_at)
               VALUES (?, ?, ?, ?)""",
            (record_id, dataset_id, json.dumps(record_data), created_at),
        )

    conn.commit()
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
    """Retrieve dataset by name."""
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
        created_at=row[3],
        records_count=row[4],
        metadata=json.loads(row[5]),
    )

async def get_dataset_records(dataset_id: str) -> list[dict]:
    """Retrieve all records from a dataset."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    rows = cursor.execute(
        "SELECT data FROM dataset_records WHERE dataset_id = ? ORDER BY created_at",
        (dataset_id,),
    ).fetchall()

    conn.close()

    return [json.loads(row[0]) for row in rows]
```

**Testing:**
```python
@pytest.mark.asyncio
async def test_create_dataset():
    data = [
        {"url": "https://example.com", "title": "Example"},
        {"url": "https://test.com", "title": "Test"},
    ]

    dataset = await create_dataset(
        name="test_dataset",
        description="Test dataset for unit tests",
        data=data,
        metadata={"source": "test"},
    )

    assert dataset.name == "test_dataset"
    assert dataset.records_count == 2

    # Retrieve dataset
    retrieved = await get_dataset("test_dataset")
    assert retrieved.id == dataset.id

    # Retrieve records
    records = await get_dataset_records(dataset.id)
    assert len(records) == 2
    assert records[0]["url"] == "https://example.com"
```

---

## Agent 4: generate_report

### Objective
Create Markdown/HTML report generator for analysis results.

### Specification

**Function Signature:**
```python
async def generate_report(
    report_type: str,
    data: dict[str, Any],
    output_path: str,
    *,
    format: str = "markdown",
) -> ReportResult:
    """Generate formatted report from analysis data."""
```

**Pydantic Models:**
```python
class ReportResult(BaseModel):
    """Result of report generation."""
    output_path: str
    report_type: str
    format: str
    sections_count: int
    file_size_bytes: int
```

**Supported Report Types:**
1. **domain_analysis** - comprehensive domain overview
2. **tech_stack** - technology report
3. **seo_audit** - SEO analysis
4. **link_analysis** - link graph report

**Requirements:**
1. Use Jinja2 templates for formatting
2. Support both Markdown and HTML output
3. Include generated timestamp
4. Auto-format large numbers (1000 → "1,000")
5. Create visualizations for numerical data (ASCII charts for Markdown)

**Implementation Pattern:**
```python
from jinja2 import Template
from pathlib import Path
import time

DOMAIN_ANALYSIS_TEMPLATE = """
# Domain Analysis Report: {{ domain }}
**Generated:** {{ timestamp }}

## Overview
- **Total Pages Analyzed:** {{ pages_analyzed }}
- **Crawl:** {{ crawl_id }}

## Technologies Detected
{% for tech, adoption in technologies.items() %}
- **{{ tech }}**: {{ adoption }}% adoption
{% endfor %}

## Link Graph
- **Total Pages:** {{ link_graph.total_pages }}
- **Total Links:** {{ link_graph.total_links }}
- **Hub Pages:**
{% for page, inbound in link_graph.hub_pages[:10] %}
  - {{ page }} ({{ inbound }} inbound links)
{% endfor %}

## Security Headers
- **Security Score:** {{ security_score }}/100
- **Headers Adoption:**
{% for header, adoption in security_headers.items() %}
  - {{ header }}: {{ adoption }}%
{% endfor %}
"""

async def generate_report(...):
    from datetime import datetime, timezone

    # Select template based on report_type
    if report_type == "domain_analysis":
        template = Template(DOMAIN_ANALYSIS_TEMPLATE)
    elif report_type == "tech_stack":
        template = Template(TECH_STACK_TEMPLATE)
    # ... other templates

    # Render report
    rendered = template.render(
        timestamp=datetime.now(timezone.utc).isoformat(),
        **data,
    )

    # Write to file
    output_path_obj = Path(output_path)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)
    output_path_obj.write_text(rendered, encoding="utf-8")

    return ReportResult(
        output_path=str(output_path),
        report_type=report_type,
        format=format,
        sections_count=rendered.count("##"),
        file_size_bytes=output_path_obj.stat().st_size,
    )
```

---

## Agent 5: export_warc_subset

### Objective
Create WARC file subset from CDX results.

### Specification

**Function Signature:**
```python
async def export_warc_subset(
    urls: list[str],
    crawl_id: str,
    output_path: str,
    *,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> ExportResult:
    """Export WARC records for specified URLs."""
```

**Requirements:**
1. Use `warcio` library for WARC creation
2. Query CDX API for each URL to get WARC locations
3. Download WARC records from S3/HTTP
4. Write combined WARC file
5. Support progress callbacks
6. Optional: Upload to MinIO if configured

**Implementation Pattern:**
```python
from warcio.warcwriter import WARCWriter
from warcio.statusandheaders import StatusAndHeaders
import io

async def export_warc_subset(...):
    from ..core.cdx_client import CDXClient
    from ..core.s3_manager import S3Manager

    cdx = CDXClient()
    s3 = S3Manager()

    output_path_obj = Path(output_path)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)

    errors = []
    records_written = 0

    with output_path_obj.open("wb") as output:
        writer = WARCWriter(output, gzip=True)

        for i, url in enumerate(urls):
            try:
                # Get CDX record
                cdx_results = await cdx.search_index(
                    query=url, crawl_id=crawl_id, limit=1, match_type="exact"
                )

                if not cdx_results.results:
                    errors.append(f"URL not found: {url}")
                    continue

                record = cdx_results.results[0]
                warc_path = record.filename
                offset = record.offset
                length = record.length

                # Download WARC record
                warc_data = await s3.download_file(warc_path)

                # Extract record at offset
                # ... WARC parsing logic ...

                # Write to output WARC
                writer.write_record(warc_record)
                records_written += 1

                if progress_callback:
                    progress_callback(i + 1, len(urls))

            except Exception as e:
                errors.append(f"URL {url}: {str(e)}")

    return ExportResult(
        output_path=str(output_path),
        format="warc",
        records_exported=records_written,
        file_size_bytes=output_path_obj.stat().st_size,
        duration_seconds=0.0,
        errors=errors,
    )
```

---

## Integration Requirements

**File:** `src/tools/export.py`

**Module Structure:**
```python
"""Export and integration tools for Common Crawl MCP Server."""

import csv
import json
import jsonlines
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from pydantic import BaseModel

# Export all public functions
__all__ = [
    "export_to_csv",
    "export_to_jsonl",
    "create_dataset",
    "get_dataset",
    "get_dataset_records",
    "generate_report",
    "export_warc_subset",
    "ExportResult",
    "Dataset",
    "ReportResult",
]
```

**MCP Server Registration:**
Add to `src/server.py`:
```python
from .tools import export

@mcp.tool()
async def export_to_csv(
    data: list[dict], output_path: str, fields: Optional[list[str]] = None
) -> dict:
    result = await export.export_to_csv(data, output_path, fields=fields)
    return result.model_dump()

# ... register other 4 tools
```

**Dependencies to Add:**
```toml
# pyproject.toml
dependencies = [
    # ... existing ...
    "jsonlines>=4.0.0",
    "jinja2>=3.1.0",
    "warcio>=1.7.4",
]
```

## Testing Requirements

**File:** `tests/integration/test_export_tools.py`

**Test Coverage:**
- [ ] test_export_to_csv_basic
- [ ] test_export_to_csv_nested_data
- [ ] test_export_to_csv_custom_fields
- [ ] test_export_to_jsonl_basic
- [ ] test_export_to_jsonl_large_dataset
- [ ] test_create_dataset_basic
- [ ] test_get_dataset_and_records
- [ ] test_generate_report_domain_analysis
- [ ] test_generate_report_markdown_and_html
- [ ] test_export_warc_subset (may need mocking)

## Acceptance Criteria

- [ ] All 5 tools implemented and tested
- [ ] CSV exports produce valid, parseable CSV files
- [ ] JSONL exports produce valid JSON Lines format
- [ ] create_dataset persists data to SQLite correctly
- [ ] get_dataset and get_dataset_records retrieve data correctly
- [ ] generate_report produces readable Markdown reports
- [ ] export_warc_subset creates valid WARC files (if WARC access works)
- [ ] All tools registered with MCP server
- [ ] Integration tests pass
- [ ] Memory usage remains reasonable for 1000+ record exports
