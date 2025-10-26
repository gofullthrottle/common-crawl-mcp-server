"""MCP resource providers for saved datasets.

This module provides resource access to saved datasets through URIs.
"""

import json
import logging

from ..server import mcp

logger = logging.getLogger(__name__)


@mcp.resource("commoncrawl://datasets")
async def list_datasets() -> str:
    """List all saved datasets.

    URI format: commoncrawl://datasets

    Returns:
        JSON string with datasets list including metadata
    """
    from ..tools.export import get_all_datasets

    datasets = await get_all_datasets()

    info = {
        "total_datasets": len(datasets),
        "datasets": [
            {
                "id": ds.id,
                "name": ds.name,
                "description": ds.description,
                "records_count": ds.records_count,
                "created_at": ds.created_at.isoformat(),
                "metadata": ds.metadata,
            }
            for ds in datasets
        ],
    }

    return json.dumps(info, indent=2)


@mcp.resource("commoncrawl://dataset/{dataset_id}")
async def get_dataset_info(dataset_id: str) -> str:
    """Get metadata for a specific dataset.

    URI format: commoncrawl://dataset/{uuid}

    Args:
        dataset_id: Dataset UUID (from URI parameter)

    Returns:
        JSON string with dataset metadata
    """

    from ..tools.export import get_dataset_by_id

    dataset = await get_dataset_by_id(dataset_id)

    if not dataset:
        return json.dumps({"error": f"Dataset not found: {dataset_id}"})

    info = {
        "id": dataset.id,
        "name": dataset.name,
        "description": dataset.description,
        "records_count": dataset.records_count,
        "created_at": dataset.created_at.isoformat(),
        "metadata": dataset.metadata,
        "uri": f"commoncrawl://dataset/{dataset.id}",
        "records_uri": f"commoncrawl://dataset/{dataset.id}/records",
    }

    return json.dumps(info, indent=2)


@mcp.resource("commoncrawl://dataset/{dataset_id}/records")
async def get_dataset_records_resource(dataset_id: str) -> str:
    """Get records from a specific dataset.

    URI format: commoncrawl://dataset/{uuid}/records

    Args:
        dataset_id: Dataset UUID (from URI parameter)

    Returns:
        JSON string with dataset records (limited to first 100 for performance)
    """

    from ..tools.export import get_dataset_records

    records = await get_dataset_records(dataset_id)

    info = {
        "dataset_id": dataset_id,
        "total_records": len(records),
        "records": records[:100],  # Limit to first 100 for performance
        "truncated": len(records) > 100,
    }

    return json.dumps(info, indent=2)
