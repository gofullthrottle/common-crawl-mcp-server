"""Investigation session state resource provider.

This module implements MCP resource providers for managing investigation sessions,
allowing users to track queries, cache results, and maintain analysis context across
multiple interactions.
"""

import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

from ..server import mcp

logger = logging.getLogger(__name__)

# Database configuration
DB_PATH = Path("./data/commoncrawl.db")


class InvestigationSession(BaseModel):
    """Investigation session state.

    An investigation session maintains state across multiple queries and analyses,
    tracking executed queries, cached results, and cumulative findings.

    Attributes:
        id: Unique session identifier (UUID)
        created_at: Session creation timestamp
        updated_at: Last update timestamp
        queries_run: List of executed queries with metadata
        cached_results: Cached query results by query identifier
        analysis_summary: Accumulated analysis findings and insights
    """

    id: str = Field(..., description="Unique session identifier (UUID)")
    created_at: datetime = Field(..., description="Session creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    queries_run: list[dict[str, Any]] = Field(
        default_factory=list, description="List of executed queries with metadata"
    )
    cached_results: dict[str, Any] = Field(
        default_factory=dict, description="Cached query results by query ID"
    )
    analysis_summary: dict[str, Any] = Field(
        default_factory=dict, description="Accumulated analysis findings"
    )


# Database schema extension for investigation sessions
INVESTIGATION_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS investigation_sessions (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    state JSON NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_investigation_sessions_created_at
ON investigation_sessions(created_at DESC);
"""


def _init_database() -> None:
    """Initialize the investigation sessions database schema."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.executescript(INVESTIGATION_SCHEMA_SQL)
    conn.commit()
    conn.close()


async def create_session() -> InvestigationSession:
    """Create a new investigation session.

    Returns:
        InvestigationSession: Newly created session with unique ID

    Example:
        >>> session = await create_session()
        >>> print(f"Created session: {session.id}")
    """
    # Initialize database
    _init_database()

    # Create new session
    session = InvestigationSession(
        id=str(uuid.uuid4()),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    # Store in database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute(
            """INSERT INTO investigation_sessions (id, created_at, updated_at, state)
               VALUES (?, ?, ?, ?)""",
            (
                session.id,
                session.created_at.isoformat(),
                session.updated_at.isoformat(),
                session.model_dump_json(),
            ),
        )
        conn.commit()
        logger.info(f"Created investigation session: {session.id}")

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to create session: {e}")
        raise

    finally:
        conn.close()

    return session


async def update_session(session: InvestigationSession) -> None:
    """Update an existing investigation session.

    Args:
        session: Session object with updated state

    Raises:
        ValueError: If session does not exist

    Example:
        >>> session = await get_session(session_id)
        >>> session.queries_run.append({"query": "example.com", "timestamp": "..."})
        >>> await update_session(session)
    """
    # Initialize database
    _init_database()

    # Update timestamp
    session.updated_at = datetime.now(timezone.utc)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        result = cursor.execute(
            """UPDATE investigation_sessions
               SET updated_at = ?, state = ?
               WHERE id = ?""",
            (session.updated_at.isoformat(), session.model_dump_json(), session.id),
        )

        if result.rowcount == 0:
            raise ValueError(f"Session not found: {session.id}")

        conn.commit()
        logger.info(f"Updated investigation session: {session.id}")

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to update session {session.id}: {e}")
        raise

    finally:
        conn.close()


async def get_session(session_id: str) -> Optional[InvestigationSession]:
    """Retrieve an investigation session by ID.

    Args:
        session_id: UUID of the session to retrieve

    Returns:
        InvestigationSession if found, None otherwise

    Example:
        >>> session = await get_session("123e4567-e89b-12d3-a456-426614174000")
        >>> if session:
        ...     print(f"Session has {len(session.queries_run)} queries")
    """
    # Initialize database
    _init_database()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        row = cursor.execute(
            """SELECT id, created_at, updated_at, state
               FROM investigation_sessions
               WHERE id = ?""",
            (session_id,),
        ).fetchone()

        if not row:
            logger.warning(f"Session not found: {session_id}")
            return None

        # Parse state from JSON
        state = json.loads(row[3])

        session = InvestigationSession(
            id=row[0],
            created_at=datetime.fromisoformat(row[1]),
            updated_at=datetime.fromisoformat(row[2]),
            queries_run=state.get("queries_run", []),
            cached_results=state.get("cached_results", {}),
            analysis_summary=state.get("analysis_summary", {}),
        )

        logger.debug(f"Retrieved session: {session_id}")
        return session

    finally:
        conn.close()


async def get_all_sessions() -> list[InvestigationSession]:
    """Retrieve all investigation sessions.

    Returns:
        List of all sessions ordered by creation date (newest first)

    Example:
        >>> sessions = await get_all_sessions()
        >>> print(f"Found {len(sessions)} active sessions")
    """
    # Initialize database
    _init_database()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        rows = cursor.execute(
            """SELECT id, created_at, updated_at, state
               FROM investigation_sessions
               ORDER BY created_at DESC"""
        ).fetchall()

        sessions = []
        for row in rows:
            try:
                state = json.loads(row[3])

                session = InvestigationSession(
                    id=row[0],
                    created_at=datetime.fromisoformat(row[1]),
                    updated_at=datetime.fromisoformat(row[2]),
                    queries_run=state.get("queries_run", []),
                    cached_results=state.get("cached_results", {}),
                    analysis_summary=state.get("analysis_summary", {}),
                )
                sessions.append(session)

            except Exception as e:
                logger.error(f"Error parsing session {row[0]}: {e}")
                continue

        logger.debug(f"Retrieved {len(sessions)} investigation sessions")
        return sessions

    finally:
        conn.close()


async def delete_session(session_id: str) -> bool:
    """Delete an investigation session.

    Args:
        session_id: UUID of the session to delete

    Returns:
        True if session was deleted, False if not found

    Example:
        >>> deleted = await delete_session(session_id)
        >>> if deleted:
        ...     print("Session deleted successfully")
    """
    # Initialize database
    _init_database()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        result = cursor.execute("DELETE FROM investigation_sessions WHERE id = ?", (session_id,))

        conn.commit()
        deleted = result.rowcount > 0

        if deleted:
            logger.info(f"Deleted investigation session: {session_id}")
        else:
            logger.warning(f"Session not found for deletion: {session_id}")

        return deleted

    finally:
        conn.close()


# MCP Resource Providers
@mcp.resource("commoncrawl://investigations")
async def list_investigations() -> str:
    """List all investigation sessions.

    This resource provides an overview of all active investigation sessions,
    showing session metadata and query counts.

    Returns:
        JSON string with sessions list

    Example URI:
        commoncrawl://investigations
    """
    sessions = await get_all_sessions()

    info = {
        "total_sessions": len(sessions),
        "sessions": [
            {
                "id": session.id,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "queries_count": len(session.queries_run),
                "has_cached_results": len(session.cached_results) > 0,
                "has_analysis": len(session.analysis_summary) > 0,
            }
            for session in sessions
        ],
    }

    return json.dumps(info, indent=2)


@mcp.resource("commoncrawl://investigation/{session_id}")
async def get_investigation_state(session_id: str) -> str:
    """Get state for a specific investigation session.

    This resource provides complete session state including all executed queries,
    cached results, and accumulated analysis findings.

    Args:
        session_id: Investigation session UUID (from URI parameter)

    Returns:
        JSON string with session state or error message

    Example URI:
        commoncrawl://investigation/123e4567-e89b-12d3-a456-426614174000
    """

    session = await get_session(session_id)

    if not session:
        return json.dumps(
            {
                "error": f"Session not found: {session_id}",
                "uri": uri,
                "suggestion": "Use commoncrawl://investigations to list available sessions",
            },
            indent=2,
        )

    # Return full session state
    info = {
        "id": session.id,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
        "queries_run": session.queries_run,
        "cached_results": session.cached_results,
        "analysis_summary": session.analysis_summary,
        "metadata": {
            "queries_count": len(session.queries_run),
            "cached_results_count": len(session.cached_results),
            "session_age_seconds": (
                datetime.now(timezone.utc) - session.created_at
            ).total_seconds(),
            "last_activity_seconds": (
                datetime.now(timezone.utc) - session.updated_at
            ).total_seconds(),
        },
    }

    return json.dumps(info, indent=2)


# Export public API
__all__ = [
    "InvestigationSession",
    "create_session",
    "update_session",
    "get_session",
    "get_all_sessions",
    "delete_session",
    "list_investigations",
    "get_investigation_state",
]
