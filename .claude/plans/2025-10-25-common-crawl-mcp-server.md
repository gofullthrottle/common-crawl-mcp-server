# Epic Common Crawl MCP Server - Implementation Plan

**Project:** Common Crawl MCP Server
**Date:** 2025-10-25
**Scope:** Build a comprehensive MCP server for querying and analyzing Common Crawl's petabyte-scale web archive

---

## Overview

Create an MCP (Model Context Protocol) server that transforms Common Crawl's massive web archive into an accessible research platform. The server will provide AI-powered tools for discovering, fetching, parsing, analyzing, and exporting web archive data.

---

## Step 0: Document This Plan ✓

This plan has been saved to `.claude/plans/2025-10-25-common-crawl-mcp-server.md`

---

## Technology Stack

**Language:** Python 3.11+
**Framework:** FastMCP (Model Context Protocol)
**Key Dependencies:**
- `mcp[server]` - FastMCP server framework
- `boto3` - AWS S3 access for Common Crawl bucket
- `warcio` - WARC file parsing
- `beautifulsoup4`, `lxml` - HTML parsing
- `pandas` - Data analysis and aggregation
- `pydantic` - Data validation and schemas
- `httpx` - Async HTTP client
- `sqlalchemy`, `aiosqlite` - Data persistence

---

## Project Architecture

```
common-crawl-mcp-server/
├── src/
│   ├── server.py              # Main FastMCP server entry point
│   ├── config.py              # Configuration management
│   ├── core/                  # Core infrastructure
│   │   ├── cc_client.py       # CDX Server API client
│   │   ├── cache.py           # Multi-tier caching layer
│   │   ├── s3_manager.py      # S3 access wrapper
│   │   └── warc_parser.py     # WARC file parsing
│   ├── tools/                 # MCP tools by category
│   │   ├── discovery.py       # Discovery & metadata tools
│   │   ├── fetching.py        # Data fetching tools
│   │   ├── parsing.py         # Parsing & analysis tools
│   │   ├── aggregation.py     # Aggregation & statistics
│   │   ├── export.py          # Export & integration
│   │   └── advanced.py        # Advanced features (optional)
│   ├── resources/             # MCP resources
│   │   └── cc_resources.py    # Common Crawl resources
│   ├── prompts/               # MCP prompts
│   │   └── cc_prompts.py      # Guided workflows
│   ├── models/                # Data models
│   │   └── schemas.py         # Pydantic models
│   └── utils/                 # Utilities
│       ├── html_parser.py
│       ├── technology_detector.py
│       └── validators.py
├── tests/                     # Test suite
├── docs/                      # Documentation
├── pyproject.toml            # Project configuration
└── README.md                 # Project documentation
```

---

## Phase 0: Project Setup & Architecture (Day 1)

### Objectives
Initialize project structure, configure dependencies, and establish architectural patterns.

### Tasks

1. **Create Project Structure**
   - Initialize `common-crawl-mcp-server/` directory
   - Set up Python package structure
   - Create all directory placeholders

2. **Configure Project with `uv`**
   - Initialize `pyproject.toml`
   - Add all required dependencies
   - Set up Python 3.11+ requirement
   - Configure development dependencies

3. **Create Base Configuration**
   - Implement `src/config.py`
   - S3 bucket settings (Common Crawl public bucket)
   - Cache directories and size limits
   - Rate limiting configuration
   - AWS region (us-east-1)

4. **Initialize Main Server**
   - Create `src/server.py` with FastMCP initialization
   - Set up basic server structure
   - Configure logging

### Success Criteria
- Project structure created
- Dependencies installable via `uv`
- Server can start (no tools yet)
- Configuration loads successfully

---

## Phase 1: Core Infrastructure (Days 2-3)

### Objectives
Build foundational components for Common Crawl interaction.

### Tasks

1. **CDX Server Client (`core/cc_client.py`)**
   - Implement CDX API wrapper (https://index.commoncrawl.org/)
   - `search_index()` - Query index for URLs/domains
   - `get_crawl_info()` - Get metadata for specific crawl
   - `list_crawls()` - List all available crawls
   - Pagination handling for large result sets
   - Error handling with exponential backoff
   - Request rate limiting

2. **S3 Manager (`core/s3_manager.py`)**
   - Boto3 wrapper for Common Crawl bucket
   - Anonymous access configuration (public dataset)
   - `download_file()` - Download WARC/WAT/WET files
   - `stream_file()` - Stream large files without full load
   - Error handling and retries
   - Cost tracking (monitor egress)
   - Rate limiting for S3 requests

3. **WARC Parser (`core/warc_parser.py`)**
   - Use `warcio` library
   - `parse_warc_file()` - Extract individual records
   - `extract_http_response()` - Get HTTP headers + payload
   - Handle gzip compression
   - Record filtering and iteration
   - Memory-efficient streaming

4. **Caching Layer (`core/cache.py`)**
   - Multi-tier architecture:
     - Memory cache (LRU for hot data)
     - Disk cache (configurable size limit)
     - S3 as ultimate source
   - `get()`, `set()`, `delete()` methods
   - TTL-based expiration
   - Cache statistics tracking
   - Eviction policies (LRU + size-based)
   - Cache warming for common queries

5. **Data Models (`models/schemas.py`)**
   - Pydantic models for type safety:
     - `CrawlInfo` - Crawl metadata
     - `IndexRecord` - CDX index record
     - `PageContent` - Fetched page data
     - `WarcRecord` - Raw WARC record
     - `DomainStats` - Domain statistics

### Success Criteria
- Can query "example.com" via CDX and receive results
- Can download and parse a WARC record from S3
- Cache reduces redundant S3 requests by >80%
- All core modules have unit tests

---

## Phase 2: Discovery & Metadata Tools (Days 4-5)

### Objectives
Enable users to explore what's available in Common Crawl before fetching data.

### Tasks - Implement `tools/discovery.py`

1. **`list_crawls()`** → `List[CrawlInfo]`
   - Query CDX for available crawls
   - Return: id, date, status, approximate size
   - Cache results (crawls don't change often)

2. **`get_crawl_stats(crawl_id: str)`** → `CrawlStats`
   - Parse `collinfo.json` from S3
   - Return: total pages, domains, file counts, size
   - Cache aggressively

3. **`search_index(query: str, crawl_id: str, limit: int = 100)`** → `List[IndexRecord]`
   - Query CDX server with URL patterns
   - Support wildcards (*.example.com)
   - Pagination support
   - Return: matching URLs with metadata

4. **`get_domain_stats(domain: str, crawl_id: str)`** → `DomainStats`
   - Count pages from domain in crawl
   - Calculate total data size
   - Identify subdomains
   - Return statistics object

5. **`compare_crawls(crawl_ids: List[str], domain: str)`** → `ComparisonResult`
   - Track domain presence across crawls
   - Identify additions/removals
   - Page count trends

6. **`estimate_query_size(filters: dict)`** → `SizeEstimate`
   - Predict data volume before fetching
   - Estimate S3 costs
   - Suggest sampling strategies

### Success Criteria
- Can list all available crawls
- Can search for specific domains/URLs
- Statistics are accurate
- Results are properly cached

---

## Phase 3: Data Fetching & Extraction Tools (Days 6-7)

### Objectives
Retrieve actual page content from Common Crawl archives.

### Tasks - Implement `tools/fetching.py`

1. **`fetch_page_content(url: str, crawl_id: str)`** → `PageContent`
   - Query CDX for URL location in WARC
   - Download WARC record from S3
   - Extract HTML content, headers, status code
   - Return structured page data

2. **`fetch_warc_records(urls: List[str], crawl_id: str)`** → `List[WarcRecord]`
   - Batch fetch multiple URLs
   - Use caching aggressively
   - Parallel downloads with rate limiting
   - Return raw WARC records

3. **`batch_fetch_pages(domain: str, crawl_id: str, limit: int = 100)`** → `List[PageContent]`
   - Get multiple pages from a domain
   - Paginated results
   - Progress reporting for large domains
   - Memory-efficient streaming

4. **`fetch_wat_metadata(url: str, crawl_id: str)`** → `WatMetadata`
   - Lightweight metadata-only fetch
   - No full page content
   - Faster than WARC download

5. **`fetch_wet_text(url: str, crawl_id: str)`** → `str`
   - Plain text extraction only
   - No HTML parsing needed
   - Useful for text analysis

### Implementation Details
- All operations check cache first
- S3 downloads are streamed, not fully loaded to memory
- Gzip decompression on-the-fly
- Parallel downloads with configurable concurrency
- Progress callbacks for long operations

### Success Criteria
- Can fetch individual pages reliably
- Batch operations handle errors gracefully
- Cache hit rate >80% for repeated queries
- Memory usage remains constant during large batches

---

## Phase 4: Parsing & Analysis Tools (Days 8-10)

### Objectives
Transform raw HTML into structured, analyzable data.

### Tasks - Implement `tools/parsing.py`

1. **`parse_html(content: str)`** → `ParsedHtml`
   - Use BeautifulSoup4 with lxml parser
   - Extract: title, meta tags, headings (h1-h6), links, scripts, styles
   - Detect charset and handle encoding
   - Return structured data model

2. **`extract_links(url: str, crawl_id: str)`** → `LinkAnalysis`
   - Fetch page and parse all `<a>` tags
   - Categorize links: internal, external, broken
   - Resolve relative URLs
   - Return link graph data

3. **`analyze_technologies(url: str, crawl_id: str)`** → `TechStack`
   - Wappalyzer-style technology detection
   - Check: meta tags, script sources, HTML patterns, HTTP headers
   - Detect: CMS, frameworks, analytics, CDNs, hosting
   - Return: technology list with confidence scores

4. **`extract_structured_data(url: str, crawl_id: str)`** → `StructuredData`
   - Parse JSON-LD embedded data
   - Extract microdata
   - Parse Open Graph tags
   - Parse Twitter Cards
   - Validate against schemas

5. **`analyze_seo(url: str, crawl_id: str)`** → `SeoAnalysis`
   - Check title length and uniqueness
   - Meta description analysis
   - Heading structure (h1-h6)
   - Canonical URLs
   - Robots meta tags
   - Hreflang attributes
   - Return: issues list and recommendations

6. **`detect_language(url: str, crawl_id: str)`** → `LanguageInfo`
   - Check HTML lang attribute
   - Use language detection library (langdetect)
   - Return detected language with confidence

### Supporting Utilities

**`utils/technology_detector.py`:**
- JSON database of detection patterns
- Popular CMS: WordPress, Drupal, Joomla, Wix, Squarespace
- Frameworks: React, Vue, Angular, Next.js, Nuxt, Svelte
- Analytics: Google Analytics, Mixpanel, Segment, Amplitude
- CDNs: Cloudflare, Fastly, Akamai
- Hosting: AWS, Vercel, Netlify, GitHub Pages

**`utils/html_parser.py`:**
- Helper functions for common parsing tasks
- HTML sanitization
- Text extraction
- Table parsing

### Success Criteria
- Can parse complex HTML pages correctly
- Technology detection has >90% accuracy on known sites
- SEO analysis identifies real issues
- Language detection is accurate

---

## Phase 5: Aggregation & Statistics Tools (Days 11-13)

### Objectives
Analyze patterns across multiple pages and generate insights.

### Tasks - Implement `tools/aggregation.py`

1. **`domain_technology_report(domain: str, crawl_id: str)`** → `TechReport`
   - Fetch all pages from domain
   - Run `analyze_technologies()` on each
   - Aggregate technology usage
   - Calculate adoption percentages
   - Return complete tech stack report

2. **`domain_link_graph(domain: str, crawl_id: str, depth: int = 1)`** → `LinkGraph`
   - Map internal link structure
   - Calculate link counts for each page
   - Identify hub pages (most linked-to)
   - Detect isolated pages
   - Calculate PageRank-style metrics
   - Return graph structure (nodes + edges)

3. **`keyword_frequency_analysis(urls: List[str], keywords: List[str])`** → `KeywordStats`
   - Extract text from all pages
   - Count keyword occurrences
   - Calculate TF-IDF scores
   - Find co-occurrence patterns
   - Return frequency matrix

4. **`domain_evolution_timeline(domain: str, crawl_ids: List[str])`** → `Timeline`
   - Compare domain across multiple crawls
   - Track page count changes
   - Monitor technology adoption/removal
   - Detect content changes
   - Return timeline data structure

5. **`header_analysis(domain: str, crawl_id: str)`** → `HeaderReport`
   - Aggregate HTTP headers across all domain pages
   - Security headers: CSP, HSTS, X-Frame-Options, X-Content-Type-Options
   - Caching policies: Cache-Control, ETag
   - Server identification
   - Calculate security score
   - Return recommendations

### Performance Considerations
- These tools process many pages → implement job queue
- Progress tracking via callbacks
- Option to sample (analyze subset for speed)
- Results cached aggressively
- Parallel processing where possible
- Memory-efficient aggregation

### Success Criteria
- Can analyze domains with 1000+ pages
- Aggregations are accurate
- Performance is acceptable (minutes, not hours)
- Progress reporting works
- Results are cacheable

---

## Phase 6: Export & Integration Tools (Days 14-15)

### Objectives
Enable users to export and use analysis results in other tools.

### Tasks - Implement `tools/export.py`

1. **`export_to_csv(data: Any, fields: List[str], filepath: str)`** → `ExportResult`
   - Convert analysis results to CSV format
   - Handle nested data structures (flatten)
   - Support custom field selection
   - Write to file or return string
   - Return: filepath, row count, file size

2. **`export_to_jsonl(data: Any, filepath: str)`** → `ExportResult`
   - JSON Lines format (one JSON object per line)
   - ML-friendly format
   - Streaming for large datasets
   - Memory-efficient writing

3. **`create_dataset(query: dict, name: str)`** → `Dataset`
   - Execute query and save results
   - Store in SQLite database
   - Add metadata (created_at, query parameters)
   - Make queryable for future use
   - Return: dataset_id, row count, metadata

4. **`generate_report(analysis_results: Any, format: str = "markdown")`** → `str`
   - Templates for common report types
   - Formats: markdown, HTML, PDF
   - Include charts/visualizations
   - Executive summary
   - Return: report content or filepath

5. **`export_warc_subset(urls: List[str], output_path: str)`** → `str`
   - Create custom WARC file from specific URLs
   - Maintain WARC format compliance
   - Useful for sharing datasets
   - Compress output

### Storage Schema (SQLite)

**Datasets Table:**
```sql
CREATE TABLE datasets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    query JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    row_count INTEGER,
    size_bytes INTEGER
);
```

**Results Table:**
```sql
CREATE TABLE results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id TEXT REFERENCES datasets(id),
    data JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Success Criteria
- CSV exports work with Excel/Google Sheets
- JSONL format is valid
- Datasets persist correctly
- Reports are readable and useful
- WARC files are spec-compliant

---

## Phase 7: MCP Resources (Day 16)

### Objectives
Expose Common Crawl data as MCP resources for LLM context.

### Tasks - Implement `resources/cc_resources.py`

1. **`@mcp.resource("commoncrawl://crawls")`**
   - List all available crawls with metadata
   - Update on access (with TTL cache)
   - Return JSON array

2. **`@mcp.resource("commoncrawl://crawl/{crawl_id}/stats")`**
   - Detailed statistics for specific crawl
   - Total pages, domains, size
   - Cache aggressively (crawls don't change)

3. **`@mcp.resource("commoncrawl://domain/{domain}/latest")`**
   - Latest crawl data for domain
   - Page count, last crawl date
   - Detected technologies
   - JSON format

4. **`@mcp.resource("commoncrawl://domain/{domain}/timeline")`**
   - Historical presence across all crawls
   - Track changes over time
   - Timeline JSON structure

5. **`@mcp.resource("commoncrawl://page/{url}")`**
   - Page content from latest crawl
   - URL must be encoded for path safety
   - Return page content

6. **`@mcp.resource("commoncrawl://datasets/saved")`**
   - User's saved datasets
   - Query from SQLite
   - List with metadata

### Purpose
Resources enable the LLM to "know about" Common Crawl data contextually without explicit function calls. When the LLM sees these resources, it can reference them in responses.

### Success Criteria
- All resources return valid JSON
- Resources are discoverable
- Data is LLM-friendly format
- Caching works properly

---

## Phase 8: MCP Prompts (Day 17)

### Objectives
Guide the LLM through complex multi-step workflows.

### Tasks - Implement `prompts/cc_prompts.py`

1. **`@mcp.prompt() investigate_domain(domain: str, focus: str = "comprehensive")`**
   - Returns prompt instructing LLM to:
     * Check domain stats across all crawls
     * Analyze technology stack
     * Examine link structure
     * Review SEO configuration
     * Generate summary report
   - Tailored by focus: "tech", "seo", "links", "comprehensive"

2. **`@mcp.prompt() competitive_analysis(domains: List[str])`**
   - Returns prompt for side-by-side comparison
   - Metrics to compare:
     * Page counts
     * Technology stacks
     * Crawl presence timeline
     * Link authority
   - Generate comparison table

3. **`@mcp.prompt() technology_audit(domain: str)`**
   - Returns prompt for deep technology analysis
   - Steps:
     * Identify all technologies
     * Check versions
     * Security implications
     * Performance considerations
     * Recommendations

4. **`@mcp.prompt() seo_audit(url: str)`**
   - Returns prompt for structured SEO investigation
   - Checklist:
     * Title and meta tags
     * Heading structure
     * Internal linking
     * Structured data
     * Technical SEO
   - Generate findings report

5. **`@mcp.prompt() historical_investigation(domain: str, start_date: str, end_date: str)`**
   - Returns prompt for temporal analysis
   - Track:
     * Page count changes
     * Technology migrations
     * Major redesigns
     * Content evolution
   - Generate timeline visualization

### Key Design Principles
- Prompts structure the LLM's approach
- They're templates formatted with user parameters
- Guide multi-step workflows
- Ensure comprehensive analysis
- Produce consistent output formats

### Success Criteria
- Prompts are discoverable
- LLM follows workflow correctly
- Output is consistent and useful
- Prompts are maintainable

---

## Phase 9: Advanced Features (Days 18-20) - Optional

### Objectives
Add sophisticated features that differentiate this from basic tools.

### Tasks - Implement `tools/advanced.py`

1. **`classify_content(url: str, crawl_id: str)`** → `ContentClassification`
   - Use keyword-based classification initially
   - Categories:
     * News/Blog
     * E-commerce
     * Documentation
     * Social Media
     * Corporate/Marketing
     * Forum/Community
   - Return category with confidence
   - Can upgrade to ML model later

2. **`detect_spam_seo(domain: str, crawl_id: str)`** → `SpamScore`
   - Heuristics detection:
     * Keyword stuffing (high keyword density)
     * Hidden text (color tricks, tiny fonts)
     * Doorway pages
     * Thin content (low word count)
     * Duplicate content
   - Return score 0-100 with indicators
   - Explain findings

3. **Cost Optimization Features**
   - Enhance `core/cache.py`:
     * Track S3 download costs
     * Predict query costs before execution
     * Suggest caching strategies
     * Alert on expensive operations
   - `query_optimizer()`:
     * Rewrite queries for efficiency
     * Use WAT instead of WARC when possible
     * Batch related queries

4. **`generate_link_graph_viz(domain: str, crawl_id: str)`** → `str`
   - Generate visualization data
   - Output formats:
     * DOT format (Graphviz)
     * JSON for D3.js
     * Mermaid diagram
   - Client-side rendering

### Success Criteria
- Content classification is reasonably accurate
- Spam detection catches obvious cases
- Cost tracking is accurate
- Visualizations are valid formats

---

## Phase 10: Testing, Documentation, Polish (Days 21-23)

### Objectives
Ensure production readiness through testing, documentation, and refinement.

### Testing Strategy

**1. Unit Tests (pytest)**
- Test coverage >80%
- Core modules:
  * `core/cc_client.py` - CDX API interactions
  * `core/cache.py` - Caching logic
  * `core/warc_parser.py` - WARC parsing
- Tool functions:
  * Mock S3/CDX responses
  * Test error handling
  * Test edge cases
- Run with: `pytest tests/unit/`

**2. Integration Tests**
- Test against real Common Crawl data (small samples)
- Verify WARC parsing with actual files
- End-to-end workflows:
  * Query → Fetch → Parse → Analyze
- Cache behavior
- Database persistence
- Run with: `pytest tests/integration/`

**3. MCP Testing**
- Use `@modelcontextprotocol/sdk` testing utilities
- Verify tool schemas are correct
- Test resource URIs
- Validate prompt outputs
- Test with actual MCP client

**4. Performance Testing**
- Benchmark critical operations
- Memory usage profiling
- Cache efficiency metrics
- Large dataset handling

### Documentation

**1. README.md**
- Project overview
- Features list
- Installation instructions:
  ```bash
  git clone https://github.com/username/common-crawl-mcp-server.git
  cd common-crawl-mcp-server
  uv sync
  ```
- Configuration guide
- Quick start examples
- MCP client integration

**2. API Documentation**
- Auto-generate from docstrings
- Tool reference:
  * Parameters
  * Return types
  * Example requests
  * Example responses
- Resource URI patterns
- Prompt templates

**3. EXAMPLES.md**
Real-world use cases with complete code:
- SEO audit workflow
- Competitive analysis
- Technology stack investigation
- Historical tracking
- Content analysis

**4. ARCHITECTURE.md**
- System design
- Component interactions
- Data flow diagrams
- Caching strategy
- Performance considerations

**5. CONTRIBUTING.md**
- Development setup
- Code style guide
- Testing requirements
- PR process

### Polish & User Experience

**1. Error Messages**
- Clear, actionable error messages
- Suggest solutions
- Include context (URL, crawl_id)
- Example:
  ```
  Error: Domain not found in crawl CC-MAIN-2024-10
  Suggestion: Try a more recent crawl. Use list_crawls() to see available crawls.
  ```

**2. Progress Indicators**
- Long operations show progress
- Estimated time remaining
- Cancellation support
- Example:
  ```
  Fetching 1000 pages from example.com...
  Progress: 45% (450/1000) - ETA: 2m 15s
  ```

**3. Cost Estimation**
- Warn before expensive operations
- Show estimated S3 egress costs
- Suggest alternatives (use cache, sample)
- Example:
  ```
  This query will download ~500MB from S3 (estimated cost: $0.04)
  Consider using cached data or sampling.
  Proceed? [y/N]
  ```

**4. Configuration Validation**
- Check configuration at startup
- Warn about missing optional features
- Suggest optimizations
- Example:
  ```
  Configuration loaded successfully
  Warning: Redis not configured - using in-memory cache only
  Tip: Install Redis for better performance
  ```

**5. Logging**
- Structured logging
- Log levels: DEBUG, INFO, WARNING, ERROR
- Request/response logging
- Performance metrics

### Success Criteria
- Test coverage >80%
- All tests passing
- Documentation complete
- No critical bugs
- Performance acceptable
- User experience polished

---

## Final Step: Document Solution Summary

After project completion, save a solution summary to:
`.claude/plans/2025-10-25-common-crawl-mcp-server-solution-summary.md`

**Solution Summary Contents:**

1. **Completion Status**
   - Which phases were fully completed
   - Partially completed phases
   - Deviations from original plan

2. **What Was Accomplished**
   - Bulleted list of completed features
   - Tool counts by category
   - Key capabilities delivered

3. **Implementation Approach**
   - Key technical decisions made
   - Design patterns used
   - Libraries and frameworks chosen
   - What worked well

4. **Deviations from Original Plan**
   - What changed and why
   - Unexpected challenges
   - New discoveries
   - Scope adjustments

5. **Files Created/Modified**
   - Complete list with file paths
   - Major additions
   - Refactorings performed

6. **Testing & Validation**
   - Test coverage achieved
   - Integration test results
   - Performance benchmarks
   - Known issues

7. **Challenges Encountered**
   - Technical challenges
   - Common Crawl quirks
   - Performance bottlenecks
   - How they were resolved

8. **Lessons Learned**
   - Key insights gained
   - What would be done differently
   - Best practices discovered
   - Common Crawl tips

9. **Next Steps**
   - Future enhancements planned
   - Known limitations
   - Feature requests
   - Performance improvements
   - ML integration opportunities

---

## MVP Deliverables (2-3 weeks)

### Core Value Proposition
Transform Common Crawl from a complex dataset into an accessible research platform through AI-powered analysis.

### MVP Scope
- **Infrastructure** (Phases 0-1): CDX client, S3 access, WARC parsing, caching
- **Discovery** (Phase 2): Explore available crawls and search index
- **Fetching** (Phase 3): Retrieve page content efficiently
- **Parsing** (Phase 4): Extract structured data from HTML
- **Basic Aggregation** (Phase 5): Domain-level analysis
- **Export** (Phase 6): CSV, JSONL, datasets
- **MCP Integration** (Phases 7-8): Resources and prompts for LLM
- **Testing & Docs** (Phase 10): Production readiness

### Future Enhancements (v2)
- Advanced aggregation features (complex link graphs, multi-crawl evolution)
- ML-powered content classification
- Automated spam detection
- Interactive visualizations
- Athena integration for massive-scale queries
- Real-time crawl monitoring
- Custom crawl scheduling
- Webhook notifications

---

## Success Metrics

### Technical Metrics
- Complete technology report for a domain in <2 minutes
- Cache reduces S3 costs by >80%
- Test coverage >80%
- Zero critical bugs
- API response times <500ms (cached), <5s (uncached)

### User Experience Metrics
- LLM can successfully orchestrate complex analysis via prompts
- Export formats work seamlessly with Excel, Jupyter, databases
- Documentation enables self-service
- Error messages guide users to solutions

### Business Metrics
- S3 costs predictable and minimized
- Useful for SEO professionals
- Valuable for security researchers
- Enables data scientists
- Supports business analysts

---

## Risk Mitigation

### Technical Risks
- **Common Crawl API changes**: Monitor API, implement version detection
- **S3 costs escalation**: Aggressive caching, cost warnings, budget alerts
- **WARC format variations**: Robust parsing, error handling
- **Performance issues**: Profiling, optimization, sampling strategies

### Operational Risks
- **Rate limiting**: Implement backoff, respect limits
- **Data quality**: Validation, error detection, user warnings
- **Cache invalidation**: TTL strategies, manual refresh options

---

## Timeline Summary

| Phase | Duration | Key Deliverables |
|-------|----------|------------------|
| 0 | Day 1 | Project setup, structure, dependencies |
| 1 | Days 2-3 | Core infrastructure (CDX, S3, WARC, cache) |
| 2 | Days 4-5 | Discovery & metadata tools |
| 3 | Days 6-7 | Data fetching & extraction tools |
| 4 | Days 8-10 | Parsing & analysis tools |
| 5 | Days 11-13 | Aggregation & statistics tools |
| 6 | Days 14-15 | Export & integration tools |
| 7 | Day 16 | MCP resources |
| 8 | Day 17 | MCP prompts |
| 9 | Days 18-20 | Advanced features (optional) |
| 10 | Days 21-23 | Testing, documentation, polish |

**Total:** 23 days (~3 weeks) for full MVP

---

## Appendix

### Common Crawl Resources
- Main Site: https://commoncrawl.org/
- CDX Server: https://index.commoncrawl.org/
- S3 Bucket: s3://commoncrawl/ (public, us-east-1)
- Documentation: https://commoncrawl.org/the-data/get-started/
- Examples: https://commoncrawl.org/examples/

### MCP Resources
- MCP Specification: https://modelcontextprotocol.io/
- Python SDK: https://github.com/modelcontextprotocol/python-sdk
- FastMCP Docs: (from Context7)

### Related Projects
- Common Crawl Index: https://index.commoncrawl.org/
- cc-index-server: https://github.com/commoncrawl/cc-index-server
- Warcio: https://github.com/webrecorder/warcio
- Wappalyzer: https://www.wappalyzer.com/

---

**Plan Status:** ✓ Approved
**Implementation Start:** 2025-10-25
**Target Completion:** 2025-11-15 (3 weeks)
