"""MCP prompts for Common Crawl workflows."""

from .competitive_analysis import competitive_analysis
from .content_discovery import content_discovery
from .domain_research import domain_research
from .seo_analysis import seo_analysis

__all__ = [
    "domain_research",
    "competitive_analysis",
    "seo_analysis",
    "content_discovery",
]
