# Copyright (c) 2026 Surinder Singh (https://github.com/surinderlohat)
# Licensed under the MIT License. See LICENSE file in the project root.
from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import RedirectResponse

from app.auth import check_api_key, verify_api_key
from app.db import get_collection
from app.log_buffer import attach_buffer_handler
from app.logger import get_logger
from app.routers import admin, collections, documents, health, search
from app.store import bootstrap_admin, get_user_by_id, init_db

logger = get_logger(__name__)

_API_KEY_SET = bool(os.getenv("API_KEY", ""))


@asynccontextmanager
async def lifespan(app: FastAPI):
    attach_buffer_handler()  # capture logs into in-memory buffer for admin dashboard
    init_db()                 # create SQLite tables if not exist
    bootstrap_admin()         # create first admin user from env vars if no users exist
    logger.info("Initializing embedded ChromaDB...")
    get_collection()
    logger.info("ChromaDB ready (embedded mode).")
    if _API_KEY_SET:
        logger.info("API key authentication enabled.")
    else:
        logger.warning("API key auth disabled — set API_KEY env var to enable.")
    yield
    logger.info("Shutting down SearchKit.")


app = FastAPI(
    title="SearchKit",
    description="Plug-in semantic search for any stack — one container, zero config, production ready.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request logging middleware ─────────────────────────────

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start   = time.perf_counter()
    response = await call_next(request)
    duration = (time.perf_counter() - start) * 1000

    # Skip logging for static/docs/admin UI page loads
    skip = {"/", "/docs", "/openapi.json", "/health"}
    if request.url.path not in skip and not request.url.path.startswith("/admin/api/logs"):
        logger.info(
            f"{request.method} {request.url.path} "
            f"→ {response.status_code} "
            f"[{duration:.1f}ms]"
        )

    return response


# ── Public endpoints ───────────────────────────────────────

@app.get("/", include_in_schema=False)
async def root():
    """Root — redirects to Swagger UI."""
    return RedirectResponse(url="/docs")


@app.get("/docs", include_in_schema=False)
async def swagger_ui():
    """Swagger UI — always public. API key entered via Authorize button."""
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="SearchKit",
        swagger_ui_parameters={
            "persistAuthorization": True,  # remembers key across page refreshes
        },
    )


@app.get("/openapi.json", include_in_schema=False)
async def openapi_schema():
    """
    OpenAPI schema — public so Swagger UI can load it without auth.
    Injects ApiKeyAuth security scheme so Swagger UI shows the Authorize
    button and sends X-API-Key header on every Try it out request.
    """
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Inject API key security scheme into the schema manually
    # get_openapi() does not support openapi_extra directly
    schema.setdefault("components", {}).setdefault("securitySchemes", {})["ApiKeyAuth"] = {
        "type": "apiKey",
        "in": "header",
        "name": "X-API-Key",
    }
    schema["security"] = [{"ApiKeyAuth": []}]

    return schema


# ── Combined auth — accepts admin session cookie OR X-API-Key ─────
# This allows the admin dashboard to call public endpoints using
# the session cookie without needing an API key.

from fastapi import Cookie

async def session_or_api_key(
    request: Request,
    sk_session: str | None = Cookie(default=None),
):
    # Check admin session cookie first
    if sk_session:
        user = get_user_by_id(sk_session)
        if user:
            return sk_session  # valid session — allow through

    # Fall back to API key verification
    api_key = request.headers.get("X-API-Key", "")
    return check_api_key(api_key)

_auth = Depends(session_or_api_key)

app.include_router(health.router, tags=["Health"], dependencies=[_auth])
app.include_router(collections.router, prefix="/collections", tags=["Collections"], dependencies=[_auth])
app.include_router(documents.router, prefix="/documents", tags=["Documents"], dependencies=[_auth])
app.include_router(search.router, prefix="/search", tags=["Search"], dependencies=[_auth])
app.include_router(admin.router, prefix="/admin", include_in_schema=False)
