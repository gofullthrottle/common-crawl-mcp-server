"""Configuration management for Common Crawl MCP Server.

This module handles all configuration settings including cache paths,
S3 settings, rate limits, and other operational parameters.
"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

# Load environment variables from .env file
load_dotenv()


class CacheConfig(BaseSettings):
    """Cache configuration settings."""

    cache_dir: Path = Field(
        default=Path("./cache"),
        description="Directory for file cache storage",
    )
    cache_max_size_gb: float = Field(
        default=50.0,
        description="Maximum cache size in gigabytes",
        ge=1.0,
        le=1000.0,
    )
    memory_cache_size_mb: int = Field(
        default=512,
        description="Maximum memory cache size in megabytes",
        ge=64,
        le=8192,
    )
    cache_ttl_seconds: int = Field(
        default=86400,  # 24 hours
        description="Default TTL for cached items in seconds",
        ge=300,  # 5 minutes minimum
    )


class S3Config(BaseSettings):
    """S3 and Common Crawl specific settings."""

    aws_region: str = Field(
        default="us-east-1",
        description="AWS region for Common Crawl bucket",
    )
    commoncrawl_bucket: str = Field(
        default="commoncrawl",
        description="Common Crawl S3 bucket name",
    )
    use_anonymous_access: bool = Field(
        default=True,
        description="Use anonymous access to public Common Crawl bucket",
    )
    aws_access_key_id: Optional[str] = Field(
        default=None,
        description="AWS access key (optional, for custom configs)",
    )
    aws_secret_access_key: Optional[str] = Field(
        default=None,
        description="AWS secret key (optional, for custom configs)",
    )


class RateLimitConfig(BaseSettings):
    """Rate limiting configuration."""

    max_concurrent_requests: int = Field(
        default=5,
        description="Maximum concurrent requests to S3/CDX",
        ge=1,
        le=50,
    )
    requests_per_second: float = Field(
        default=10.0,
        description="Maximum requests per second",
        ge=1.0,
        le=100.0,
    )
    retry_max_attempts: int = Field(
        default=3,
        description="Maximum retry attempts for failed requests",
        ge=1,
        le=10,
    )
    retry_backoff_base: float = Field(
        default=2.0,
        description="Base for exponential backoff (seconds)",
        ge=1.0,
        le=10.0,
    )


class CDXConfig(BaseSettings):
    """CDX Server configuration."""

    cdx_server_url: str = Field(
        default="https://index.commoncrawl.org",
        description="CDX Server base URL",
    )
    cdx_timeout_seconds: int = Field(
        default=30,
        description="Timeout for CDX requests",
        ge=5,
        le=120,
    )
    cdx_max_results: int = Field(
        default=1000,
        description="Maximum results per CDX query",
        ge=10,
        le=10000,
    )


class RedisConfig(BaseSettings):
    """Redis configuration for distributed caching."""

    redis_url: Optional[str] = Field(
        default=None,
        description="Redis connection URL (optional)",
    )
    redis_enabled: bool = Field(
        default=False,
        description="Enable Redis caching",
    )
    redis_ttl_seconds: int = Field(
        default=3600,  # 1 hour
        description="Default TTL for Redis cached items",
        ge=60,
    )


class ServerConfig(BaseSettings):
    """MCP server configuration."""

    server_name: str = Field(
        default="common-crawl-mcp-server",
        description="MCP server name",
    )
    server_version: str = Field(
        default="0.1.0",
        description="MCP server version",
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level",
    )
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string",
    )


class DatabaseConfig(BaseSettings):
    """Database configuration for persistent storage."""

    db_path: Path = Field(
        default=Path("./data/commoncrawl.db"),
        description="Path to SQLite database",
    )
    db_echo: bool = Field(
        default=False,
        description="Echo SQL statements (for debugging)",
    )


class Config:
    """Main configuration class combining all settings."""

    def __init__(self):
        """Initialize configuration from environment variables."""
        self.cache = CacheConfig()
        self.s3 = S3Config()
        self.rate_limit = RateLimitConfig()
        self.cdx = CDXConfig()
        self.redis = RedisConfig()
        self.server = ServerConfig()
        self.database = DatabaseConfig()

        # Create necessary directories
        self._create_directories()

        # Enable Redis if URL is provided
        if self.redis.redis_url:
            self.redis.redis_enabled = True

    def _create_directories(self):
        """Create necessary directories for cache and data storage."""
        self.cache.cache_dir.mkdir(parents=True, exist_ok=True)
        self.database.db_path.parent.mkdir(parents=True, exist_ok=True)

    def validate(self) -> list[str]:
        """Validate configuration and return list of warnings/errors.

        Returns:
            List of validation warnings or errors. Empty if all valid.
        """
        warnings = []

        # Check cache directory is writable
        if not os.access(self.cache.cache_dir, os.W_OK):
            warnings.append(f"Cache directory not writable: {self.cache.cache_dir}")

        # Warn if cache is very small
        if self.cache.cache_max_size_gb < 10:
            warnings.append(
                f"Cache size is small ({self.cache.cache_max_size_gb}GB). "
                "Consider increasing for better performance."
            )

        # Check Redis configuration
        if self.redis.redis_url and not self.redis.redis_enabled:
            warnings.append("Redis URL provided but Redis is disabled")

        # Check database path is writable
        db_dir = self.database.db_path.parent
        if not os.access(db_dir, os.W_OK):
            warnings.append(f"Database directory not writable: {db_dir}")

        return warnings

    def __repr__(self) -> str:
        """Return string representation of configuration."""
        return (
            f"Config(\n"
            f"  server={self.server.server_name} v{self.server.server_version}\n"
            f"  cache_dir={self.cache.cache_dir}\n"
            f"  cache_size={self.cache.cache_max_size_gb}GB\n"
            f"  s3_bucket={self.s3.commoncrawl_bucket}\n"
            f"  redis_enabled={self.redis.redis_enabled}\n"
            f"  max_concurrent={self.rate_limit.max_concurrent_requests}\n"
            f")"
        )


# Global configuration instance
config = Config()


# Convenience function for getting config
def get_config() -> Config:
    """Get the global configuration instance.

    Returns:
        The global Config instance.
    """
    return config
