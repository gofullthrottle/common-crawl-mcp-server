"""HTML parsing utilities for Common Crawl MCP Server.

This module provides helper functions for parsing and extracting data from HTML,
including clean text extraction, table parsing, and common selector operations.
"""

import logging
import re
from typing import Any, Optional

from bs4 import BeautifulSoup, Comment

logger = logging.getLogger(__name__)


def parse_html(html: str, parser: str = "lxml") -> BeautifulSoup:
    """Parse HTML string to BeautifulSoup object.

    Args:
        html: HTML content as string
        parser: Parser to use ("lxml", "html.parser", "html5lib")

    Returns:
        BeautifulSoup object

    Example:
        >>> soup = parse_html("<html><body>Hello</body></html>")
        >>> soup.body.text
        'Hello'
    """
    try:
        return BeautifulSoup(html, parser)
    except Exception as e:
        logger.warning(f"Error parsing with {parser}, falling back to html.parser: {e}")
        return BeautifulSoup(html, "html.parser")


def extract_clean_text(html: str, preserve_paragraphs: bool = False) -> str:
    """Extract clean text from HTML, removing scripts, styles, and comments.

    Args:
        html: HTML content as string
        preserve_paragraphs: If True, preserve paragraph breaks with double newlines

    Returns:
        Clean text content

    Example:
        >>> html = '<p>Hello</p><script>bad();</script><p>World</p>'
        >>> extract_clean_text(html)
        'Hello World'
    """
    try:
        soup = parse_html(html)

        # Remove unwanted elements
        for element in soup(["script", "style", "noscript", "iframe", "meta", "link"]):
            element.decompose()

        # Remove comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        # Remove hidden elements (common for SEO spam)
        for element in soup.find_all(style=re.compile(r"display:\s*none", re.I)):
            element.decompose()

        # Extract text
        if preserve_paragraphs:
            # Keep paragraph structure
            paragraphs = []
            for p in soup.find_all(["p", "div", "section", "article"]):
                text = p.get_text(strip=True)
                if text:
                    paragraphs.append(text)
            return "\n\n".join(paragraphs)
        else:
            # All text, space-separated
            text = soup.get_text(separator=" ", strip=True)
            # Normalize whitespace
            text = re.sub(r"\s+", " ", text)
            return text

    except Exception as e:
        logger.error(f"Error extracting clean text: {e}")
        return ""


def parse_table(table_html: str) -> list[dict[str, str]]:
    """Parse HTML table to list of dictionaries.

    Args:
        table_html: HTML containing a <table> element

    Returns:
        List of dictionaries, one per row, with header as keys

    Example:
        >>> html = '<table><tr><th>Name</th><th>Age</th></tr><tr><td>John</td><td>30</td></tr></table>'
        >>> parse_table(html)
        [{'Name': 'John', 'Age': '30'}]
    """
    try:
        soup = parse_html(table_html)
        table = soup.find("table")

        if not table:
            logger.warning("No table found in HTML")
            return []

        # Extract headers
        headers = []
        header_row = table.find("tr")
        if header_row:
            for th in header_row.find_all(["th", "td"]):
                headers.append(th.get_text(strip=True))

        # If no headers found, use column indices
        if not headers:
            first_row = table.find("tr")
            if first_row:
                headers = [f"col_{i}" for i in range(len(first_row.find_all("td")))]

        # Extract rows
        rows = []
        for tr in table.find_all("tr")[1:]:  # Skip header row
            cells = tr.find_all("td")
            if not cells:
                continue

            row_data = {}
            for i, cell in enumerate(cells):
                header = headers[i] if i < len(headers) else f"col_{i}"
                row_data[header] = cell.get_text(strip=True)

            rows.append(row_data)

        return rows

    except Exception as e:
        logger.error(f"Error parsing table: {e}")
        return []


def sanitize_html(html: str, allowed_tags: Optional[list[str]] = None) -> str:
    """Sanitize HTML by removing dangerous elements and attributes.

    Args:
        html: HTML content to sanitize
        allowed_tags: List of allowed tags (defaults to safe tags)

    Returns:
        Sanitized HTML string

    Example:
        >>> sanitize_html('<p onclick="bad()">Safe</p>')
        '<p>Safe</p>'
    """
    if allowed_tags is None:
        allowed_tags = [
            "p", "br", "span", "div", "h1", "h2", "h3", "h4", "h5", "h6",
            "ul", "ol", "li", "a", "strong", "em", "b", "i", "u",
            "table", "tr", "td", "th", "tbody", "thead", "tfoot",
            "blockquote", "pre", "code"
        ]

    try:
        soup = parse_html(html)

        # Remove all tags not in allowed list
        for tag in soup.find_all():
            if tag.name not in allowed_tags:
                tag.unwrap()

        # Remove event handlers and dangerous attributes
        dangerous_attrs = ["onclick", "onload", "onerror", "onmouseover", "onfocus"]

        for tag in soup.find_all():
            for attr in list(tag.attrs):
                # Remove event handlers
                if attr.lower() in dangerous_attrs or attr.lower().startswith("on"):
                    del tag.attrs[attr]

                # Remove javascript: URLs
                if attr in ["href", "src"]:
                    if tag.attrs[attr].strip().lower().startswith("javascript:"):
                        del tag.attrs[attr]

        return str(soup)

    except Exception as e:
        logger.error(f"Error sanitizing HTML: {e}")
        return ""


def extract_meta_tags(html: str) -> dict[str, str]:
    """Extract all meta tags from HTML.

    Args:
        html: HTML content

    Returns:
        Dictionary of meta tag name/property to content

    Example:
        >>> html = '<meta name="description" content="A great page">'
        >>> extract_meta_tags(html)
        {'description': 'A great page'}
    """
    soup = parse_html(html)
    meta_tags = {}

    for meta in soup.find_all("meta"):
        # Get name or property
        name = meta.get("name") or meta.get("property") or meta.get("http-equiv")
        content = meta.get("content")

        if name and content:
            meta_tags[name] = content

    return meta_tags


def extract_headings(html: str) -> dict[str, list[str]]:
    """Extract all heading tags (h1-h6) from HTML.

    Args:
        html: HTML content

    Returns:
        Dictionary mapping heading level to list of heading texts

    Example:
        >>> html = '<h1>Title</h1><h2>Section</h2>'
        >>> extract_headings(html)
        {'h1': ['Title'], 'h2': ['Section']}
    """
    soup = parse_html(html)
    headings = {f"h{i}": [] for i in range(1, 7)}

    for level in range(1, 7):
        for heading in soup.find_all(f"h{level}"):
            text = heading.get_text(strip=True)
            if text:
                headings[f"h{level}"].append(text)

    return headings


def extract_links(html: str, base_url: Optional[str] = None) -> list[dict[str, str]]:
    """Extract all links from HTML.

    Args:
        html: HTML content
        base_url: Base URL for resolving relative links

    Returns:
        List of dictionaries with href, text, and title

    Example:
        >>> html = '<a href="/page" title="Go">Click</a>'
        >>> extract_links(html)
        [{'href': '/page', 'text': 'Click', 'title': 'Go'}]
    """
    soup = parse_html(html)
    links = []

    for a_tag in soup.find_all("a", href=True):
        href = a_tag.get("href", "")
        text = a_tag.get_text(strip=True)
        title = a_tag.get("title", "")

        # Resolve relative URLs if base_url provided
        if base_url and not href.startswith(("http://", "https://", "mailto:", "tel:")):
            from urllib.parse import urljoin
            href = urljoin(base_url, href)

        links.append({
            "href": href,
            "text": text,
            "title": title
        })

    return links


def get_element_count(html: str, tag: str) -> int:
    """Count occurrences of a specific HTML tag.

    Args:
        html: HTML content
        tag: Tag name to count

    Returns:
        Number of occurrences

    Example:
        >>> html = '<div>One</div><div>Two</div>'
        >>> get_element_count(html, 'div')
        2
    """
    soup = parse_html(html)
    return len(soup.find_all(tag))


def calculate_html_depth(html: str) -> int:
    """Calculate maximum nesting depth of HTML.

    Args:
        html: HTML content

    Returns:
        Maximum depth

    Example:
        >>> html = '<div><div><div>Deep</div></div></div>'
        >>> calculate_html_depth(html)
        3
    """
    try:
        soup = parse_html(html)

        def get_depth(element, current_depth=0):
            if not element.children:
                return current_depth

            max_child_depth = current_depth
            for child in element.children:
                if hasattr(child, "children"):
                    child_depth = get_depth(child, current_depth + 1)
                    max_child_depth = max(max_child_depth, child_depth)

            return max_child_depth

        return get_depth(soup)

    except Exception as e:
        logger.error(f"Error calculating HTML depth: {e}")
        return 0
