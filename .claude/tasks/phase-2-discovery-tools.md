# Phase 2: Discovery & Metadata Tools

**Epic**: Enable exploration of Common Crawl datasets
**Estimated Duration**: 4-6 hours
**Dependencies**: Phase 1 (Core Infrastructure)
**Agent**: Backend Specialist
**Wave**: 2

## Tasks

### Task 2.1: Implement list_crawls() Tool
**Duration**: 1 hour | **Priority**: High

**Acceptance Criteria**:
- [ ] Returns all available crawls from CDX
- [ ] Includes metadata (date, status, size)
- [ ] Cached with 24h TTL
- [ ] MCP tool properly registered
- [ ] Error handling for CDX failures

**Files**: `src/tools/discovery.py`

### Task 2.2: Implement get_crawl_stats() Tool
**Duration**: 1.5 hours | **Priority**: High

**Acceptance Criteria**:
- [ ] Fetches collinfo.json from S3
- [ ] Parses statistics correctly
- [ ] Caches results aggressively
- [ ] Returns CrawlStats model

**Files**: `src/tools/discovery.py`

### Task 2.3: Implement search_index() Tool
**Duration**: 1 hour | **Priority**: High

**Acceptance Criteria**:
- [ ] Queries CDX with various match types
- [ ] Supports wildcards and patterns
- [ ] Pagination working
- [ ] Returns IndexRecord list

**Files**: `src/tools/discovery.py`

### Task 2.4: Implement get_domain_stats() Tool
**Duration**: 1.5 hours | **Priority**: Medium

**Acceptance Criteria**:
- [ ] Counts pages for domain
- [ ] Calculates total size
- [ ] Identifies subdomains
- [ ] Returns DomainStats model

**Files**: `src/tools/discovery.py`

### Task 2.5: Implement compare_crawls() Tool
**Duration**: 1 hour | **Priority**: Low

**Acceptance Criteria**:
- [ ] Compares domain across multiple crawls
- [ ] Shows trends (growing/shrinking)
- [ ] Returns ComparisonResult

**Files**: `src/tools/discovery.py`

### Task 2.6: Register Tools with MCP Server
**Duration**: 30 min | **Priority**: High

**Files**: `src/server.py`

**Total**: 5 tasks, 6.5 hours
