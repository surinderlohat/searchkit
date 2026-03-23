# Copyright (c) 2026 Surinder Singh (https://github.com/surinderlohat)
# Licensed under the MIT License. See LICENSE file in the project root.
from __future__ import annotations

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from app.logger import get_logger

logger = get_logger(__name__)

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def check_api_key(api_key: str) -> str:
    """
    Core key verification — accepts a raw string.
    Used both by the FastAPI dependency and the combined session_or_api_key auth.
    If no keys exist in DB yet, open access is allowed (initial setup).
    """
    from app.store import list_api_keys
    from app.store import verify_api_key as db_verify

    if not list_api_keys():
        logger.debug("No API keys configured — open access")
        return ""
    if api_key and db_verify(api_key):
        logger.debug("API key verified")
        return api_key
    logger.warning("Unauthorized — invalid or missing API key")
    raise HTTPException(
        status_code=401,
        detail="Invalid or missing API key. Pass it via the X-API-Key header.",
    )


def verify_api_key(api_key: str = Security(API_KEY_HEADER)) -> str:
    """FastAPI dependency — reads X-API-Key from request header."""
    return check_api_key(api_key)
