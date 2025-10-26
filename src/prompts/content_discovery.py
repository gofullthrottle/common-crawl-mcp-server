"""Content discovery prompt for content mining workflow.

This module provides an MCP prompt that guides users through discovering
and analyzing content patterns across a domain, including keyword analysis,
structured data extraction, and content theme identification.
"""

from mcp import types
from mcp.server.fastmcp import FastMCP

# Access the global mcp instance from server
from ..server import mcp


@mcp.prompt()
async def content_discovery() -> list[types.PromptMessage]:
    """Discover and analyze content patterns across a domain.

    This prompt helps you:
    - Find pages containing specific keywords
    - Extract structured data (JSON-LD, microdata)
    - Analyze keyword frequency
    - Identify content themes

    Example usage:
    1. Run this prompt
    2. Provide domain and keywords when asked
    3. Tools will be orchestrated automatically
    """
    return [
        types.PromptMessage(
            role="user",
            content=types.TextContent(
                type="text",
                text="""Let's discover content patterns in Common Crawl data.

**Step 1: Search for Pages**
Find pages containing your keywords:
```
Use tool: search_index(
    query="example.com",
    crawl_id="CC-MAIN-2024-10",
    limit=100,
    match_type="domain",
    filter="statuscode:200"
)
```

**Step 2: Keyword Frequency Analysis**
Analyze how often keywords appear:
```
Use tool: keyword_frequency_analysis(
    domain="example.com",
    keywords=["product", "pricing", "feature", "documentation"],
    crawl_id="CC-MAIN-2024-10",
    sample_size=100
)
```

**Step 3: Extract Structured Data**
Parse pages for structured data:
```
For each interesting URL:
Use tool: extract_structured_data(url=<url>, crawl_id="CC-MAIN-2024-10")
```

**Step 4: Identify Content Types**
Classify pages by type:
```
For sample URLs:
Use tool: analyze_seo(url=<url>, crawl_id="CC-MAIN-2024-10")
```
Look at title patterns, heading structure, meta descriptions.

**Step 5: Export Results**
Save your findings:
```
Use tool: export_to_jsonl(
    data=[<all extracted structured data>],
    output_path="./data/example-com-content.jsonl"
)
```

Replace "example.com" and keyword list with your targets.
""",
            ),
        ),
    ]
