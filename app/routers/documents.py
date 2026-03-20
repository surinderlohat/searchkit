from fastapi import APIRouter, HTTPException
from app.db import get_collection, safe_upsert, safe_delete
from app.schemas import (
    UpsertRequest,
    SingleUpsertRequest,
    DeleteRequest,
    StatusResponse,
)

router = APIRouter()

BATCH_SIZE = 256


@router.post("/upsert", response_model=StatusResponse)
async def upsert_single(req: SingleUpsertRequest):
    """
    Insert or update a single document.

    - If the ID exists → updates it.
    - If the ID is new → inserts it.
    - Embedding is generated automatically from the `text` field.

    Example:
        {
            "collection": "default",
            "id": "doc_1",
            "text": "Hello world",
            "metadata": { "source": "wiki" }
        }
    """
    try:
        collection = get_collection(req.collection)
        await safe_upsert(
            collection,
            ids=[req.id],
            documents=[req.text],
            metadatas=[req.metadata] if req.metadata else None,
        )
        return StatusResponse(
            status="ok",
            message=f"Upserted document '{req.id}' into '{req.collection}'. Total: {collection.count()}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upsert/bulk", response_model=StatusResponse)
async def upsert_bulk(req: UpsertRequest):
    """
    Insert or update multiple documents in one call.

    - Processes in batches of 256 for memory efficiency.
    - Each document with an existing ID gets updated, new IDs get inserted.
    - Embeddings are generated automatically from each `text` field.

    Example:
        {
            "collection": "default",
            "documents": [
                { "id": "doc_1", "text": "Hello world", "metadata": { "source": "wiki" } },
                { "id": "doc_2", "text": "FastAPI is great", "metadata": { "source": "blog" } }
            ]
        }
    """
    try:
        collection = get_collection(req.collection)
        total = len(req.documents)

        for i in range(0, total, BATCH_SIZE):
            batch = req.documents[i : i + BATCH_SIZE]
            await safe_upsert(
                collection,
                ids=[doc.id for doc in batch],
                documents=[doc.text for doc in batch],
                metadatas=[doc.metadata for doc in batch],
            )

        return StatusResponse(
            status="ok",
            message=f"Upserted {total} documents into '{req.collection}'. Total: {collection.count()}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete", response_model=StatusResponse)
async def delete_documents(req: DeleteRequest):
    """
    Delete documents by their IDs.

    Example:
        {
            "collection": "default",
            "ids": ["doc_1", "doc_2"]
        }
    """
    try:
        collection = get_collection(req.collection)
        await safe_delete(collection, ids=req.ids)
        return StatusResponse(
            status="ok",
            message=f"Deleted {len(req.ids)} documents from '{req.collection}'. Remaining: {collection.count()}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
