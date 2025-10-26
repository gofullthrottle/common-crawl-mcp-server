# Investigation State Resources

## Overview

The investigation state resource provider enables tracking and managing investigation sessions across the Common Crawl MCP server. This allows users to maintain context across multiple queries, cache intermediate results, and build cumulative analysis over time.

## Use Cases

- **Research Sessions**: Track queries and findings during domain research
- **Comparative Analysis**: Maintain state when comparing multiple domains
- **Result Caching**: Store intermediate results for reuse
- **Progress Tracking**: Monitor investigation progress over time
- **Context Preservation**: Maintain analysis context across multiple interactions

## Resource URIs

### List All Sessions

```
commoncrawl://investigations
```

Returns a list of all investigation sessions with metadata.

**Response Structure:**
```json
{
  "total_sessions": 2,
  "sessions": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:45:00Z",
      "queries_count": 5,
      "has_cached_results": true,
      "has_analysis": true
    }
  ]
}
```

### Get Session State

```
commoncrawl://investigation/{session_id}
```

Returns complete state for a specific investigation session.

**Response Structure:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:45:00Z",
  "queries_run": [
    {
      "tool": "search_index",
      "query": "example.com",
      "crawl_id": "CC-MAIN-2024-10",
      "timestamp": "2024-01-15T10:30:00Z",
      "results_count": 150
    }
  ],
  "cached_results": {
    "query_1": {
      "urls": ["https://example.com", "..."],
      "total_found": 150
    }
  },
  "analysis_summary": {
    "domain": "example.com",
    "total_pages_found": 150,
    "technologies_detected": 12,
    "key_findings": ["..."]
  },
  "metadata": {
    "queries_count": 5,
    "cached_results_count": 3,
    "session_age_seconds": 900,
    "last_activity_seconds": 30
  }
}
```

## Python API

### Creating Sessions

```python
from src.resources.investigation_state import create_session

# Create a new investigation session
session = await create_session()
print(f"Session ID: {session.id}")
```

### Tracking Queries

```python
from datetime import datetime, timezone

# Add query to session
session.queries_run.append({
    "tool": "search_index",
    "query": "example.com",
    "crawl_id": "CC-MAIN-2024-10",
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "results_count": 150
})

# Update session
await update_session(session)
```

### Caching Results

```python
# Cache query results
session.cached_results["domain_stats"] = {
    "total_pages": 150,
    "total_size_mb": 45.2,
    "subdomains": ["www", "blog", "api"]
}

await update_session(session)
```

### Building Analysis Summary

```python
# Add cumulative findings
session.analysis_summary = {
    "domain": "example.com",
    "total_pages_found": 150,
    "pages_analyzed": 50,
    "technologies_detected": 12,
    "key_findings": [
        "React is the primary frontend framework (45.2% adoption)",
        "WordPress powers about 1/3 of the pages"
    ],
    "security_score": 72,
    "recommendations": [
        "Consider implementing HSTS header",
        "Improve meta description coverage"
    ]
}

await update_session(session)
```

### Retrieving Sessions

```python
from src.resources.investigation_state import get_session, get_all_sessions

# Get specific session
session = await get_session(session_id)

# Get all sessions
all_sessions = await get_all_sessions()
```

## Data Model

### InvestigationSession

```python
class InvestigationSession(BaseModel):
    """Investigation session state."""

    id: str
    # Unique session identifier (UUID)

    created_at: datetime
    # Session creation timestamp

    updated_at: datetime
    # Last update timestamp

    queries_run: list[dict[str, Any]] = []
    # List of executed queries with metadata
    # Example: [{"tool": "search_index", "query": "...", "timestamp": "..."}]

    cached_results: dict[str, Any] = {}
    # Cached query results by query identifier
    # Example: {"query_1": {"urls": [...], "total_found": 150}}

    analysis_summary: dict[str, Any] = {}
    # Accumulated analysis findings
    # Example: {"domain": "...", "key_findings": [...], "recommendations": [...]}
```

## Database Schema

```sql
CREATE TABLE IF NOT EXISTS investigation_sessions (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    state JSON NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_investigation_sessions_created_at
ON investigation_sessions(created_at DESC);
```

## Usage Examples

### Example 1: Domain Research Session

```python
import asyncio
from datetime import datetime, timezone
from src.resources.investigation_state import (
    create_session, update_session, get_session
)

async def research_domain(domain: str, crawl_id: str):
    # Create session
    session = await create_session()

    # Query 1: Search for pages
    # (In real usage, call the actual search_index tool)
    search_results = {"urls": [...], "total": 150}

    session.queries_run.append({
        "tool": "search_index",
        "query": domain,
        "crawl_id": crawl_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "results_count": search_results["total"]
    })
    session.cached_results["search"] = search_results

    # Query 2: Analyze technologies
    # (In real usage, call domain_technology_report tool)
    tech_results = {"technologies": {"React": 45.2, "WordPress": 32.1}}

    session.queries_run.append({
        "tool": "domain_technology_report",
        "domain": domain,
        "crawl_id": crawl_id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    session.cached_results["technologies"] = tech_results

    # Build analysis summary
    session.analysis_summary = {
        "domain": domain,
        "total_pages_found": search_results["total"],
        "technologies_detected": len(tech_results["technologies"]),
        "key_findings": [
            f"React adoption: {tech_results['technologies']['React']}%",
            f"WordPress adoption: {tech_results['technologies']['WordPress']}%"
        ]
    }

    # Save session
    await update_session(session)

    return session.id

# Run research
session_id = asyncio.run(research_domain("example.com", "CC-MAIN-2024-10"))
print(f"Research session saved: {session_id}")
```

### Example 2: Resuming an Investigation

```python
async def continue_investigation(session_id: str):
    # Load existing session
    session = await get_session(session_id)

    if not session:
        print(f"Session not found: {session_id}")
        return

    print(f"Resuming session from {session.created_at}")
    print(f"Previous queries: {len(session.queries_run)}")

    # Review cached results
    if "search" in session.cached_results:
        search_data = session.cached_results["search"]
        print(f"Found {search_data['total']} pages previously")

    # Continue with new queries
    # (Add more queries, update analysis summary, etc.)

    await update_session(session)
```

### Example 3: MCP Resource Access

```python
from src.resources.investigation_state import (
    list_investigations,
    get_investigation_state
)

# List all sessions
sessions_json = await list_investigations("commoncrawl://investigations")
print(sessions_json)

# Get specific session state
session_json = await get_investigation_state(
    f"commoncrawl://investigation/{session_id}"
)
print(session_json)
```

## Best Practices

### 1. Session Organization

```python
# Use descriptive queries with metadata
session.queries_run.append({
    "tool": "search_index",
    "query": "example.com",
    "crawl_id": "CC-MAIN-2024-10",
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "results_count": 150,
    "description": "Initial domain discovery"  # Add context
})
```

### 2. Result Caching

```python
# Cache results with meaningful keys
session.cached_results["initial_search"] = search_results
session.cached_results["tech_analysis"] = tech_results
session.cached_results["link_graph"] = graph_results
```

### 3. Progressive Analysis

```python
# Build analysis incrementally
if not session.analysis_summary:
    session.analysis_summary = {}

session.analysis_summary["total_pages_analyzed"] = (
    session.analysis_summary.get("total_pages_analyzed", 0) + new_pages
)

session.analysis_summary.setdefault("key_findings", []).append(
    "New finding from latest analysis"
)
```

### 4. Session Cleanup

```python
from src.resources.investigation_state import delete_session

# Delete old sessions when no longer needed
deleted = await delete_session(old_session_id)
if deleted:
    print("Session deleted successfully")
```

## Error Handling

```python
try:
    session = await get_session(session_id)
    if not session:
        print(f"Session not found: {session_id}")
        return
except Exception as e:
    print(f"Error retrieving session: {e}")
```

## Performance Considerations

- **Session Size**: Keep `cached_results` reasonable in size. For large result sets, consider storing only summaries or references.
- **Update Frequency**: Batch multiple changes before calling `update_session()` to reduce database writes.
- **Session Cleanup**: Regularly delete old sessions that are no longer needed to maintain database performance.

## Integration with MCP Prompts

Investigation sessions work seamlessly with MCP prompts:

```python
# In domain_research prompt
session = await create_session()

# Execute queries as part of prompt workflow
# Each tool call adds to session.queries_run

# Build cumulative findings
session.analysis_summary = build_summary_from_results()

# Save session for later reference
await update_session(session)
```

## See Also

- [Saved Datasets Resources](./saved-datasets.md) - For persisting query results
- [Crawl Info Resources](./crawl-info.md) - For accessing crawl metadata
- [MCP Prompts](../prompts/README.md) - For workflow automation
