#!/usr/bin/env python3
"""Quick test to verify export_warc_subset implementation."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))


async def test_export_warc_subset():
    """Test the export_warc_subset function."""
    from src.tools.export import export_warc_subset

    # Test with a known URL from Common Crawl
    test_urls = [
        "https://example.com/",
    ]

    crawl_id = "CC-MAIN-2024-10"
    output_path = "/tmp/test_export.warc.gz"

    print(f"Testing WARC export for {len(test_urls)} URL(s)...")
    print(f"Crawl ID: {crawl_id}")
    print(f"Output: {output_path}")

    def progress(current, total):
        print(f"Progress: {current}/{total}")

    try:
        result = await export_warc_subset(
            urls=test_urls,
            crawl_id=crawl_id,
            output_path=output_path,
            progress_callback=progress,
        )

        print("\n--- Export Result ---")
        print(f"Format: {result.format}")
        print(f"Output path: {result.output_path}")
        print(f"Records exported: {result.records_exported}")
        print(f"File size: {result.file_size_bytes:,} bytes")
        print(f"Duration: {result.duration_seconds}s")

        if result.errors:
            print(f"\nErrors ({len(result.errors)}):")
            for error in result.errors:
                print(f"  - {error}")
        else:
            print("\n✓ Export completed successfully!")

        # Check if file exists
        if Path(output_path).exists():
            print(f"\n✓ Output file exists: {output_path}")
        else:
            print(f"\n✗ Output file not found: {output_path}")

    except Exception as e:
        print(f"\n✗ Export failed: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_export_warc_subset())
