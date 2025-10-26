"""Integration tests for core Common Crawl MCP Server components.

This module tests the integration between CDX client, S3 manager,
WARC parser, and caching system.
"""

import pytest
from pathlib import Path

from src.config import get_config
from src.core.cache import CacheManager
from src.core.cc_client import CDXClient
from src.core.s3_manager import S3Manager
from src.core.warc_parser import WarcParser


@pytest.fixture
def config():
    """Get server configuration."""
    return get_config()


@pytest.fixture
def cache_manager(tmp_path):
    """Create cache manager with temporary directory."""
    config = get_config()
    # Use temp directory for testing
    original_cache_dir = config.cache.cache_dir
    config.cache.cache_dir = tmp_path / "cache"

    manager = CacheManager()

    yield manager

    # Restore original
    config.cache.cache_dir = original_cache_dir


@pytest.fixture
def cdx_client():
    """Create CDX client."""
    return CDXClient()


@pytest.fixture
def s3_manager():
    """Create S3 manager."""
    return S3Manager()


@pytest.fixture
def warc_parser():
    """Create WARC parser."""
    return WarcParser()


class TestConfiguration:
    """Test configuration system."""

    def test_config_loads(self, config):
        """Test that configuration loads successfully."""
        assert config is not None
        assert config.server.server_name == "common-crawl-mcp-server"
        assert config.cdx.cdx_server_url == "https://index.commoncrawl.org"
        assert config.s3.commoncrawl_bucket == "commoncrawl"

    def test_config_validation(self, config):
        """Test configuration validation."""
        warnings = config.validate()
        # Should not have critical errors
        assert isinstance(warnings, list)


class TestCacheManager:
    """Test cache manager functionality."""

    @pytest.mark.asyncio
    async def test_cache_set_and_get(self, cache_manager):
        """Test basic cache operations."""
        key = "test_key"
        value = {"data": "test_value", "number": 42}

        # Set value
        await cache_manager.set(key, value)

        # Get value
        retrieved = await cache_manager.get(key)
        assert retrieved == value

    @pytest.mark.asyncio
    async def test_cache_miss(self, cache_manager):
        """Test cache miss returns None."""
        result = await cache_manager.get("nonexistent_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_stats(self, cache_manager):
        """Test cache statistics."""
        # Perform some operations
        await cache_manager.set("key1", "value1")
        await cache_manager.get("key1")  # Hit
        await cache_manager.get("key2")  # Miss

        stats = cache_manager.get_stats()
        assert "hits" in stats
        assert "misses" in stats
        assert "hit_rate_percent" in stats
        assert stats["hits"] >= 1
        assert stats["misses"] >= 1

    @pytest.mark.asyncio
    async def test_cache_clear(self, cache_manager):
        """Test cache clearing."""
        # Add some data
        await cache_manager.set("key1", "value1")
        await cache_manager.set("key2", "value2")

        # Clear cache
        await cache_manager.clear()

        # Verify cleared
        result = await cache_manager.get("key1")
        assert result is None


class TestCDXClient:
    """Test CDX client functionality."""

    @pytest.mark.asyncio
    async def test_list_crawls(self, cdx_client):
        """Test listing available crawls."""
        crawls = await cdx_client.list_crawls()

        assert isinstance(crawls, list)
        assert len(crawls) > 0

        # Check first crawl has required fields
        first_crawl = crawls[0]
        assert hasattr(first_crawl, "id")
        assert hasattr(first_crawl, "name")
        assert first_crawl.id.startswith("CC-MAIN-")

    @pytest.mark.asyncio
    async def test_get_latest_crawl(self, cdx_client):
        """Test getting latest crawl."""
        latest = await cdx_client.get_latest_crawl()

        assert latest is not None
        assert isinstance(latest, str)
        assert latest.startswith("CC-MAIN-")

    @pytest.mark.asyncio
    async def test_search_index(self, cdx_client):
        """Test searching CDX index."""
        # Search for a common domain
        results = await cdx_client.search_index(
            query="example.com",
            limit=5
        )

        assert isinstance(results, list)
        # Results may be empty depending on crawl, but should not error

    @pytest.mark.asyncio
    async def test_search_with_limit(self, cdx_client):
        """Test search respects limit."""
        results = await cdx_client.search_index(
            query="example.com",
            limit=3
        )

        assert len(results) <= 3


class TestS3Manager:
    """Test S3 manager functionality."""

    @pytest.mark.asyncio
    async def test_s3_client_initialized(self, s3_manager):
        """Test S3 client is properly initialized."""
        assert s3_manager.client is not None
        assert s3_manager.bucket == "commoncrawl"

    @pytest.mark.asyncio
    async def test_file_exists_check(self, s3_manager):
        """Test checking if file exists."""
        # Test with a known public file that should exist
        # Using a well-known index file from a recent crawl
        test_key = "crawl-data/CC-MAIN-2024-51/cc-index.paths.gz"

        try:
            exists = await s3_manager.file_exists(test_key)
            # File may or may not exist, but should not error
            assert isinstance(exists, bool)
        except Exception as e:
            # If we get a 403 or other error, that's okay for this test
            # The point is to verify the method handles errors gracefully
            assert "403" in str(e) or "Forbidden" in str(e) or "404" in str(e)
            pytest.skip(f"S3 access test skipped due to: {e}")

    def test_cost_tracking(self, s3_manager):
        """Test cost tracking functionality."""
        initial_cost = s3_manager.estimated_cost_usd
        assert initial_cost >= 0.0

        # Simulate download
        s3_manager._bytes_downloaded += 1024 * 1024  # 1 MB

        new_cost = s3_manager.estimated_cost_usd
        assert new_cost > initial_cost

        # Reset tracking
        s3_manager.reset_cost_tracking()
        assert s3_manager.bytes_downloaded == 0


class TestWarcParser:
    """Test WARC parser functionality."""

    def test_parser_initialized(self, warc_parser):
        """Test WARC parser is properly initialized."""
        assert warc_parser is not None

    def test_count_records_empty(self, warc_parser):
        """Test counting records in empty data."""
        # Create minimal WARC content
        empty_warc = b""

        counts = warc_parser.count_records(empty_warc)
        assert isinstance(counts, dict)
        assert len(counts) == 0


class TestIntegration:
    """Test integration between components."""

    @pytest.mark.asyncio
    async def test_cdx_with_cache(self, cdx_client, cache_manager):
        """Test CDX client with caching."""
        # First request - cache miss
        cache_key = "crawls:list"
        cached = await cache_manager.get(cache_key)
        assert cached is None

        # Get crawls
        crawls = await cdx_client.list_crawls()

        # Cache the results
        await cache_manager.set(cache_key, [c.model_dump() for c in crawls])

        # Second request - cache hit
        cached = await cache_manager.get(cache_key)
        assert cached is not None
        assert len(cached) == len(crawls)

    @pytest.mark.asyncio
    async def test_server_health_check_components(self, config):
        """Test that all components can be initialized for health check."""
        from src.server import get_cache, get_cdx_client, get_s3_manager, get_warc_parser

        # All components should initialize without error
        cache = get_cache()
        cdx = get_cdx_client()
        s3 = get_s3_manager()
        warc = get_warc_parser()

        assert cache is not None
        assert cdx is not None
        assert s3 is not None
        assert warc is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
