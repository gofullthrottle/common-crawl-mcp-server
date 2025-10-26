"""Aggregation and statistics tools for Common Crawl MCP Server.

This module provides domain-wide analysis tools that aggregate data across
multiple pages to generate comprehensive reports, link graphs, and statistics.
"""

import asyncio
import logging
import re
from collections import Counter, defaultdict
from typing import Any, Callable, Optional
from urllib.parse import urlparse

from ..core.cache import CacheManager
from ..core.cc_client import CDXClient
from ..models.schemas import TechReport, LinkGraph, KeywordStats, Timeline, HeaderReport
from .parsing import analyze_technologies, extract_links_analysis, parse_html_content
from .fetching import fetch_page_content as fetch_page_dict

logger = logging.getLogger(__name__)

# Module-level cache and CDX client
_cache: Optional[CacheManager] = None
_cdx_client: Optional[CDXClient] = None


def _get_cache() -> CacheManager:
    """Get cache manager instance."""
    global _cache
    if _cache is None:
        from ..server import get_cache

        _cache = get_cache()
    return _cache


def _get_cdx_client() -> CDXClient:
    """Get CDX client instance."""
    global _cdx_client
    if _cdx_client is None:
        from ..server import get_cdx_client

        _cdx_client = get_cdx_client()
    return _cdx_client


async def domain_technology_report(
    domain: str,
    crawl_id: str = "CC-MAIN-2024-10",
    sample_size: int = 100,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> TechReport:
    """Generate technology usage report for an entire domain.

    Args:
        domain: Domain to analyze (e.g., "example.com")
        crawl_id: Common Crawl crawl identifier
        sample_size: Maximum number of pages to analyze (default: 100)
        progress_callback: Optional callback(current, total) for progress tracking

    Returns:
        TechReport: Aggregated technology usage across domain

    Example:
        >>> report = await domain_technology_report("wordpress.com", sample_size=50)
        >>> print(f"Analyzed {report.pages_analyzed} pages")
        >>> for tech, percentage in report.adoption_percentage.items():
        ...     print(f"{tech}: {percentage:.1f}%")
    """
    cache_key = f"tech_report:{crawl_id}:{domain}:{sample_size}"

    # Check cache (7-day TTL)
    cache = _get_cache()
    cached = await cache.get(cache_key)
    if cached:
        logger.info(f"Returning cached technology report for {domain}")
        return TechReport(**cached)

    logger.info(f"Generating technology report for {domain} (sample: {sample_size})")

    # Step 1: Get all URLs from domain
    cdx = _get_cdx_client()

    search_results = await cdx.search_index(
        query=domain, crawl_id=crawl_id, limit=sample_size, match_type="domain"
    )

    if not search_results:
        logger.warning(f"No pages found for domain: {domain}")
        return TechReport(
            domain=domain,
            crawl_id=crawl_id,
            pages_analyzed=0,
            technologies={},
            categories={},
            adoption_percentage={},
        )

    # Extract unique URLs (CDX may have duplicates)
    urls = list(set(result.url for result in search_results))
    urls = urls[:sample_size]  # Limit to sample size

    total_pages = len(urls)
    logger.info(f"Found {total_pages} unique pages to analyze")

    # Step 2: Analyze technologies for each page (with concurrency control)
    semaphore = asyncio.Semaphore(10)  # Limit concurrent requests

    async def analyze_with_semaphore(url: str, index: int) -> Optional[dict]:
        """Analyze single page with semaphore."""
        async with semaphore:
            try:
                result = await analyze_technologies(url, crawl_id)

                # Report progress
                if progress_callback:
                    progress_callback(index + 1, total_pages)

                return result.model_dump()
            except Exception as e:
                logger.error(f"Error analyzing {url}: {e}")
                return None

    # Analyze all pages concurrently
    tasks = [analyze_with_semaphore(url, i) for i, url in enumerate(urls)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter out None and exceptions
    valid_results = [r for r in results if r and not isinstance(r, Exception)]

    pages_analyzed = len(valid_results)
    logger.info(f"Successfully analyzed {pages_analyzed}/{total_pages} pages")

    # Step 3: Aggregate technology usage
    tech_counter = Counter()  # technology -> page count
    category_tech_counter = defaultdict(Counter)  # category -> {tech: count}

    for result in valid_results:
        for tech in result.get("technologies", []):
            tech_name = tech["name"]
            tech_category = tech["category"]

            tech_counter[tech_name] += 1
            category_tech_counter[tech_category][tech_name] += 1

    # Step 4: Calculate adoption percentages
    adoption_percentage = {}
    for tech_name, count in tech_counter.items():
        adoption_percentage[tech_name] = (count / pages_analyzed) * 100

    # Step 5: Convert category counter to dict format
    categories_dict = {}
    for category, tech_counts in category_tech_counter.items():
        categories_dict[category] = dict(tech_counts)

    # Create report
    report = TechReport(
        domain=domain,
        crawl_id=crawl_id,
        pages_analyzed=pages_analyzed,
        technologies=dict(tech_counter),
        categories=categories_dict,
        adoption_percentage=adoption_percentage,
    )

    # Cache for 7 days
    await cache.set(cache_key, report.model_dump(), ttl=7 * 24 * 3600)

    return report


async def domain_link_graph(
    domain: str,
    crawl_id: str = "CC-MAIN-2024-10",
    sample_size: int = 100,
    depth: int = 1,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> LinkGraph:
    """Generate link graph for an entire domain.

    Args:
        domain: Domain to analyze (e.g., "example.com")
        crawl_id: Common Crawl crawl identifier
        sample_size: Maximum number of pages to analyze (default: 100)
        depth: Link crawl depth (1=direct links only, 2=links from linked pages)
        progress_callback: Optional callback(current, total) for progress tracking

    Returns:
        LinkGraph: Graph structure with nodes, edges, hub pages, and PageRank

    Example:
        >>> graph = await domain_link_graph("wordpress.com", sample_size=50)
        >>> print(f"Found {len(graph.nodes)} pages")
        >>> print(f"Hub pages: {graph.hub_pages[:5]}")
    """
    cache_key = f"link_graph:{crawl_id}:{domain}:{sample_size}:{depth}"

    # Check cache (7-day TTL)
    cache = _get_cache()
    cached = await cache.get(cache_key)
    if cached:
        logger.info(f"Returning cached link graph for {domain}")
        return LinkGraph(**cached)

    logger.info(f"Generating link graph for {domain} (sample: {sample_size}, depth: {depth})")

    # Step 1: Get all URLs from domain
    cdx = _get_cdx_client()

    search_results = await cdx.search_index(
        query=domain, crawl_id=crawl_id, limit=sample_size, match_type="domain"
    )

    if not search_results:
        logger.warning(f"No pages found for domain: {domain}")
        return LinkGraph(
            domain=domain,
            crawl_id=crawl_id,
            nodes=[],
            edges=[],
            hub_pages=[],
            pagerank={}
        )

    # Extract unique URLs (CDX may have duplicates)
    urls = list(set(result.url for result in search_results))
    urls = urls[:sample_size]  # Limit to sample size

    total_pages = len(urls)
    logger.info(f"Found {total_pages} unique pages to analyze")

    # Step 2: Extract links from each page (with concurrency control)
    semaphore = asyncio.Semaphore(10)  # Limit concurrent requests

    async def extract_with_semaphore(url: str, index: int) -> Optional[dict]:
        """Extract links from single page with semaphore."""
        async with semaphore:
            try:
                result = await extract_links_analysis(url, crawl_id)

                # Report progress
                if progress_callback:
                    progress_callback(index + 1, total_pages)

                return result.model_dump()
            except Exception as e:
                logger.error(f"Error extracting links from {url}: {e}")
                return None

    # Extract all links concurrently
    tasks = [extract_with_semaphore(url, i) for i, url in enumerate(urls)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter out None and exceptions
    valid_results = [r for r in results if r and not isinstance(r, Exception)]

    logger.info(f"Successfully extracted links from {len(valid_results)}/{total_pages} pages")

    # Step 3: Build graph structure
    nodes = set(urls)  # Start with our analyzed pages
    edges = []
    inbound_counts = defaultdict(int)  # Track incoming links
    outbound_counts = defaultdict(int)  # Track outgoing links

    for result in valid_results:
        source_url = result.get("url")
        if not source_url:
            continue

        # Get internal links (within same domain)
        internal_links = result.get("internal_links", [])

        for link_info in internal_links:
            target_url = link_info.get("url") if isinstance(link_info, dict) else link_info

            if not target_url:
                continue

            # Add edge
            edges.append((source_url, target_url))

            # Track counts
            outbound_counts[source_url] += 1
            inbound_counts[target_url] += 1

            # Add target to nodes if not already present
            nodes.add(target_url)

    # Convert nodes to list
    nodes_list = list(nodes)

    logger.info(f"Graph: {len(nodes_list)} nodes, {len(edges)} edges")

    # Step 4: Calculate hub pages (most linked-to)
    hub_pages = sorted(
        [(url, count) for url, count in inbound_counts.items()],
        key=lambda x: x[1],
        reverse=True
    )[:20]  # Top 20 hub pages

    # Step 5: Calculate simple PageRank
    pagerank = _calculate_pagerank(nodes_list, edges, iterations=20)

    # Create graph
    graph = LinkGraph(
        domain=domain,
        crawl_id=crawl_id,
        nodes=nodes_list,
        edges=edges,
        hub_pages=hub_pages,
        pagerank=pagerank,
    )

    # Cache for 7 days
    await cache.set(cache_key, graph.model_dump(), ttl=7 * 24 * 3600)

    return graph


def _calculate_pagerank(
    nodes: list[str],
    edges: list[tuple[str, str]],
    damping: float = 0.85,
    iterations: int = 20,
) -> dict[str, float]:
    """Calculate PageRank scores for graph nodes.

    Args:
        nodes: List of node URLs
        edges: List of (from_url, to_url) edge pairs
        damping: Damping factor (default: 0.85)
        iterations: Number of iterations (default: 20)

    Returns:
        Dictionary mapping URL to PageRank score
    """
    if not nodes:
        return {}

    # Initialize PageRank scores
    num_nodes = len(nodes)
    scores = {node: 1.0 / num_nodes for node in nodes}

    # Build outbound links map
    outbound = defaultdict(list)
    for source, target in edges:
        if source in scores and target in scores:  # Only include nodes in our set
            outbound[source].append(target)

    # Calculate PageRank iteratively
    for _ in range(iterations):
        new_scores = {}

        for node in nodes:
            # Base probability (random surfer)
            rank = (1 - damping) / num_nodes

            # Add contributions from inbound links
            for source, targets in outbound.items():
                if node in targets:
                    # Distribute source's PageRank across its outbound links
                    contribution = scores[source] / len(targets)
                    rank += damping * contribution

            new_scores[node] = rank

        scores = new_scores

    # Normalize scores to sum to 1.0
    total = sum(scores.values())
    if total > 0:
        scores = {node: score / total for node, score in scores.items()}

    return scores


async def keyword_frequency_analysis(
    domain: str,
    keywords: list[str],
    crawl_id: str = "CC-MAIN-2024-10",
    sample_size: int = 100,
    case_sensitive: bool = False,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> KeywordStats:
    """Analyze keyword frequency across a domain.

    Args:
        domain: Domain to analyze (e.g., "example.com")
        keywords: List of keywords to search for
        crawl_id: Common Crawl crawl identifier
        sample_size: Maximum number of pages to analyze (default: 100)
        case_sensitive: Whether keyword matching is case-sensitive
        progress_callback: Optional callback(current, total) for progress tracking

    Returns:
        KeywordStats: Keyword frequencies and TF-IDF scores

    Example:
        >>> stats = await keyword_frequency_analysis(
        ...     "example.com",
        ...     ["python", "javascript", "machine learning"],
        ...     sample_size=50
        ... )
        >>> print(f"'python' found on {len(stats.frequencies['python'])} pages")
    """
    cache_key = f"keyword_freq:{crawl_id}:{domain}:{'-'.join(sorted(keywords))}:{sample_size}:{case_sensitive}"

    # Check cache (7-day TTL)
    cache = _get_cache()
    cached = await cache.get(cache_key)
    if cached:
        logger.info(f"Returning cached keyword analysis for {domain}")
        return KeywordStats(**cached)

    logger.info(f"Analyzing keywords for {domain} (sample: {sample_size})")

    # Step 1: Get all URLs from domain
    cdx = _get_cdx_client()

    search_results = await cdx.search_index(
        query=domain, crawl_id=crawl_id, limit=sample_size, match_type="domain"
    )

    if not search_results:
        logger.warning(f"No pages found for domain: {domain}")
        return KeywordStats(
            keywords=keywords,
            frequencies={},
            total_occurrences={kw: 0 for kw in keywords},
            tfidf_scores={}
        )

    # Extract unique URLs
    urls = list(set(result.url for result in search_results))
    urls = urls[:sample_size]

    total_pages = len(urls)
    logger.info(f"Found {total_pages} unique pages to analyze")

    # Step 2: Extract text content from each page
    semaphore = asyncio.Semaphore(10)

    async def extract_text_with_semaphore(url: str, index: int) -> Optional[dict]:
        """Extract text content from single page."""
        async with semaphore:
            try:
                result = await parse_html_content(url, crawl_id)

                # Report progress
                if progress_callback:
                    progress_callback(index + 1, total_pages)

                return {
                    "url": result.url,
                    "text": result.text or ""
                }
            except Exception as e:
                logger.error(f"Error extracting text from {url}: {e}")
                return None

    # Extract all text concurrently
    tasks = [extract_text_with_semaphore(url, i) for i, url in enumerate(urls)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter out None and exceptions
    valid_results = [r for r in results if r and not isinstance(r, Exception)]

    logger.info(f"Successfully extracted text from {len(valid_results)}/{total_pages} pages")

    # Step 3: Count keyword occurrences
    frequencies = {kw: {} for kw in keywords}
    total_occurrences = {kw: 0 for kw in keywords}
    document_frequencies = {kw: 0 for kw in keywords}  # Number of documents containing keyword

    for result in valid_results:
        url = result["url"]
        text = result["text"]

        # Normalize text for matching
        search_text = text if case_sensitive else text.lower()

        for keyword in keywords:
            search_keyword = keyword if case_sensitive else keyword.lower()

            # Count occurrences using word boundary matching
            pattern = r'\b' + re.escape(search_keyword) + r'\b'
            matches = re.findall(pattern, search_text)
            count = len(matches)

            if count > 0:
                frequencies[keyword][url] = count
                total_occurrences[keyword] += count
                document_frequencies[keyword] += 1

    # Step 4: Calculate TF-IDF scores
    tfidf_scores = _calculate_tfidf(
        frequencies,
        document_frequencies,
        total_pages
    )

    # Create stats
    stats = KeywordStats(
        keywords=keywords,
        frequencies=frequencies,
        total_occurrences=total_occurrences,
        tfidf_scores=tfidf_scores
    )

    # Cache for 7 days
    await cache.set(cache_key, stats.model_dump(), ttl=7 * 24 * 3600)

    return stats


def _calculate_tfidf(
    frequencies: dict[str, dict[str, int]],
    document_frequencies: dict[str, int],
    total_documents: int,
) -> dict[str, dict[str, float]]:
    """Calculate TF-IDF scores for keywords.

    Args:
        frequencies: keyword -> {url: count} mapping
        document_frequencies: keyword -> number of documents containing it
        total_documents: Total number of documents analyzed

    Returns:
        Dictionary mapping keyword -> {url: tfidf_score}
    """
    import math

    tfidf_scores = {}

    for keyword, url_counts in frequencies.items():
        tfidf_scores[keyword] = {}

        # Calculate IDF (inverse document frequency)
        df = document_frequencies[keyword]
        if df == 0:
            continue

        idf = math.log(total_documents / df)

        # Calculate TF-IDF for each document
        for url, count in url_counts.items():
            # TF (term frequency) = raw count normalized by document length
            # For simplicity, we use raw count here
            tf = count

            # TF-IDF = TF * IDF
            tfidf = tf * idf
            tfidf_scores[keyword][url] = round(tfidf, 4)

    return tfidf_scores


async def domain_evolution_timeline(
    domain: str,
    crawl_ids: list[str],
    sample_size: int = 100,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> Timeline:
    """Track domain evolution across multiple crawls.

    Args:
        domain: Domain to analyze (e.g., "example.com")
        crawl_ids: List of crawl IDs to compare (chronological order)
        sample_size: Maximum number of pages to analyze per crawl
        progress_callback: Optional callback(current, total) for progress tracking

    Returns:
        Timeline: Evolution metrics across crawls

    Example:
        >>> timeline = await domain_evolution_timeline(
        ...     "example.com",
        ...     ["CC-MAIN-2024-01", "CC-MAIN-2024-10"],
        ...     sample_size=50
        ... )
        >>> print(f"Growth: {timeline.page_counts}")
    """
    cache_key = f"timeline:{domain}:{'-'.join(crawl_ids)}:{sample_size}"

    # Check cache (7-day TTL)
    cache = _get_cache()
    cached = await cache.get(cache_key)
    if cached:
        logger.info(f"Returning cached timeline for {domain}")
        return Timeline(**cached)

    logger.info(f"Generating evolution timeline for {domain} across {len(crawl_ids)} crawls")

    cdx = _get_cdx_client()

    page_counts = {}
    size_bytes = {}
    technologies_by_crawl = {}

    total_crawls = len(crawl_ids)

    # Step 1: Analyze each crawl
    for crawl_index, crawl_id in enumerate(crawl_ids):
        logger.info(f"Analyzing crawl {crawl_index + 1}/{total_crawls}: {crawl_id}")

        # Report progress
        if progress_callback:
            progress_callback(crawl_index + 1, total_crawls)

        # Get page count
        search_results = await cdx.search_index(
            query=domain, crawl_id=crawl_id, limit=sample_size, match_type="domain"
        )

        if not search_results:
            logger.warning(f"No pages found for {domain} in {crawl_id}")
            page_counts[crawl_id] = 0
            size_bytes[crawl_id] = 0
            technologies_by_crawl[crawl_id] = set()
            continue

        # Extract unique URLs
        urls = list(set(result.url for result in search_results))
        urls = urls[:sample_size]

        page_counts[crawl_id] = len(urls)

        # Calculate total size (approximation from CDX records)
        total_size = sum(getattr(result, 'length', 0) for result in search_results[:sample_size])
        size_bytes[crawl_id] = total_size

        # Analyze technologies (sample first 10 pages for performance)
        sample_urls = urls[:10]
        technologies = set()

        semaphore = asyncio.Semaphore(5)  # Lower concurrency for cross-crawl analysis

        async def analyze_tech_with_semaphore(url: str) -> Optional[set]:
            """Analyze technologies for single page."""
            async with semaphore:
                try:
                    result = await analyze_technologies(url, crawl_id)
                    return {tech.name for tech in result.technologies}
                except Exception as e:
                    logger.debug(f"Error analyzing {url}: {e}")
                    return set()

        # Analyze technologies concurrently
        tasks = [analyze_tech_with_semaphore(url) for url in sample_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect all technologies
        for tech_set in results:
            if tech_set and not isinstance(tech_set, Exception):
                technologies.update(tech_set)

        technologies_by_crawl[crawl_id] = technologies

        logger.info(f"Crawl {crawl_id}: {page_counts[crawl_id]} pages, {len(technologies)} technologies")

    # Step 2: Calculate technology changes
    technologies_added = {}
    technologies_removed = {}

    for i in range(len(crawl_ids) - 1):
        current_crawl = crawl_ids[i]
        next_crawl = crawl_ids[i + 1]

        current_tech = technologies_by_crawl.get(current_crawl, set())
        next_tech = technologies_by_crawl.get(next_crawl, set())

        # Technologies added in next crawl
        added = next_tech - current_tech
        technologies_added[next_crawl] = sorted(list(added))

        # Technologies removed in next crawl
        removed = current_tech - next_tech
        technologies_removed[next_crawl] = sorted(list(removed))

    # Create timeline
    timeline = Timeline(
        domain=domain,
        crawls=crawl_ids,
        page_counts=page_counts,
        size_bytes=size_bytes,
        technologies_added=technologies_added,
        technologies_removed=technologies_removed,
    )

    # Cache for 7 days
    await cache.set(cache_key, timeline.model_dump(), ttl=7 * 24 * 3600)

    return timeline


async def header_analysis(
    domain: str,
    crawl_id: str = "CC-MAIN-2024-10",
    sample_size: int = 100,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> HeaderReport:
    """Analyze HTTP headers across a domain.

    Args:
        domain: Domain to analyze (e.g., "example.com")
        crawl_id: Common Crawl crawl identifier
        sample_size: Maximum number of pages to analyze (default: 100)
        progress_callback: Optional callback(current, total) for progress tracking

    Returns:
        HeaderReport: Header adoption rates and security score

    Example:
        >>> report = await header_analysis("example.com", sample_size=50)
        >>> print(f"Security score: {report.security_score}/100")
        >>> print(f"HSTS adoption: {report.security_headers.get('strict-transport-security', 0)}%")
    """
    cache_key = f"header_analysis:{crawl_id}:{domain}:{sample_size}"

    # Check cache (7-day TTL)
    cache = _get_cache()
    cached = await cache.get(cache_key)
    if cached:
        logger.info(f"Returning cached header analysis for {domain}")
        return HeaderReport(**cached)

    logger.info(f"Analyzing HTTP headers for {domain} (sample: {sample_size})")

    # Step 1: Get all URLs from domain
    cdx = _get_cdx_client()

    search_results = await cdx.search_index(
        query=domain, crawl_id=crawl_id, limit=sample_size, match_type="domain"
    )

    if not search_results:
        logger.warning(f"No pages found for domain: {domain}")
        return HeaderReport(
            domain=domain,
            crawl_id=crawl_id,
            pages_analyzed=0,
            security_headers={},
            caching_policies={},
            servers={},
            security_score=0.0,
            recommendations=["No data available for analysis"]
        )

    # Extract unique URLs
    urls = list(set(result.url for result in search_results))
    urls = urls[:sample_size]

    total_pages = len(urls)
    logger.info(f"Found {total_pages} unique pages to analyze")

    # Step 2: Fetch headers from each page
    semaphore = asyncio.Semaphore(10)

    async def fetch_headers_with_semaphore(url: str, index: int) -> Optional[dict]:
        """Fetch HTTP headers from single page."""
        async with semaphore:
            try:
                page_dict = await fetch_page_dict(url, crawl_id)

                # Report progress
                if progress_callback:
                    progress_callback(index + 1, total_pages)

                return {
                    "url": url,
                    "headers": page_dict.get("headers", {})
                }
            except Exception as e:
                logger.error(f"Error fetching headers from {url}: {e}")
                return None

    # Fetch all headers concurrently
    tasks = [fetch_headers_with_semaphore(url, i) for i, url in enumerate(urls)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter out None and exceptions
    valid_results = [r for r in results if r and not isinstance(r, Exception)]

    pages_analyzed = len(valid_results)
    logger.info(f"Successfully analyzed headers from {pages_analyzed}/{total_pages} pages")

    # Step 3: Analyze security headers
    security_header_counts = Counter()
    caching_policy_counts = Counter()
    server_counts = Counter()

    # Security headers to check
    SECURITY_HEADERS = [
        "strict-transport-security",  # HSTS
        "content-security-policy",  # CSP
        "x-frame-options",  # Clickjacking protection
        "x-content-type-options",  # MIME sniffing protection
        "referrer-policy",  # Referrer control
        "permissions-policy",  # Feature policy
        "x-xss-protection",  # XSS filter (legacy)
    ]

    for result in valid_results:
        headers = result["headers"]

        # Normalize header names to lowercase
        normalized_headers = {k.lower(): v for k, v in headers.items()}

        # Check security headers
        for security_header in SECURITY_HEADERS:
            if security_header in normalized_headers:
                security_header_counts[security_header] += 1

        # Check caching headers
        if "cache-control" in normalized_headers:
            cache_value = normalized_headers["cache-control"]
            # Categorize caching policies
            if "no-cache" in cache_value or "no-store" in cache_value:
                caching_policy_counts["no-cache"] += 1
            elif "max-age" in cache_value:
                caching_policy_counts["max-age"] += 1
            else:
                caching_policy_counts["other"] += 1

        # Check server header
        if "server" in normalized_headers:
            server = normalized_headers["server"]
            # Extract server name (e.g., "nginx/1.18.0" -> "nginx")
            server_name = server.split("/")[0].lower()
            server_counts[server_name] += 1

    # Step 4: Calculate adoption percentages
    security_headers_adoption = {}
    for header in SECURITY_HEADERS:
        count = security_header_counts.get(header, 0)
        adoption_percentage = (count / pages_analyzed) * 100 if pages_analyzed > 0 else 0
        security_headers_adoption[header] = round(adoption_percentage, 2)

    # Step 5: Calculate security score (0-100)
    # Each essential security header contributes to the score
    ESSENTIAL_HEADERS = [
        "strict-transport-security",
        "content-security-policy",
        "x-frame-options",
        "x-content-type-options",
    ]

    score_per_header = 100 / len(ESSENTIAL_HEADERS)
    security_score = 0.0

    for header in ESSENTIAL_HEADERS:
        adoption = security_headers_adoption.get(header, 0)
        security_score += (adoption / 100) * score_per_header

    security_score = round(security_score, 2)

    # Step 6: Generate recommendations
    recommendations = []

    if security_headers_adoption.get("strict-transport-security", 0) < 80:
        recommendations.append(
            "Enable HSTS (Strict-Transport-Security) to enforce HTTPS connections"
        )

    if security_headers_adoption.get("content-security-policy", 0) < 50:
        recommendations.append(
            "Implement Content-Security-Policy to prevent XSS and data injection attacks"
        )

    if security_headers_adoption.get("x-frame-options", 0) < 80:
        recommendations.append(
            "Add X-Frame-Options header to prevent clickjacking attacks"
        )

    if security_headers_adoption.get("x-content-type-options", 0) < 80:
        recommendations.append(
            "Set X-Content-Type-Options: nosniff to prevent MIME sniffing"
        )

    if security_score >= 90:
        recommendations.append("Excellent security header coverage!")
    elif security_score >= 70:
        recommendations.append("Good security header coverage with room for improvement")
    elif security_score >= 50:
        recommendations.append("Moderate security header coverage - consider improvements")
    else:
        recommendations.append("Critical: Poor security header coverage - immediate action recommended")

    # Create report
    report = HeaderReport(
        domain=domain,
        crawl_id=crawl_id,
        pages_analyzed=pages_analyzed,
        security_headers=security_headers_adoption,
        caching_policies=dict(caching_policy_counts),
        servers=dict(server_counts),
        security_score=security_score,
        recommendations=recommendations,
    )

    # Cache for 7 days
    await cache.set(cache_key, report.model_dump(), ttl=7 * 24 * 3600)

    return report
