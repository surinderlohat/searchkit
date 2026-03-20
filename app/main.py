# Copyright (c) 2026 Surinder Singh (https://github.com/surinderlohat)
# Licensed under the MIT License. See LICENSE file in the project root.
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import get_collection
from app.logger import get_logger
from app.routers import collections, documents, health, search

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing embedded ChromaDB...")
    get_collection()
    logger.info("ChromaDB ready (embedded mode).")
    yield
    logger.info("Shutting down ChromaDB wrapper service.")


app = FastAPI(
    title="SearchKit",
    description="Plug-in semantic search for any stack — one container, zero config, production ready.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["Health"])
app.include_router(collections.router, prefix="/collections", tags=["Collections"])
app.include_router(documents.router, prefix="/documents", tags=["Documents"])
app.include_router(search.router, prefix="/search", tags=["Search"])
