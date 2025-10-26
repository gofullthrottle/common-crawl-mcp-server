#!/usr/bin/env python3
"""Quick test for crawl_info resource providers.

This script tests the crawl_info resource providers to ensure they work correctly.
"""

import asyncio
import json
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


async def test_resources():
    """Test crawl_info resource providers."""
    print("Testing crawl_info resource providers...")
    print("=" * 60)

    # Import the resource functions
    from resources.crawl_info import get_crawl_info, list_all_crawls

    # Test 1: List all crawls
    print("\n1. Testing list_all_crawls()...")
    try:
        result = await list_all_crawls("commoncrawl://crawls")
        data = json.loads(result)
        print(f"   ✓ Total crawls: {data.get('total_crawls', 0)}")
        print(f"   ✓ Latest crawl: {data.get('latest_crawl', 'N/A')}")
        if "error" in data:
            print(f"   ✗ Error: {data['error']}")
        else:
            print(f"   ✓ Successfully retrieved {len(data.get('crawls', []))} crawls")
    except Exception as e:
        print(f"   ✗ Exception: {e}")
        import traceback

        traceback.print_exc()

    # Test 2: Get specific crawl info (using latest or a known crawl)
    print("\n2. Testing get_crawl_info()...")
    try:
        # Try to get info for a recent crawl
        test_crawl_id = "CC-MAIN-2024-10"
        result = await get_crawl_info(f"commoncrawl://crawl/{test_crawl_id}")
        data = json.loads(result)

        if "error" in data:
            print(f"   ⚠ Crawl {test_crawl_id} not found, trying another...")
            # Try latest crawl from list
            list_result = await list_all_crawls("commoncrawl://crawls")
            list_data = json.loads(list_result)
            if list_data.get("crawls"):
                test_crawl_id = list_data["crawls"][0]["id"]
                print(f"   → Using latest crawl: {test_crawl_id}")
                result = await get_crawl_info(f"commoncrawl://crawl/{test_crawl_id}")
                data = json.loads(result)

        if "error" not in data:
            print(f"   ✓ Crawl ID: {data.get('crawl_id', 'N/A')}")
            print(f"   ✓ Name: {data.get('name', 'N/A')}")
            print(f"   ✓ CDX API: {data.get('cdx_api', 'N/A')}")
            print(f"   ✓ Total Size: {data.get('total_size_gb', 0)} GB")
            print(f"   ✓ WARC Files: {data.get('warc_files', 0)}")
            print("   ✓ Successfully retrieved crawl info")
        else:
            print(f"   ✗ Error: {data['error']}")
    except Exception as e:
        print(f"   ✗ Exception: {e}")
        import traceback

        traceback.print_exc()

    # Test 3: Test error handling with invalid crawl ID
    print("\n3. Testing error handling...")
    try:
        result = await get_crawl_info("commoncrawl://crawl/INVALID-CRAWL-ID")
        data = json.loads(result)
        if "error" in data:
            print(f"   ✓ Error handling works: {data['error']}")
            print(f"   ✓ Suggested crawls: {data.get('available_crawls', [])[:3]}")
        else:
            print("   ✗ Expected error for invalid crawl ID")
    except Exception as e:
        print(f"   ✗ Exception: {e}")

    print("\n" + "=" * 60)
    print("Tests completed!")


if __name__ == "__main__":
    asyncio.run(test_resources())
