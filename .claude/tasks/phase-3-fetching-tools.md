# Phase 3: Data Fetching & Extraction Tools

**Epic**: Retrieve actual page content from archives
**Estimated Duration**: 5-7 hours
**Dependencies**: Phase 1, Phase 2
**Agent**: Backend Specialist
**Wave**: 2

## Tasks

### Task 3.1: Implement fetch_page_content() Tool
**Duration**: 2 hours | **Priority**: High

**Acceptance Criteria**:
- [ ] Queries CDX for URL location
- [ ] Downloads WARC from S3
- [ ] Parses HTTP response
- [ ] Extracts HTML and metadata
- [ ] Returns PageContent model
- [ ] Caching works correctly

**Files**: `src/tools/fetching.py`

### Task 3.2: Implement batch_fetch_pages() Tool
**Duration**: 2 hours | **Priority**: High

**Acceptance Criteria**:
- [ ] Fetches multiple pages efficiently
- [ ] Parallel downloads with rate limiting
- [ ] Progress reporting
- [ ] Memory-efficient

**Files**: `src/tools/fetching.py`

### Task 3.3: Implement fetch_warc_records() Tool
**Duration**: 1.5 hours | **Priority**: Medium

**Acceptance Criteria**:
- [ ] Returns raw WARC records
- [ ] Batch processing
- [ ] Proper error handling

**Files**: `src/tools/fetching.py`

### Task 3.4: Implement fetch_wat_metadata() & fetch_wet_text() Tools
**Duration**: 1.5 hours | **Priority**: Low

**Files**: `src/tools/fetching.py`

### Task 3.5: Integration Testing
**Duration**: 1 hour | **Priority**: Medium

**Files**: `tests/integration/test_fetching.py`

**Total**: 5 tasks, 8 hours
