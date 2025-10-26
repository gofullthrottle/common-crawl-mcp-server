"""Domain research prompt for comprehensive domain analysis workflow.

This module provides an MCP prompt that guides users through analyzing
a domain's technology stack, site structure, security posture, and content patterns.
"""

from mcp import types
from mcp.server.fastmcp import FastMCP

# Access the global mcp instance from server
from ..server import mcp


@mcp.prompt()
async def domain_research() -> list[types.PromptMessage]:
    """Comprehensive domain analysis workflow.

    This prompt guides you through analyzing a domain's:
    - Technology stack
    - Site structure (link graph)
    - Security posture
    - Content patterns

    Example usage:
    1. Run this prompt
    2. Provide domain when asked (e.g., "example.com")
    3. Tools will be orchestrated automatically
    """
    return [
        types.PromptMessage(
            role="user",
            content=types.TextContent(
                type="text",
                text="""Let's conduct a comprehensive domain analysis.

**Step 1: Select Crawl**
First, let's see available crawls:
```
Use tool: list_crawls()
```
Select the latest crawl ID.

**Step 2: Discover Pages**
Search for pages in the domain:
```
Use tool: search_index(query="example.com", crawl_id="CC-MAIN-2024-10", limit=100, match_type="domain")
```

**Step 3: Technology Analysis**
Analyze the technology stack:
```
Use tool: domain_technology_report(domain="example.com", crawl_id="CC-MAIN-2024-10", sample_size=50)
```

**Step 4: Site Structure**
Generate link graph:
```
Use tool: domain_link_graph(domain="example.com", crawl_id="CC-MAIN-2024-10", sample_size=50)
```

**Step 5: Security Analysis**
Check HTTP security headers:
```
Use tool: header_analysis(domain="example.com", crawl_id="CC-MAIN-2024-10", sample_size=50)
```

**Step 6: Generate Report**
Create comprehensive report:
```
Use tool: generate_report(
    report_type="domain_analysis",
    data={
        "domain": "example.com",
        "technologies": <results from step 3>,
        "link_graph": <results from step 4>,
        "security_headers": <results from step 5>
    },
    output_path="./reports/example.com-analysis.md"
)
```

Please replace "example.com" with your target domain.
""",
            ),
        ),
    ]
