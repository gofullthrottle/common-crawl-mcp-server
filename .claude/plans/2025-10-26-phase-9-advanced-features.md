# Phase 9: Advanced Features Implementation Plan

**Date:** 2025-10-26
**Status:** In Progress
**Goal:** Implement 3 advanced analysis tools from Phase 9 (Wave 3)

## Overview

Implement intelligent classification, spam detection, and trend analysis capabilities by composing existing tool primitives. This completes the deferred Phase 9 work from the Ultra Development Marathon.

## Context

From the marathon completion:
- **Project Status:** 70% complete (Phases 1-8 done)
- **Existing Tools:** 32 MCP tools, 7 resources, 4 prompts
- **Phase 9 Status:** Previously marked OPTIONAL and deferred
- **User Request:** Implement 3 of 4 Phase 9 tools (excluding dataset_management)

## Tools to Implement

### 1. content_classification
**Purpose:** Classify web pages by type (blog, e-commerce, news, documentation, etc.)

**Approach:** Composition of existing tools
- analyze_seo_metrics - For content structure signals
- detect_language - For language detection
- extract_structured_data_from_page - For schema.org signals

**Classification Logic:**
1. URL pattern signals (/blog/, /product/, /docs/, etc.)
2. Schema.org structured data (BlogPosting, Product, NewsArticle)
3. Heading structure quality
4. Confidence calculation based on signal strength

**Output:** ContentClassification model with page_type, confidence, signals, language, quality score

### 2. spam_detection
**Purpose:** Identify spam, low-quality, or auto-generated content

**Approach:** Composition of existing tools
- parse_html_content - For content analysis
- analyze_technologies - For legitimacy signals

**Detection Logic:**
1. Security headers check (missing = spam signal)
2. Title/meta quality (poor = spam signal)
3. Link density analysis (excessive external = spam)
4. Keyword stuffing detection (repetition ratio)
5. Technology signals (known tech = quality)
6. Spam score 0-100 with recommendation

**Output:** SpamAnalysis model with spam_score, confidence, signals, recommendation

### 3. trend_analysis
**Purpose:** Track technology adoption trends across multiple crawls

**Approach:** Composition of existing tools
- domain_evolution_timeline - For historical data

**Analysis Logic:**
1. Page count trends (increasing/decreasing/stable)
2. Technology adoption rates
3. Statistical rate of change calculations
4. Insight generation from patterns

**Output:** TrendAnalysis model with trends list and insights

## Implementation Steps

### Step 0: Document This Plan ✅
- Save plan to `.claude/plans/2025-10-26-phase-9-advanced-features.md`
- Track progress through todos

### Step 1: Add Pydantic Models
**File:** `src/models/schemas.py`
**Estimated Time:** 15 minutes

Add 4 new model classes:

```python
class ContentClassification(BaseModel):
    """Web page classification result."""
    url: str
    page_type: str  # blog, product, documentation, news, landing_page, other
    confidence: float  # 0.0 to 1.0
    signals: dict[str, Any]  # Evidence for classification
    language: str
    content_quality_score: float  # 0-100

class SpamAnalysis(BaseModel):
    """Spam detection result."""
    url: str
    spam_score: float  # 0-100, higher = more likely spam
    confidence: float  # 0.0-1.0
    spam_signals: list[str]
    quality_signals: list[str]
    recommendation: str  # "likely_spam", "suspicious", "likely_legitimate"

class Trend(BaseModel):
    """Individual trend detected."""
    metric: str  # "page_count", "technology_adoption", "content_volume"
    direction: str  # "increasing", "decreasing", "stable"
    rate_of_change: float  # Percentage change
    confidence: float  # 0.0-1.0

class TrendAnalysis(BaseModel):
    """Trend analysis result."""
    domain: str
    time_period: dict[str, str]  # {"start": crawl_id, "end": crawl_id}
    trends: list[Trend]
    insights: list[str]
```

### Step 2: Implement Advanced Tools
**File:** `src/tools/advanced.py` (new file)
**Estimated Time:** 45 minutes
**Lines:** ~350

Module structure:
```python
"""Advanced analysis features for Common Crawl MCP Server.

This module provides intelligent classification, spam detection, and trend
analysis by composing existing tool primitives.
"""

import logging
from typing import Any, Optional

from ..models.schemas import (
    ContentClassification,
    SpamAnalysis,
    Trend,
    TrendAnalysis,
)

logger = logging.getLogger(__name__)

__all__ = [
    "content_classification",
    "spam_detection",
    "trend_analysis",
]
```

#### Function 1: content_classification

```python
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
    from .parsing import (
        analyze_seo_metrics,
        detect_language,
        extract_structured_data_from_page,
    )

    # Gather signals
    seo = await analyze_seo_metrics(url, crawl_id)
    lang = await detect_language(url, crawl_id)
    structured = await extract_structured_data_from_page(url, crawl_id)

    signals = {}

    # URL pattern signals
    if "/blog/" in url or "/post/" in url or "/article/" in url:
        signals["url_pattern"] = "blog"
    elif "/product/" in url or "/shop/" in url or "/item/" in url:
        signals["url_pattern"] = "product"
    elif "/docs/" in url or "/documentation/" in url or "/api/" in url:
        signals["url_pattern"] = "documentation"
    elif "/news/" in url:
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

    # Strong signals (schema.org)
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

    return ContentClassification(
        url=url,
        page_type=page_type,
        confidence=confidence,
        signals=signals,
        language=lang.language,
        content_quality_score=seo.seo_score,
    )
```

#### Function 2: spam_detection

```python
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
    from .parsing import analyze_technologies, parse_html_content

    # Gather signals
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
            link for link in parsed.links
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

    # Clamp score
    spam_score = max(0, min(100, spam_score))

    # Recommendation
    if spam_score > 70:
        recommendation = "likely_spam"
        confidence = 0.8
    elif spam_score > 40:
        recommendation = "suspicious"
        confidence = 0.6
    else:
        recommendation = "likely_legitimate"
        confidence = 0.7

    return SpamAnalysis(
        url=url,
        spam_score=spam_score,
        confidence=confidence,
        spam_signals=spam_signals,
        quality_signals=quality_signals,
        recommendation=recommendation,
    )
```

#### Function 3: trend_analysis

```python
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
    from .aggregation import domain_evolution_timeline

    # Get evolution data
    timeline = await domain_evolution_timeline(domain, crawl_ids, sample_size)

    trends = []
    insights = []

    # Analyze page count trend
    if hasattr(timeline, 'page_counts') and timeline.page_counts:
        page_counts = list(timeline.page_counts.values())
        if len(page_counts) >= 2:
            initial_count = page_counts[0]
            final_count = page_counts[-1]

            if initial_count > 0:
                rate_of_change = ((final_count - initial_count) / initial_count) * 100
            else:
                rate_of_change = 100.0 if final_count > 0 else 0.0

            if rate_of_change > 5:
                direction = "increasing"
            elif rate_of_change < -5:
                direction = "decreasing"
            else:
                direction = "stable"

            trends.append(Trend(
                metric="page_count",
                direction=direction,
                rate_of_change=round(rate_of_change, 2),
                confidence=0.8,
            ))

            if direction == "increasing":
                insights.append(
                    f"Domain is growing: {rate_of_change:.1f}% increase in indexed pages"
                )
            elif direction == "decreasing":
                insights.append(
                    f"Domain is shrinking: {abs(rate_of_change):.1f}% decrease in indexed pages"
                )

    # Analyze technology adoption trends
    if hasattr(timeline, 'technologies_added') and timeline.technologies_added:
        tech_added_counts = [len(v) for v in timeline.technologies_added.values()]
        if tech_added_counts:
            avg_adoption = sum(tech_added_counts) / len(tech_added_counts)
            if avg_adoption > 1:
                trends.append(Trend(
                    metric="technology_adoption",
                    direction="increasing",
                    rate_of_change=round(avg_adoption, 2),
                    confidence=0.7,
                ))
                insights.append(
                    f"Active technology adoption: averaging {avg_adoption:.1f} new technologies per crawl"
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
```

### Step 3: Register MCP Tools
**File:** `src/server.py`
**Estimated Time:** 15 minutes
**Location:** After Phase 6 export tools (around line 687)

```python
# ============================================================================
# Phase 9: Advanced Analysis Tools
# ============================================================================

from .tools import advanced

@mcp.tool()
async def classify_content(url: str, crawl_id: str = "CC-MAIN-2024-10") -> dict[str, Any]:
    """Classify web page by type and purpose.

    Detects page types: blog, product, documentation, news, landing_page, other

    Args:
        url: URL to classify
        crawl_id: Common Crawl crawl identifier

    Returns:
        Classification result with page type, confidence, and signals
    """
    result = await advanced.content_classification(url, crawl_id)
    return result.model_dump()


@mcp.tool()
async def detect_spam(url: str, crawl_id: str = "CC-MAIN-2024-10") -> dict[str, Any]:
    """Detect if page is spam or low-quality.

    Analyzes content quality signals and returns spam score 0-100.

    Args:
        url: URL to analyze
        crawl_id: Common Crawl crawl identifier

    Returns:
        Spam analysis with score, signals, and recommendation
    """
    result = await advanced.spam_detection(url, crawl_id)
    return result.model_dump()


@mcp.tool()
async def analyze_trends(
    domain: str,
    crawl_ids: list[str],
    sample_size: int = 100
) -> dict[str, Any]:
    """Analyze trends in domain evolution across multiple crawls.

    Tracks page count changes, technology adoption, and generates insights.

    Args:
        domain: Domain to analyze (e.g., "example.com")
        crawl_ids: List of crawl IDs in chronological order
        sample_size: Number of pages to sample per crawl

    Returns:
        Trend analysis with detected trends and insights
    """
    result = await advanced.trend_analysis(domain, crawl_ids, sample_size=sample_size)
    return result.model_dump()
```

### Step 4: Update Module Exports
**File:** `src/tools/__init__.py`
**Estimated Time:** 5 minutes

Add to existing imports:
```python
from . import advanced
```

### Step 5: Integration Verification
**Estimated Time:** 10 minutes

Test commands:
```bash
# Verify server loads
uv run python -c "from src.server import mcp; print('✅ Server loads successfully')"

# Verify tool count
uv run python -c "from src.server import mcp; print(f'Total tools: {len(mcp._mcp_tools)}')"
```

Expected output:
- Server loads without errors
- Total tools: 35 (32 existing + 3 new)

### Final Step: Document Solution Summary
Create `.claude/plans/2025-10-26-phase-9-advanced-features-solution-summary.md`

## Success Criteria

- ✅ All 3 functions follow Wave 3 specification
- ✅ Composition pattern used (no primitive reimplementation)
- ✅ Error handling for dependent tool failures
- ✅ MCP server loads with 35 tools
- ✅ Pydantic models properly typed and validated
- ✅ Code quality matches existing modules
- ✅ Comprehensive docstrings with examples
- ✅ Proper logging at INFO level

## Time Estimates

| Step | Task | Time |
|------|------|------|
| 0 | Document plan | 5 min |
| 1 | Add Pydantic models | 15 min |
| 2 | Implement advanced.py | 45 min |
| 3 | Register MCP tools | 15 min |
| 4 | Update exports | 5 min |
| 5 | Verify integration | 10 min |
| Final | Document summary | 5 min |
| **Total** | | **~100 min** |

## Files Modified

1. `src/models/schemas.py` - Add 4 models (~50 lines)
2. `src/tools/advanced.py` - NEW file (~350 lines)
3. `src/server.py` - Add 3 registrations (~50 lines)
4. `src/tools/__init__.py` - Export advanced (~1 line)

**Total:** ~450 lines across 4 files

## Project Impact

**Before:**
- 32 MCP tools
- 7 resources
- 4 prompts
- 70% project completion

**After:**
- 35 MCP tools (+3)
- 7 resources
- 4 prompts
- ~72% project completion (Phase 9 partial)

## Risks and Mitigation

**Risk 1: Dependent tool failures**
- Mitigation: Error handling in each function, graceful degradation

**Risk 2: Model validation errors**
- Mitigation: Comprehensive type hints, test with known data

**Risk 3: Performance impact**
- Mitigation: Composition reuses cached results from primitives

## References

- Wave 3 specification: `.claude/tasks/wave-3-advanced-features.md`
- Marathon completion: `.claude/marathon-completion-report.md`
- Existing tool patterns: `src/tools/parsing.py`, `src/tools/aggregation.py`
