#!/usr/bin/env python3
"""Demonstration of investigation state resource functionality.

This script demonstrates how to use the investigation session management
system to track queries, cache results, and maintain analysis context.
"""

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from resources.investigation_state import (create_session, get_all_sessions,
                                           get_investigation_state,
                                           get_session, list_investigations,
                                           update_session)


async def main():
    """Run demonstration of investigation state functionality."""
    print("=" * 80)
    print("Investigation State Resource Demo")
    print("=" * 80)
    print()

    # Step 1: Create a new investigation session
    print("Step 1: Creating a new investigation session...")
    session = await create_session()
    print(f"✓ Created session: {session.id}")
    print(f"  - Created at: {session.created_at}")
    print(f"  - Queries run: {len(session.queries_run)}")
    print()

    # Step 2: Simulate running some queries
    print("Step 2: Simulating query execution...")

    # Query 1: Search for a domain
    query1 = {
        "tool": "search_index",
        "query": "example.com",
        "crawl_id": "CC-MAIN-2024-10",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "results_count": 150,
    }
    session.queries_run.append(query1)

    # Cache results for query 1
    session.cached_results["query_1"] = {
        "urls": [
            "https://example.com",
            "https://example.com/about",
            "https://example.com/products",
        ],
        "total_found": 150,
    }

    print(f"✓ Added query: {query1['tool']} for {query1['query']}")
    print()

    # Query 2: Analyze technologies
    query2 = {
        "tool": "domain_technology_report",
        "domain": "example.com",
        "crawl_id": "CC-MAIN-2024-10",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "technologies_found": 12,
    }
    session.queries_run.append(query2)

    # Cache results for query 2
    session.cached_results["query_2"] = {
        "technologies": {
            "React": 45.2,
            "WordPress": 32.1,
            "Google Analytics": 78.5,
        },
        "total_pages_analyzed": 50,
    }

    print(f"✓ Added query: {query2['tool']} for {query2['domain']}")
    print()

    # Step 3: Add analysis summary
    print("Step 3: Adding analysis summary...")
    session.analysis_summary = {
        "domain": "example.com",
        "total_pages_found": 150,
        "pages_analyzed": 50,
        "technologies_detected": 12,
        "key_findings": [
            "React is the primary frontend framework (45.2% adoption)",
            "WordPress powers about 1/3 of the pages",
            "Google Analytics is widely deployed (78.5%)",
        ],
        "security_score": 72,
        "recommendations": [
            "Consider implementing HSTS header",
            "Improve meta description coverage",
        ],
    }
    print("✓ Analysis summary added")
    print()

    # Step 4: Update the session
    print("Step 4: Updating session in database...")
    await update_session(session)
    print("✓ Session updated")
    print()

    # Step 5: Retrieve the session
    print("Step 5: Retrieving session from database...")
    retrieved_session = await get_session(session.id)
    print(f"✓ Retrieved session: {retrieved_session.id}")
    print(f"  - Queries run: {len(retrieved_session.queries_run)}")
    print(f"  - Cached results: {len(retrieved_session.cached_results)} entries")
    print(f"  - Has analysis: {'Yes' if retrieved_session.analysis_summary else 'No'}")
    print()

    # Step 6: Create another session for demonstration
    print("Step 6: Creating second session...")
    session2 = await create_session()
    print(f"✓ Created session: {session2.id}")
    print()

    # Step 7: List all sessions using resource provider
    print("Step 7: Listing all sessions (via resource provider)...")
    sessions_json = await list_investigations("commoncrawl://investigations")
    sessions_data = json.loads(sessions_json)
    print(f"✓ Found {sessions_data['total_sessions']} sessions")
    print()

    for i, sess in enumerate(sessions_data["sessions"], 1):
        print(f"  Session {i}:")
        print(f"    - ID: {sess['id']}")
        print(f"    - Created: {sess['created_at']}")
        print(f"    - Queries: {sess['queries_count']}")
        print()

    # Step 8: Get full session state using resource provider
    print("Step 8: Getting full session state (via resource provider)...")
    uri = f"commoncrawl://investigation/{session.id}"
    state_json = await get_investigation_state(uri)
    state_data = json.loads(state_json)

    print(f"✓ Retrieved state for session: {state_data['id']}")
    print()
    print("  Queries executed:")
    for i, query in enumerate(state_data["queries_run"], 1):
        print(f"    {i}. {query['tool']} - {query.get('query', query.get('domain'))}")

    print()
    print("  Key findings:")
    for finding in state_data["analysis_summary"]["key_findings"]:
        print(f"    • {finding}")

    print()
    print("  Metadata:")
    for key, value in state_data["metadata"].items():
        if "seconds" in key:
            print(f"    - {key}: {int(value)}s")
        else:
            print(f"    - {key}: {value}")

    print()
    print("=" * 80)
    print("Demo completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
