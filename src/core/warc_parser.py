"""WARC file parser for Common Crawl.

This module provides parsing capabilities for WARC (Web ARChive) files
used by Common Crawl to store archived web pages.

WARC Specification: https://iipc.github.io/warc-specifications/
"""

import gzip
import io
import logging
from datetime import datetime
from typing import Any, Iterator, Optional

from warcio.archiveiterator import ArchiveIterator

from ..models.schemas import WarcRecord

logger = logging.getLogger(__name__)


class WarcParser:
    """Parser for WARC (Web ARChive) files.

    WARC files contain HTTP request/response pairs along with metadata.
    Common Crawl uses WARC format to store archived web pages.
    """

    def __init__(self):
        """Initialize WARC parser."""
        pass

    def parse_file(self, content: bytes, decompress: bool = True) -> Iterator[WarcRecord]:
        """Parse a WARC file from bytes.

        Args:
            content: WARC file content (may be gzipped)
            decompress: Whether to attempt gzip decompression

        Yields:
            WarcRecord objects
        """
        # Try to decompress if gzipped
        if decompress and content[:2] == b"\x1f\x8b":  # Gzip magic number
            try:
                content = gzip.decompress(content)
                logger.debug("Decompressed gzipped WARC file")
            except Exception as e:
                logger.warning(f"Failed to decompress WARC: {e}")

        # Parse WARC records
        stream = io.BytesIO(content)

        for record in ArchiveIterator(stream):
            try:
                warc_record = self._parse_record(record)
                if warc_record:
                    yield warc_record
            except Exception as e:
                logger.warning(f"Error parsing WARC record: {e}")
                continue

    def parse_stream(self, stream: io.BytesIO) -> Iterator[WarcRecord]:
        """Parse a WARC file from a stream.

        Args:
            stream: IO stream containing WARC data

        Yields:
            WarcRecord objects
        """
        for record in ArchiveIterator(stream):
            try:
                warc_record = self._parse_record(record)
                if warc_record:
                    yield warc_record
            except Exception as e:
                logger.warning(f"Error parsing WARC record: {e}")
                continue

    def _parse_record(self, record: Any) -> Optional[WarcRecord]:
        """Parse a single WARC record.

        Args:
            record: WARC record from warcio

        Returns:
            WarcRecord or None if parsing fails
        """
        try:
            # Get record metadata
            record_id = record.rec_headers.get_header("WARC-Record-ID", "")
            record_type = record.rec_headers.get_header("WARC-Type", "")
            target_uri = record.rec_headers.get_header("WARC-Target-URI", "")
            date_str = record.rec_headers.get_header("WARC-Date", "")
            content_type = record.rec_headers.get_header("Content-Type", "")
            content_length = int(record.rec_headers.get_header("Content-Length", "0"))

            # Parse date
            try:
                date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except Exception:
                date = datetime.now()

            # Extract HTTP headers if this is a response record
            http_headers = None
            if record_type == "response" and hasattr(record, "http_headers"):
                http_headers = dict(record.http_headers.headers)

            # Extract payload
            payload = None
            if record.content_stream():
                try:
                    payload = record.content_stream().read()
                except Exception as e:
                    logger.warning(f"Error reading payload: {e}")

            return WarcRecord(
                record_id=record_id,
                record_type=record_type,
                target_uri=target_uri,
                date=date,
                content_type=content_type,
                content_length=content_length,
                http_headers=http_headers,
                payload=payload,
            )

        except Exception as e:
            logger.error(f"Error parsing WARC record: {e}")
            return None

    def extract_http_response(self, record: WarcRecord) -> Optional[dict]:
        """Extract HTTP response from a WARC record.

        Args:
            record: WarcRecord to extract from

        Returns:
            Dictionary with status_code, headers, and body
        """
        if record.record_type != "response":
            return None

        if not record.payload:
            return None

        try:
            # Parse HTTP response
            payload_str = record.payload.decode("utf-8", errors="replace")

            # Split headers and body
            parts = payload_str.split("\r\n\r\n", 1)
            if len(parts) < 2:
                parts = payload_str.split("\n\n", 1)

            if len(parts) < 2:
                logger.warning("Could not split HTTP headers and body")
                return {
                    "status_code": 200,  # Assume success
                    "headers": record.http_headers or {},
                    "body": payload_str,
                }

            header_section, body = parts

            # Parse status line
            lines = header_section.split("\n")
            status_line = lines[0] if lines else ""

            # Extract status code
            status_code = 200
            try:
                status_parts = status_line.split()
                if len(status_parts) >= 2:
                    status_code = int(status_parts[1])
            except Exception:
                pass

            return {
                "status_code": status_code,
                "headers": record.http_headers or {},
                "body": body,
            }

        except Exception as e:
            logger.error(f"Error extracting HTTP response: {e}")
            return None

    def find_record_by_url(
        self,
        content: bytes,
        url: str,
    ) -> Optional[WarcRecord]:
        """Find a specific URL in a WARC file.

        Args:
            content: WARC file content
            url: URL to search for

        Returns:
            First matching WarcRecord or None
        """
        for record in self.parse_file(content):
            if record.target_uri == url:
                return record
        return None

    def count_records(self, content: bytes) -> dict[str, int]:
        """Count records by type in a WARC file.

        Args:
            content: WARC file content

        Returns:
            Dictionary mapping record type to count
        """
        counts: dict[str, int] = {}

        for record in self.parse_file(content):
            record_type = record.record_type
            counts[record_type] = counts.get(record_type, 0) + 1

        return counts
