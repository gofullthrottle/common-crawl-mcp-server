"""MCP resource providers for Common Crawl crawl metadata.

This module provides resource providers for accessing crawl information
through the MCP resource URI scheme.
"""

import json
import logging
from typing import Any

from ..server import mcp

logger = logging.getLogger(__name__)


@mcp.resource("commoncrawl://crawl/{crawl_id}")
async def get_crawl_info(crawl_id: str) -> str:
    """Get metadata for a specific Common Crawl crawl.

    URI format: commoncrawl://crawl/CC-MAIN-2024-10

    Args:
        crawl_id: Common Crawl crawl identifier (from URI parameter)

    Returns:
        JSON string with crawl metadata

    Example:
        >>> info = await get_crawl_info("CC-MAIN-2024-10")
        >>> data = json.loads(info)
        >>> print(data["crawl_id"])
        CC-MAIN-2024-10
    """
    try:
        logger.info(f"Fetching crawl info for: {crawl_id}")

        # Import discovery tools to avoid circular imports
        from ..tools import discovery

        # Use existing list_crawls tool to get all crawls
        crawls_result = await discovery.list_crawls()

        # Find matching crawl
        matching_crawl = next(
            (c for c in crawls_result.get("crawls", []) if c["id"] == crawl_id),
            None,
        )

        if not matching_crawl:
            logger.warning(f"Crawl not found: {crawl_id}")
            return json.dumps(
                {
                    "error": f"Crawl not found: {crawl_id}",
                    "available_crawls": [c["id"] for c in crawls_result.get("crawls", [])[:5]],
                },
                indent=2,
            )

        # Get detailed stats for the crawl
        stats_result = await discovery.get_crawl_stats(crawl_id)

        # Build comprehensive crawl info
        info = {
            "crawl_id": matching_crawl["id"],
            "name": matching_crawl["name"],
            "date": matching_crawl["date"],
            "cdx_api": f"https://index.commoncrawl.org/{crawl_id}-index",
            "s3_prefix": f"s3://commoncrawl/crawl-data/{crawl_id}/",
            "http_prefix": f"https://data.commoncrawl.org/crawl-data/{crawl_id}/",
            "estimated_pages": stats_result.get("num_pages", "billions"),
            "total_size_gb": stats_result.get("total_size_gb", 0),
            "warc_files": stats_result.get("warc_files", 0),
            "wat_files": stats_result.get("wat_files", 0),
            "wet_files": stats_result.get("wet_files", 0),
            "formats_available": ["WARC", "WAT", "WET"],
        }

        logger.info(f"Successfully retrieved info for crawl: {crawl_id}")
        return json.dumps(info, indent=2)

    except Exception as e:
        logger.error(f"Error fetching crawl info: {e}", exc_info=True)
        return json.dumps(
            {
                "error": f"Failed to fetch crawl info: {str(e)}",
                "crawl_id": crawl_id if "crawl_id" in locals() else "unknown",
            },
            indent=2,
        )


@mcp.resource("commoncrawl://crawls")
async def list_all_crawls() -> str:
    """List all available Common Crawl crawls.

    URI format: commoncrawl://crawls

    Returns:
        JSON string with crawls list

    Example:
        >>> info = await list_all_crawls("commoncrawl://crawls")
        >>> data = json.loads(info)
        >>> print(f"Total crawls: {data['total_crawls']}")
    """
    try:
        logger.info("Fetching list of all crawls")

        # Import discovery tools to avoid circular imports
        from ..tools import discovery

        # Use existing list_crawls tool
        crawls_result = await discovery.list_crawls()

        # Build resource info
        crawls = crawls_result.get("crawls", [])
        info = {
            "total_crawls": len(crawls),
            "latest_crawl": crawls[0]["id"] if crawls else None,
            "crawls": [
                {
                    "id": crawl["id"],
                    "name": crawl["name"],
                    "date": crawl["date"],
                }
                for crawl in crawls
            ],
        }

        logger.info(f"Successfully listed {len(crawls)} crawls")
        return json.dumps(info, indent=2)

    except Exception as e:
        logger.error(f"Error listing crawls: {e}", exc_info=True)
        return json.dumps(
            {
                "error": f"Failed to list crawls: {str(e)}",
                "total_crawls": 0,
                "crawls": [],
            },
            indent=2,
        )
