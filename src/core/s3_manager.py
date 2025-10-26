"""S3 Manager for Common Crawl data access.

This module provides efficient access to Common Crawl's S3 bucket,
handling downloads, streaming, and cost tracking.

Common Crawl S3 Bucket: s3://commoncrawl/ (public, us-east-1)
"""

import asyncio
import gzip
import logging
from pathlib import Path
from typing import AsyncIterator, Callable, Optional

import boto3
from botocore import UNSIGNED
from botocore.client import Config
from botocore.exceptions import ClientError

from ..config import get_config

logger = logging.getLogger(__name__)
config = get_config()


class S3Manager:
    """Manage S3 access to Common Crawl bucket.

    Provides efficient downloading and streaming of WARC/WAT/WET files
    with automatic gzip decompression and progress tracking.
    """

    def __init__(self):
        """Initialize S3 client for Common Crawl."""
        # Use anonymous access for public Common Crawl bucket
        if config.s3.use_anonymous_access:
            self.client = boto3.client(
                "s3",
                region_name=config.s3.aws_region,
                config=Config(signature_version=UNSIGNED),
            )
        else:
            # Use provided credentials
            self.client = boto3.client(
                "s3",
                region_name=config.s3.aws_region,
                aws_access_key_id=config.s3.aws_access_key_id,
                aws_secret_access_key=config.s3.aws_secret_access_key,
            )

        self.bucket = config.s3.commoncrawl_bucket
        self._bytes_downloaded = 0
        self._rate_limiter = asyncio.Semaphore(config.rate_limit.max_concurrent_requests)

    @property
    def bytes_downloaded(self) -> int:
        """Get total bytes downloaded (for cost tracking)."""
        return self._bytes_downloaded

    @property
    def estimated_cost_usd(self) -> float:
        """Estimate S3 egress cost.

        AWS S3 egress pricing (approximate):
        - First 10 TB/month: $0.09 per GB
        - Next 40 TB/month: $0.085 per GB
        - Over 50 TB/month: $0.07 per GB

        Using conservative $0.09/GB estimate.
        """
        gb_downloaded = self._bytes_downloaded / (1024**3)
        return gb_downloaded * 0.09

    async def download_file(
        self,
        key: str,
        local_path: Optional[Path] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> bytes:
        """Download a file from S3.

        Args:
            key: S3 object key (e.g., "crawl-data/CC-MAIN-2024-10/...")
            local_path: Optional path to save file
            progress_callback: Optional callback(bytes_downloaded, total_bytes)

        Returns:
            File contents as bytes

        Raises:
            ClientError: If S3 download fails
        """
        async with self._rate_limiter:
            try:
                logger.info(f"Downloading s3://{self.bucket}/{key}")

                # Get file size first (using our fixed method)
                total_size = await self.get_file_size(key)

                # Download object
                response = self.client.get_object(Bucket=self.bucket, Key=key)
                body = response["Body"]

                # Read content in chunks
                chunks = []
                bytes_read = 0

                chunk_size = 64 * 1024  # 64KB chunks
                while True:
                    chunk = body.read(chunk_size)
                    if not chunk:
                        break

                    chunks.append(chunk)
                    bytes_read += len(chunk)
                    self._bytes_downloaded += len(chunk)

                    if progress_callback:
                        progress_callback(bytes_read, total_size)

                content = b"".join(chunks)

                # Save to file if requested
                if local_path:
                    local_path.parent.mkdir(parents=True, exist_ok=True)
                    local_path.write_bytes(content)
                    logger.info(f"Saved to {local_path}")

                logger.info(f"Downloaded {len(content):,} bytes from {key}")
                return content

            except ClientError as e:
                logger.error(f"S3 download error for {key}: {e}")
                raise

    async def stream_file(
        self,
        key: str,
        chunk_size: int = 64 * 1024,
    ) -> AsyncIterator[bytes]:
        """Stream a file from S3 in chunks.

        Args:
            key: S3 object key
            chunk_size: Chunk size in bytes

        Yields:
            Chunks of file content
        """
        async with self._rate_limiter:
            try:
                logger.info(f"Streaming s3://{self.bucket}/{key}")

                response = self.client.get_object(Bucket=self.bucket, Key=key)
                body = response["Body"]

                while True:
                    chunk = body.read(chunk_size)
                    if not chunk:
                        break

                    self._bytes_downloaded += len(chunk)
                    yield chunk

            except ClientError as e:
                logger.error(f"S3 streaming error for {key}: {e}")
                raise

    async def download_and_decompress(
        self,
        key: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> bytes:
        """Download a gzipped file and decompress it.

        Args:
            key: S3 object key (should end with .gz)
            progress_callback: Optional progress callback

        Returns:
            Decompressed content
        """
        compressed_data = await self.download_file(key, progress_callback=progress_callback)

        try:
            decompressed_data = gzip.decompress(compressed_data)
            logger.info(
                f"Decompressed {len(compressed_data):,} → {len(decompressed_data):,} bytes"
            )
            return decompressed_data
        except gzip.BadGzipFile:
            logger.warning(f"File {key} is not gzipped, returning as-is")
            return compressed_data

    async def stream_and_decompress(
        self,
        key: str,
        chunk_size: int = 64 * 1024,
    ) -> AsyncIterator[bytes]:
        """Stream a gzipped file and decompress it.

        Args:
            key: S3 object key (should end with .gz)
            chunk_size: Chunk size for reading

        Yields:
            Decompressed chunks
        """
        decompressor = gzip.GzipFile(fileobj=None)

        async for chunk in self.stream_file(key, chunk_size):
            try:
                decompressed = decompressor.decompress(chunk)
                if decompressed:
                    yield decompressed
            except Exception as e:
                logger.warning(f"Decompression error: {e}")
                # If not gzipped, yield raw chunk
                yield chunk

    async def file_exists(self, key: str) -> bool:
        """Check if a file exists in S3.

        Args:
            key: S3 object key

        Returns:
            True if file exists

        Note:
            For anonymous access, head_object requires authentication.
            We use get_object with Range header instead (only fetches metadata).
        """
        try:
            # For anonymous access, use get_object with Range to avoid auth issues
            # This only fetches metadata, not actual content
            self.client.get_object(
                Bucket=self.bucket,
                Key=key,
                Range="bytes=0-0"  # Just check if file exists
            )
            return True
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in ("404", "NoSuchKey"):
                return False
            # For other errors (like 403 on non-existent files), assume doesn't exist
            if error_code in ("403", "Forbidden"):
                return False
            raise

    async def get_file_size(self, key: str) -> int:
        """Get size of a file in S3.

        Args:
            key: S3 object key

        Returns:
            File size in bytes

        Raises:
            ClientError: If file doesn't exist

        Note:
            For anonymous access, we use get_object with Range header
            to get ContentLength without authentication issues.
        """
        try:
            # Use Range request to get metadata including ContentLength
            response = self.client.get_object(
                Bucket=self.bucket,
                Key=key,
                Range="bytes=0-0"
            )
            # ContentRange header format: "bytes 0-0/12345" where 12345 is total size
            content_range = response.get("ContentRange", "")
            if content_range and "/" in content_range:
                total_size = int(content_range.split("/")[1])
                return total_size
            # Fallback: return ContentLength (will be 1 for Range request)
            return response.get("ContentLength", 0)
        except ClientError as e:
            logger.error(f"Failed to get file size for {key}: {e}")
            raise

    def reset_cost_tracking(self):
        """Reset the bytes downloaded counter."""
        self._bytes_downloaded = 0
        logger.info("Reset S3 cost tracking")
