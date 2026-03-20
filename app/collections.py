# Copyright (c) 2025 Surinder Singh (https://github.com/surinderlohat)
# Licensed under the MIT License. See LICENSE file in the project root.
from fastapi import APIRouter, HTTPException
from app.db import get_collection, list_collections, delete_collection
from app.logger import get_logger
from app.schemas import CollectionListResponse, CollectionInfo, StatusResponse

logger = get_logger(__name__)
router = APIRouter()


@router.get("", response_model=CollectionListResponse)
def get_all_collections():
    """List all collections with their document counts."""
    logger.debug("Listing all collections")
    names = list_collections()
    collections = []
    for name in names:
        col = get_collection(name)
        collections.append(CollectionInfo(name=name, count=col.count()))
    logger.info(f"Found {len(collections)} collections")
    return CollectionListResponse(collections=collections, total=len(collections))


@router.get("/{name}", response_model=CollectionInfo)
def get_single_collection(name: str):
    """Get info about a specific collection."""
    logger.debug(f"Fetching info for collection '{name}'")
    try:
        col = get_collection(name)
        return CollectionInfo(name=name, count=col.count())
    except Exception as e:
        logger.error(f"Collection '{name}' not found: {e}")
        raise HTTPException(status_code=404, detail=f"Collection '{name}' not found: {e}")


@router.delete("/{name}", response_model=StatusResponse)
def drop_collection(name: str):
    """Delete an entire collection and all its documents."""
    logger.warning(f"Drop requested for collection '{name}'")
    try:
        delete_collection(name)
        logger.info(f"Collection '{name}' dropped successfully")
        return StatusResponse(status="ok", message=f"Collection '{name}' deleted.")
    except Exception as e:
        logger.error(f"Failed to drop collection '{name}': {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
