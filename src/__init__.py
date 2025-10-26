"""Common Crawl MCP Server.

Transform Common Crawl's petabyte-scale web archive into an accessible
research platform through AI-powered analysis.
"""

__version__ = "0.1.0"
__author__ = "Your Name"
__license__ = "MIT"

from .config import config, get_config
from .server import mcp

__all__ = ["config", "get_config", "mcp"]
