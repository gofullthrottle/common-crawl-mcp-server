"""Advanced analysis features for Common Crawl MCP Server.

This module provides intelligent classification, spam detection, and trend
analysis by composing existing tool primitives.
"""

import logging
from typing import Any

from ..models.schemas import (ContentClassification, SpamAnalysis, Trend,
                              TrendAnalysis)

logger = logging.getLogger(__name__)

__all__ = [
    "content_classification",
    "spam_detection",
    "trend_analysis",
]


async def content_classification(
    url: str,
    crawl_id: str = "CC-MAIN-2024-10",
) -> ContentClassification:
    """Classify a web page by type and purpose.

    Uses composition of existing tools to gather classification signals:
    - SEO metrics for content structure
    - Language detection
    - Structured data (schema.org, Open Graph)

    Args:
        url: URL to classify
        crawl_id: Common Crawl crawl identifier

    Returns:
        ContentClassification with page type, confidence, and signals

    Example:
        >>> result = await content_classification("https://example.com/blog/post")
        >>> print(result.page_type)
        'blog'
        >>> print(result.confidence)
        0.9
    """
    logger.info(f"Classifying content for URL: {url}")

    from .parsing import (analyze_seo_metrics, detect_language,
                          extract_structured_data_from_page)

    try:
        # Gather signals from existing tools
        seo = await analyze_seo_metrics(url, crawl_id)
        lang = await detect_language(url, crawl_id)
        structured = await extract_structured_data_from_page(url, crawl_id)

        signals = {}

        # URL pattern signals
        url_lower = url.lower()
        if "/blog/" in url_lower or "/post/" in url_lower or "/article/" in url_lower:
            signals["url_pattern"] = "blog"
        elif "/product/" in url_lower or "/shop/" in url_lower or "/item/" in url_lower:
            signals["url_pattern"] = "product"
        elif "/docs/" in url_lower or "/documentation/" in url_lower or "/api/" in url_lower:
            signals["url_pattern"] = "documentation"
        elif "/news/" in url_lower:
            signals["url_pattern"] = "news"

        # Structured data signals
        if structured.schema_org:
            schema_types = str(structured.schema_org)
            if "BlogPosting" in schema_types or "Article" in schema_types:
                signals["schema_org"] = "blog"
            elif "Product" in schema_types:
                signals["schema_org"] = "product"
            elif "NewsArticle" in schema_types:
                signals["schema_org"] = "news"

        # Content structure signals
        if seo.headings:
            h1_count = len(seo.headings.get("h1", []))
            if h1_count == 1:
                signals["heading_structure"] = "well_structured"
            elif h1_count > 1:
                signals["heading_structure"] = "multiple_h1"

        # Classify based on signals
        page_type = "other"
        confidence = 0.5

        # Strong signals (schema.org) have highest priority
        if signals.get("schema_org") == "blog":
            page_type = "blog"
            confidence = 0.9
        elif signals.get("schema_org") == "product":
            page_type = "product"
            confidence = 0.9
        elif signals.get("schema_org") == "news":
            page_type = "news"
            confidence = 0.9
        # Medium signals (URL patterns)
        elif signals.get("url_pattern") == "blog":
            page_type = "blog"
            confidence = 0.7
        elif signals.get("url_pattern") == "product":
            page_type = "product"
            confidence = 0.7
        elif signals.get("url_pattern") == "documentation":
            page_type = "documentation"
            confidence = 0.75
        elif signals.get("url_pattern") == "news":
            page_type = "news"
            confidence = 0.7

        # Landing pages typically lack blog/product patterns
        if not signals.get("url_pattern") and signals.get("heading_structure") == "well_structured":
            if seo.seo_score > 70:
                page_type = "landing_page"
                confidence = 0.6

        logger.info(f"Classified {url} as '{page_type}' with confidence {confidence}")

        return ContentClassification(
            url=url,
            page_type=page_type,
            confidence=confidence,
            signals=signals,
            language=lang.language,
            content_quality_score=seo.seo_score,
        )

    except Exception as e:
        logger.error(f"Error classifying content for {url}: {e}", exc_info=True)
        # Return default classification on error
        return ContentClassification(
            url=url,
            page_type="other",
            confidence=0.5,
            signals={"error": str(e)},
            language="unknown",
            content_quality_score=0.0,
        )


async def spam_detection(
    url: str,
    crawl_id: str = "CC-MAIN-2024-10",
) -> SpamAnalysis:
    """Detect if a page is likely spam or low-quality.

    Analyzes multiple quality signals:
    - Security headers
    - Title and meta quality
    - Link patterns
    - Content quality (keyword stuffing)
    - Technology legitimacy

    Args:
        url: URL to analyze
        crawl_id: Common Crawl crawl identifier

    Returns:
        SpamAnalysis with spam score, signals, and recommendation

    Example:
        >>> result = await spam_detection("https://example.com")
        >>> print(result.spam_score)
        15.0
        >>> print(result.recommendation)
        'likely_legitimate'
    """
    logger.info(f"Analyzing spam signals for URL: {url}")

    from .parsing import analyze_technologies, parse_html_content

    try:
        # Gather signals from existing tools
        parsed = await parse_html_content(url, crawl_id)
        tech = await analyze_technologies(url, crawl_id)

        spam_signals = []
        quality_signals = []
        spam_score = 0

        # Security header signals
        if not parsed.headers or len(parsed.headers) == 0:
            spam_signals.append("missing_security_headers")
            spam_score += 20

        # Content quality signals
        if not parsed.title or len(parsed.title) < 10:
            spam_signals.append("poor_title")
            spam_score += 15

        if not parsed.meta_tags.get("description"):
            spam_signals.append("missing_meta_description")
            spam_score += 10

        # Link spam signals
        if parsed.links:
            external_links = [
                link
                for link in parsed.links
                if link.get("href") and url not in link.get("href", "")
            ]
            if len(external_links) > 50:
                spam_signals.append("excessive_external_links")
                spam_score += 20

        # Technology signals (legitimate sites use known tech)
        if tech.technologies and len(tech.technologies) > 0:
            quality_signals.append("uses_known_technologies")
            spam_score -= 10

        # Keyword stuffing detection
        if parsed.text:
            words = parsed.text.lower().split()
            if len(words) > 100:  # Only check for longer content
                unique_words = set(words)
                repetition_ratio = 1 - (len(unique_words) / len(words))
                if repetition_ratio > 0.5:
                    spam_signals.append("keyword_stuffing")
                    spam_score += 25

        # Well-structured content is quality signal
        if parsed.title and parsed.meta_tags.get("description"):
            quality_signals.append("proper_metadata")

        # Clamp score to 0-100 range
        spam_score = max(0, min(100, spam_score))

        # Determine recommendation based on score
        if spam_score > 70:
            recommendation = "likely_spam"
            confidence = 0.8
        elif spam_score > 40:
            recommendation = "suspicious"
            confidence = 0.6
        else:
            recommendation = "likely_legitimate"
            confidence = 0.7

        logger.info(f"Spam analysis for {url}: score={spam_score}, recommendation={recommendation}")

        return SpamAnalysis(
            url=url,
            spam_score=spam_score,
            confidence=confidence,
            spam_signals=spam_signals,
            quality_signals=quality_signals,
            recommendation=recommendation,
        )

    except Exception as e:
        logger.error(f"Error detecting spam for {url}: {e}", exc_info=True)
        # Return neutral analysis on error
        return SpamAnalysis(
            url=url,
            spam_score=50.0,
            confidence=0.5,
            spam_signals=["analysis_error"],
            quality_signals=[],
            recommendation="suspicious",
        )


async def trend_analysis(
    domain: str,
    crawl_ids: list[str],
    *,
    sample_size: int = 100,
) -> TrendAnalysis:
    """Analyze trends in domain evolution across multiple crawls.

    Tracks changes over time:
    - Page count trends
    - Technology adoption/removal
    - Content volume

    Args:
        domain: Domain to analyze (e.g., "example.com")
        crawl_ids: List of crawl IDs in chronological order
        sample_size: Number of pages to sample per crawl

    Returns:
        TrendAnalysis with detected trends and insights

    Example:
        >>> result = await trend_analysis(
        ...     "example.com",
        ...     ["CC-MAIN-2024-10", "CC-MAIN-2024-18"],
        ...     sample_size=100
        ... )
        >>> print(result.insights)
        ['Domain is growing: 25.5% increase in indexed pages']
    """
    logger.info(f"Analyzing trends for domain {domain} across {len(crawl_ids)} crawls")

    from .aggregation import domain_evolution_timeline

    try:
        # Get evolution data from existing tool
        timeline = await domain_evolution_timeline(domain, crawl_ids, sample_size)

        trends = []
        insights = []

        # Analyze page count trend
        if hasattr(timeline, "page_counts") and timeline.page_counts:
            page_counts = list(timeline.page_counts.values())
            if len(page_counts) >= 2:
                initial_count = page_counts[0]
                final_count = page_counts[-1]

                # Calculate rate of change
                if initial_count > 0:
                    rate_of_change = ((final_count - initial_count) / initial_count) * 100
                else:
                    rate_of_change = 100.0 if final_count > 0 else 0.0

                # Determine direction
                if rate_of_change > 5:
                    direction = "increasing"
                elif rate_of_change < -5:
                    direction = "decreasing"
                else:
                    direction = "stable"

                trends.append(
                    Trend(
                        metric="page_count",
                        direction=direction,
                        rate_of_change=round(rate_of_change, 2),
                        confidence=0.8,
                    )
                )

                # Generate insights
                if direction == "increasing":
                    insights.append(
                        f"Domain is growing: {rate_of_change:.1f}% increase in indexed pages"
                    )
                elif direction == "decreasing":
                    insights.append(
                        f"Domain is shrinking: {abs(rate_of_change):.1f}% decrease in indexed pages"
                    )
                else:
                    insights.append(
                        f"Domain size is stable: {abs(rate_of_change):.1f}% change in indexed pages"
                    )

        # Analyze technology adoption trends
        if hasattr(timeline, "technologies_added") and timeline.technologies_added:
            tech_added_counts = [len(v) for v in timeline.technologies_added.values()]
            if tech_added_counts:
                avg_adoption = sum(tech_added_counts) / len(tech_added_counts)
                if avg_adoption > 1:
                    trends.append(
                        Trend(
                            metric="technology_adoption",
                            direction="increasing",
                            rate_of_change=round(avg_adoption, 2),
                            confidence=0.7,
                        )
                    )
                    insights.append(
                        f"Active technology adoption: averaging {avg_adoption:.1f} new technologies per crawl"
                    )

        # Analyze technology removal trends
        if hasattr(timeline, "technologies_removed") and timeline.technologies_removed:
            tech_removed_counts = [len(v) for v in timeline.technologies_removed.values()]
            if tech_removed_counts:
                avg_removal = sum(tech_removed_counts) / len(tech_removed_counts)
                if avg_removal > 1:
                    trends.append(
                        Trend(
                            metric="technology_removal",
                            direction="decreasing",
                            rate_of_change=round(-avg_removal, 2),
                            confidence=0.7,
                        )
                    )
                    insights.append(
                        f"Technology removal trend: averaging {avg_removal:.1f} removed technologies per crawl"
                    )

        logger.info(
            f"Trend analysis complete for {domain}: {len(trends)} trends, {len(insights)} insights"
        )

        return TrendAnalysis(
            domain=domain,
            time_period={
                "start": crawl_ids[0] if crawl_ids else "unknown",
                "end": crawl_ids[-1] if crawl_ids else "unknown",
            },
            trends=trends,
            insights=insights,
        )

    except Exception as e:
        logger.error(f"Error analyzing trends for {domain}: {e}", exc_info=True)
        # Return empty analysis on error
        return TrendAnalysis(
            domain=domain,
            time_period={
                "start": crawl_ids[0] if crawl_ids else "unknown",
                "end": crawl_ids[-1] if crawl_ids else "unknown",
            },
            trends=[],
            insights=[f"Error analyzing trends: {str(e)}"],
        )
