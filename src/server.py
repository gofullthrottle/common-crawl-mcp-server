"""Main MCP server for Common Crawl.

This module initializes the FastMCP server and registers all tools,
resources, and prompts for Common Crawl analysis.
"""

import asyncio
import logging
import sys
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

from .config import get_config

# Initialize configuration
config = get_config()

# Set up logging
logging.basicConfig(
    level=getattr(logging, config.server.log_level),
    format=config.server.log_format,
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP(name=config.server.server_name)


# Import core infrastructure
from .core.cache import CacheManager
from .core.cc_client import CDXClient
from .core.s3_manager import S3Manager
from .core.warc_parser import WarcParser

# Initialize core components (lazy)
_cache_manager: Optional[CacheManager] = None
_cdx_client: Optional[CDXClient] = None
_s3_manager: Optional[S3Manager] = None
_warc_parser: Optional[WarcParser] = None


def get_cache() -> CacheManager:
    """Get cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


def get_cdx_client() -> CDXClient:
    """Get CDX client instance."""
    global _cdx_client
    if _cdx_client is None:
        _cdx_client = CDXClient()
    return _cdx_client


def get_s3_manager() -> S3Manager:
    """Get S3 manager instance."""
    global _s3_manager
    if _s3_manager is None:
        _s3_manager = S3Manager()
    return _s3_manager


def get_warc_parser() -> WarcParser:
    """Get WARC parser instance."""
    global _warc_parser
    if _warc_parser is None:
        _warc_parser = WarcParser()
    return _warc_parser


# Diagnostic & monitoring tools
@mcp.tool()
def health_check() -> dict[str, Any]:
    """Check server health and configuration status.

    Returns:
        Dictionary containing health status and configuration info.
    """
    warnings = config.validate()

    return {
        "status": "healthy" if not warnings else "degraded",
        "server": {
            "name": config.server.server_name,
            "version": config.server.server_version,
        },
        "infrastructure": {
            "cdx_client": "initialized" if _cdx_client else "not initialized",
            "s3_manager": "initialized" if _s3_manager else "not initialized",
            "cache_manager": "initialized" if _cache_manager else "not initialized",
            "warc_parser": "initialized" if _warc_parser else "not initialized",
        },
        "cache": {
            "directory": str(config.cache.cache_dir),
            "max_size_gb": config.cache.cache_max_size_gb,
        },
        "redis": {
            "enabled": config.redis.redis_enabled,
        },
        "warnings": warnings,
    }


@mcp.tool()
async def cache_stats() -> dict[str, Any]:
    """Get cache statistics.

    Returns:
        Dictionary with cache hit rate, size, and other metrics.
    """
    cache = get_cache()
    return cache.get_stats()


@mcp.tool()
async def clear_cache() -> dict[str, str]:
    """Clear all cache tiers (memory, disk, Redis).

    Returns:
        Confirmation message.
    """
    cache = get_cache()
    await cache.clear()
    return {"status": "success", "message": "All cache tiers cleared"}


@mcp.tool()
async def test_cdx_connection() -> dict[str, Any]:
    """Test connectivity to Common Crawl CDX server.

    Returns:
        Connection status and available crawls.
    """
    try:
        cdx = get_cdx_client()
        crawls = await cdx.list_crawls()

        return {
            "status": "success",
            "cdx_server": config.cdx.cdx_server_url,
            "crawls_found": len(crawls),
            "latest_crawl": crawls[0].id if crawls else None,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


@mcp.tool()
async def test_s3_connection() -> dict[str, Any]:
    """Test connectivity to Common Crawl S3 bucket.

    Returns:
        Connection status and cost tracking info.
    """
    try:
        s3 = get_s3_manager()

        # Try to check if a known file exists
        test_key = "crawl-data/CC-MAIN-2024-10/cc-index.paths.gz"
        exists = await s3.file_exists(test_key)

        return {
            "status": "success",
            "bucket": config.s3.commoncrawl_bucket,
            "region": config.s3.aws_region,
            "test_file_exists": exists,
            "bytes_downloaded": s3.bytes_downloaded,
            "estimated_cost_usd": round(s3.estimated_cost_usd, 4),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


# MCP Prompts (Phase 8)
from .prompts import (competitive_analysis, content_discovery, domain_research,
                      seo_analysis)
# MCP Resources (Phase 7)
from .resources import (get_crawl_info, get_dataset_info,
                        get_dataset_records_resource, get_investigation_state,
                        list_all_crawls, list_datasets, list_investigations)
# Aggregation & Statistics Tools (Phase 5)
# HTML Parsing & Analysis Tools (Phase 4)
# Data Fetching & Extraction Tools (Phase 3)
# Discovery & Metadata Tools (Phase 2)
from .tools import aggregation, discovery, fetching, parsing


@mcp.tool()
async def list_crawls() -> dict[str, Any]:
    """List all available Common Crawl datasets.

    Returns:
        Dictionary with list of crawls and metadata.
    """
    return await discovery.list_crawls()


@mcp.tool()
async def get_crawl_stats(crawl_id: str) -> dict[str, Any]:
    """Get detailed statistics for a specific crawl.

    Args:
        crawl_id: Crawl identifier (e.g., "CC-MAIN-2024-10")

    Returns:
        Dictionary with crawl statistics and metadata.
    """
    return await discovery.get_crawl_stats(crawl_id)


@mcp.tool()
async def search_index(
    query: str,
    crawl_id: str = None,
    limit: int = 100,
    match_type: str = "exact",
) -> dict[str, Any]:
    """Search the Common Crawl index for URLs.

    Args:
        query: URL or domain to search for
        crawl_id: Specific crawl to search (None for latest)
        limit: Maximum results to return
        match_type: Match type - "exact", "prefix", "domain"

    Returns:
        Dictionary with search results.
    """
    return await discovery.search_index(query, crawl_id, limit, match_type)


@mcp.tool()
async def get_domain_stats(
    domain: str,
    crawl_id: str = None,
    sample_size: int = 1000,
) -> dict[str, Any]:
    """Get statistics about a domain's presence in Common Crawl.

    Args:
        domain: Domain to analyze (e.g., "example.com")
        crawl_id: Specific crawl to analyze (None for latest)
        sample_size: Number of pages to sample for analysis

    Returns:
        Dictionary with domain statistics.
    """
    return await discovery.get_domain_stats(domain, crawl_id, sample_size)


@mcp.tool()
async def compare_crawls(
    domain: str,
    crawl_id_1: str,
    crawl_id_2: str,
) -> dict[str, Any]:
    """Compare a domain's presence across two crawls.

    Args:
        domain: Domain to compare
        crawl_id_1: First crawl ID
        crawl_id_2: Second crawl ID

    Returns:
        Dictionary with comparison results.
    """
    return await discovery.compare_crawls(domain, crawl_id_1, crawl_id_2)


@mcp.tool()
async def fetch_page_content(
    url: str,
    crawl_id: str = None,
) -> dict[str, Any]:
    """Fetch archived page content from Common Crawl.

    Args:
        url: URL to fetch
        crawl_id: Specific crawl to fetch from (None for latest)

    Returns:
        Dictionary with page content and metadata.
    """
    return await fetching.fetch_page_content(url, crawl_id)


@mcp.tool()
async def batch_fetch_pages(
    urls: list[str],
    crawl_id: str = None,
    max_concurrent: int = 5,
) -> dict[str, Any]:
    """Fetch multiple pages in parallel.

    Args:
        urls: List of URLs to fetch
        crawl_id: Specific crawl to fetch from (None for latest)
        max_concurrent: Maximum concurrent downloads

    Returns:
        Dictionary with results for all URLs.
    """
    return await fetching.batch_fetch_pages(urls, crawl_id, max_concurrent)


@mcp.tool()
async def fetch_warc_records(
    urls: list[str],
    crawl_id: str = None,
) -> dict[str, Any]:
    """Fetch raw WARC records for URLs.

    Args:
        urls: List of URLs to fetch WARC records for
        crawl_id: Specific crawl to fetch from (None for latest)

    Returns:
        Dictionary with WARC records.
    """
    return await fetching.fetch_warc_records(urls, crawl_id)


@mcp.tool()
async def fetch_wat_metadata(
    url: str,
    crawl_id: str = None,
) -> dict[str, Any]:
    """Fetch WAT (Web Archive Transformation) metadata for a URL.

    Args:
        url: URL to fetch metadata for
        crawl_id: Specific crawl to fetch from (None for latest)

    Returns:
        Dictionary with extracted metadata.
    """
    return await fetching.fetch_wat_metadata(url, crawl_id)


@mcp.tool()
async def fetch_wet_text(
    url: str,
    crawl_id: str = None,
) -> dict[str, Any]:
    """Fetch WET (plain text) extraction for a URL.

    Args:
        url: URL to fetch plain text for
        crawl_id: Specific crawl to fetch from (None for latest)

    Returns:
        Dictionary with extracted plain text.
    """
    return await fetching.fetch_wet_text(url, crawl_id)


# Parsing & Analysis Tools
@mcp.tool()
async def parse_html(url: str, crawl_id: str = "CC-MAIN-2024-10") -> dict[str, Any]:
    """Parse HTML and extract structured data.

    Args:
        url: URL to parse
        crawl_id: Common Crawl crawl identifier

    Returns:
        Dictionary with parsed HTML data (title, meta, headings, links, text).
    """
    result = await parsing.parse_html_content(url, crawl_id)
    return result.model_dump()


@mcp.tool()
async def extract_links(url: str, crawl_id: str = "CC-MAIN-2024-10") -> dict[str, Any]:
    """Extract and analyze links from a page.

    Args:
        url: URL to analyze
        crawl_id: Common Crawl crawl identifier

    Returns:
        Dictionary with link analysis (internal/external classification).
    """
    result = await parsing.extract_links_analysis(url, crawl_id)
    return result.model_dump()


@mcp.tool()
async def analyze_technologies(url: str, crawl_id: str = "CC-MAIN-2024-10") -> dict[str, Any]:
    """Detect technologies used by a website.

    Args:
        url: URL to analyze
        crawl_id: Common Crawl crawl identifier

    Returns:
        Dictionary with detected technologies and confidence scores.
    """
    result = await parsing.analyze_technologies(url, crawl_id)
    return result.model_dump()


@mcp.tool()
async def extract_structured_data(url: str, crawl_id: str = "CC-MAIN-2024-10") -> dict[str, Any]:
    """Extract structured data (JSON-LD, Open Graph, Twitter Cards).

    Args:
        url: URL to analyze
        crawl_id: Common Crawl crawl identifier

    Returns:
        Dictionary with extracted structured data.
    """
    result = await parsing.extract_structured_data_from_page(url, crawl_id)
    return result.model_dump()


@mcp.tool()
async def analyze_seo(url: str, crawl_id: str = "CC-MAIN-2024-10") -> dict[str, Any]:
    """Analyze SEO best practices for a page.

    Args:
        url: URL to analyze
        crawl_id: Common Crawl crawl identifier

    Returns:
        Dictionary with SEO analysis, score, issues, and recommendations.
    """
    result = await parsing.analyze_seo_metrics(url, crawl_id)
    return result.model_dump()


@mcp.tool()
async def detect_language(url: str, crawl_id: str = "CC-MAIN-2024-10") -> dict[str, Any]:
    """Detect language of a page.

    Args:
        url: URL to analyze
        crawl_id: Common Crawl crawl identifier

    Returns:
        Dictionary with language detection result and confidence.
    """
    result = await parsing.detect_language(url, crawl_id)
    return result.model_dump()


# Aggregation & Statistics Tools
@mcp.tool()
async def domain_technology_report(
    domain: str, crawl_id: str = "CC-MAIN-2024-10", sample_size: int = 100
) -> dict[str, Any]:
    """Generate technology usage report for an entire domain.

    Args:
        domain: Domain to analyze (e.g., "example.com")
        crawl_id: Common Crawl crawl identifier
        sample_size: Maximum number of pages to analyze

    Returns:
        Dictionary with aggregated technology usage across domain.
    """
    result = await aggregation.domain_technology_report(domain, crawl_id, sample_size)
    return result.model_dump()


@mcp.tool()
async def domain_link_graph(
    domain: str,
    crawl_id: str = "CC-MAIN-2024-10",
    sample_size: int = 100,
    depth: int = 1,
) -> dict[str, Any]:
    """Generate link graph for an entire domain.

    Args:
        domain: Domain to analyze (e.g., "example.com")
        crawl_id: Common Crawl crawl identifier
        sample_size: Maximum number of pages to analyze
        depth: Link crawl depth (1=direct links only)

    Returns:
        Dictionary with graph structure (nodes, edges, hub pages, PageRank).
    """
    result = await aggregation.domain_link_graph(domain, crawl_id, sample_size, depth)
    return result.model_dump()


@mcp.tool()
async def keyword_frequency_analysis(
    domain: str,
    keywords: list[str],
    crawl_id: str = "CC-MAIN-2024-10",
    sample_size: int = 100,
    case_sensitive: bool = False,
) -> dict[str, Any]:
    """Analyze keyword frequency across a domain.

    Args:
        domain: Domain to analyze (e.g., "example.com")
        keywords: List of keywords to search for
        crawl_id: Common Crawl crawl identifier
        sample_size: Maximum number of pages to analyze
        case_sensitive: Whether keyword matching is case-sensitive

    Returns:
        Dictionary with keyword frequencies and TF-IDF scores.
    """
    result = await aggregation.keyword_frequency_analysis(
        domain, keywords, crawl_id, sample_size, case_sensitive
    )
    return result.model_dump()


@mcp.tool()
async def domain_evolution_timeline(
    domain: str,
    crawl_ids: list[str],
    sample_size: int = 100,
) -> dict[str, Any]:
    """Track domain evolution across multiple crawls.

    Args:
        domain: Domain to analyze (e.g., "example.com")
        crawl_ids: List of crawl IDs to compare (chronological order)
        sample_size: Maximum number of pages to analyze per crawl

    Returns:
        Dictionary with evolution metrics (page counts, technologies added/removed).
    """
    result = await aggregation.domain_evolution_timeline(domain, crawl_ids, sample_size)
    return result.model_dump()


@mcp.tool()
async def header_analysis(
    domain: str,
    crawl_id: str = "CC-MAIN-2024-10",
    sample_size: int = 100,
) -> dict[str, Any]:
    """Analyze HTTP headers across a domain.

    Args:
        domain: Domain to analyze (e.g., "example.com")
        crawl_id: Common Crawl crawl identifier
        sample_size: Maximum number of pages to analyze

    Returns:
        Dictionary with security header adoption rates and security score.
    """
    result = await aggregation.header_analysis(domain, crawl_id, sample_size)
    return result.model_dump()


# ============================================================================
# Phase 6: Export & Integration Tools
# ============================================================================


@mcp.tool()
async def export_to_csv(
    data: list[dict], output_path: str, fields: Optional[list[str]] = None
) -> dict[str, Any]:
    """Export data to CSV format with automatic field flattening.

    Args:
        data: List of dictionaries to export
        output_path: Path to output CSV file
        fields: Optional list of fields to export (auto-detected if not provided)

    Returns:
        Export statistics and file information
    """
    from .tools import export as export_tools

    result = await export_tools.export_to_csv(data, output_path, fields=fields)
    return result.model_dump()


@mcp.tool()
async def export_to_jsonl(data: list[dict], output_path: str) -> dict[str, Any]:
    """Export data to JSON Lines format.

    Args:
        data: List of dictionaries to export
        output_path: Path to output JSONL file

    Returns:
        Export statistics and file information
    """
    from .tools import export as export_tools

    result = await export_tools.export_to_jsonl(data, output_path)
    return result.model_dump()


@mcp.tool()
async def create_dataset(
    name: str,
    description: str,
    data: list[dict],
    metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Create a named dataset from query results.

    Args:
        name: Dataset name (must be unique)
        description: Dataset description
        data: List of records to store
        metadata: Optional metadata dictionary

    Returns:
        Dataset information including ID and record count
    """
    from .tools import export as export_tools

    result = await export_tools.create_dataset(name, description, data, metadata=metadata)
    return result.model_dump()


@mcp.tool()
async def generate_report(
    report_type: str,
    data: dict[str, Any],
    output_path: str,
    format: str = "markdown",
) -> dict[str, Any]:
    """Generate formatted report from analysis data.

    Args:
        report_type: Type of report ("domain_analysis", "tech_stack", "seo_audit")
        data: Report data dictionary
        output_path: Path to output file
        format: Output format ("markdown" or "html")

    Returns:
        Report generation statistics
    """
    from .tools import export as export_tools

    result = await export_tools.generate_report(report_type, data, output_path, format=format)
    return result.model_dump()


@mcp.tool()
async def export_warc_subset(urls: list[str], crawl_id: str, output_path: str) -> dict[str, Any]:
    """Export WARC records for specified URLs.

    Args:
        urls: List of URLs to export
        crawl_id: Common Crawl crawl identifier
        output_path: Path to output WARC file

    Returns:
        Export statistics including records exported and errors
    """
    from .tools import export as export_tools

    result = await export_tools.export_warc_subset(urls, crawl_id, output_path)
    return result.model_dump()


# ============================================================================
# Phase 9: Advanced Analysis Tools
# ============================================================================

from .tools import advanced


@mcp.tool()
async def classify_content(url: str, crawl_id: str = "CC-MAIN-2024-10") -> dict[str, Any]:
    """Classify web page by type and purpose.

    Detects page types: blog, product, documentation, news, landing_page, other

    Uses composition of existing analysis tools to gather classification signals
    from URL patterns, schema.org structured data, and content structure.

    Args:
        url: URL to classify
        crawl_id: Common Crawl crawl identifier

    Returns:
        Classification result with page type, confidence, and supporting signals

    Example:
        >>> result = await classify_content("https://example.com/blog/post")
        >>> print(result["page_type"])
        'blog'
    """
    result = await advanced.content_classification(url, crawl_id)
    return result.model_dump()


@mcp.tool()
async def detect_spam(url: str, crawl_id: str = "CC-MAIN-2024-10") -> dict[str, Any]:
    """Detect if page is spam or low-quality.

    Analyzes multiple quality signals including security headers, title/meta quality,
    link patterns, keyword stuffing, and technology legitimacy. Returns spam score 0-100
    where higher scores indicate more likely spam.

    Args:
        url: URL to analyze
        crawl_id: Common Crawl crawl identifier

    Returns:
        Spam analysis with score, detected signals, and recommendation

    Example:
        >>> result = await detect_spam("https://example.com")
        >>> print(result["spam_score"])
        15.0
        >>> print(result["recommendation"])
        'likely_legitimate'
    """
    result = await advanced.spam_detection(url, crawl_id)
    return result.model_dump()


@mcp.tool()
async def analyze_trends(
    domain: str, crawl_ids: list[str], sample_size: int = 100
) -> dict[str, Any]:
    """Analyze trends in domain evolution across multiple crawls.

    Tracks page count changes, technology adoption/removal trends, and generates
    insights from statistical patterns over time.

    Args:
        domain: Domain to analyze (e.g., "example.com")
        crawl_ids: List of crawl IDs in chronological order (at least 2)
        sample_size: Number of pages to sample per crawl (default: 100)

    Returns:
        Trend analysis with detected trends, rate of change, and generated insights

    Example:
        >>> result = await analyze_trends(
        ...     "example.com",
        ...     ["CC-MAIN-2024-10", "CC-MAIN-2024-18"],
        ...     sample_size=100
        ... )
        >>> print(result["insights"])
        ['Domain is growing: 25.5% increase in indexed pages']
    """
    result = await advanced.trend_analysis(domain, crawl_ids, sample_size=sample_size)
    return result.model_dump()


# ============================================================================
# Server Information
# ============================================================================


@mcp.tool()
def get_server_info() -> dict[str, Any]:
    """Get detailed server information and capabilities.

    Returns:
        Dictionary containing server capabilities and configuration.
    """
    return {
        "name": config.server.server_name,
        "version": config.server.server_version,
        "description": "MCP server for querying and analyzing Common Crawl web archive",
        "capabilities": {
            "discovery": {
                "description": "Explore available crawls and search the index",
                "tools": [
                    "list_crawls",
                    "get_crawl_stats",
                    "search_index",
                    "get_domain_stats",
                    "compare_crawls",
                    "estimate_query_size",
                ],
                "status": "planned",
            },
            "fetching": {
                "description": "Retrieve page content from archives",
                "tools": [
                    "fetch_page_content",
                    "fetch_warc_records",
                    "batch_fetch_pages",
                    "fetch_wat_metadata",
                    "fetch_wet_text",
                ],
                "status": "planned",
            },
            "parsing": {
                "description": "Parse and analyze HTML content",
                "tools": [
                    "parse_html",
                    "extract_links",
                    "analyze_technologies",
                    "extract_structured_data",
                    "analyze_seo",
                    "detect_language",
                ],
                "status": "implemented",
            },
            "aggregation": {
                "description": "Aggregate data across multiple pages",
                "tools": [
                    "domain_technology_report",
                    "domain_link_graph",
                    "keyword_frequency_analysis",
                    "domain_evolution_timeline",
                    "header_analysis",
                ],
                "status": "planned",
            },
            "export": {
                "description": "Export results to various formats",
                "tools": [
                    "export_to_csv",
                    "export_to_jsonl",
                    "create_dataset",
                    "generate_report",
                    "export_warc_subset",
                ],
                "status": "planned",
            },
        },
        "configuration": {
            "cache_enabled": True,
            "cache_size_gb": config.cache.cache_max_size_gb,
            "redis_enabled": config.redis.redis_enabled,
            "s3_bucket": config.s3.commoncrawl_bucket,
            "cdx_server": config.cdx.cdx_server_url,
        },
    }


# Resource: Server configuration
@mcp.resource("commoncrawl://server/config")
def get_server_config() -> str:
    """Get server configuration as a resource.

    Returns:
        JSON string containing server configuration.
    """
    import json

    return json.dumps(
        {
            "server": {
                "name": config.server.server_name,
                "version": config.server.server_version,
            },
            "cache": {
                "directory": str(config.cache.cache_dir),
                "max_size_gb": config.cache.cache_max_size_gb,
                "ttl_seconds": config.cache.cache_ttl_seconds,
            },
            "s3": {
                "region": config.s3.aws_region,
                "bucket": config.s3.commoncrawl_bucket,
            },
            "rate_limits": {
                "max_concurrent": config.rate_limit.max_concurrent_requests,
                "requests_per_second": config.rate_limit.requests_per_second,
            },
        },
        indent=2,
    )


def main():
    """Run the MCP server.

    This is the main entry point for the server.
    """
    logger.info(f"Starting {config.server.server_name} v{config.server.server_version}")

    # Validate configuration
    warnings = config.validate()
    if warnings:
        logger.warning("Configuration warnings:")
        for warning in warnings:
            logger.warning(f"  - {warning}")

    # Log configuration
    logger.info(f"Cache directory: {config.cache.cache_dir}")
    logger.info(f"Cache size limit: {config.cache.cache_max_size_gb}GB")
    logger.info(f"Redis enabled: {config.redis.redis_enabled}")
    logger.info(f"S3 bucket: {config.s3.commoncrawl_bucket}")
    logger.info(f"CDX server: {config.cdx.cdx_server_url}")

    # Run the server
    try:
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
