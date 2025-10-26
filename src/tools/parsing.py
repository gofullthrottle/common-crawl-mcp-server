"""Parsing and analysis tools for Common Crawl MCP Server.

This module provides tools for parsing HTML, analyzing technologies, extracting
structured data, and performing SEO analysis on archived web pages.
"""

import json
import logging
import re
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from ..core.cache import CacheManager
from ..models.schemas import (LanguageInfo, LinkAnalysis, PageContent,
                              ParsedHtml, SeoAnalysis, SeoIssue,
                              StructuredData, Technology, TechStack)
from ..utils.html_parser import (extract_clean_text, extract_headings,
                                 extract_links, extract_meta_tags, parse_html)
from ..utils.technology_detector import TechnologyDetector
from .fetching import fetch_page_content as fetch_page_dict

logger = logging.getLogger(__name__)

# Module-level cache and technology detector
_cache: Optional[CacheManager] = None
tech_detector = TechnologyDetector()


def _get_cache() -> CacheManager:
    """Get cache manager instance."""
    global _cache
    if _cache is None:
        from ..server import get_cache

        _cache = get_cache()
    return _cache


async def _fetch_page(url: str, crawl_id: str) -> PageContent:
    """Fetch page and convert dict to PageContent model."""
    page_dict = await fetch_page_dict(url, crawl_id)

    # Handle error case
    if "error" in page_dict:
        # Return empty PageContent
        from datetime import datetime, timezone

        return PageContent(
            url=url,
            crawl_id=crawl_id,
            html=None,
            text=None,
            status_code=404,
            headers={},
            mime_type="text/html",
            length=0,
            timestamp=datetime.now(timezone.utc),
        )

    # Convert dict to PageContent
    return PageContent(**page_dict)


async def parse_html_content(url: str, crawl_id: str = "CC-MAIN-2024-10") -> ParsedHtml:
    """Parse HTML and extract structured data.

    Args:
        url: URL to parse
        crawl_id: Common Crawl crawl identifier

    Returns:
        ParsedHtml: Structured parsing result with title, meta tags, headings, links, text

    Example:
        >>> result = await parse_html_content("https://example.com")
        >>> print(result.title)
        'Example Domain'
    """
    cache_key = f"parsed_html:{crawl_id}:{url}"

    # Check cache (24h TTL)
    cache = _get_cache()
    cached = await cache.get(cache_key)
    if cached:
        return ParsedHtml(**cached)

    # Fetch page content
    page = await _fetch_page(url, crawl_id)

    if not page.html:
        logger.warning(f"No HTML content for {url}")
        return ParsedHtml(url=url)

    soup = parse_html(page.html)

    # Extract title
    title = None
    title_tag = soup.find("title")
    if title_tag:
        title = title_tag.get_text(strip=True)

    # Extract meta tags
    meta_tags = extract_meta_tags(page.html)

    # Extract headings
    headings = extract_headings(page.html)

    # Extract links
    link_list = extract_links(page.html, base_url=url)
    links = [link["href"] for link in link_list if link.get("href")]

    # Extract scripts
    scripts = []
    for script in soup.find_all("script", src=True):
        src = script.get("src")
        if src:
            # Resolve relative URLs
            if not src.startswith(("http://", "https://", "//")):
                src = urljoin(url, src)
            scripts.append(src)

    # Extract stylesheets
    styles = []
    for link_tag in soup.find_all("link", rel="stylesheet"):
        href = link_tag.get("href")
        if href:
            if not href.startswith(("http://", "https://", "//")):
                href = urljoin(url, href)
            styles.append(href)

    # Extract images
    images = []
    for img in soup.find_all("img", src=True):
        src = img.get("src")
        if src:
            if not src.startswith(("http://", "https://", "//")):
                src = urljoin(url, src)
            images.append(src)

    # Extract clean text
    text_content = extract_clean_text(page.html, preserve_paragraphs=False)

    result = ParsedHtml(
        url=url,
        title=title,
        meta_tags=meta_tags,
        headings=headings,
        links=links,
        scripts=scripts,
        styles=styles,
        images=images,
        text_content=text_content[:10000] if text_content else None,  # Limit size
    )

    # Cache for 24 hours
    await cache.set(cache_key, result.model_dump(), ttl=86400)

    return result


async def extract_links_analysis(url: str, crawl_id: str = "CC-MAIN-2024-10") -> LinkAnalysis:
    """Extract and analyze links from a page.

    Args:
        url: URL to analyze
        crawl_id: Common Crawl crawl identifier

    Returns:
        LinkAnalysis: Link structure with internal/external classification

    Example:
        >>> result = await extract_links_analysis("https://example.com")
        >>> print(f"Internal: {len(result.internal_links)}, External: {len(result.external_links)}")
    """
    cache_key = f"link_analysis:{crawl_id}:{url}"

    cache = _get_cache()
    cached = await cache.get(cache_key)
    if cached:
        return LinkAnalysis(**cached)

    # Fetch page
    page = await _fetch_page(url, crawl_id)

    if not page.html:
        return LinkAnalysis(url=url)

    # Extract links with metadata
    links = extract_links(page.html, base_url=url)

    # Parse base domain
    parsed_url = urlparse(url)
    base_domain = parsed_url.netloc

    internal_links = []
    external_links = []
    broken_links = []

    for link in links:
        href = link.get("href", "")

        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue

        # Parse link
        try:
            link_parsed = urlparse(href)

            # Classify as internal/external
            if link_parsed.netloc == base_domain or not link_parsed.netloc:
                internal_links.append(href)
            else:
                external_links.append(href)

        except Exception as e:
            logger.debug(f"Failed to parse link {href}: {e}")
            broken_links.append(href)

    result = LinkAnalysis(
        url=url,
        internal_links=list(set(internal_links)),  # Deduplicate
        external_links=list(set(external_links)),
        broken_links=list(set(broken_links)),
        total_links=len(links),
    )

    await cache.set(cache_key, result.model_dump(), ttl=86400)

    return result


async def analyze_technologies(url: str, crawl_id: str = "CC-MAIN-2024-10") -> TechStack:
    """Detect technologies used by a website.

    Args:
        url: URL to analyze
        crawl_id: Common Crawl crawl identifier

    Returns:
        TechStack: Detected technologies with confidence scores

    Example:
        >>> result = await analyze_technologies("https://wordpress.com")
        >>> for tech in result.technologies:
        ...     print(f"{tech.name} ({tech.category}): {tech.confidence:.0%}")
    """
    cache_key = f"tech_stack:{crawl_id}:{url}"

    cache = _get_cache()
    cached = await cache.get(cache_key)
    if cached:
        return TechStack(**cached)

    # Fetch page
    page = await _fetch_page(url, crawl_id)

    if not page.html:
        return TechStack(url=url)

    # Run technology detection
    detection_result = tech_detector.detect(page.html, page.headers)

    # Convert to Technology objects
    technologies = []
    for tech_name, info in detection_result["detected"].items():
        technologies.append(
            Technology(
                name=tech_name,
                category=info["category"],
                version=info.get("version"),
                confidence=info["confidence"],
                evidence=[],  # Could be enhanced to show specific patterns matched
            )
        )

    result = TechStack(
        url=url, technologies=technologies, categories=detection_result["categories"]
    )

    await cache.set(cache_key, result.model_dump(), ttl=86400)

    return result


async def extract_structured_data_from_page(
    url: str, crawl_id: str = "CC-MAIN-2024-10"
) -> StructuredData:
    """Extract structured data (JSON-LD, Microdata, Open Graph, Twitter Cards).

    Args:
        url: URL to analyze
        crawl_id: Common Crawl crawl identifier

    Returns:
        StructuredData: Extracted structured data from various formats

    Example:
        >>> result = await extract_structured_data_from_page("https://example.com")
        >>> for item in result.json_ld:
        ...     print(item.get('@type'))
    """
    cache_key = f"structured_data:{crawl_id}:{url}"

    cache = _get_cache()
    cached = await cache.get(cache_key)
    if cached:
        return StructuredData(**cached)

    # Fetch page
    page = await _fetch_page(url, crawl_id)

    if not page.html:
        return StructuredData(url=url)

    soup = parse_html(page.html)

    # Extract JSON-LD
    json_ld = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            json_ld.append(data)
        except (json.JSONDecodeError, TypeError) as e:
            logger.debug(f"Failed to parse JSON-LD: {e}")

    # Extract Open Graph tags
    open_graph = {}
    for meta in soup.find_all("meta", property=re.compile(r"^og:")):
        prop = meta.get("property")
        content = meta.get("content")
        if prop and content:
            open_graph[prop] = content

    # Extract Twitter Card tags
    twitter_card = {}
    for meta in soup.find_all("meta", attrs={"name": re.compile(r"^twitter:")}):
        name = meta.get("name")
        content = meta.get("content")
        if name and content:
            twitter_card[name] = content

    # Note: Microdata parsing is complex and would require additional library
    # For now, return empty list
    microdata = []

    result = StructuredData(
        url=url,
        json_ld=json_ld,
        microdata=microdata,
        open_graph=open_graph,
        twitter_card=twitter_card,
    )

    await cache.set(cache_key, result.model_dump(), ttl=86400)

    return result


async def analyze_seo_metrics(url: str, crawl_id: str = "CC-MAIN-2024-10") -> SeoAnalysis:
    """Analyze SEO best practices for a page.

    Args:
        url: URL to analyze
        crawl_id: Common Crawl crawl identifier

    Returns:
        SeoAnalysis: SEO analysis with score, issues, and recommendations

    Example:
        >>> result = await analyze_seo_metrics("https://example.com")
        >>> print(f"SEO Score: {result.score:.1f}/100")
        >>> for issue in result.issues:
        ...     print(f"{issue.severity}: {issue.message}")
    """
    cache_key = f"seo_analysis:{crawl_id}:{url}"

    cache = _get_cache()
    cached = await cache.get(cache_key)
    if cached:
        return SeoAnalysis(**cached)

    # Fetch parsed HTML
    parsed = await parse_html_content(url, crawl_id)
    page = await _fetch_page(url, crawl_id)

    issues: list[SeoIssue] = []
    score = 100.0  # Start with perfect score, deduct for issues

    # Check title
    title_length = len(parsed.title) if parsed.title else 0

    if not parsed.title:
        issues.append(
            SeoIssue(
                severity="error",
                category="title",
                message="Missing title tag",
                recommendation="Add a descriptive <title> tag (50-60 characters)",
            )
        )
        score -= 20
    elif title_length < 30:
        issues.append(
            SeoIssue(
                severity="warning",
                category="title",
                message=f"Title too short ({title_length} chars)",
                recommendation="Use 50-60 characters for optimal display",
            )
        )
        score -= 10
    elif title_length > 60:
        issues.append(
            SeoIssue(
                severity="warning",
                category="title",
                message=f"Title too long ({title_length} chars)",
                recommendation="Keep title under 60 characters to avoid truncation",
            )
        )
        score -= 5

    # Check meta description
    meta_desc = parsed.meta_tags.get("description")
    meta_desc_length = len(meta_desc) if meta_desc else 0

    if not meta_desc:
        issues.append(
            SeoIssue(
                severity="error",
                category="meta",
                message="Missing meta description",
                recommendation="Add meta description (150-160 characters)",
            )
        )
        score -= 15
    elif meta_desc_length < 120:
        issues.append(
            SeoIssue(
                severity="warning",
                category="meta",
                message=f"Meta description too short ({meta_desc_length} chars)",
                recommendation="Use 150-160 characters for best results",
            )
        )
        score -= 5
    elif meta_desc_length > 160:
        issues.append(
            SeoIssue(
                severity="info",
                category="meta",
                message=f"Meta description too long ({meta_desc_length} chars)",
                recommendation="Keep under 160 characters to avoid truncation",
            )
        )
        score -= 3

    # Check heading structure
    heading_structure = {level: len(headings) for level, headings in parsed.headings.items()}

    h1_count = heading_structure.get("h1", 0)
    if h1_count == 0:
        issues.append(
            SeoIssue(
                severity="error",
                category="headings",
                message="Missing H1 heading",
                recommendation="Add exactly one H1 heading to the page",
            )
        )
        score -= 15
    elif h1_count > 1:
        issues.append(
            SeoIssue(
                severity="warning",
                category="headings",
                message=f"Multiple H1 headings ({h1_count})",
                recommendation="Use only one H1 heading per page",
            )
        )
        score -= 10

    # Check for canonical URL
    has_canonical = "canonical" in parsed.meta_tags or any(
        "rel" in str(tag) and "canonical" in str(tag) for tag in [parsed.meta_tags]
    )

    if not has_canonical:
        issues.append(
            SeoIssue(
                severity="info",
                category="links",
                message="Missing canonical URL",
                recommendation="Add <link rel='canonical'> to prevent duplicate content issues",
            )
        )
        score -= 5

    # Check robots meta tag
    robots_meta = parsed.meta_tags.get("robots")

    if robots_meta and "noindex" in robots_meta.lower():
        issues.append(
            SeoIssue(
                severity="warning",
                category="meta",
                message="Page is set to noindex",
                recommendation="Remove noindex if page should be indexed",
            )
        )

    # Check content length
    text_length = len(parsed.text_content) if parsed.text_content else 0

    if text_length < 300:
        issues.append(
            SeoIssue(
                severity="warning",
                category="content",
                message=f"Thin content ({text_length} characters)",
                recommendation="Add more content (aim for 300+ words)",
            )
        )
        score -= 10

    # Check for images without alt text (basic check)
    if parsed.images and not any("alt=" in str(parsed.meta_tags)):
        issues.append(
            SeoIssue(
                severity="info",
                category="images",
                message="Images may be missing alt text",
                recommendation="Add descriptive alt text to all images",
            )
        )
        score -= 5

    # Ensure score doesn't go below 0
    score = max(0.0, score)

    result = SeoAnalysis(
        url=url,
        score=score,
        issues=issues,
        title_length=title_length,
        meta_description_length=meta_desc_length,
        heading_structure=heading_structure,
        has_canonical=has_canonical,
        robots_meta=robots_meta,
    )

    await cache.set(cache_key, result.model_dump(), ttl=86400)

    return result


async def detect_language(url: str, crawl_id: str = "CC-MAIN-2024-10") -> LanguageInfo:
    """Detect language of a page.

    Args:
        url: URL to analyze
        crawl_id: Common Crawl crawl identifier

    Returns:
        LanguageInfo: Language detection result with ISO 639-1 code

    Example:
        >>> result = await detect_language("https://example.com")
        >>> print(f"Language: {result.detected_language} ({result.confidence:.0%})")
    """
    cache_key = f"language:{crawl_id}:{url}"

    cache = _get_cache()
    cached = await cache.get(cache_key)
    if cached:
        return LanguageInfo(**cached)

    # Fetch page
    page = await _fetch_page(url, crawl_id)

    if not page.html:
        return LanguageInfo(url=url, detected_language="unknown", confidence=0.0)

    soup = parse_html(page.html)

    # Check HTML lang attribute (most reliable)
    html_lang = None
    html_tag = soup.find("html")
    if html_tag:
        html_lang = html_tag.get("lang")

    # If HTML lang attribute exists, use it
    if html_lang:
        # Normalize to ISO 639-1 (take first 2 chars)
        lang_code = html_lang.split("-")[0].lower()[:2]

        result = LanguageInfo(
            url=url,
            detected_language=lang_code,
            confidence=0.95,  # High confidence for explicit lang attribute
            html_lang_attribute=html_lang,
        )
    else:
        # Fallback to langdetect library
        try:
            from langdetect import detect_langs

            text = extract_clean_text(page.html)

            if text and len(text) > 50:
                # Get language with confidence
                langs = detect_langs(text)

                if langs:
                    detected = langs[0]
                    result = LanguageInfo(
                        url=url,
                        detected_language=detected.lang,
                        confidence=detected.prob,
                        html_lang_attribute=None,
                    )
                else:
                    result = LanguageInfo(url=url, detected_language="unknown", confidence=0.0)
            else:
                result = LanguageInfo(url=url, detected_language="unknown", confidence=0.0)

        except ImportError:
            logger.warning("langdetect library not installed, falling back to 'en'")
            result = LanguageInfo(
                url=url,
                detected_language="en",
                confidence=0.5,
                html_lang_attribute=None,
            )
        except Exception as e:
            logger.error(f"Language detection failed: {e}")
            result = LanguageInfo(url=url, detected_language="unknown", confidence=0.0)

    await cache.set(cache_key, result.model_dump(), ttl=86400)

    return result
