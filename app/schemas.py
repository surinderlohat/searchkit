# Copyright (c) 2026 Surinder Singh (https://github.com/surinderlohat)
# Licensed under the MIT License. See LICENSE file in the project root.
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

# ── Documents ──────────────────────────────────────────────


class DocumentItem(BaseModel):
    """A single document entry."""

    id: str
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class UpsertRequest(BaseModel):
    """Bulk upsert — insert or update multiple documents at once."""

    collection: str = "default"
    documents: list[DocumentItem]

    model_config = {
        "json_schema_extra": {
            "example": {
                "collection": "default",
                "documents": [
                    {"id": "doc_1", "text": "Hello world", "metadata": {"source": "wiki"}},
                    {"id": "doc_2", "text": "FastAPI is great", "metadata": {"source": "blog"}},
                ],
            }
        }
    }


class SingleUpsertRequest(BaseModel):
    """Single document upsert — insert or update one document."""

    collection: str = "default"
    id: str
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {
        "json_schema_extra": {
            "example": {
                "collection": "default",
                "id": "doc_1",
                "text": "Hello world",
                "metadata": {"source": "wiki"},
            }
        }
    }


class DeleteRequest(BaseModel):
    ids: list[str]
    collection: str = "default"

    model_config = {
        "json_schema_extra": {
            "example": {
                "collection": "default",
                "ids": ["doc_1", "doc_2"],
            }
        }
    }


class DocumentResult(BaseModel):
    id: str
    text: str  # our API field name
    metadata: dict[str, Any]
    distance: float

    @classmethod
    def from_chroma(
        cls,
        id: str,
        document: str,
        metadata: dict,
        distance: float,
    ) -> DocumentResult:
        """Factory method — maps ChromaDB's 'document' field to our 'text' field."""
        return cls(id=id, text=document, metadata=metadata, distance=distance)


# ── Search ─────────────────────────────────────────────────


class SearchRequest(BaseModel):
    query: str
    top_k: int = Field(default=10, ge=1, le=100)
    collection: str = "default"
    where: dict[str, Any] | None = Field(
        default=None,
        description='Optional metadata filter e.g. {"source": "wiki"}',
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "What is machine learning?",
                "top_k": 5,
                "collection": "default",
                "where": {"source": "wiki"},
            }
        }
    }


class SearchResponse(BaseModel):
    query: str
    results: list[DocumentResult]
    total: int


# ── Collections ────────────────────────────────────────────


class CollectionInfo(BaseModel):
    name: str
    count: int


class CollectionListResponse(BaseModel):
    collections: list[CollectionInfo]
    total: int


# ── Generic ────────────────────────────────────────────────


class StatusResponse(BaseModel):
    status: str
    message: str
