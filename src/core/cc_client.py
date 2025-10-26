"""Common Crawl CDX Server API client.

This module provides a client for interacting with the Common Crawl CDX Server API
to search the index and retrieve metadata about archived pages.

CDX API Documentation: https://index.commoncrawl.org/
"""

import asyncio
import logging
from datetime import datetime
from typing import AsyncIterator, Optional
from urllib.parse import quote, urlencode

import httpx

from ..config import get_config
from ..models.schemas import CrawlInfo, CrawlStatus, IndexRecord

logger = logging.getLogger(__name__)
config = get_config()


class CDXClient:
    """Client for Common Crawl CDX Server API.

    The CDX Server provides an index of URLs captured in Common Crawl crawls.
    This client handles queries, pagination, and rate limiting.
    """

    def __init__(self):
        """Initialize the CDX client."""
        self.base_url = config.cdx.cdx_server_url
        self.timeout = config.cdx.cdx_timeout_seconds
        self.max_results = config.cdx.cdx_max_results

        # HTTP client with connection pooling
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            limits=httpx.Limits(
                max_keepalive_connections=config.rate_limit.max_concurrent_requests,
                max_connections=config.rate_limit.max_concurrent_requests * 2,
            ),
        )

        # Rate limiting
        self._rate_limiter = asyncio.Semaphore(config.rate_limit.max_concurrent_requests)
        self._last_request_time = 0.0

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def _rate_limited_request(
        self, url: str, params: Optional[dict] = None
    ) -> httpx.Response:
        """Make a rate-limited HTTP request.

        Args:
            url: URL to request
            params: Query parameters

        Returns:
            HTTP response

        Raises:
            httpx.HTTPError: If request fails
        """
        async with self._rate_limiter:
            # Enforce requests per second limit
            current_time = asyncio.get_event_loop().time()
            time_since_last = current_time - self._last_request_time
            min_interval = 1.0 / config.rate_limit.requests_per_second

            if time_since_last < min_interval:
                await asyncio.sleep(min_interval - time_since_last)

            try:
                response = await self.client.get(url, params=params)
                response.raise_for_status()
                self._last_request_time = asyncio.get_event_loop().time()
                return response
            except httpx.HTTPError as e:
                logger.error(f"HTTP error querying CDX: {e}")
                raise

    async def list_crawls(self) -> list[CrawlInfo]:
        """List all available Common Crawl crawls.

        Returns:
            List of crawl information.
        """
        url = f"{self.base_url}/collinfo.json"

        try:
            response = await self._rate_limited_request(url)
            data = response.json()

            crawls = []
            for crawl_data in data:
                crawl_id = crawl_data.get("id", "")

                # Parse date from crawl ID (e.g., CC-MAIN-2024-10)
                try:
                    # Extract year and week number
                    parts = crawl_id.split("-")
                    if len(parts) >= 3:
                        year = int(parts[2])
                        week = int(parts[3]) if len(parts) > 3 else 1
                        # Approximate date (first day of year + week offset)
                        crawl_date = datetime(year, 1, 1) + timedelta(weeks=week - 1)
                    else:
                        crawl_date = datetime.now()
                except (ValueError, IndexError):
                    crawl_date = datetime.now()

                crawls.append(
                    CrawlInfo(
                        id=crawl_id,
                        name=crawl_data.get("name", crawl_id),
                        date=crawl_date,
                        status=CrawlStatus.COMPLETE,  # All listed crawls are complete
                    )
                )

            logger.info(f"Retrieved {len(crawls)} crawls from CDX server")
            return crawls

        except Exception as e:
            logger.error(f"Error listing crawls: {e}")
            return []

    async def search_index(
        self,
        query: str,
        crawl_id: Optional[str] = None,
        limit: int = 100,
        match_type: str = "exact",
    ) -> list[IndexRecord]:
        """Search the CDX index for URLs matching a query.

        Args:
            query: URL or domain to search for (e.g., "example.com", "example.com/*")
            crawl_id: Specific crawl to search (e.g., "CC-MAIN-2024-10"), or None for all
            limit: Maximum results to return
            match_type: "exact", "prefix", "domain", or "range"

        Returns:
            List of index records matching the query.
        """
        # Build CDX query URL
        if crawl_id:
            url = f"{self.base_url}/{crawl_id}-index"
        else:
            url = f"{self.base_url}/CC-MAIN-2024-10-index"  # Default to recent crawl

        params = {
            "url": query,
            "output": "json",
            "limit": min(limit, self.max_results),
        }

        # Add match type if not exact
        if match_type != "exact":
            params["matchType"] = match_type

        try:
            response = await self._rate_limited_request(url, params=params)
            lines = response.text.strip().split("\n")

            records = []
            for line in lines:
                if not line:
                    continue

                try:
                    data = httpx._utils.json.loads(line)

                    # Parse CDX format
                    # Format: [urlkey, timestamp, original_url, mime_type, status_code,
                    #          digest, length, offset, filename]
                    if len(data) >= 9:
                        records.append(
                            IndexRecord(
                                url=data[2],
                                mime_type=data[3],
                                status_code=int(data[4]),
                                digest=data[5],
                                timestamp=data[1],
                                length=int(data[6]),
                                offset=int(data[7]),
                                filename=data[8],
                            )
                        )
                except Exception as e:
                    logger.warning(f"Error parsing CDX record: {e}")
                    continue

            logger.info(f"Found {len(records)} index records for query: {query}")
            return records

        except Exception as e:
            logger.error(f"Error searching index: {e}")
            return []

    async def get_domain_urls(
        self,
        domain: str,
        crawl_id: str,
        limit: Optional[int] = None,
    ) -> AsyncIterator[IndexRecord]:
        """Get all URLs from a domain, paginated.

        Args:
            domain: Domain to query (e.g., "example.com")
            crawl_id: Crawl identifier
            limit: Maximum results (None for all)

        Yields:
            Index records for the domain.
        """
        page_size = 1000
        fetched = 0

        # Use domain match to get all URLs from domain
        query = f"*.{domain}/*"

        url = f"{self.base_url}/{crawl_id}-index"
        params = {
            "url": query,
            "output": "json",
            "matchType": "domain",
            "limit": page_size,
        }

        page = 0
        while True:
            if limit and fetched >= limit:
                break

            params["page"] = page

            try:
                response = await self._rate_limited_request(url, params=params)
                lines = response.text.strip().split("\n")

                if not lines or lines == [""]:
                    break

                for line in lines:
                    if not line:
                        continue

                    try:
                        data = httpx._utils.json.loads(line)
                        if len(data) >= 9:
                            record = IndexRecord(
                                url=data[2],
                                mime_type=data[3],
                                status_code=int(data[4]),
                                digest=data[5],
                                timestamp=data[1],
                                length=int(data[6]),
                                offset=int(data[7]),
                                filename=data[8],
                            )
                            yield record
                            fetched += 1

                            if limit and fetched >= limit:
                                return

                    except Exception as e:
                        logger.warning(f"Error parsing CDX record: {e}")
                        continue

                page += 1

            except Exception as e:
                logger.error(f"Error fetching page {page}: {e}")
                break

    async def get_latest_crawl(self) -> Optional[str]:
        """Get the ID of the most recent crawl.

        Returns:
            Crawl ID (e.g., "CC-MAIN-2024-10") or None.
        """
        crawls = await self.list_crawls()
        if not crawls:
            return None

        # Sort by date and return most recent
        crawls.sort(key=lambda c: c.date, reverse=True)
        return crawls[0].id


# Import timedelta for date calculations
from datetime import timedelta
