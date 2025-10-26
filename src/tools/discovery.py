"""Discovery and metadata tools for Common Crawl MCP Server.

This module provides tools for exploring Common Crawl datasets,
querying the index, and analyzing domain statistics.
"""

import json
import logging
from typing import Any, Optional

from ..config import get_config
from ..core.cache import CacheManager
from ..core.cc_client import CDXClient
from ..core.s3_manager import S3Manager
from ..models.schemas import CrawlInfo, CrawlStats, DomainStats, IndexRecord

logger = logging.getLogger(__name__)
config = get_config()


# Lazy initialization
_cache: Optional[CacheManager] = None
_cdx_client: Optional[CDXClient] = None
_s3_manager: Optional[S3Manager] = None


def _get_cache() -> CacheManager:
    """Get cache manager instance."""
    global _cache
    if _cache is None:
        from ..server import get_cache
        _cache = get_cache()
    return _cache


def _get_cdx_client() -> CDXClient:
    """Get CDX client instance."""
    global _cdx_client
    if _cdx_client is None:
        from ..server import get_cdx_client
        _cdx_client = get_cdx_client()
    return _cdx_client


def _get_s3_manager() -> S3Manager:
    """Get S3 manager instance."""
    global _s3_manager
    if _s3_manager is None:
        from ..server import get_s3_manager
        _s3_manager = get_s3_manager()
    return _s3_manager


# Tool 2.1: List Crawls
async def list_crawls() -> dict[str, Any]:
    """List all available Common Crawl datasets.

    Returns:
        Dictionary with list of crawls and metadata.

    Example:
        >>> result = await list_crawls()
        >>> print(f"Found {len(result['crawls'])} crawls")
    """
    try:
        cache = _get_cache()
        cache_key = "crawls:list"

        # Check cache (24h TTL)
        cached = await cache.get(cache_key)
        if cached:
            logger.info("Returning cached crawl list")
            return cached

        # Fetch from CDX
        cdx = _get_cdx_client()
        crawls = await cdx.list_crawls()

        # Format response
        result = {
            "count": len(crawls),
            "crawls": [
                {
                    "id": crawl.id,
                    "name": crawl.name,
                    "date": crawl.date.isoformat(),
                }
                for crawl in crawls
            ],
        }

        # Cache for 24 hours
        await cache.set(cache_key, result, ttl=24 * 3600)

        logger.info(f"Listed {len(crawls)} crawls")
        return result

    except Exception as e:
        logger.error(f"Error listing crawls: {e}")
        return {
            "error": str(e),
            "count": 0,
            "crawls": [],
        }


# Tool 2.2: Get Crawl Stats
async def get_crawl_stats(crawl_id: str) -> dict[str, Any]:
    """Get detailed statistics for a specific crawl.

    Args:
        crawl_id: Crawl identifier (e.g., "CC-MAIN-2024-10")

    Returns:
        Dictionary with crawl statistics and metadata.

    Example:
        >>> stats = await get_crawl_stats("CC-MAIN-2024-10")
        >>> print(f"Pages: {stats['num_pages']:,}")
    """
    try:
        cache = _get_cache()
        cache_key = f"crawl_stats:{crawl_id}"

        # Check cache (7 days TTL - stats don't change)
        cached = await cache.get(cache_key)
        if cached:
            logger.info(f"Returning cached stats for {crawl_id}")
            return cached

        # Fetch collinfo.json from S3
        s3 = _get_s3_manager()
        collinfo_key = f"crawl-data/{crawl_id}/collinfo.json"

        try:
            content = await s3.download_file(collinfo_key)
            stats_data = json.loads(content.decode("utf-8"))

            # Parse statistics
            result = {
                "crawl_id": crawl_id,
                "num_pages": stats_data.get("page_count", 0),
                "total_size_gb": round(stats_data.get("size", 0) / (1024**3), 2),
                "warc_files": stats_data.get("warc_file_count", 0),
                "wat_files": stats_data.get("wat_file_count", 0),
                "wet_files": stats_data.get("wet_file_count", 0),
                "metadata": stats_data,
            }

            # Cache for 7 days
            await cache.set(cache_key, result, ttl=7 * 24 * 3600)

            logger.info(f"Retrieved stats for {crawl_id}")
            return result

        except Exception as e:
            logger.warning(f"Could not fetch collinfo.json: {e}")
            # Return minimal stats
            return {
                "crawl_id": crawl_id,
                "error": f"Stats not available: {str(e)}",
                "num_pages": 0,
                "total_size_gb": 0,
            }

    except Exception as e:
        logger.error(f"Error getting crawl stats: {e}")
        return {
            "crawl_id": crawl_id,
            "error": str(e),
        }


# Tool 2.3: Search Index
async def search_index(
    query: str,
    crawl_id: Optional[str] = None,
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

    Example:
        >>> results = await search_index("example.com", match_type="domain")
        >>> print(f"Found {len(results['results'])} pages")
    """
    try:
        cache = _get_cache()
        cache_key = f"search:{query}:{crawl_id}:{limit}:{match_type}"

        # Check cache (1 hour TTL)
        cached = await cache.get(cache_key)
        if cached:
            logger.info(f"Returning cached search results for: {query}")
            return cached

        # Search CDX
        cdx = _get_cdx_client()

        # Get latest crawl if not specified
        if not crawl_id:
            crawl_id = await cdx.get_latest_crawl()

        results = await cdx.search_index(
            query=query,
            crawl_id=crawl_id,
            limit=limit,
            match_type=match_type,
        )

        # Format response
        result = {
            "query": query,
            "crawl_id": crawl_id,
            "match_type": match_type,
            "count": len(results),
            "results": [
                {
                    "url": record.url,
                    "timestamp": record.timestamp,
                    "status_code": record.status_code,
                    "mime_type": record.mime_type,
                    "length": record.length,
                    "digest": record.digest,
                    "filename": record.filename,
                    "offset": record.offset,
                }
                for record in results
            ],
        }

        # Cache for 1 hour
        await cache.set(cache_key, result, ttl=3600)

        logger.info(f"Found {len(results)} results for query: {query}")
        return result

    except Exception as e:
        logger.error(f"Error searching index: {e}")
        return {
            "query": query,
            "error": str(e),
            "count": 0,
            "results": [],
        }


# Tool 2.4: Get Domain Stats
async def get_domain_stats(
    domain: str,
    crawl_id: Optional[str] = None,
    sample_size: int = 1000,
) -> dict[str, Any]:
    """Get statistics about a domain's presence in Common Crawl.

    Args:
        domain: Domain to analyze (e.g., "example.com")
        crawl_id: Specific crawl to analyze (None for latest)
        sample_size: Number of pages to sample for analysis

    Returns:
        Dictionary with domain statistics.

    Example:
        >>> stats = await get_domain_stats("example.com")
        >>> print(f"Total pages: {stats['total_pages']}")
    """
    try:
        cache = _get_cache()
        cache_key = f"domain_stats:{domain}:{crawl_id}"

        # Check cache (6 hours TTL)
        cached = await cache.get(cache_key)
        if cached:
            logger.info(f"Returning cached domain stats for: {domain}")
            return cached

        # Search for domain
        cdx = _get_cdx_client()

        # Get latest crawl if not specified
        if not crawl_id:
            crawl_id = await cdx.get_latest_crawl()

        # Search with domain match
        results = await cdx.search_index(
            query=domain,
            crawl_id=crawl_id,
            limit=sample_size,
            match_type="domain",
        )

        # Analyze results
        subdomains = set()
        total_size = 0
        status_codes = {}
        mime_types = {}

        for record in results:
            # Extract subdomain
            url_domain = record.url.split("://")[1].split("/")[0] if "://" in record.url else record.url.split("/")[0]
            subdomains.add(url_domain)

            # Aggregate size
            total_size += record.length

            # Count status codes
            status_codes[record.status_code] = status_codes.get(record.status_code, 0) + 1

            # Count MIME types
            mime_types[record.mime_type] = mime_types.get(record.mime_type, 0) + 1

        result = {
            "domain": domain,
            "crawl_id": crawl_id,
            "total_pages": len(results),
            "unique_subdomains": len(subdomains),
            "subdomains": sorted(list(subdomains)),
            "total_size_mb": round(total_size / (1024**2), 2),
            "status_codes": status_codes,
            "mime_types": mime_types,
            "sample_size": sample_size,
            "note": f"Stats based on sample of up to {sample_size} pages" if len(results) == sample_size else "Complete domain coverage",
        }

        # Cache for 6 hours
        await cache.set(cache_key, result, ttl=6 * 3600)

        logger.info(f"Generated domain stats for: {domain}")
        return result

    except Exception as e:
        logger.error(f"Error getting domain stats: {e}")
        return {
            "domain": domain,
            "error": str(e),
        }


# Tool 2.5: Compare Crawls
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

    Example:
        >>> comparison = await compare_crawls("example.com", "CC-MAIN-2024-10", "CC-MAIN-2024-18")
        >>> print(f"Change: {comparison['change_percent']}%")
    """
    try:
        cache = _get_cache()
        cache_key = f"compare:{domain}:{crawl_id_1}:{crawl_id_2}"

        # Check cache (24 hours TTL)
        cached = await cache.get(cache_key)
        if cached:
            logger.info(f"Returning cached comparison for: {domain}")
            return cached

        # Get stats for both crawls
        stats_1 = await get_domain_stats(domain, crawl_id_1)
        stats_2 = await get_domain_stats(domain, crawl_id_2)

        # Calculate changes
        pages_1 = stats_1.get("total_pages", 0)
        pages_2 = stats_2.get("total_pages", 0)

        change = pages_2 - pages_1
        change_percent = round((change / pages_1 * 100), 2) if pages_1 > 0 else 0

        # Determine trend
        if change > 0:
            trend = "growing"
        elif change < 0:
            trend = "shrinking"
        else:
            trend = "stable"

        result = {
            "domain": domain,
            "crawl_1": {
                "id": crawl_id_1,
                "pages": pages_1,
            },
            "crawl_2": {
                "id": crawl_id_2,
                "pages": pages_2,
            },
            "change": {
                "absolute": change,
                "percent": change_percent,
                "trend": trend,
            },
        }

        # Cache for 24 hours
        await cache.set(cache_key, result, ttl=24 * 3600)

        logger.info(f"Compared {domain} across {crawl_id_1} and {crawl_id_2}")
        return result

    except Exception as e:
        logger.error(f"Error comparing crawls: {e}")
        return {
            "domain": domain,
            "error": str(e),
        }
