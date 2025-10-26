# Ultra Development Marathon - Strategic Plan
**Project:** Common Crawl MCP Server - Phases 6-10
**Created:** 2025-10-25
**Estimated Time:** 15-21 hours (core) or 20-28 hours (with optional Phase 9)

## Executive Summary

This strategic plan outlines the completion of the Common Crawl MCP Server project through a 5-wave parallel execution architecture. Phases 6-10 will add export capabilities, MCP resources, MCP prompts, advanced features (optional), and comprehensive testing/documentation.

**Current Status:**
- Project: 56% complete (48h of 86h done)
- Phases Complete: 1-5 (Infrastructure, Discovery, Fetching, Parsing, Aggregation)
- MCP Tools Implemented: 27
- Test Coverage: 44%

**Remaining Work:**
- Phase 6: Export & Integration Tools (5 tools)
- Phase 7: MCP Resources (3 providers)
- Phase 8: MCP Prompts (4 workflows)
- Phase 9: Advanced Features (4 tools - OPTIONAL)
- Phase 10: Testing & Documentation

## Reference Class Forecasting

Based on actual performance from Phases 4-5:

**Phase 4 Actual:**
- Components: 2 utility modules + 6 MCP tools + tests
- Lines of code: ~1,487 lines
- Velocity: ~186-248 LOC/hour

**Phase 5 Actual:**
- Components: 5 aggregation tools
- Lines of code: ~905 lines
- Velocity: ~129-181 LOC/hour

**Average Velocity: 157-215 LOC/hour**

**Revised Estimates:**
- Phase 6: 4-6 hours (600-800 lines)
- Phase 7: 2-3 hours (300-400 lines)
- Phase 8: 1-2 hours (200-300 lines)
- Phase 9: 5-7 hours (800-1000 lines) - OPTIONAL
- Phase 10: 8-10 hours (1500-2200 lines)

## 5-Wave Parallel Architecture

### Wave 1: Export Tools (Phase 6) - 5 Parallel Agents

**Agent 1: export_to_csv**
- Create `src/tools/export.py` module
- Implement streaming CSV writer using `csv.DictWriter`
- Support multiple model types (ParsedHtml, TechStack, SeoAnalysis, etc.)
- Add progress callback support
- Estimated: 120-150 lines

**Agent 2: export_to_jsonl**
- Implement streaming JSONL writer using jsonlines library
- Use `model.model_dump()` for serialization
- Handle large datasets with chunking
- Estimated: 100-120 lines

**Agent 3: create_dataset**
- Implement SQLite-based dataset storage in `src/data/`
- Schema: `datasets` table with metadata, `results` table with JSON blobs
- Support saving results from any tool
- Enable resumable queries
- Estimated: 200-250 lines

**Agent 4: generate_report**
- Create Markdown/HTML report generator
- Support multiple report types (domain analysis, tech stack, SEO audit)
- Use Jinja2 templates for formatting
- Include charts/visualizations (optional: matplotlib/plotly)
- Estimated: 150-200 lines

**Agent 5: export_warc_subset**
- Implement WARC file creator (warc library)
- Filter URLs from CDX results
- Download WARC records and write to new file
- Optional: Upload to MinIO if configured
- Estimated: 150-180 lines

**Total Wave 1: 720-900 lines, 4-6 hours**

### Wave 2a: MCP Resources (Phase 7) - 3 Parallel Agents

**Agent 6: crawl_info_resource**
- Implement resource provider for crawl metadata
- URI: `commoncrawl://crawl/{crawl_id}`
- Return: crawl dates, URL counts, data locations
- Estimated: 80-100 lines

**Agent 7: saved_datasets_resource**
- Implement resource provider for datasets list
- URI: `commoncrawl://datasets` or `commoncrawl://dataset/{id}`
- Return: dataset metadata, query info, result counts
- Estimated: 100-120 lines

**Agent 8: investigation_state_resource**
- Implement resource provider for investigation sessions
- URI: `commoncrawl://investigation/{session_id}`
- Return: queries run, results cached, analysis performed
- Estimated: 120-150 lines

**Total Wave 2a: 300-370 lines, 2-3 hours**

### Wave 2b: MCP Prompts (Phase 8) - 4 Parallel Agents

**Agent 9: domain_research_prompt**
- Create comprehensive domain analysis workflow
- Orchestrates: search_index → domain_technology_report → domain_link_graph → header_analysis
- Include concrete examples with actual domains
- Estimated: 50-75 lines

**Agent 10: competitive_analysis_prompt**
- Create competitor comparison workflow
- Orchestrates: domain_technology_report for multiple domains → comparison matrix
- Estimated: 50-75 lines

**Agent 11: content_discovery_prompt**
- Create content mining workflow
- Orchestrates: search_index → parse_html → extract_structured_data → keyword_frequency
- Estimated: 50-75 lines

**Agent 12: seo_analysis_prompt**
- Create SEO audit workflow
- Orchestrates: analyze_seo → header_analysis → domain_link_graph → generate_report
- Estimated: 50-75 lines

**Total Wave 2b: 200-300 lines, 1-2 hours**

### Wave 3: Advanced Features (Phase 9 - OPTIONAL) - 3+1 Agents

**Agent 13: content_classification**
- Compose existing tools: analyze_seo + detect_language + extract_structured_data
- Classify pages as: blog, product, documentation, news, landing_page, etc.
- Use heuristics: URL patterns, heading structure, meta tags
- Estimated: 200-250 lines

**Agent 14: spam_detection**
- Compose: header_analysis + analyze_technologies + parse_html
- Detect spam signals: missing security headers, suspicious redirects, keyword stuffing
- Return spam score 0-100 with confidence level
- Estimated: 200-250 lines

**Agent 15: trend_analysis**
- Enhance domain_evolution_timeline with trend detection
- Identify: technology adoption curves, content volume changes, domain growth
- Statistical analysis: moving averages, rate of change
- Estimated: 200-250 lines

**Agent 16: dataset_management** (depends on Wave 1 completion)
- CRUD operations for saved datasets
- Use create_dataset + export_to_csv/jsonl from Wave 1
- Enable merging, filtering, deduplication of datasets
- Estimated: 200-250 lines

**Total Wave 3: 800-1000 lines, 5-7 hours**

### Wave 4: Integration Testing (Phase 10 Part A) - Sequential

**Agent 17: integration_tests_export**
- Test all 5 export tools with real data
- Verify CSV/JSONL format correctness
- Test large dataset handling (1000+ records)
- Validate WARC file creation
- Estimated: 200-250 lines, 2-3 hours

**Agent 18: integration_tests_resources**
- Test resource URIs resolve correctly
- Validate JSON schema compliance
- Test resource updates with state changes
- Estimated: 100-150 lines, 1-2 hours

**Agent 19: integration_tests_prompts**
- Test each prompt workflow end-to-end
- Verify tool orchestration works
- Validate example outputs
- Estimated: 100-150 lines, 1-2 hours

**Agent 20: performance_benchmarks**
- Benchmark export performance (throughput, memory)
- Benchmark concurrent aggregation (10+ domains)
- Profile cache hit rates
- Generate performance report
- Estimated: 150-200 lines, 2-3 hours

**Total Wave 4: 550-750 lines, 6-10 hours**

### Wave 5: Documentation (Phase 10 Part B) - Parallel + Sequential

**Agent 21: api_documentation** (can start early)
- Update OpenAPI spec with new tools
- Document all export formats
- Document resource URIs
- Document prompt workflows
- Estimated: 300-400 lines, 2-3 hours

**Agent 22: user_guides** (can start early)
- Write "Getting Started" guide
- Write "Common Use Cases" guide
- Write "Export Data" guide
- Write "Using Resources" guide
- Estimated: 400-600 lines, 2-3 hours

**Agent 23: tutorials** (depends on all features)
- Tutorial 1: Domain Research Workflow
- Tutorial 2: Competitive Analysis
- Tutorial 3: Content Mining at Scale
- Tutorial 4: Building Custom Datasets
- Estimated: 500-700 lines, 3-4 hours

**Agent 24: architecture_update** (can start early)
- Update architecture.md with export layer
- Document resource provider architecture
- Document prompt system design
- Add deployment guide updates
- Estimated: 200-300 lines, 1-2 hours

**Total Wave 5: 1400-2000 lines, 8-12 hours**

## Technical Decisions & Hypotheses

### Hypothesis 1: Export Tools Should Use Streaming
**Evidence:** Aggregation tools already process 100+ pages concurrently; large datasets could exceed memory limits.

**Decision:** Implement streaming exports with optional in-memory buffering for small datasets.

**Implementation:**
- Use `csv.DictWriter` with file handles
- Use `jsonlines` library for line-by-line writing
- Process data in chunks of 1000 records

### Hypothesis 2: MCP Resources Should Mirror Tool Output Structure
**Evidence:** All tools return Pydantic models with `.model_dump()`.

**Decision:** Resource URIs follow pattern: `commoncrawl://resource-type/identifier`

**URI Scheme:**
- `commoncrawl://crawl/CC-MAIN-2024-10` → crawl metadata
- `commoncrawl://dataset/my-dataset` → saved dataset info
- `commoncrawl://investigation/session-123` → investigation state

### Hypothesis 3: MCP Prompts Should Be Task-Oriented Workflows
**Evidence:** We have discovery → fetching → parsing → aggregation pipeline.

**Decision:** Each prompt orchestrates multiple tools in a logical workflow.

**Example Prompt Structure:**
```
Name: Domain Research
Description: Comprehensive domain analysis
Workflow:
1. list_crawls() → get latest crawl
2. search_index(domain) → find pages
3. domain_technology_report() → tech stack
4. domain_link_graph() → site structure
5. header_analysis() → security posture
```

### Hypothesis 4: Advanced Features Should Leverage Existing Tools
**Evidence:** content_classification can use analyze_seo + detect_language + extract_structured_data.

**Decision:** Phase 9 tools primarily compose existing tools rather than implementing new logic.

**Implications:** Phase 9 may be simpler than estimated - composition over creation.

## Risk Assessment & Mitigation

### Risk 1: Export Tool Memory Issues with Large Datasets
**Probability:** Medium
**Impact:** High (could crash server)

**Mitigation:**
- Implement streaming for all exports
- Add chunk size limits (1000 records at a time)
- Add memory monitoring and graceful degradation
- Test with large sample_size parameters (1000+ pages)

### Risk 2: MCP Resource Schema Compatibility
**Probability:** Low
**Impact:** Medium (resources might not work with MCP clients)

**Mitigation:**
- Follow FastMCP resource documentation exactly
- Use URI scheme that's clearly namespaced
- Validate resource JSON schemas match MCP spec
- Test resources with actual MCP client (Claude Desktop)

### Risk 3: MCP Prompts Don't Provide Value
**Probability:** Medium
**Impact:** Low (prompts are nice-to-have, not critical)

**Mitigation:**
- Base prompts on real use cases
- Include concrete examples with actual domains
- Test prompts interactively to verify they guide users
- Make prompts discoverable (clear names, descriptions)

### Risk 4: Phase 9 Advanced Features Scope Creep
**Probability:** High
**Impact:** Medium (could delay completion)

**Mitigation:**
- Mark Phase 9 as explicitly OPTIONAL
- Use composition approach (leverage existing tools)
- Implement simplest viable version of each feature
- Skip Phase 9 entirely if time runs short

### Risk 5: Testing Phase Takes Longer Than Expected
**Probability:** Medium
**Impact:** High (untested code is unreliable)

**Mitigation:**
- Write tests incrementally as tools are developed
- Focus on integration tests over unit tests
- Use parametrized tests to cover multiple scenarios
- Prioritize testing export tools (highest risk)

### Risk 6: Documentation Incomplete
**Probability:** Low
**Impact:** Medium (affects usability)

**Mitigation:**
- Start documentation early (architecture updates, API docs)
- Use docstrings that auto-generate API docs
- Create working examples alongside each tool
- Reserve final 2-3 hours for documentation polish

## Execution Timeline

### Hours 0-12: Waves 1 + 2 Launch Simultaneously
**12 agents working in parallel:**
- Wave 1: 5 export tools (Agents 1-5)
- Wave 2a: 3 resources (Agents 6-8)
- Wave 2b: 4 prompts (Agents 9-12)

**Expected Completion:** 60% of remaining work

**Parallel Documentation:**
- Agent 21: Start API documentation
- Agent 24: Start architecture updates

### Hour 12: Go/No-Go Decision Point 1
**Assessment Criteria:**
- If >90% complete → Continue with Wave 3+4
- If 70-90% complete → Skip Wave 3, proceed to Wave 4
- If <70% complete → Debug blocking issues, adjust plan

### Hours 12-19: Wave 3 (Optional) + Wave 4 Testing Begins
**If proceeding with Wave 3:**
- Agents 13-15: Start immediately (3 parallel)
- Agent 16: Start after Wave 1 completes

**Wave 4 Testing (incremental):**
- Agent 17: integration_tests_export (after Wave 1)
- Agent 18: integration_tests_resources (after Wave 2a)
- Agent 19: integration_tests_prompts (after Wave 2b)

### Hour 18: Go/No-Go Decision Point 2
**Assessment Criteria:**
- If Phases 6-8 complete → Proceed with Phase 9+10
- If Phases 6-7 complete → Skip Phase 9, focus on testing/docs
- If Phase 6 only → Complete minimal testing, document what exists

### Hours 19-28: Wave 5 Documentation + Final Testing
**Documentation (parallel):**
- Agent 22: User guides (can start after Wave 2)
- Agent 23: Tutorials (requires all features complete)

**Final Testing:**
- Agent 20: Performance benchmarks (all tools complete)
- Integration test debugging and fixes

## Success Criteria

### Phase 6 Complete ✓
- [ ] All 5 export tools implemented
- [ ] CSV/JSONL exports produce valid output
- [ ] create_dataset stores data in SQLite
- [ ] generate_report produces readable Markdown
- [ ] export_warc_subset creates valid WARC files

### Phase 7 Complete ✓
- [ ] All 3 resource providers registered
- [ ] Resources accessible via URI scheme
- [ ] Resource JSON validates against MCP spec
- [ ] Resources tested in MCP client

### Phase 8 Complete ✓
- [ ] All 4 prompts registered
- [ ] Prompts guide users through workflows
- [ ] Prompts include working examples
- [ ] Prompts tested interactively

### Phase 9 Complete ✓ (OPTIONAL)
- [ ] content_classification achieves >80% accuracy
- [ ] spam_detection identifies known spam patterns
- [ ] trend_analysis detects technology adoption
- [ ] dataset_management CRUD operations work

### Phase 10 Complete ✓
- [ ] Integration tests achieve >80% coverage for new code
- [ ] All integration tests pass
- [ ] Performance benchmarks document baseline metrics
- [ ] API documentation complete with examples
- [ ] User guides cover all major use cases
- [ ] At least 3 end-to-end tutorials published
- [ ] Architecture documentation updated

## Dependencies & Parallelization

### No Dependencies (Can Start Immediately):
- Wave 1: All 5 export tools (Agents 1-5)
- Wave 2a: All 3 resources (Agents 6-8)
- Wave 2b: All 4 prompts (Agents 9-12)
- Wave 3: Agents 13-15 (content_classification, spam_detection, trend_analysis)
- Wave 5: Agents 21, 24 (API docs, architecture)

### Sequential Dependencies:
- Agent 16 (dataset_management) → Depends on Wave 1 export tools
- Agent 17 (integration_tests_export) → Depends on Wave 1
- Agent 18 (integration_tests_resources) → Depends on Wave 2a
- Agent 19 (integration_tests_prompts) → Depends on Wave 2b
- Agent 20 (performance_benchmarks) → Depends on all tools
- Agent 22 (user_guides) → Depends on Wave 2
- Agent 23 (tutorials) → Depends on all features

### Optimal Parallelization:
- **Launch immediately:** Waves 1 + 2 (12 agents)
- **Launch after Wave 1:** Agent 16, Agent 17
- **Launch after Wave 2:** Agent 18, Agent 19, Agent 22
- **Launch after all features:** Agent 20, Agent 23

## Resource Requirements

### Development Resources:
- 24 autonomous agents (general-purpose task agents)
- Shared codebase access (git coordination)
- Shared infrastructure (Redis, SQLite)

### Infrastructure Resources:
- Redis cache for distributed coordination
- SQLite database for dataset storage
- Common Crawl CDX API (HTTP endpoint)
- S3/HTTP access for WARC files (fallback to HTTP)

### Testing Resources:
- Real Common Crawl data (example.com, test domains)
- MCP client for resource/prompt testing
- Performance profiling tools

## Conclusion

This strategic plan enables completion of the Common Crawl MCP Server through highly parallelized execution. By launching 12 agents simultaneously for Waves 1+2, we can achieve 60% of remaining work in the first 12 hours. Phase 9 is explicitly optional, allowing us to prioritize core functionality (export, resources, prompts) and quality (testing, documentation).

**Key Success Factors:**
1. Parallel execution of independent components
2. Incremental testing as features complete
3. Early documentation to avoid last-minute rush
4. Clear go/no-go decision points
5. Optional Phase 9 provides buffer for schedule slippage

**Ready to proceed to Marathon Phase 2: Wave Decomposition**
