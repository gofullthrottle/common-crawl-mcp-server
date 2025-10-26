"""SEO analysis workflow prompt for Common Crawl MCP server.

This module provides a comprehensive SEO audit workflow that guides users
through analyzing a domain's on-page SEO, link structure, and security posture
using archived Common Crawl data.
"""

from mcp import types
from mcp.server.fastmcp import FastMCP

# Access the global mcp instance from server
from ..server import mcp


@mcp.prompt()
async def seo_analysis() -> list[types.PromptMessage]:
    """Perform comprehensive SEO audit using Common Crawl data.

    This prompt helps you:
    - Analyze on-page SEO factors
    - Check internal linking structure
    - Evaluate security headers
    - Generate actionable recommendations

    The workflow guides through a 5-step SEO audit process using
    archived web data from Common Crawl.

    Returns:
        List of prompt messages for the SEO analysis workflow
    """
    return [
        types.PromptMessage(
            role="user",
            content=types.TextContent(
                type="text",
                text="""Let's perform an SEO audit using archived web data.

**Step 1: Sample Representative Pages**
Get diverse page types:
```
Use tool: search_index(
    query="example.com",
    crawl_id="CC-MAIN-2024-10",
    limit=50,
    match_type="domain"
)
```

**Step 2: On-Page SEO Analysis**
For each page type (homepage, product, blog, etc.):
```
Use tool: analyze_seo(url=<url>, crawl_id="CC-MAIN-2024-10")
```
Pay attention to:
- SEO score (should be >70)
- Title and meta description quality
- Heading structure (proper h1-h6 hierarchy)
- Image alt text coverage

**Step 3: Link Graph Analysis**
Understand internal linking:
```
Use tool: domain_link_graph(
    domain="example.com",
    crawl_id="CC-MAIN-2024-10",
    sample_size=50
)
```
Check:
- Hub pages (most linked-to content)
- Orphan pages (no inbound links)
- PageRank distribution

**Step 4: Security Headers Check**
SEO is affected by security:
```
Use tool: header_analysis(
    domain="example.com",
    crawl_id="CC-MAIN-2024-10",
    sample_size=50
)
```
Ensure:
- HTTPS usage (HSTS header)
- Security score >70
- No mixed content issues

**Step 5: Generate SEO Report**
Create actionable report:
```
Use tool: generate_report(
    report_type="seo_audit",
    data={
        "domain": "example.com",
        "seo_scores": [<results from step 2>],
        "link_graph": <results from step 3>,
        "security": <results from step 4>,
        "recommendations": [
            "Improve meta descriptions (50% missing)",
            "Add alt text to images (30% missing)",
            "Implement HSTS header",
        ]
    },
    output_path="./reports/example.com-seo-audit.md"
)
```

Replace "example.com" with your target domain.
""",
            ),
        ),
    ]
