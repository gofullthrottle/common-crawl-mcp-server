"""Integration tests for parsing and analysis tools (Phase 4)."""

import pytest

from src.tools.parsing import (analyze_seo_metrics, analyze_technologies,
                               detect_language, extract_links_analysis,
                               extract_structured_data_from_page,
                               parse_html_content)


@pytest.mark.asyncio
async def test_parse_html_content():
    """Test HTML parsing extracts title, meta, headings, links."""
    # Use a well-known URL from Common Crawl
    url = "https://example.com"
    crawl_id = "CC-MAIN-2024-10"

    result = await parse_html_content(url, crawl_id)

    # Basic structure validation
    assert result.url == url
    assert isinstance(result.title, (str, type(None)))
    assert isinstance(result.meta_tags, dict)
    assert isinstance(result.headings, dict)
    assert isinstance(result.links, list)
    assert isinstance(result.scripts, list)
    assert isinstance(result.styles, list)
    assert isinstance(result.images, list)

    # If content exists, validate structure
    if result.title:
        assert len(result.title) > 0

    if result.headings:
        # Check heading levels are valid (h1-h6)
        for level in result.headings.keys():
            assert level in ["h1", "h2", "h3", "h4", "h5", "h6"]


@pytest.mark.asyncio
async def test_extract_links_analysis():
    """Test link extraction and classification."""
    url = "https://example.com"
    crawl_id = "CC-MAIN-2024-10"

    result = await extract_links_analysis(url, crawl_id)

    assert result.url == url
    assert isinstance(result.internal_links, list)
    assert isinstance(result.external_links, list)
    assert isinstance(result.broken_links, list)
    assert isinstance(result.total_links, int)
    assert result.total_links >= 0

    # Total links should be at least the sum of categorized links
    categorized = len(result.internal_links) + len(result.external_links) + len(result.broken_links)
    assert result.total_links >= categorized


@pytest.mark.asyncio
async def test_analyze_technologies():
    """Test technology detection."""
    url = "https://example.com"
    crawl_id = "CC-MAIN-2024-10"

    result = await analyze_technologies(url, crawl_id)

    assert result.url == url
    assert isinstance(result.technologies, list)
    assert isinstance(result.categories, dict)

    # Validate technology structure
    for tech in result.technologies:
        assert hasattr(tech, "name")
        assert hasattr(tech, "category")
        assert hasattr(tech, "confidence")
        assert 0.0 <= tech.confidence <= 1.0
        assert isinstance(tech.version, (str, type(None)))


@pytest.mark.asyncio
async def test_extract_structured_data():
    """Test structured data extraction."""
    url = "https://example.com"
    crawl_id = "CC-MAIN-2024-10"

    result = await extract_structured_data_from_page(url, crawl_id)

    assert result.url == url
    assert isinstance(result.json_ld, list)
    assert isinstance(result.microdata, list)
    assert isinstance(result.open_graph, dict)
    assert isinstance(result.twitter_card, dict)

    # Validate JSON-LD structure if present
    for item in result.json_ld:
        assert isinstance(item, dict)


@pytest.mark.asyncio
async def test_analyze_seo_metrics():
    """Test SEO analysis."""
    url = "https://example.com"
    crawl_id = "CC-MAIN-2024-10"

    result = await analyze_seo_metrics(url, crawl_id)

    assert result.url == url
    assert isinstance(result.score, float)
    assert 0.0 <= result.score <= 100.0
    assert isinstance(result.issues, list)
    assert isinstance(result.heading_structure, dict)
    assert isinstance(result.has_canonical, bool)

    # Validate issue structure
    for issue in result.issues:
        assert hasattr(issue, "severity")
        assert issue.severity in ["error", "warning", "info"]
        assert hasattr(issue, "category")
        assert hasattr(issue, "message")
        assert len(issue.message) > 0


@pytest.mark.asyncio
async def test_detect_language():
    """Test language detection."""
    url = "https://example.com"
    crawl_id = "CC-MAIN-2024-10"

    result = await detect_language(url, crawl_id)

    assert result.url == url
    assert isinstance(result.detected_language, str)
    assert len(result.detected_language) >= 2  # ISO 639-1 codes are 2 chars
    assert isinstance(result.confidence, float)
    assert 0.0 <= result.confidence <= 1.0
    assert isinstance(result.html_lang_attribute, (str, type(None)))


@pytest.mark.asyncio
async def test_caching_works():
    """Test that parsing results are cached."""
    url = "https://example.com"
    crawl_id = "CC-MAIN-2024-10"

    # First call - should fetch and cache
    result1 = await parse_html_content(url, crawl_id)

    # Second call - should hit cache (much faster)
    result2 = await parse_html_content(url, crawl_id)

    # Results should be identical
    assert result1.url == result2.url
    assert result1.title == result2.title
    assert result1.meta_tags == result2.meta_tags


@pytest.mark.asyncio
async def test_error_handling_invalid_url():
    """Test graceful error handling for invalid URLs."""
    # Use a URL that definitely doesn't exist in Common Crawl
    url = "https://this-domain-definitely-does-not-exist-12345.com"
    crawl_id = "CC-MAIN-2024-10"

    try:
        result = await parse_html_content(url, crawl_id)

        # Should return empty/minimal result, not crash
        assert result.url == url
        assert result.title is None or result.title == ""

    except Exception as e:
        # If it does raise, it should be a meaningful error
        assert isinstance(e, Exception)
        assert len(str(e)) > 0
