"""Competitive analysis prompt for multi-domain technology comparison workflow.

This module provides an MCP prompt that guides users through analyzing
and comparing technology stacks across multiple competitor domains.
"""

from mcp import types
from mcp.server.fastmcp import FastMCP

# Access the global mcp instance from server
from ..server import mcp


@mcp.prompt()
async def competitive_analysis() -> list[types.PromptMessage]:
    """Compare technology stacks across multiple competitor domains.

    This prompt helps you:
    - Analyze multiple domains simultaneously
    - Compare technology adoption
    - Identify competitive advantages

    Example: Compare Shopify vs WooCommerce vs Magento sites
    """
    return [
        types.PromptMessage(
            role="user",
            content=types.TextContent(
                type="text",
                text="""Let's compare competitor domains' technology stacks.

**Step 1: Define Competitors**
List the domains you want to compare:
```
competitors = [
    "competitor1.com",
    "competitor2.com",
    "competitor3.com",
]
```

**Step 2: Analyze Each Domain**
For each competitor, run:
```
Use tool: domain_technology_report(domain=<competitor>, crawl_id="CC-MAIN-2024-10", sample_size=50)
```

**Step 3: Compare Results**
Create comparison matrix:
```python
comparison = {
    "domains": competitors,
    "technologies": {
        "React": [True, False, True],  # Which domains use React
        "WordPress": [False, True, False],
        "Google Analytics": [True, True, True],
    },
    "adoption_rates": {
        "competitor1.com": {"React": 85%, "WordPress": 0%},
        "competitor2.com": {"React": 0%, "WordPress": 100%},
    }
}
```

**Step 4: Identify Trends**
- Which technologies are most common?
- Which competitor is most modern?
- Are there unique technologies used by one competitor?

**Step 5: Save Dataset**
```
Use tool: create_dataset(
    name="competitor_analysis_<date>",
    description="Technology comparison of competitors",
    data=[<technology reports for each domain>]
)
```

Replace the competitor list with your actual target domains.
""",
            ),
        ),
    ]
