# Phase 5: Aggregation & Statistics Tools

## Epic: Domain-Wide Aggregation & Statistics

Build powerful aggregation tools that analyze patterns across multiple pages to generate comprehensive reports, link graphs, timelines, and statistical insights about entire domains.

**Estimated Duration**: 12 hours
**Phase**: 5
**Priority**: High
**Complexity**: Complex

## Methodology Guidance

This task follows the **Distributed SPECTRA** methodology for autonomous agent execution.

**Your Focus**: Context → Clarify (if needed) → Implement → Test → Refine → Handoff

**Time Allocation Guide**:
- Context Gathering (5-10%): Read this spec, review dependencies and handoffs
- Implementation (40-50%): Production-quality code with error handling
- Testing (25-30%): MANDATORY - comprehensive unit and integration tests
- Refinement (5-10%): Code review for quality, performance, security
- Handoff (5-10%): Document decisions and specs for dependent tasks

**Wave Context**: Wave 3 - Depends on Waves 1-2 and Phase 4

Review handoffs from:
- Phase 1: Core Infrastructure (caching, S3, CDX client)
- Phase 3: Fetching Tools (batch fetching capabilities)
- Phase 4: Parsing Tools (technology detection, link extraction, SEO analysis)

Specs are provided - minimal clarification needed. Focus on scalability and performance.

**Quality Requirements**:
- ✅ Tests must exist and pass (minimum 70% coverage, target 80%)
- ✅ Code quality checks must pass (linting, type checking)
- ✅ Documentation required for all public tools
- ✅ Performance optimization required (handles 1000+ pages)
- ✅ Handoff required for Phase 6 (Export needs aggregated data structures)

📚 **Full Methodology**: `~/.claude/docs/agent-task-execution-methodology.md`

## Context

### Why This Epic Matters
Aggregation transforms individual page analysis into domain-wide insights. These tools enable competitive analysis, historical tracking, and comprehensive reports that would be impossible to create manually.

### What It Depends On
- **Phase 1**: CDX client for domain queries, caching for performance
- **Phase 3**: Batch fetching for efficient page retrieval
- **Phase 4**: Parsing utilities for extracting data from pages

### What Depends On It
- **Phase 6**: Export tools format aggregated results
- **Phase 8**: Prompts guide aggregation workflows
- **Phase 9**: Advanced features build on aggregation capabilities

## Tasks

### Task 5.1: Implement domain_technology_report() Tool (2.5h)
**Agent**: Backend Specialist
**Complexity**: Complex

**Subtasks**:
- [ ] Create `tools/aggregation.py`
- [ ] Implement `domain_technology_report(domain, crawl_id, sample_size)` tool
- [ ] Fetch all pages from domain (up to sample_size)
- [ ] Run `analyze_technologies()` on each page
- [ ] Aggregate technology usage across all pages
- [ ] Calculate adoption percentages
- [ ] Identify version consistency
- [ ] Group by technology category (CMS, Analytics, CDN, etc.)
- [ ] Implement progress tracking
- [ ] Cache aggressively (TTL: 7 days)
- [ ] Return `TechReport` schema

**Acceptance Criteria**:
- Handles domains with 1000+ pages
- Progress reporting works
- Aggregation is accurate
- Caching reduces repeat work
- Memory efficient (streaming/batch processing)

### Task 5.2: Implement domain_link_graph() Tool (3h)
**Agent**: Backend Specialist
**Complexity**: Complex

**Subtasks**:
- [ ] Implement `domain_link_graph(domain, crawl_id, depth)` tool
- [ ] Fetch all domain pages
- [ ] Extract links using Phase 4's `extract_links()`
- [ ] Build graph structure (nodes = pages, edges = links)
- [ ] Calculate metrics:
  - In-degree (incoming links)
  - Out-degree (outgoing links)
  - Hub pages (most linked-to)
  - Authority pages (link to hubs)
  - Orphan pages (no incoming links)
- [ ] Implement simple PageRank-style algorithm
- [ ] Support depth parameter for multi-level crawling
- [ ] Return `LinkGraph` schema (nodes + edges + metrics)
- [ ] Memory-efficient graph construction

**Acceptance Criteria**:
- Correctly builds link graph from domain pages
- Hub/authority detection is accurate
- PageRank values are reasonable
- Handles circular links correctly
- Memory efficient for large domains

### Task 5.3: Implement keyword_frequency_analysis() Tool (2h)
**Agent**: Backend Specialist
**Complexity**: Standard

**Subtasks**:
- [ ] Implement `keyword_frequency_analysis(urls, keywords)` tool
- [ ] Fetch and parse HTML from all URLs
- [ ] Extract clean text (remove scripts, styles, nav)
- [ ] Count keyword occurrences (case-insensitive)
- [ ] Calculate TF-IDF scores for each keyword
- [ ] Find co-occurrence patterns (keywords appearing together)
- [ ] Generate frequency matrix
- [ ] Support stemming/lemmatization (optional)
- [ ] Return `KeywordStats` schema

**Acceptance Criteria**:
- Accurate keyword counting
- TF-IDF scores are correctly calculated
- Co-occurrence detection works
- Handles large keyword lists
- Results are actionable

### Task 5.4: Implement domain_evolution_timeline() Tool (2.5h)
**Agent**: Backend Specialist
**Complexity**: Complex

**Subtasks**:
- [ ] Implement `domain_evolution_timeline(domain, crawl_ids)` tool
- [ ] Fetch domain stats from each crawl in list
- [ ] Compare page counts across crawls
- [ ] Track technology adoption/removal
- [ ] Detect major content changes
- [ ] Calculate growth/decline rates
- [ ] Identify significant events (major redesigns, migrations)
- [ ] Return `Timeline` schema with time-series data

**Acceptance Criteria**:
- Correctly tracks changes across crawls
- Technology migrations are detected
- Growth patterns are accurate
- Timeline is chronologically ordered
- Results are visualization-ready

### Task 5.5: Implement header_analysis() Tool (1.5h)
**Agent**: Backend Specialist
**Complexity**: Standard

**Subtasks**:
- [ ] Implement `header_analysis(domain, crawl_id)` tool
- [ ] Fetch all pages from domain
- [ ] Aggregate HTTP headers across pages
- [ ] Analyze security headers:
  - Content-Security-Policy
  - Strict-Transport-Security
  - X-Frame-Options
  - X-Content-Type-Options
  - Referrer-Policy
- [ ] Analyze caching headers:
  - Cache-Control
  - ETag
  - Expires
- [ ] Check server identification
- [ ] Calculate security score (0-100)
- [ ] Generate recommendations
- [ ] Return `HeaderReport` schema

**Acceptance Criteria**:
- Correctly identifies all security headers
- Security scoring is reasonable
- Recommendations are actionable
- Handles inconsistent headers across pages
- Reports common misconfigurations

### Task 5.6: Add Progress Tracking & Sampling (1h)
**Agent**: Backend Specialist
**Complexity**: Standard

**Subtasks**:
- [ ] Implement progress callback system for long operations
- [ ] Add sampling support (analyze subset for speed)
- [ ] Implement memory-efficient streaming
- [ ] Add cancellation support
- [ ] Log progress at regular intervals

**Acceptance Criteria**:
- Progress callbacks work correctly
- Sampling is representative
- Memory usage stays bounded
- Cancellation is clean (no orphaned resources)

### Task 5.7: Integration & Performance Testing (1.5h)
**Agent**: QA Specialist + Backend Specialist
**Complexity**: Complex

**Subtasks**:
- [ ] Create `tests/integration/test_aggregation.py`
- [ ] Test domain_technology_report on multi-page domains
- [ ] Test domain_link_graph with circular links
- [ ] Test keyword_frequency_analysis with real content
- [ ] Test domain_evolution_timeline across multiple crawls
- [ ] Test header_analysis on security-focused sites
- [ ] Benchmark performance with 100, 500, 1000 pages
- [ ] Profile memory usage
- [ ] Test caching effectiveness
- [ ] Achieve >70% coverage

**Acceptance Criteria**:
- All integration tests pass
- Performance is acceptable (<5min for 1000 pages)
- Memory usage is bounded
- Caching reduces repeat work by >80%
- Coverage >70%

## Acceptance Criteria

### Functional
- [ ] All 5 aggregation tools are implemented and working
- [ ] Technology reports show accurate adoption percentages
- [ ] Link graphs correctly represent domain structure
- [ ] Keyword analysis provides TF-IDF scores
- [ ] Timeline tools track changes across crawls
- [ ] Header analysis identifies security issues

### Performance
- [ ] Can analyze domains with 1000+ pages
- [ ] Analysis completes in reasonable time (<10min for 1000 pages)
- [ ] Memory usage stays below 1GB for large domains
- [ ] Progress reporting works for long operations
- [ ] Caching reduces repeat work significantly

### Technical
- [ ] Code follows project patterns (async, caching, error handling)
- [ ] All tools return proper Pydantic models
- [ ] Streaming/batch processing for memory efficiency
- [ ] Error messages are clear and actionable
- [ ] Type hints are complete

### Testing
- [ ] Unit tests cover aggregation logic
- [ ] Integration tests use real multi-page scenarios
- [ ] Performance tests validate scalability
- [ ] Test coverage >70% (target 80%)
- [ ] All tests pass

### Documentation
- [ ] All tools have comprehensive docstrings
- [ ] Examples included for each tool
- [ ] Performance characteristics documented
- [ ] Memory usage notes included
- [ ] Handoff document created for Phase 6

## Dependencies

**Depends On:**
- Phase 1: Core Infrastructure (CDX client, caching, S3)
- Phase 3: Fetching Tools (batch_fetch_pages)
- Phase 4: Parsing Tools (analyze_technologies, extract_links, analyze_seo)

**Blocks:**
- Phase 6: Export & Integration (needs aggregated data structures)
- Phase 8: MCP Prompts (guides aggregation workflows)
- Phase 9: Advanced Features (builds on aggregation)

**Parallel Work:**
Can work in parallel with Phase 6 if export tools don't depend on aggregation.

## Technical Notes

### Technology Stack
- **Graph Analysis**: NetworkX (optional, for advanced metrics)
- **Text Analysis**: NLTK or spaCy (for stemming/lemmatization)
- **Performance**: asyncio for concurrent operations
- **Memory**: Generator patterns for streaming

### Patterns to Use
- **Streaming**: Process pages incrementally, don't load all in memory
- **Batching**: Fetch pages in batches of 50-100
- **Caching**: Aggressive caching of expensive operations (7-day TTL)
- **Progress**: Callback-based progress reporting
- **Sampling**: Default to analyzing sample, option for full analysis

### Performance Optimization Strategies

1. **Parallel Processing**:
   ```python
   async def analyze_domain(domain, pages):
       # Fetch and analyze pages concurrently
       tasks = [analyze_page(p) for p in pages]
       results = await asyncio.gather(*tasks, return_exceptions=True)
   ```

2. **Memory Management**:
   ```python
   async def stream_analysis(domain):
       # Process pages in batches
       async for batch in fetch_in_batches(domain, batch_size=50):
           yield analyze_batch(batch)
           # Batch is garbage collected after yield
   ```

3. **Caching Strategy**:
   - Cache individual page analyses (24h TTL)
   - Cache aggregated reports (7-day TTL)
   - Invalidate cache if crawl_id changes

### Known Challenges

1. **Large Domains**: Sites with 10,000+ pages
   - **Solution**: Default to sampling (1000 pages), option for full scan

2. **Memory Usage**: Graph construction can be memory-intensive
   - **Solution**: Use sparse data structures, stream where possible

3. **Long Processing Times**: 1000 pages might take 5-10 minutes
   - **Solution**: Progress callbacks, async execution, caching

4. **Circular Links**: Internal link graphs often have cycles
   - **Solution**: Track visited nodes, handle cycles in PageRank

### Security Considerations
- Rate limit domain queries to avoid overwhelming CDX
- Sanitize domain names before querying
- Set max_pages limits to prevent abuse
- Validate keyword lists (prevent injection)

## Handoff Document (for Phase 6)

After completing this phase, create `handoffs/phase-5-to-6.md` with:

1. **Aggregation Data Structures**:
   - `TechReport` schema and example
   - `LinkGraph` schema and example
   - `KeywordStats` schema and example
   - `Timeline` schema and example
   - `HeaderReport` schema and example

2. **Export Requirements**:
   - What formats make sense for each aggregation type
   - Suggested CSV column layouts
   - JSON structure for visualizations

3. **Performance Characteristics**:
   - Average processing time for various domain sizes
   - Memory usage patterns
   - Cache hit rates

4. **Known Limitations**:
   - Maximum practical domain size
   - Sampling strategies
   - Edge cases to handle

5. **Visualization Suggestions**:
   - Link graph: D3.js force-directed layout
   - Timeline: Line charts with annotations
   - Tech report: Stacked bar charts
   - Keywords: Word clouds, frequency tables

## Resources

- [NetworkX Documentation](https://networkx.org/) (for advanced graph metrics)
- [TF-IDF Explanation](https://en.wikipedia.org/wiki/Tf%E2%80%93idf)
- [PageRank Algorithm](https://en.wikipedia.org/wiki/PageRank)
- [HTTP Security Headers](https://securityheaders.com/)
- [Python asyncio Patterns](https://docs.python.org/3/library/asyncio.html)

## Success Metrics

- [ ] 5 aggregation tools implemented and registered
- [ ] Can analyze domains with 1000+ pages in <10 minutes
- [ ] Memory usage <1GB for large domains
- [ ] Technology reports >95% accurate
- [ ] Link graphs correctly represent structure
- [ ] Timeline tools detect major changes
- [ ] Integration tests all passing
- [ ] Code coverage >70%
- [ ] Zero critical bugs
- [ ] Documentation complete
- [ ] Handoff document created
