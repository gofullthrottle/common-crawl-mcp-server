# Wave 3: Advanced Features (Phase 9 - OPTIONAL)
**Agents:** 4 agents (3 parallel + 1 dependent)
**Dependencies:** Wave 1 (for dataset_management only)
**Estimated Time:** 5-7 hours total
**Expected Output:** `src/tools/advanced.py` with 4 enhancement tools

**⚠️ OPTIONAL PHASE:** This wave can be skipped if time is constrained. Focus should be on Waves 1, 2, 4, and 5 for core functionality.

## Agent 13: content_classification

### Objective
Classify web pages by type using composition of existing tools.

### Specification

**Function Signature:**
```python
async def content_classification(
    url: str,
    crawl_id: str = "CC-MAIN-2024-10",
) -> ContentClassification:
    """Classify a web page by type and purpose."""
```

**Pydantic Models:**
```python
class ContentClassification(BaseModel):
    """Web page classification result."""
    url: str
    page_type: str  # blog, product, documentation, news, landing_page, other
    confidence: float  # 0.0 to 1.0
    signals: dict[str, Any]  # Evidence for classification
    language: str
    content_quality_score: float  # 0-100
```

**Classification Logic:**
```python
async def content_classification(...):
    from .parsing import analyze_seo, detect_language, extract_structured_data

    # Gather signals
    seo = await analyze_seo(url, crawl_id)
    lang = await detect_language(url, crawl_id)
    structured = await extract_structured_data(url, crawl_id)

    signals = {}

    # URL pattern signals
    if "/blog/" in url or "/post/" in url or "/article/" in url:
        signals["url_pattern"] = "blog"
    elif "/product/" in url or "/shop/" in url:
        signals["url_pattern"] = "product"
    elif "/docs/" in url or "/documentation/" in url:
        signals["url_pattern"] = "documentation"

    # Structured data signals
    if structured.schema_org:
        if any("BlogPosting" in s for s in structured.schema_org):
            signals["schema_org"] = "blog"
        elif any("Product" in s for s in structured.schema_org):
            signals["schema_org"] = "product"
        elif any("NewsArticle" in s for s in structured.schema_org):
            signals["schema_org"] = "news"

    # Content signals from SEO analysis
    if seo.headings:
        h1_count = len(seo.headings.get("h1", []))
        if h1_count == 1:
            signals["heading_structure"] = "well_structured"

    # Classify based on signals
    page_type = "other"
    confidence = 0.5

    if signals.get("schema_org") == "blog" or signals.get("url_pattern") == "blog":
        page_type = "blog"
        confidence = 0.9 if signals.get("schema_org") == "blog" else 0.7
    elif signals.get("schema_org") == "product" or signals.get("url_pattern") == "product":
        page_type = "product"
        confidence = 0.9 if signals.get("schema_org") == "product" else 0.7
    # ... other classifications

    return ContentClassification(
        url=url,
        page_type=page_type,
        confidence=confidence,
        signals=signals,
        language=lang.language,
        content_quality_score=seo.seo_score,
    )
```

---

## Agent 14: spam_detection

### Objective
Detect spam/low-quality pages using composition of existing tools.

### Specification

**Function Signature:**
```python
async def spam_detection(
    url: str,
    crawl_id: str = "CC-MAIN-2024-10",
) -> SpamAnalysis:
    """Detect if a page is likely spam or low-quality."""
```

**Pydantic Models:**
```python
class SpamAnalysis(BaseModel):
    """Spam detection result."""
    url: str
    spam_score: float  # 0-100, higher = more likely spam
    confidence: float  # 0.0-1.0
    spam_signals: list[str]
    quality_signals: list[str]
    recommendation: str  # "likely_spam", "suspicious", "likely_legitimate"
```

**Detection Logic:**
```python
async def spam_detection(...):
    from .parsing import analyze_technologies, parse_html
    from .aggregation import header_analysis

    # Gather signals
    tech = await analyze_technologies(url, crawl_id)
    parsed = await parse_html(url, crawl_id)

    spam_signals = []
    quality_signals = []
    spam_score = 0

    # Security header signals
    if not parsed.headers:
        spam_signals.append("missing_security_headers")
        spam_score += 20

    # Content quality signals
    if not parsed.title or len(parsed.title) < 10:
        spam_signals.append("poor_title")
        spam_score += 15

    if not parsed.meta_tags.get("description"):
        spam_signals.append("missing_meta_description")
        spam_score += 10

    # Link spam signals
    if parsed.links:
        external_links = [l for l in parsed.links if not url in l.get("href", "")]
        if len(external_links) > 50:
            spam_signals.append("excessive_external_links")
            spam_score += 20

    # Technology signals (legitimate sites use known tech)
    if tech.technologies:
        quality_signals.append("uses_known_technologies")
        spam_score -= 10

    # Keyword stuffing detection
    if parsed.text:
        words = parsed.text.lower().split()
        if words:
            unique_words = set(words)
            repetition_ratio = 1 - (len(unique_words) / len(words))
            if repetition_ratio > 0.5:
                spam_signals.append("keyword_stuffing")
                spam_score += 25

    # Clamp score
    spam_score = max(0, min(100, spam_score))

    # Recommendation
    if spam_score > 70:
        recommendation = "likely_spam"
        confidence = 0.8
    elif spam_score > 40:
        recommendation = "suspicious"
        confidence = 0.6
    else:
        recommendation = "likely_legitimate"
        confidence = 0.7

    return SpamAnalysis(
        url=url,
        spam_score=spam_score,
        confidence=confidence,
        spam_signals=spam_signals,
        quality_signals=quality_signals,
        recommendation=recommendation,
    )
```

---

## Agent 15: trend_analysis

### Objective
Detect trends in domain evolution using statistical analysis.

### Specification

**Function Signature:**
```python
async def trend_analysis(
    domain: str,
    crawl_ids: list[str],
    *,
    sample_size: int = 100,
) -> TrendAnalysis:
    """Analyze trends in domain evolution across crawls."""
```

**Pydantic Models:**
```python
class Trend(BaseModel):
    """Individual trend detected."""
    metric: str  # "page_count", "technology_adoption", "content_volume"
    direction: str  # "increasing", "decreasing", "stable"
    rate_of_change: float  # Percentage change
    confidence: float  # 0.0-1.0

class TrendAnalysis(BaseModel):
    """Trend analysis result."""
    domain: str
    time_period: dict[str, str]  # {"start": crawl_id, "end": crawl_id}
    trends: list[Trend]
    insights: list[str]
```

**Analysis Logic:**
```python
async def trend_analysis(...):
    from .aggregation import domain_evolution_timeline

    # Get evolution data
    timeline = await domain_evolution_timeline(domain, crawl_ids, sample_size)

    trends = []
    insights = []

    # Analyze page count trend
    page_counts = list(timeline.page_counts.values())
    if len(page_counts) >= 2:
        initial_count = page_counts[0]
        final_count = page_counts[-1]
        rate_of_change = ((final_count - initial_count) / initial_count) * 100

        direction = "increasing" if rate_of_change > 5 else ("decreasing" if rate_of_change < -5 else "stable")

        trends.append(Trend(
            metric="page_count",
            direction=direction,
            rate_of_change=round(rate_of_change, 2),
            confidence=0.8,
        ))

        if direction == "increasing":
            insights.append(f"Domain is growing: {rate_of_change:.1f}% increase in indexed pages")
        elif direction == "decreasing":
            insights.append(f"Domain is shrinking: {abs(rate_of_change):.1f}% decrease in indexed pages")

    # Analyze technology adoption trends
    tech_added_counts = [len(v) for v in timeline.technologies_added.values()]
    tech_removed_counts = [len(v) for v in timeline.technologies_removed.values()]

    if tech_added_counts:
        avg_adoption = sum(tech_added_counts) / len(tech_added_counts)
        if avg_adoption > 1:
            insights.append(f"Active technology adoption: averaging {avg_adoption:.1f} new technologies per crawl")

    # Moving average for content volume (simplified)
    # ... statistical analysis ...

    return TrendAnalysis(
        domain=domain,
        time_period={
            "start": crawl_ids[0],
            "end": crawl_ids[-1],
        },
        trends=trends,
        insights=insights,
    )
```

---

## Agent 16: dataset_management

### Objective
CRUD operations for managing saved datasets.

### Dependencies
**⚠️ Depends on Wave 1 export tools being complete**

### Specification

**Function Signatures:**
```python
async def list_datasets_tool() -> DatasetList:
    """List all saved datasets."""

async def get_dataset_tool(name: str) -> DatasetInfo:
    """Get dataset metadata and preview."""

async def merge_datasets(
    dataset_names: list[str],
    output_name: str,
    *,
    deduplicate: bool = True,
) -> Dataset:
    """Merge multiple datasets into one."""

async def filter_dataset(
    dataset_name: str,
    filter_expr: dict[str, Any],
    output_name: str,
) -> Dataset:
    """Filter dataset records by criteria."""

async def export_dataset(
    dataset_name: str,
    output_path: str,
    format: str = "jsonl",
) -> ExportResult:
    """Export dataset to file."""

async def delete_dataset(name: str) -> DeleteResult:
    """Delete a dataset."""
```

**Pydantic Models:**
```python
class DatasetList(BaseModel):
    """List of datasets."""
    total: int
    datasets: list[Dataset]

class DatasetInfo(BaseModel):
    """Dataset with preview."""
    dataset: Dataset
    preview: list[dict[str, Any]]  # First 10 records

class DeleteResult(BaseModel):
    """Result of delete operation."""
    success: bool
    dataset_name: str
    records_deleted: int
```

**Implementation:**
```python
async def merge_datasets(...):
    from .export import get_dataset, get_dataset_records, create_dataset

    all_records = []
    seen = set()  # For deduplication

    for name in dataset_names:
        dataset = await get_dataset(name)
        if not dataset:
            continue

        records = await get_dataset_records(dataset.id)

        if deduplicate:
            for record in records:
                # Use URL as deduplication key
                key = record.get("url", json.dumps(record))
                if key not in seen:
                    all_records.append(record)
                    seen.add(key)
        else:
            all_records.extend(records)

    merged = await create_dataset(
        name=output_name,
        description=f"Merged from: {', '.join(dataset_names)}",
        data=all_records,
        metadata={"source_datasets": dataset_names, "deduplicated": deduplicate},
    )

    return merged


async def filter_dataset(...):
    from .export import get_dataset, get_dataset_records, create_dataset

    dataset = await get_dataset(dataset_name)
    if not dataset:
        raise ValueError(f"Dataset not found: {dataset_name}")

    records = await get_dataset_records(dataset.id)

    # Apply filter
    filtered_records = []
    for record in records:
        match = True
        for key, value in filter_expr.items():
            if record.get(key) != value:
                match = False
                break
        if match:
            filtered_records.append(record)

    filtered = await create_dataset(
        name=output_name,
        description=f"Filtered from {dataset_name}: {filter_expr}",
        data=filtered_records,
        metadata={"source_dataset": dataset_name, "filter": filter_expr},
    )

    return filtered


async def delete_dataset(name: str):
    from .export import get_dataset

    dataset = await get_dataset(name)
    if not dataset:
        return DeleteResult(success=False, dataset_name=name, records_deleted=0)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Delete records first
    cursor.execute("DELETE FROM dataset_records WHERE dataset_id = ?", (dataset.id,))
    records_deleted = cursor.rowcount

    # Delete dataset
    cursor.execute("DELETE FROM datasets WHERE id = ?", (dataset.id,))

    conn.commit()
    conn.close()

    return DeleteResult(
        success=True,
        dataset_name=name,
        records_deleted=records_deleted,
    )
```

---

## Integration Requirements

**File:** `src/tools/advanced.py`

**Module Structure:**
```python
"""Advanced features for Common Crawl MCP Server."""

from typing import Any, Optional
from pydantic import BaseModel
from datetime import datetime

__all__ = [
    "content_classification",
    "spam_detection",
    "trend_analysis",
    "list_datasets_tool",
    "get_dataset_tool",
    "merge_datasets",
    "filter_dataset",
    "export_dataset",
    "delete_dataset",
]
```

**MCP Server Registration:**

Add to `src/server.py`:
```python
from .tools import advanced

@mcp.tool()
async def classify_content(url: str, crawl_id: str = "CC-MAIN-2024-10") -> dict:
    """Classify web page by type and purpose."""
    result = await advanced.content_classification(url, crawl_id)
    return result.model_dump()

@mcp.tool()
async def detect_spam(url: str, crawl_id: str = "CC-MAIN-2024-10") -> dict:
    """Detect if page is spam or low-quality."""
    result = await advanced.spam_detection(url, crawl_id)
    return result.model_dump()

@mcp.tool()
async def analyze_trends(
    domain: str, crawl_ids: list[str], sample_size: int = 100
) -> dict:
    """Analyze trends in domain evolution."""
    result = await advanced.trend_analysis(domain, crawl_ids, sample_size=sample_size)
    return result.model_dump()

# Dataset management tools
@mcp.tool()
async def list_datasets() -> dict:
    """List all saved datasets."""
    result = await advanced.list_datasets_tool()
    return result.model_dump()

@mcp.tool()
async def merge_datasets(
    dataset_names: list[str], output_name: str, deduplicate: bool = True
) -> dict:
    """Merge multiple datasets."""
    result = await advanced.merge_datasets(dataset_names, output_name, deduplicate=deduplicate)
    return result.model_dump()

# ... register other dataset management tools
```

## Testing Requirements

**File:** `tests/integration/test_advanced_features.py`

**Test Coverage:**
- [ ] test_content_classification_blog
- [ ] test_content_classification_product
- [ ] test_spam_detection_legitimate
- [ ] test_spam_detection_spam
- [ ] test_trend_analysis_growing_domain
- [ ] test_trend_analysis_stable_domain
- [ ] test_merge_datasets
- [ ] test_merge_datasets_with_deduplication
- [ ] test_filter_dataset
- [ ] test_export_dataset
- [ ] test_delete_dataset

## Acceptance Criteria

- [ ] content_classification achieves >80% accuracy on test pages
- [ ] spam_detection identifies known spam patterns
- [ ] trend_analysis detects page count changes correctly
- [ ] Dataset merge handles duplicates properly
- [ ] Dataset filter applies criteria correctly
- [ ] Dataset delete removes all records
- [ ] All tools registered with MCP server
- [ ] Integration tests pass
- [ ] Performance remains acceptable (no significant slowdown)

## Priority Notes

**This wave is OPTIONAL.** If time is constrained:

1. **Skip entirely** - Focus on Waves 1, 2, 4, 5
2. **Partial implementation** - Implement only dataset_management (most useful)
3. **Simplified versions** - Reduce classification/spam detection sophistication

The core value is in Waves 1-2 (export, resources, prompts) and Wave 4-5 (testing, docs).
