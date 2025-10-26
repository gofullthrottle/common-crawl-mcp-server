# Wave 2: MCP Resources & Prompts (Phases 7-8)
**Agents:** 7 parallel agents (3 resources + 4 prompts)
**Dependencies:** None - references existing tools
**Estimated Time:** 3-5 hours total
**Expected Output:** Resource providers in `src/resources/` + Prompts in `src/prompts/`

## Wave 2a: MCP Resources (Phase 7)

### Agent 6: crawl_info_resource

### Objective
Implement MCP resource provider for Common Crawl crawl metadata.

### Specification

**Resource URI Scheme:**
```
commoncrawl://crawl/CC-MAIN-2024-10
commoncrawl://crawls  (list all available crawls)
```

**FastMCP Resource Registration:**
```python
from mcp import types

@mcp.resource("commoncrawl://crawl/{crawl_id}")
async def get_crawl_info(uri: str) -> str:
    """Get metadata for a specific Common Crawl crawl.

    URI format: commoncrawl://crawl/CC-MAIN-2024-10

    Returns:
        JSON string with crawl metadata
    """
    crawl_id = uri.split("/")[-1]

    from ..tools import discovery

    # Use existing list_crawls tool
    crawls_result = await discovery.list_crawls()

    # Find matching crawl
    matching_crawl = next(
        (c for c in crawls_result.crawls if c.id == crawl_id),
        None,
    )

    if not matching_crawl:
        return json.dumps({
            "error": f"Crawl not found: {crawl_id}",
            "available_crawls": [c.id for c in crawls_result.crawls[:5]],
        })

    # Return detailed crawl info
    info = {
        "crawl_id": matching_crawl.id,
        "name": matching_crawl.name,
        "data_available": matching_crawl.data_available,
        "cdx_api": f"https://index.commoncrawl.org/{crawl_id}-index",
        "s3_prefix": f"s3://commoncrawl/crawl-data/{crawl_id}/",
        "http_prefix": f"https://data.commoncrawl.org/crawl-data/{crawl_id}/",
        "estimated_pages": "billions",
        "formats_available": ["WARC", "WAT", "WET"],
    }

    return json.dumps(info, indent=2)


@mcp.resource("commoncrawl://crawls")
async def list_all_crawls(uri: str) -> str:
    """List all available Common Crawl crawls.

    Returns:
        JSON string with crawls list
    """
    from ..tools import discovery

    crawls_result = await discovery.list_crawls()

    info = {
        "total_crawls": len(crawls_result.crawls),
        "latest_crawl": crawls_result.crawls[0].id if crawls_result.crawls else None,
        "crawls": [
            {
                "id": crawl.id,
                "name": crawl.name,
                "data_available": crawl.data_available,
            }
            for crawl in crawls_result.crawls
        ],
    }

    return json.dumps(info, indent=2)
```

**File:** `src/resources/crawl_info.py`

**Testing:**
```python
@pytest.mark.asyncio
async def test_crawl_info_resource():
    # Test specific crawl
    result = await get_crawl_info("commoncrawl://crawl/CC-MAIN-2024-10")
    data = json.loads(result)

    assert "crawl_id" in data
    assert data["crawl_id"] == "CC-MAIN-2024-10"
    assert "cdx_api" in data

@pytest.mark.asyncio
async def test_list_crawls_resource():
    result = await list_all_crawls("commoncrawl://crawls")
    data = json.loads(result)

    assert "total_crawls" in data
    assert "latest_crawl" in data
    assert len(data["crawls"]) > 0
```

---

### Agent 7: saved_datasets_resource

### Objective
Implement MCP resource provider for saved datasets.

### Specification

**Resource URI Scheme:**
```
commoncrawl://datasets  (list all datasets)
commoncrawl://dataset/{dataset_id}  (specific dataset info)
commoncrawl://dataset/{dataset_id}/records  (dataset records)
```

**FastMCP Resource Registration:**
```python
@mcp.resource("commoncrawl://datasets")
async def list_datasets(uri: str) -> str:
    """List all saved datasets.

    Returns:
        JSON string with datasets list
    """
    from ..tools.export import get_all_datasets

    datasets = await get_all_datasets()

    info = {
        "total_datasets": len(datasets),
        "datasets": [
            {
                "id": ds.id,
                "name": ds.name,
                "description": ds.description,
                "records_count": ds.records_count,
                "created_at": ds.created_at.isoformat(),
            }
            for ds in datasets
        ],
    }

    return json.dumps(info, indent=2)


@mcp.resource("commoncrawl://dataset/{dataset_id}")
async def get_dataset_info(uri: str) -> str:
    """Get metadata for a specific dataset.

    URI format: commoncrawl://dataset/{uuid}

    Returns:
        JSON string with dataset metadata
    """
    dataset_id = uri.split("/")[-1]

    from ..tools.export import get_dataset_by_id

    dataset = await get_dataset_by_id(dataset_id)

    if not dataset:
        return json.dumps({"error": f"Dataset not found: {dataset_id}"})

    info = {
        "id": dataset.id,
        "name": dataset.name,
        "description": dataset.description,
        "records_count": dataset.records_count,
        "created_at": dataset.created_at.isoformat(),
        "metadata": dataset.metadata,
        "uri": f"commoncrawl://dataset/{dataset.id}",
        "records_uri": f"commoncrawl://dataset/{dataset.id}/records",
    }

    return json.dumps(info, indent=2)


@mcp.resource("commoncrawl://dataset/{dataset_id}/records")
async def get_dataset_records_resource(uri: str) -> str:
    """Get records from a specific dataset.

    URI format: commoncrawl://dataset/{uuid}/records

    Returns:
        JSON string with dataset records (limited to first 100)
    """
    dataset_id = uri.split("/")[-2]

    from ..tools.export import get_dataset_records

    records = await get_dataset_records(dataset_id)

    info = {
        "dataset_id": dataset_id,
        "total_records": len(records),
        "records": records[:100],  # Limit to first 100
        "truncated": len(records) > 100,
    }

    return json.dumps(info, indent=2)
```

**Additional Functions Needed in `export.py`:**
```python
async def get_all_datasets() -> list[Dataset]:
    """Retrieve all datasets."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    rows = cursor.execute(
        """SELECT id, name, description, created_at, records_count, metadata
           FROM datasets ORDER BY created_at DESC"""
    ).fetchall()

    conn.close()

    return [
        Dataset(
            id=row[0],
            name=row[1],
            description=row[2],
            created_at=row[3],
            records_count=row[4],
            metadata=json.loads(row[5]),
        )
        for row in rows
    ]


async def get_dataset_by_id(dataset_id: str) -> Optional[Dataset]:
    """Retrieve dataset by ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    row = cursor.execute(
        """SELECT id, name, description, created_at, records_count, metadata
           FROM datasets WHERE id = ?""",
        (dataset_id,),
    ).fetchone()

    conn.close()

    if not row:
        return None

    return Dataset(
        id=row[0],
        name=row[1],
        description=row[2],
        created_at=row[3],
        records_count=row[4],
        metadata=json.loads(row[5]),
    )
```

**File:** `src/resources/saved_datasets.py`

---

### Agent 8: investigation_state_resource

### Objective
Implement MCP resource provider for investigation session state.

### Specification

**Resource URI Scheme:**
```
commoncrawl://investigations  (list all sessions)
commoncrawl://investigation/{session_id}  (specific session state)
```

**Session State Schema:**
```python
class InvestigationSession(BaseModel):
    """Investigation session state."""
    id: str  # UUID
    created_at: datetime
    updated_at: datetime
    queries_run: list[dict[str, Any]] = []
    cached_results: dict[str, Any] = {}
    analysis_summary: dict[str, Any] = {}
```

**Database Schema Addition:**
```sql
CREATE TABLE IF NOT EXISTS investigation_sessions (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    state JSON NOT NULL
);
```

**FastMCP Resource Registration:**
```python
@mcp.resource("commoncrawl://investigations")
async def list_investigations(uri: str) -> str:
    """List all investigation sessions.

    Returns:
        JSON string with sessions list
    """
    sessions = await get_all_sessions()

    info = {
        "total_sessions": len(sessions),
        "sessions": [
            {
                "id": session.id,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "queries_count": len(session.queries_run),
            }
            for session in sessions
        ],
    }

    return json.dumps(info, indent=2)


@mcp.resource("commoncrawl://investigation/{session_id}")
async def get_investigation_state(uri: str) -> str:
    """Get state for a specific investigation session.

    URI format: commoncrawl://investigation/{uuid}

    Returns:
        JSON string with session state
    """
    session_id = uri.split("/")[-1]

    session = await get_session(session_id)

    if not session:
        return json.dumps({"error": f"Session not found: {session_id}"})

    info = {
        "id": session.id,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
        "queries_run": session.queries_run,
        "cached_results": session.cached_results,
        "analysis_summary": session.analysis_summary,
    }

    return json.dumps(info, indent=2)


# Helper functions
async def create_session() -> InvestigationSession:
    """Create new investigation session."""
    session = InvestigationSession(
        id=str(uuid.uuid4()),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """INSERT INTO investigation_sessions (id, created_at, updated_at, state)
           VALUES (?, ?, ?, ?)""",
        (session.id, session.created_at, session.updated_at, session.model_dump_json()),
    )

    conn.commit()
    conn.close()

    return session


async def update_session(session: InvestigationSession) -> None:
    """Update investigation session state."""
    session.updated_at = datetime.now(timezone.utc)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """UPDATE investigation_sessions
           SET updated_at = ?, state = ?
           WHERE id = ?""",
        (session.updated_at, session.model_dump_json(), session.id),
    )

    conn.commit()
    conn.close()
```

**File:** `src/resources/investigation_state.py`

---

## Wave 2b: MCP Prompts (Phase 8)

### Agent 9: domain_research_prompt

### Objective
Create comprehensive domain analysis workflow prompt.

### Specification

**Prompt Registration:**
```python
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
```

**File:** `src/prompts/domain_research.py`

---

### Agent 10: competitive_analysis_prompt

### Objective
Create competitor comparison workflow prompt.

### Specification

**Prompt Registration:**
```python
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
```

**File:** `src/prompts/competitive_analysis.py`

---

### Agent 11: content_discovery_prompt

### Objective
Create content mining workflow prompt.

### Specification

**Prompt Registration:**
```python
@mcp.prompt()
async def content_discovery() -> list[types.PromptMessage]:
    """Discover and analyze content patterns across a domain.

    This prompt helps you:
    - Find pages containing specific keywords
    - Extract structured data (JSON-LD, microdata)
    - Analyze keyword frequency
    - Identify content themes
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
```

**File:** `src/prompts/content_discovery.py`

---

### Agent 12: seo_analysis_prompt

### Objective
Create SEO audit workflow prompt.

### Specification

**Prompt Registration:**
```python
@mcp.prompt()
async def seo_analysis() -> list[types.PromptMessage]:
    """Perform comprehensive SEO audit using Common Crawl data.

    This prompt helps you:
    - Analyze on-page SEO factors
    - Check internal linking structure
    - Evaluate security headers
    - Generate actionable recommendations
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
```

**File:** `src/prompts/seo_analysis.py`

---

## Integration Requirements

**Module Structure:**

`src/resources/__init__.py`:
```python
"""MCP resource providers for Common Crawl server."""

from .crawl_info import get_crawl_info, list_all_crawls
from .saved_datasets import list_datasets, get_dataset_info, get_dataset_records_resource
from .investigation_state import list_investigations, get_investigation_state

__all__ = [
    "get_crawl_info",
    "list_all_crawls",
    "list_datasets",
    "get_dataset_info",
    "get_dataset_records_resource",
    "list_investigations",
    "get_investigation_state",
]
```

`src/prompts/__init__.py`:
```python
"""MCP prompts for Common Crawl workflows."""

from .domain_research import domain_research
from .competitive_analysis import competitive_analysis
from .content_discovery import content_discovery
from .seo_analysis import seo_analysis

__all__ = [
    "domain_research",
    "competitive_analysis",
    "content_discovery",
    "seo_analysis",
]
```

**Server Registration:**

Update `src/server.py` to import resources and prompts:
```python
# Resources are auto-registered via @mcp.resource() decorator
from .resources import (
    get_crawl_info,
    list_all_crawls,
    list_datasets,
    get_dataset_info,
    get_dataset_records_resource,
    list_investigations,
    get_investigation_state,
)

# Prompts are auto-registered via @mcp.prompt() decorator
from .prompts import (
    domain_research,
    competitive_analysis,
    content_discovery,
    seo_analysis,
)
```

## Testing Requirements

**File:** `tests/integration/test_resources_and_prompts.py`

**Test Coverage:**
- [ ] test_crawl_info_resource
- [ ] test_list_crawls_resource
- [ ] test_datasets_resource
- [ ] test_dataset_info_resource
- [ ] test_investigation_resource
- [ ] test_domain_research_prompt
- [ ] test_competitive_analysis_prompt
- [ ] test_content_discovery_prompt
- [ ] test_seo_analysis_prompt

## Acceptance Criteria

### Resources:
- [ ] All 3 resource providers implemented
- [ ] Resources accessible via URI scheme
- [ ] Resource JSON validates against MCP spec
- [ ] Resources return proper error messages for invalid URIs
- [ ] Resources tested with actual MCP client (if available)

### Prompts:
- [ ] All 4 prompts implemented
- [ ] Prompts include clear step-by-step workflows
- [ ] Prompts include concrete examples
- [ ] Prompts reference actual tool names correctly
- [ ] Prompts tested interactively for usability
