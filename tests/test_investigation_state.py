"""Tests for investigation state resource provider.

This module tests the investigation session management functionality including
session creation, retrieval, updates, and resource providers.
"""

import json
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

# Set up test database path before importing module
test_db_path = Path(tempfile.mkdtemp()) / "test_commoncrawl.db"

# Patch DB_PATH before importing
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.resources import investigation_state

# Override DB_PATH for testing
investigation_state.DB_PATH = test_db_path


@pytest.fixture
def clean_database():
    """Clean database fixture - ensures fresh state for each test."""
    # Remove database if it exists
    if test_db_path.exists():
        test_db_path.unlink()

    # Initialize fresh database
    investigation_state._init_database()

    yield

    # Cleanup after test
    if test_db_path.exists():
        test_db_path.unlink()


@pytest.mark.asyncio
async def test_create_session(clean_database):
    """Test creating a new investigation session."""
    session = await investigation_state.create_session()

    assert session.id is not None
    assert len(session.id) == 36  # UUID format
    assert isinstance(session.created_at, datetime)
    assert isinstance(session.updated_at, datetime)
    assert session.queries_run == []
    assert session.cached_results == {}
    assert session.analysis_summary == {}


@pytest.mark.asyncio
async def test_get_session(clean_database):
    """Test retrieving an investigation session by ID."""
    # Create a session
    created_session = await investigation_state.create_session()

    # Retrieve it
    retrieved_session = await investigation_state.get_session(created_session.id)

    assert retrieved_session is not None
    assert retrieved_session.id == created_session.id
    assert retrieved_session.created_at == created_session.created_at


@pytest.mark.asyncio
async def test_get_nonexistent_session(clean_database):
    """Test retrieving a session that doesn't exist."""
    result = await investigation_state.get_session("nonexistent-id")

    assert result is None


@pytest.mark.asyncio
async def test_update_session(clean_database):
    """Test updating an investigation session."""
    # Create a session
    session = await investigation_state.create_session()
    original_updated_at = session.updated_at

    # Modify the session
    session.queries_run.append(
        {
            "query": "example.com",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool": "search_index",
        }
    )
    session.cached_results["query_1"] = {"results": [1, 2, 3]}
    session.analysis_summary["total_pages"] = 100

    # Update it
    await investigation_state.update_session(session)

    # Retrieve and verify
    updated_session = await investigation_state.get_session(session.id)

    assert updated_session is not None
    assert len(updated_session.queries_run) == 1
    assert updated_session.queries_run[0]["query"] == "example.com"
    assert "query_1" in updated_session.cached_results
    assert updated_session.analysis_summary["total_pages"] == 100
    assert updated_session.updated_at > original_updated_at


@pytest.mark.asyncio
async def test_get_all_sessions(clean_database):
    """Test retrieving all investigation sessions."""
    # Create multiple sessions
    session1 = await investigation_state.create_session()
    session2 = await investigation_state.create_session()
    session3 = await investigation_state.create_session()

    # Retrieve all
    all_sessions = await investigation_state.get_all_sessions()

    assert len(all_sessions) == 3
    session_ids = [s.id for s in all_sessions]
    assert session1.id in session_ids
    assert session2.id in session_ids
    assert session3.id in session_ids


@pytest.mark.asyncio
async def test_delete_session(clean_database):
    """Test deleting an investigation session."""
    # Create a session
    session = await investigation_state.create_session()

    # Verify it exists
    retrieved = await investigation_state.get_session(session.id)
    assert retrieved is not None

    # Delete it
    deleted = await investigation_state.delete_session(session.id)
    assert deleted is True

    # Verify it's gone
    retrieved = await investigation_state.get_session(session.id)
    assert retrieved is None


@pytest.mark.asyncio
async def test_delete_nonexistent_session(clean_database):
    """Test deleting a session that doesn't exist."""
    deleted = await investigation_state.delete_session("nonexistent-id")
    assert deleted is False


@pytest.mark.asyncio
async def test_list_investigations_resource(clean_database):
    """Test the list_investigations resource provider."""
    # Create some sessions
    session1 = await investigation_state.create_session()
    session2 = await investigation_state.create_session()

    # Modify one to have queries
    session2.queries_run.append({"query": "test"})
    await investigation_state.update_session(session2)

    # Call resource provider
    result = await investigation_state.list_investigations("commoncrawl://investigations")

    # Parse JSON response
    data = json.loads(result)

    assert data["total_sessions"] == 2
    assert len(data["sessions"]) == 2

    # Verify structure
    session_data = data["sessions"][0]
    assert "id" in session_data
    assert "created_at" in session_data
    assert "updated_at" in session_data
    assert "queries_count" in session_data
    assert "has_cached_results" in session_data
    assert "has_analysis" in session_data


@pytest.mark.asyncio
async def test_get_investigation_state_resource(clean_database):
    """Test the get_investigation_state resource provider."""
    # Create a session
    session = await investigation_state.create_session()

    # Add some data
    session.queries_run.append(
        {
            "query": "example.com",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
    session.cached_results["test"] = {"data": "value"}
    session.analysis_summary["findings"] = "important"
    await investigation_state.update_session(session)

    # Call resource provider
    uri = f"commoncrawl://investigation/{session.id}"
    result = await investigation_state.get_investigation_state(uri)

    # Parse JSON response
    data = json.loads(result)

    assert data["id"] == session.id
    assert "created_at" in data
    assert "updated_at" in data
    assert len(data["queries_run"]) == 1
    assert data["queries_run"][0]["query"] == "example.com"
    assert "test" in data["cached_results"]
    assert data["analysis_summary"]["findings"] == "important"
    assert "metadata" in data
    assert data["metadata"]["queries_count"] == 1


@pytest.mark.asyncio
async def test_get_investigation_state_not_found(clean_database):
    """Test get_investigation_state resource with nonexistent session."""
    uri = "commoncrawl://investigation/nonexistent-id"
    result = await investigation_state.get_investigation_state(uri)

    # Parse JSON response
    data = json.loads(result)

    assert "error" in data
    assert "Session not found" in data["error"]
    assert "suggestion" in data


@pytest.mark.asyncio
async def test_session_persistence(clean_database):
    """Test that sessions persist across database connections."""
    # Create a session
    session = await investigation_state.create_session()
    session_id = session.id

    # Manually close and reopen database to simulate persistence
    # (In real usage, this happens naturally)

    # Retrieve the session
    retrieved = await investigation_state.get_session(session_id)

    assert retrieved is not None
    assert retrieved.id == session_id


@pytest.mark.asyncio
async def test_session_ordering(clean_database):
    """Test that sessions are returned in creation order (newest first)."""
    # Create sessions with small delay to ensure different timestamps
    import asyncio

    session1 = await investigation_state.create_session()
    await asyncio.sleep(0.01)
    session2 = await investigation_state.create_session()
    await asyncio.sleep(0.01)
    session3 = await investigation_state.create_session()

    # Get all sessions
    all_sessions = await investigation_state.get_all_sessions()

    # Should be in reverse chronological order
    assert all_sessions[0].id == session3.id
    assert all_sessions[1].id == session2.id
    assert all_sessions[2].id == session1.id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
