"""Data fetching and extraction tools for Common Crawl MCP Server.

This module provides tools for fetching actual page content and WARC records
from Common Crawl's S3 archive.
"""

import asyncio
import io
import logging
from typing import Any, Optional

from ..config import get_config
from ..core.cache import CacheManager
from ..core.cc_client import CDXClient
from ..core.s3_manager import S3Manager
from ..core.warc_parser import WarcParser
from ..models.schemas import IndexRecord, PageContent

logger = logging.getLogger(__name__)
config = get_config()


# Lazy initialization
_cache: Optional[CacheManager] = None
_cdx_client: Optional[CDXClient] = None
_s3_manager: Optional[S3Manager] = None
_warc_parser: Optional[WarcParser] = None


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


def _get_warc_parser() -> WarcParser:
    """Get WARC parser instance."""
    global _warc_parser
    if _warc_parser is None:
        from ..server import get_warc_parser
        _warc_parser = get_warc_parser()
    return _warc_parser


# Tool 3.1: Fetch Page Content
async def fetch_page_content(
    url: str,
    crawl_id: Optional[str] = None,
) -> dict[str, Any]:
    """Fetch archived page content from Common Crawl.

    Args:
        url: URL to fetch
        crawl_id: Specific crawl to fetch from (None for latest)

    Returns:
        Dictionary with page content and metadata.

    Example:
        >>> page = await fetch_page_content("https://example.com")
        >>> print(page['html'][:100])
    """
    try:
        cache = _get_cache()
        cache_key = f"page:{url}:{crawl_id}"

        # Check cache
        cached = await cache.get(cache_key)
        if cached:
            logger.info(f"Returning cached page for: {url}")
            return cached

        # Step 1: Query CDX index to find URL
        cdx = _get_cdx_client()

        if not crawl_id:
            crawl_id = await cdx.get_latest_crawl()

        results = await cdx.search_index(
            query=url,
            crawl_id=crawl_id,
            limit=1,
            match_type="exact",
        )

        if not results:
            return {
                "url": url,
                "crawl_id": crawl_id,
                "error": "URL not found in index",
            }

        record = results[0]

        # Step 2: Download WARC file from S3
        s3 = _get_s3_manager()
        warc_path = record.filename

        # Download only the relevant segment using byte range
        # WARC files can be 1GB+, so we use range requests
        start_offset = record.offset
        end_offset = start_offset + record.length

        logger.info(f"Downloading WARC segment: {warc_path} bytes {start_offset}-{end_offset}")

        # For now, download the full file (TODO: implement range requests)
        warc_content = await s3.download_and_decompress(warc_path)

        # Step 3: Parse WARC to extract HTTP response
        parser = _get_warc_parser()
        warc_record = parser.find_record_by_url(warc_content, url)

        if not warc_record:
            return {
                "url": url,
                "crawl_id": crawl_id,
                "error": "WARC record not found",
            }

        # Step 4: Extract HTTP response
        http_response = parser.extract_http_response(warc_record)

        if not http_response:
            return {
                "url": url,
                "crawl_id": crawl_id,
                "error": "Could not extract HTTP response",
            }

        # Step 5: Format response
        result = {
            "url": url,
            "crawl_id": crawl_id,
            "status_code": http_response["status_code"],
            "headers": http_response["headers"],
            "html": http_response["body"],
            "mime_type": record.mime_type,
            "timestamp": record.timestamp,
            "length": record.length,
        }

        # Cache for 24 hours
        await cache.set(cache_key, result, ttl=24 * 3600)

        logger.info(f"Fetched page content for: {url}")
        return result

    except Exception as e:
        logger.error(f"Error fetching page content: {e}")
        return {
            "url": url,
            "error": str(e),
        }


# Tool 3.2: Batch Fetch Pages
async def batch_fetch_pages(
    urls: list[str],
    crawl_id: Optional[str] = None,
    max_concurrent: int = 5,
) -> dict[str, Any]:
    """Fetch multiple pages in parallel.

    Args:
        urls: List of URLs to fetch
        crawl_id: Specific crawl to fetch from (None for latest)
        max_concurrent: Maximum concurrent downloads

    Returns:
        Dictionary with results for all URLs.

    Example:
        >>> urls = ["https://example.com", "https://example.org"]
        >>> results = await batch_fetch_pages(urls)
        >>> print(f"Fetched {results['successful']} pages")
    """
    try:
        semaphore = asyncio.Semaphore(max_concurrent)

        async def fetch_with_semaphore(url: str) -> tuple[str, dict]:
            async with semaphore:
                result = await fetch_page_content(url, crawl_id)
                return url, result

        # Fetch all pages in parallel
        tasks = [fetch_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks)

        # Organize results
        pages = {}
        successful = 0
        failed = 0

        for url, result in results:
            pages[url] = result
            if "error" in result:
                failed += 1
            else:
                successful += 1

        logger.info(f"Batch fetch: {successful} successful, {failed} failed")

        return {
            "total": len(urls),
            "successful": successful,
            "failed": failed,
            "pages": pages,
        }

    except Exception as e:
        logger.error(f"Error in batch fetch: {e}")
        return {
            "total": len(urls),
            "error": str(e),
            "pages": {},
        }


# Tool 3.3: Fetch WARC Records
async def fetch_warc_records(
    urls: list[str],
    crawl_id: Optional[str] = None,
) -> dict[str, Any]:
    """Fetch raw WARC records for URLs.

    Args:
        urls: List of URLs to fetch WARC records for
        crawl_id: Specific crawl to fetch from (None for latest)

    Returns:
        Dictionary with WARC records.

    Example:
        >>> records = await fetch_warc_records(["https://example.com"])
        >>> print(records['records'][0]['record_type'])
    """
    try:
        cdx = _get_cdx_client()
        s3 = _get_s3_manager()
        parser = _get_warc_parser()

        if not crawl_id:
            crawl_id = await cdx.get_latest_crawl()

        records = []

        for url in urls:
            try:
                # Find URL in index
                index_results = await cdx.search_index(
                    query=url,
                    crawl_id=crawl_id,
                    limit=1,
                    match_type="exact",
                )

                if not index_results:
                    records.append({
                        "url": url,
                        "error": "Not found in index",
                    })
                    continue

                index_record = index_results[0]

                # Download WARC
                warc_content = await s3.download_and_decompress(index_record.filename)

                # Parse WARC
                warc_record = parser.find_record_by_url(warc_content, url)

                if not warc_record:
                    records.append({
                        "url": url,
                        "error": "WARC record not found",
                    })
                    continue

                # Add record
                records.append({
                    "url": url,
                    "record_id": warc_record.record_id,
                    "record_type": warc_record.record_type,
                    "content_type": warc_record.content_type,
                    "content_length": warc_record.content_length,
                    "date": warc_record.date.isoformat(),
                    "http_headers": warc_record.http_headers,
                    "payload_size": len(warc_record.payload) if warc_record.payload else 0,
                })

            except Exception as e:
                logger.error(f"Error fetching WARC for {url}: {e}")
                records.append({
                    "url": url,
                    "error": str(e),
                })

        return {
            "crawl_id": crawl_id,
            "count": len(records),
            "records": records,
        }

    except Exception as e:
        logger.error(f"Error fetching WARC records: {e}")
        return {
            "error": str(e),
            "records": [],
        }


# Tool 3.4a: Fetch WAT Metadata
async def fetch_wat_metadata(
    url: str,
    crawl_id: Optional[str] = None,
) -> dict[str, Any]:
    """Fetch WAT (Web Archive Transformation) metadata for a URL.

    WAT files contain extracted metadata like links, images, and page structure.

    Args:
        url: URL to fetch metadata for
        crawl_id: Specific crawl to fetch from (None for latest)

    Returns:
        Dictionary with extracted metadata.
    """
    try:
        # WAT files are parallel to WARC files
        # Path: crawl-data/CC-MAIN-YYYY-WW/segments/.../warc/....warc.gz
        # Becomes: crawl-data/CC-MAIN-YYYY-WW/segments/.../wat/....warc.wat.gz

        return {
            "url": url,
            "crawl_id": crawl_id,
            "note": "WAT metadata extraction not yet implemented",
            "status": "planned",
        }

    except Exception as e:
        logger.error(f"Error fetching WAT metadata: {e}")
        return {
            "url": url,
            "error": str(e),
        }


# Tool 3.4b: Fetch WET Text
async def fetch_wet_text(
    url: str,
    crawl_id: Optional[str] = None,
) -> dict[str, Any]:
    """Fetch WET (plain text) extraction for a URL.

    WET files contain plain text extracted from HTML pages.

    Args:
        url: URL to fetch plain text for
        crawl_id: Specific crawl to fetch from (None for latest)

    Returns:
        Dictionary with extracted plain text.
    """
    try:
        # WET files are parallel to WARC files
        # Path: crawl-data/CC-MAIN-YYYY-WW/segments/.../warc/....warc.gz
        # Becomes: crawl-data/CC-MAIN-YYYY-WW/segments/.../wet/....warc.wet.gz

        return {
            "url": url,
            "crawl_id": crawl_id,
            "note": "WET text extraction not yet implemented",
            "status": "planned",
        }

    except Exception as e:
        logger.error(f"Error fetching WET text: {e}")
        return {
            "url": url,
            "error": str(e),
        }
