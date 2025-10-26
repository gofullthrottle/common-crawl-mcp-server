# Phase 4: HTML Parsing & Analysis Tools

## Epic: HTML Parsing & Analysis

Build comprehensive HTML parsing and analysis capabilities to extract structured data, links, technologies, SEO information, and language detection from archived web pages.

**Estimated Duration**: 12 hours
**Phase**: 4
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

**Wave Context**: Wave 3 - Depends on Waves 1-2 (Core Infrastructure + Discovery/Fetching)

Review handoffs from:
- Phase 1: Core Infrastructure (warc_parser.py, data schemas)
- Phase 3: Fetching Tools (fetch_page_content provides HTML input)

Specs are provided - minimal clarification needed. Focus on implementation quality.

**Quality Requirements**:
- ✅ Tests must exist and pass (minimum 70% coverage, target 85%)
- ✅ Code quality checks must pass (linting, type checking)
- ✅ Documentation required for all public tools
- ✅ Handoff required for Phase 5 (Aggregation needs these utilities)

📚 **Full Methodology**: `~/.claude/docs/agent-task-execution-methodology.md`

## Context

### Why This Epic Matters
HTML parsing is the foundation for all content analysis. These tools extract meaningful data from raw HTML, enabling downstream analysis for SEO, technology detection, link graphs, and aggregation workflows.

### What It Depends On
- **Phase 1**: WARC parser provides HTML content
- **Phase 2**: Search index identifies pages to analyze
- **Phase 3**: Fetching tools retrieve page content

### What Depends On It
- **Phase 5**: Aggregation tools use parsing utilities for domain-wide analysis
- **Phase 6**: Export tools need structured data extraction
- **Phase 8**: Prompts guide analysis workflows

## Tasks

### Task 4.1: Create HTML Parsing Utilities (2h)
**Agent**: Backend Specialist
**Complexity**: Standard

**Subtasks**:
- [ ] Implement `utils/html_parser.py` with BeautifulSoup
- [ ] Create clean text extraction (strip scripts, styles, comments)
- [ ] Implement table parsing to structured data
- [ ] Add HTML sanitization helpers
- [ ] Write helper for common selectors (meta tags, links, headings)

**Acceptance Criteria**:
- Clean text extraction removes all non-content HTML
- Table parser handles rowspan/colspan correctly
- Handles malformed HTML gracefully
- Unit tests cover edge cases

### Task 4.2: Implement parse_html() Tool (1.5h)
**Agent**: Backend Specialist
**Complexity**: Standard

**Subtasks**:
- [ ] Create `tools/parsing.py`
- [ ] Implement `parse_html(url, crawl_id)` tool
- [ ] Extract: title, meta description, headings (h1-h6), body text
- [ ] Parse HTML structure (tag counts, depth metrics)
- [ ] Cache parsed results (TTL: 24h)
- [ ] Return `ParsedHtml` schema

**Acceptance Criteria**:
- Extracts all standard HTML elements correctly
- Returns structured Pydantic model
- Handles missing elements gracefully
- Caching works properly

### Task 4.3: Implement extract_links() Tool (1.5h)
**Agent**: Backend Specialist
**Complexity**: Standard

**Subtasks**:
- [ ] Implement `extract_links(url, crawl_id, link_types)` tool
- [ ] Extract internal vs external links
- [ ] Parse anchor text
- [ ] Identify link types: navigation, content, footer
- [ ] Calculate link metrics (total, unique, broken estimates)
- [ ] Return `LinkAnalysis` schema

**Acceptance Criteria**:
- Correctly classifies internal/external links
- Handles relative URLs properly
- Extracts anchor text
- Provides useful link metrics

### Task 4.4: Implement Technology Detection (3h)
**Agent**: Backend Specialist
**Complexity**: Complex

**Subtasks**:
- [ ] Create `utils/technology_detector.py` with detection patterns
- [ ] Build JSON database of tech signatures:
  - CMS: WordPress, Drupal, Joomla, Wix, Squarespace, Shopify
  - Frameworks: React, Vue, Angular, Next.js, Nuxt, Svelte, jQuery
  - Analytics: Google Analytics, Mixpanel, Segment, Amplitude, Hotjar
  - CDNs: Cloudflare, Fastly, Akamai, CloudFront
  - Hosting: AWS, Vercel, Netlify, GitHub Pages
  - Tag Managers: GTM, Tealium
  - Advertising: Google Ads, Facebook Pixel
- [ ] Implement `analyze_technologies(url, crawl_id)` tool
- [ ] Multi-pass detection: meta tags, scripts, comments, HTML patterns
- [ ] Version detection where possible
- [ ] Confidence scoring
- [ ] Return `TechStack` schema with detected technologies

**Acceptance Criteria**:
- Detects 20+ common technologies with >90% accuracy
- No false positives on control sites
- Version detection works for major frameworks
- Confidence scores are calibrated

### Task 4.5: Implement extract_structured_data() Tool (1.5h)
**Agent**: Backend Specialist
**Complexity**: Standard

**Subtasks**:
- [ ] Implement `extract_structured_data(url, crawl_id)` tool
- [ ] Parse JSON-LD structured data
- [ ] Extract Microdata (Schema.org)
- [ ] Parse Open Graph tags
- [ ] Extract Twitter Card metadata
- [ ] Return `StructuredData` schema

**Acceptance Criteria**:
- Parses all common structured data formats
- Handles multiple JSON-LD scripts
- Extracts Schema.org types correctly
- Returns well-structured output

### Task 4.6: Implement SEO Analysis Tool (2h)
**Agent**: Backend Specialist
**Complexity**: Complex

**Subtasks**:
- [ ] Implement `analyze_seo(url, crawl_id)` tool
- [ ] Check title tag (length 50-60 chars, uniqueness)
- [ ] Analyze meta description (length 150-160 chars)
- [ ] Validate heading structure (single h1, hierarchy)
- [ ] Check canonical URLs
- [ ] Analyze robots meta tags
- [ ] Check hreflang attributes
- [ ] Identify common issues
- [ ] Provide actionable recommendations
- [ ] Return `SeoAnalysis` schema

**Acceptance Criteria**:
- Identifies real SEO issues accurately
- Recommendations are actionable
- No false positives
- Scoring is reasonable

### Task 4.7: Implement Language Detection (0.5h)
**Agent**: Backend Specialist
**Complexity**: Simple

**Subtasks**:
- [ ] Install `langdetect` library
- [ ] Implement `detect_language(url, crawl_id)` tool
- [ ] Check HTML lang attribute first
- [ ] Use langdetect on body text as fallback
- [ ] Return language code and confidence
- [ ] Return `LanguageInfo` schema

**Acceptance Criteria**:
- HTML lang attribute is preferred source
- Fallback detection is accurate
- Returns ISO 639-1 codes
- Confidence scoring works

### Task 4.8: Register Tools with MCP Server (0.5h)
**Agent**: Backend Specialist
**Complexity**: Simple

**Subtasks**:
- [ ] Import parsing tools in `src/server.py`
- [ ] Register all 6 tools with `@mcp.tool()` decorators
- [ ] Add proper type hints and docstrings
- [ ] Test tools load without errors

### Task 4.9: Integration Testing (1.5h)
**Agent**: QA Specialist
**Complexity**: Standard

**Subtasks**:
- [ ] Create `tests/integration/test_parsing.py`
- [ ] Test parse_html on real HTML samples
- [ ] Test extract_links with various link types
- [ ] Test analyze_technologies on known sites
- [ ] Test extract_structured_data with JSON-LD samples
- [ ] Test analyze_seo on good/bad examples
- [ ] Test detect_language on multilingual content
- [ ] Achieve >70% coverage

**Acceptance Criteria**:
- All integration tests pass
- Real-world HTML is handled correctly
- Edge cases are covered
- Coverage >70%

## Acceptance Criteria

### Functional
- [ ] All 6 parsing tools are implemented and working
- [ ] Technology detection identifies 20+ technologies accurately
- [ ] SEO analysis provides actionable insights
- [ ] Language detection is reliable
- [ ] Structured data extraction handles all common formats
- [ ] Link extraction classifies internal/external correctly

### Technical
- [ ] Code follows project patterns (async, caching, error handling)
- [ ] All tools return proper Pydantic models
- [ ] Caching is implemented with appropriate TTLs
- [ ] Error messages are clear and actionable
- [ ] Type hints are complete

### Testing
- [ ] Unit tests cover all utilities
- [ ] Integration tests use real HTML samples
- [ ] Test coverage >70% (target 85%)
- [ ] All tests pass
- [ ] Edge cases are handled

### Documentation
- [ ] All tools have comprehensive docstrings
- [ ] Examples included in docstrings
- [ ] Technical notes documented for complex logic
- [ ] Handoff document created for Phase 5

## Dependencies

**Depends On:**
- Phase 1: Core Infrastructure (WARC parser, schemas)
- Phase 3: Fetching Tools (provides HTML content)

**Blocks:**
- Phase 5: Aggregation & Statistics (uses parsing utilities)
- Phase 6: Export & Integration (needs structured data)
- Phase 8: MCP Prompts (guides parsing workflows)

**Parallel Work:**
Can work in parallel with other Wave 3 tasks if they exist.

## Technical Notes

### Technology Stack
- **HTML Parsing**: BeautifulSoup4 + lxml parser
- **Language Detection**: langdetect library
- **Structured Data**: JSON-LD, Microdata, Open Graph parsers
- **SEO Analysis**: Custom heuristics based on best practices

### Patterns to Use
- **Caching Strategy**: 24h TTL for parsed content (HTML doesn't change)
- **Error Handling**: Graceful degradation (return partial results if possible)
- **Performance**: Use lxml parser (faster than html.parser)
- **Validation**: Pydantic models for all outputs

### Known Challenges
1. **Malformed HTML**: Common Crawl contains broken HTML
   - **Solution**: Use lxml's lenient parsing

2. **Encoding Issues**: Various character encodings
   - **Solution**: Auto-detect with chardet if needed

3. **Large Pages**: Some pages are >10MB
   - **Solution**: Set parsing size limits, truncate if needed

4. **JavaScript-rendered Content**: Not in HTML source
   - **Limitation**: Can only analyze static HTML (document in tool descriptions)

### Security Considerations
- Sanitize all HTML before processing
- Be cautious with user-controlled URLs
- Validate structured data before parsing
- Set recursion limits for nested structures

## Handoff Document (for Phase 5)

After completing this phase, create `handoffs/phase-4-to-5.md` with:

1. **Parsing Utilities Available**:
   - List all utility functions in `utils/html_parser.py`
   - Usage examples for each

2. **Technology Detection Patterns**:
   - JSON structure of detection database
   - How to add new technologies

3. **Data Models**:
   - `ParsedHtml` schema fields
   - `LinkAnalysis` schema fields
   - `TechStack` schema fields
   - `SeoAnalysis` schema fields
   - `StructuredData` schema fields
   - `LanguageInfo` schema fields

4. **Performance Notes**:
   - Average parsing time for typical pages
   - Memory usage patterns
   - Caching effectiveness

5. **Known Limitations**:
   - What parsing cannot handle
   - Edge cases to be aware of

## Resources

- [BeautifulSoup Documentation](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- [Schema.org Documentation](https://schema.org/)
- [Open Graph Protocol](https://ogp.me/)
- [SEO Best Practices](https://developers.google.com/search/docs)
- [langdetect Library](https://pypi.org/project/langdetect/)

## Success Metrics

- [ ] 6 parsing tools implemented and registered
- [ ] Technology detection >90% accuracy on test set
- [ ] SEO analysis catches real issues
- [ ] Language detection >95% accuracy
- [ ] Integration tests all passing
- [ ] Code coverage >70%
- [ ] Zero critical bugs
- [ ] Documentation complete
- [ ] Handoff document created
