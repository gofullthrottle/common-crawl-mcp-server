"""Pydantic models for Common Crawl MCP Server.

This module defines all data models used throughout the server for type safety
and validation.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, HttpUrl


# Enums
class CrawlStatus(str, Enum):
    """Status of a Common Crawl crawl."""

    ACTIVE = "active"
    COMPLETE = "complete"
    PROCESSING = "processing"
    UNKNOWN = "unknown"


class ContentType(str, Enum):
    """MIME content types."""

    HTML = "text/html"
    JSON = "application/json"
    XML = "application/xml"
    PDF = "application/pdf"
    TEXT = "text/plain"
    OTHER = "other"


# Crawl Models
class CrawlInfo(BaseModel):
    """Information about a Common Crawl crawl."""

    id: str = Field(..., description="Crawl identifier (e.g., CC-MAIN-2024-10)")
    name: str = Field(..., description="Human-readable crawl name")
    date: datetime = Field(..., description="Crawl date")
    status: CrawlStatus = Field(default=CrawlStatus.UNKNOWN, description="Crawl status")
    approximate_size_gb: Optional[float] = Field(None, description="Approximate size in gigabytes")


class CrawlStats(BaseModel):
    """Detailed statistics for a crawl."""

    crawl_id: str
    total_pages: Optional[int] = None
    total_domains: Optional[int] = None
    total_size_bytes: Optional[int] = None
    warc_files: Optional[int] = None
    wat_files: Optional[int] = None
    wet_files: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


# Index Models
class IndexRecord(BaseModel):
    """Record from the CDX index."""

    url: str = Field(..., description="URL of the page")
    mime_type: str = Field(..., description="MIME type")
    status_code: int = Field(..., description="HTTP status code")
    digest: str = Field(..., description="Content digest (hash)")
    timestamp: str = Field(..., description="Crawl timestamp (YYYYMMDDhhmmss)")
    length: int = Field(..., description="Content length in bytes")
    offset: int = Field(..., description="Offset in WARC file")
    filename: str = Field(..., description="WARC filename")


# Domain Models
class DomainStats(BaseModel):
    """Statistics for a specific domain."""

    domain: str
    crawl_id: str
    total_pages: int = Field(..., description="Number of pages crawled")
    total_size_bytes: int = Field(..., description="Total size in bytes")
    subdomains: list[str] = Field(default_factory=list, description="List of subdomains")
    first_seen: Optional[datetime] = Field(None, description="First crawl date")
    last_seen: Optional[datetime] = Field(None, description="Last crawl date")


class ComparisonResult(BaseModel):
    """Result of comparing domain across crawls."""

    domain: str
    crawls_compared: list[str]
    page_counts: dict[str, int] = Field(..., description="Pages per crawl")
    total_size_bytes: dict[str, int] = Field(..., description="Size per crawl")
    trend: str = Field(..., description="growing, shrinking, stable")


# Page Content Models
class PageContent(BaseModel):
    """Content and metadata for a fetched page."""

    url: str
    crawl_id: str
    html: Optional[str] = Field(None, description="HTML content")
    text: Optional[str] = Field(None, description="Extracted plain text")
    status_code: int
    headers: dict[str, str] = Field(default_factory=dict)
    mime_type: str
    length: int
    timestamp: datetime
    fetch_time: Optional[datetime] = Field(None, description="When we fetched it")


class WarcRecord(BaseModel):
    """Raw WARC record."""

    record_id: str
    record_type: str = Field(..., description="response, request, metadata, etc.")
    target_uri: str
    date: datetime
    content_type: str
    content_length: int
    http_headers: Optional[dict[str, str]] = None
    payload: Optional[bytes] = None


class WatMetadata(BaseModel):
    """Metadata from WAT files."""

    url: str
    timestamp: datetime
    envelope: dict[str, Any] = Field(default_factory=dict)
    http_response_metadata: Optional[dict[str, Any]] = None


# Parsing Models
class ParsedHtml(BaseModel):
    """Structured HTML parsing result."""

    url: str
    title: Optional[str] = None
    meta_tags: dict[str, str] = Field(default_factory=dict)
    headings: dict[str, list[str]] = Field(default_factory=dict, description="h1-h6 headings")
    links: list[str] = Field(default_factory=list)
    scripts: list[str] = Field(default_factory=list, description="Script sources")
    styles: list[str] = Field(default_factory=list, description="Stylesheet sources")
    images: list[str] = Field(default_factory=list)
    text_content: Optional[str] = None


class LinkAnalysis(BaseModel):
    """Link structure analysis."""

    url: str
    internal_links: list[str] = Field(default_factory=list)
    external_links: list[str] = Field(default_factory=list)
    broken_links: list[str] = Field(default_factory=list)
    total_links: int = 0


class Technology(BaseModel):
    """Detected technology."""

    name: str
    category: str = Field(..., description="CMS, Framework, Analytics, etc.")
    version: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    evidence: list[str] = Field(default_factory=list, description="Detection evidence")


class TechStack(BaseModel):
    """Complete technology stack for a page."""

    url: str
    technologies: list[Technology] = Field(default_factory=list)
    categories: dict[str, list[str]] = Field(
        default_factory=dict, description="Technologies grouped by category"
    )


class StructuredData(BaseModel):
    """Structured data from page."""

    url: str
    json_ld: list[dict[str, Any]] = Field(default_factory=list)
    microdata: list[dict[str, Any]] = Field(default_factory=list)
    open_graph: dict[str, str] = Field(default_factory=dict)
    twitter_card: dict[str, str] = Field(default_factory=dict)


class SeoIssue(BaseModel):
    """SEO issue or recommendation."""

    severity: str = Field(..., description="error, warning, info")
    category: str = Field(..., description="title, meta, headings, links, etc.")
    message: str
    recommendation: Optional[str] = None


class SeoAnalysis(BaseModel):
    """SEO analysis result."""

    url: str
    score: float = Field(..., ge=0.0, le=100.0, description="Overall SEO score")
    issues: list[SeoIssue] = Field(default_factory=list)
    title_length: Optional[int] = None
    meta_description_length: Optional[int] = None
    heading_structure: dict[str, int] = Field(default_factory=dict)
    has_canonical: bool = False
    robots_meta: Optional[str] = None


class LanguageInfo(BaseModel):
    """Language detection result."""

    url: str
    detected_language: str = Field(..., description="ISO 639-1 language code")
    confidence: float = Field(..., ge=0.0, le=1.0)
    html_lang_attribute: Optional[str] = None


# Aggregation Models
class TechReport(BaseModel):
    """Domain technology report."""

    domain: str
    crawl_id: str
    pages_analyzed: int
    technologies: dict[str, int] = Field(..., description="Technology -> page count")
    categories: dict[str, dict[str, int]] = Field(..., description="Category -> {tech: count}")
    adoption_percentage: dict[str, float] = Field(
        ..., description="Technology -> percentage of pages"
    )


class LinkGraph(BaseModel):
    """Link graph structure."""

    domain: str
    crawl_id: str
    nodes: list[str] = Field(..., description="List of URLs")
    edges: list[tuple[str, str]] = Field(..., description="(from_url, to_url) pairs")
    hub_pages: list[tuple[str, int]] = Field(..., description="(url, inbound_links)")
    pagerank: Optional[dict[str, float]] = None


class KeywordStats(BaseModel):
    """Keyword frequency analysis."""

    keywords: list[str]
    frequencies: dict[str, dict[str, int]] = Field(..., description="keyword -> {url: count}")
    total_occurrences: dict[str, int] = Field(..., description="keyword -> total")
    tfidf_scores: Optional[dict[str, dict[str, float]]] = None


class Timeline(BaseModel):
    """Domain evolution timeline."""

    domain: str
    crawls: list[str]
    page_counts: dict[str, int] = Field(..., description="crawl_id -> page_count")
    size_bytes: dict[str, int] = Field(..., description="crawl_id -> size")
    technologies_added: dict[str, list[str]] = Field(..., description="crawl_id -> [technologies]")
    technologies_removed: dict[str, list[str]] = Field(
        ..., description="crawl_id -> [technologies]"
    )


class HeaderReport(BaseModel):
    """HTTP header analysis."""

    domain: str
    crawl_id: str
    pages_analyzed: int
    security_headers: dict[str, float] = Field(..., description="header -> adoption_percentage")
    caching_policies: dict[str, int] = Field(..., description="policy -> count")
    servers: dict[str, int] = Field(..., description="server -> count")
    security_score: float = Field(..., ge=0.0, le=100.0)
    recommendations: list[str] = Field(default_factory=list)


# Export Models
class ExportResult(BaseModel):
    """Result of export operation."""

    output_path: str = Field(..., description="Path to the exported file")
    format: str = Field(..., description="Export format (csv, jsonl, warc, etc.)")
    records_exported: int = Field(..., description="Number of records successfully exported")
    file_size_bytes: int = Field(..., description="Size of exported file in bytes")
    duration_seconds: float = Field(..., description="Time taken to export in seconds")
    errors: list[str] = Field(
        default_factory=list, description="List of errors encountered during export"
    )


class Dataset(BaseModel):
    """Saved dataset."""

    dataset_id: str
    name: str
    query: dict[str, Any]
    created_at: datetime
    row_count: int
    size_bytes: int
    description: Optional[str] = None


# Query Models
class SizeEstimate(BaseModel):
    """Size estimate for a query."""

    estimated_pages: int
    estimated_size_mb: float
    estimated_download_time_seconds: float
    estimated_cost_usd: float = Field(..., description="Estimated S3 egress cost")
    recommendation: str = Field(..., description="Use cache, sample, or proceed")


# Advanced Analysis Models (Phase 9)
class ContentClassification(BaseModel):
    """Web page classification result.

    Classifies web pages by type using composition of multiple analysis tools.
    """

    url: str = Field(..., description="URL that was classified")
    page_type: str = Field(
        ..., description="Page type: blog, product, documentation, news, landing_page, or other"
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Classification confidence")
    signals: dict[str, Any] = Field(
        default_factory=dict, description="Evidence signals used for classification"
    )
    language: str = Field(..., description="Detected language code")
    content_quality_score: float = Field(..., ge=0.0, le=100.0, description="SEO quality score")


class SpamAnalysis(BaseModel):
    """Spam detection analysis result.

    Analyzes content quality signals to detect spam or low-quality pages.
    """

    url: str = Field(..., description="URL that was analyzed")
    spam_score: float = Field(..., ge=0.0, le=100.0, description="Spam score (0=clean, 100=spam)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence")
    spam_signals: list[str] = Field(
        default_factory=list, description="List of spam indicators detected"
    )
    quality_signals: list[str] = Field(
        default_factory=list, description="List of quality indicators detected"
    )
    recommendation: str = Field(
        ..., description="Overall recommendation: likely_spam, suspicious, or likely_legitimate"
    )


class Trend(BaseModel):
    """Individual trend metric detected."""

    metric: str = Field(..., description="Metric name: page_count, technology_adoption, etc.")
    direction: str = Field(..., description="Trend direction: increasing, decreasing, or stable")
    rate_of_change: float = Field(..., description="Percentage change rate")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Trend confidence")


class TrendAnalysis(BaseModel):
    """Domain trend analysis result.

    Analyzes domain evolution trends across multiple crawls.
    """

    domain: str = Field(..., description="Domain that was analyzed")
    time_period: dict[str, str] = Field(..., description="Time period with start and end crawl IDs")
    trends: list[Trend] = Field(default_factory=list, description="List of detected trends")
    insights: list[str] = Field(
        default_factory=list, description="Generated insights from trend analysis"
    )
