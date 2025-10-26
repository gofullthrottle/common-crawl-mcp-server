#!/usr/bin/env python3
"""Verify crawl_info resource implementation.

This script verifies that the crawl_info resource providers are correctly implemented.
"""

import os


def verify_implementation():
    """Verify the implementation against the specification."""
    print("Verifying crawl_info resource implementation...")
    print("=" * 70)

    # Check file exists
    file_path = "src/resources/crawl_info.py"
    if not os.path.exists(file_path):
        print(f"✗ File not found: {file_path}")
        return False

    print(f"✓ File exists: {file_path}")

    # Read file content
    with open(file_path, "r") as f:
        content = f.read()

    # Verify key elements
    checks = [
        ("@mcp.resource decorator", '@mcp.resource("commoncrawl://crawl/{crawl_id}")'),
        ("get_crawl_info function", "async def get_crawl_info(uri: str) -> str:"),
        ("list_all_crawls function", "async def list_all_crawls(uri: str) -> str:"),
        ("URI scheme: commoncrawl://crawl/", "commoncrawl://crawl/"),
        ("URI scheme: commoncrawl://crawls", "commoncrawl://crawls"),
        ("Import from server", "from ..server import mcp"),
        ("Import discovery tools", "from ..tools import discovery"),
        ("JSON dumps", "json.dumps("),
        ("Error handling", "except Exception"),
        ("Logger", "logger."),
    ]

    passed = 0
    failed = 0

    for check_name, check_string in checks:
        if check_string in content:
            print(f"✓ {check_name}")
            passed += 1
        else:
            print(f"✗ {check_name}")
            failed += 1

    # Check resources/__init__.py
    init_path = "src/resources/__init__.py"
    print(f"\nChecking {init_path}...")

    with open(init_path, "r") as f:
        init_content = f.read()

    init_checks = [
        ("Import get_crawl_info", "get_crawl_info"),
        ("Import list_all_crawls", "list_all_crawls"),
        ("Export get_crawl_info", '"get_crawl_info"'),
        ("Export list_all_crawls", '"list_all_crawls"'),
    ]

    for check_name, check_string in init_checks:
        if check_string in init_content:
            print(f"✓ {check_name}")
            passed += 1
        else:
            print(f"✗ {check_name}")
            failed += 1

    # Check server.py imports
    server_path = "src/server.py"
    print(f"\nChecking {server_path}...")

    with open(server_path, "r") as f:
        server_content = f.read()

    server_checks = [
        ("Import get_crawl_info", "get_crawl_info"),
        ("Import list_all_crawls", "list_all_crawls"),
    ]

    for check_name, check_string in server_checks:
        if check_string in server_content:
            print(f"✓ {check_name}")
            passed += 1
        else:
            print(f"✗ {check_name}")
            failed += 1

    print("\n" + "=" * 70)
    print(f"Verification Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("✓ All checks passed!")
        return True
    else:
        print("✗ Some checks failed")
        return False


if __name__ == "__main__":
    success = verify_implementation()
    exit(0 if success else 1)
