# Phase 1: Core Infrastructure

**Epic**: Build foundational components for Common Crawl interaction
**Estimated Duration**: 8-12 hours
**Dependencies**: Phase 0 (Complete)
**Agent**: Backend Specialist
**Wave**: 1

---

## Tasks

### Task 1.1: Complete CDX Client Implementation
**Duration**: 2 hours
**Priority**: High
**Status**: Partial (Basic client exists)

**Description**:
Enhance the existing CDX client with full error handling, retries, and comprehensive testing.

**Acceptance Criteria**:
- [ ] Exponential backoff implemented for failed requests
- [ ] Retry logic with configurable max attempts
- [ ] Comprehensive error messages
- [ ] Unit tests for all public methods
- [ ] Integration test with real CDX server
- [ ] Pagination working correctly for large result sets

**Technical Notes**:
- Use `tenacity` library for retry logic
- Add circuit breaker pattern for repeated failures
- Mock CDX responses in tests

**Files to Modify**:
- `src/core/cc_client.py` - Add retry logic
- `tests/test_core/test_cc_client.py` - Create test suite

---

### Task 1.2: Implement S3 Manager
**Duration**: 3 hours
**Priority**: High
**Status**: Not Started

**Description**:
Create S3Manager class for downloading WARC/WAT/WET files from Common Crawl's S3 bucket.

**Acceptance Criteria**:
- [ ] Can download individual WARC files by filename
- [ ] Streaming download for large files (no full memory load)
- [ ] Anonymous access working (no AWS credentials needed)
- [ ] Progress callbacks for large downloads
- [ ] Automatic gzip decompression
- [ ] Rate limiting for S3 requests
- [ ] Cost tracking (bytes downloaded)
- [ ] Unit tests with mocked S3 responses

**Technical Notes**:
- Bucket: `s3://commoncrawl/` (public, us-east-1)
- Use boto3 with anonymous credentials
- Implement streaming with `client.get_object()` and `StreamingBody`
- Track egress for cost estimation

**Files to Create**:
- `src/core/s3_manager.py` - S3Manager class
- `tests/test_core/test_s3_manager.py` - Test suite

---

### Task 1.3: Implement WARC Parser
**Duration**: 2-3 hours
**Priority**: High
**Status**: Not Started

**Description**:
Create WarcParser class for extracting HTTP responses and content from WARC files.

**Acceptance Criteria**:
- [ ] Can parse WARC file from bytes or stream
- [ ] Extract HTTP headers correctly
- [ ] Extract HTML/text payload
- [ ] Handle different record types (response, request, metadata)
- [ ] Memory-efficient iteration over records
- [ ] Handle malformed records gracefully
- [ ] Unit tests with sample WARC data

**Technical Notes**:
- Use `warcio` library
- WARC format: https://iipc.github.io/warc-specifications/
- Handle both gzipped and uncompressed
- Implement as iterator for memory efficiency

**Files to Create**:
- `src/core/warc_parser.py` - WarcParser class
- `tests/fixtures/sample.warc.gz` - Test data
- `tests/test_core/test_warc_parser.py` - Test suite

---

### Task 1.4: Implement Multi-Tier Caching Layer
**Duration**: 3-4 hours
**Priority**: Medium
**Status**: Not Started

**Description**:
Create comprehensive caching system with memory, disk, and optional Redis support.

**Acceptance Criteria**:
- [ ] Memory cache (LRU) for hot data
- [ ] Disk cache with size limits and eviction
- [ ] Cache key generation from URLs/queries
- [ ] TTL-based expiration
- [ ] Cache statistics (hit rate, size, etc.)
- [ ] Optional Redis backend support
- [ ] Thread-safe operations
- [ ] Unit tests for all cache tiers

**Technical Notes**:
- Use `functools.lru_cache` for memory tier
- Implement custom disk cache with SQLite metadata
- Cache structure: `{cache_dir}/{hash[:2]}/{hash[2:4]}/{hash}.cache`
- Store metadata (URL, timestamp, size) in SQLite
- Redis key format: `cc:{hash}`

**Files to Create**:
- `src/core/cache.py` - CacheManager class
- `tests/test_core/test_cache.py` - Test suite

---

### Task 1.5: Integration Testing of Core Components
**Duration**: 1-2 hours
**Priority**: Medium
**Status**: Not Started

**Description**:
Create end-to-end integration tests for the complete fetch workflow.

**Acceptance Criteria**:
- [ ] Test: CDX query → S3 download → WARC parse
- [ ] Test: Cache hit prevents S3 download
- [ ] Test: Cache miss triggers download
- [ ] Test: Error handling throughout pipeline
- [ ] Test: Rate limiting works correctly
- [ ] Documentation of test scenarios

**Technical Notes**:
- Use pytest fixtures for setup/teardown
- Mock S3 for most tests, one real integration test
- Test with small WARC sample (~1MB)

**Files to Create**:
- `tests/integration/test_fetch_pipeline.py`
- `tests/integration/conftest.py` - Shared fixtures

---

### Task 1.6: Update Server with Core Tools
**Duration**: 1 hour
**Priority**: Low
**Status**: Not Started

**Description**:
Wire up core infrastructure to FastMCP server with basic diagnostic tools.

**Acceptance Criteria**:
- [ ] Add `test_cdx_connection()` tool
- [ ] Add `test_s3_connection()` tool
- [ ] Add `cache_stats()` tool
- [ ] Add `clear_cache()` tool
- [ ] Update `health_check()` with real status
- [ ] Documentation in server.py

**Files to Modify**:
- `src/server.py` - Add diagnostic tools

---

## Summary

**Total Tasks**: 6
**Total Estimated Hours**: 12-15 hours
**Complexity**: High
**Blockers**: None (Phase 0 complete)
**Deliverables**:
- Fully functional CDX client
- S3 download capability
- WARC parsing
- Multi-tier caching
- Integration tests
- Diagnostic tools in MCP server
