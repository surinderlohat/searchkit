# Copyright (c) 2026 Surinder Singh (https://github.com/surinderlohat)
# Licensed under the MIT License. See LICENSE file in the project root.
from __future__ import annotations

import asyncio
import csv
import io
import json
import os

from fastapi import APIRouter, BackgroundTasks, Cookie, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader

from app.db import get_collection, list_collections, safe_upsert
from app.jobs import JobStatus, create_job, get_job, list_jobs
from app.log_buffer import get_logs
from app.logger import get_logger
from app.memory import MEMORY_LIMIT_MB, MEMORY_WARN_MB, get_memory_mb
from app.store import (
    ApiKey,
    User,
    create_api_key,
    create_user,
    delete_api_key,
    delete_user,
    get_user_by_credentials,
    get_user_by_id,
    list_api_keys,
    list_users,
    update_user_role,
    user_exists,
)

logger = get_logger(__name__)
router = APIRouter()

SESSION_TOKEN = "sk_session"

_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "../templates")
templates = Jinja2Templates(env=Environment(
    loader=FileSystemLoader(_TEMPLATES_DIR),
    autoescape=True,
))


# ── Session auth ───────────────────────────────────────────

def get_session_user(
    session: str | None = Cookie(default=None, alias=SESSION_TOKEN),
) -> User:
    """Verify session cookie — returns User or redirects to login."""
    if not session:
        raise HTTPException(status_code=302, headers={"Location": "/admin/login"})
    user = get_user_by_id(session)
    if not user:
        raise HTTPException(status_code=302, headers={"Location": "/admin/login"})
    return user


def require_admin(user: User = Depends(get_session_user)) -> User:
    """Only allow admin role."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return user


# ── Login / Logout ─────────────────────────────────────────

@router.get("/login", include_in_schema=False)
async def login_page(request: Request):
    return templates.TemplateResponse("admin_login.html", {"request": request})


@router.post("/login", include_in_schema=False)
async def login(request: Request):
    form     = await request.form()
    username = form.get("username", "").strip()
    password = form.get("password", "")
    user     = get_user_by_credentials(username, password)
    if user:
        response = RedirectResponse(url="/admin", status_code=302)
        response.set_cookie(SESSION_TOKEN, user.id, httponly=True, samesite="strict")
        logger.info(f"Admin login: '{username}' ({user.role})")
        return response
    logger.warning(f"Admin login failed for '{username}'")
    return templates.TemplateResponse(
        "admin_login.html",
        {"request": request, "error": "Invalid username or password"},
        status_code=401,
    )


@router.get("/logout", include_in_schema=False)
async def logout():
    response = RedirectResponse(url="/admin/login", status_code=302)
    response.delete_cookie(SESSION_TOKEN)
    return response


# ── Dashboard ──────────────────────────────────────────────

@router.get("", include_in_schema=False)
async def dashboard(request: Request, user: User = Depends(get_session_user)):
    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request,
        "user": user,
    })


# ── Stats ──────────────────────────────────────────────────

@router.get("/api/stats", include_in_schema=False)
async def stats(user: User = Depends(get_session_user)):
    names = list_collections()
    collections = [
        {"name": name, "count": get_collection(name).count()}
        for name in names
    ]
    return {
        "collections":     collections,
        "memory_mb":       round(get_memory_mb(), 1),
        "memory_warn_mb":  MEMORY_WARN_MB,
        "memory_limit_mb": MEMORY_LIMIT_MB,
    }


# ── Document browse ────────────────────────────────────────

@router.get("/api/documents/browse", include_in_schema=False)
async def browse_documents(
    collection: str = "default",
    limit: int = 50,
    user: User = Depends(get_session_user),
):
    col     = get_collection(collection)
    results = col.get(limit=limit, include=["documents", "metadatas"])
    return {
        "documents": [
            {
                "id":       results["ids"][i],
                "text":     results["documents"][i],
                "metadata": results["metadatas"][i] or {} if results["metadatas"] else {},
            }
            for i in range(len(results["ids"]))
        ],
        "total": col.count(),
    }


# ── Users ──────────────────────────────────────────────────

@router.get("/api/users", include_in_schema=False)
async def get_users(user: User = Depends(require_admin)):
    return {"users": [
        {"id": u.id, "username": u.username, "role": u.role, "created_at": u.created_at}
        for u in list_users()
    ]}


@router.post("/api/users", include_in_schema=False)
async def add_user(request: Request, user: User = Depends(require_admin)):
    body     = await request.json()
    username = body.get("username", "").strip()
    password = body.get("password", "").strip()
    role     = body.get("role", "readonly")

    if not username or not password:
        raise HTTPException(status_code=422, detail="Username and password are required")
    if role not in ("readwrite", "readonly"):
        raise HTTPException(status_code=422, detail="Role must be 'readwrite' or 'readonly'. Admin role cannot be assigned.")
    if user_exists(username):
        raise HTTPException(status_code=409, detail=f"User '{username}' already exists")

    new_user = create_user(username, password, role)
    logger.info(f"Admin '{user.username}' created user '{username}' ({role})")
    return {"id": new_user.id, "username": new_user.username, "role": new_user.role}


@router.patch("/api/users/{user_id}", include_in_schema=False)
async def change_user_role(user_id: str, request: Request, user: User = Depends(require_admin)):
    body = await request.json()
    role = body.get("role", "").strip()
    if role not in ("readwrite", "readonly"):
        raise HTTPException(status_code=422, detail="Role must be 'readwrite' or 'readonly'")
    target = get_user_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.role == "admin":
        raise HTTPException(status_code=400, detail="Admin role cannot be changed")
    if not update_user_role(user_id, role):
        raise HTTPException(status_code=400, detail="Role update failed")
    logger.info(f"Admin '{user.username}' changed user '{target.username}' role to '{role}'")
    return {"status": "ok", "username": target.username, "role": role}


@router.delete("/api/users/{user_id}", include_in_schema=False)
async def remove_user(user_id: str, user: User = Depends(require_admin)):
    if user_id == user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    target = get_user_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.role == "admin":
        raise HTTPException(status_code=400, detail="The admin account cannot be deleted")
    if not delete_user(user_id):
        raise HTTPException(status_code=404, detail="User not found")
    logger.warning(f"Admin '{user.username}' deleted user '{user_id}'")
    return {"status": "ok"}


# ── API Keys ───────────────────────────────────────────────

@router.get("/api/keys", include_in_schema=False)
async def get_keys(user: User = Depends(require_admin)):
    return {"keys": [
        {"id": k.id, "name": k.name, "preview": k.key_preview, "created_by": k.created_by, "created_at": k.created_at}
        for k in list_api_keys()
    ]}


@router.post("/api/keys", include_in_schema=False)
async def add_key(request: Request, user: User = Depends(require_admin)):
    body = await request.json()
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="Key name is required")
    api_key, raw_key = create_api_key(name, created_by=user.username)
    logger.info(f"Admin '{user.username}' created API key '{name}'")
    # raw_key shown ONCE — client must copy it now
    return {
        "id":      api_key.id,
        "name":    api_key.name,
        "key":     raw_key,   # only time full key is returned
        "preview": api_key.key_preview,
    }


@router.delete("/api/keys/{key_id}", include_in_schema=False)
async def remove_key(key_id: str, user: User = Depends(require_admin)):
    if not delete_api_key(key_id):
        raise HTTPException(status_code=404, detail="Key not found")
    logger.warning(f"Admin '{user.username}' revoked key '{key_id}'")
    return {"status": "ok"}


# ── CSV Import ─────────────────────────────────────────────

@router.post("/api/csv/preview", include_in_schema=False)
async def csv_preview(request: Request, user: User = Depends(get_session_user)):
    form    = await request.form()
    file    = form.get("file")
    content = await file.read()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1")
    reader  = csv.DictReader(io.StringIO(text))
    columns = reader.fieldnames or []
    rows    = [dict(row) for i, row in enumerate(reader) if i < 5]
    return {"columns": list(columns), "preview": rows}


@router.post("/api/csv/import", include_in_schema=False)
async def csv_import(
    request: Request,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_session_user),
):
    form        = await request.form()
    file        = form.get("file")
    collection  = form.get("collection", "default")
    id_field    = form.get("id_field", "")
    text_fields = [f.strip() for f in form.get("text_fields", "").split(",") if f.strip()]
    text_sep    = form.get("text_separator", " ")
    batch_size  = int(form.get("batch_size", "200"))
    start_from  = int(form.get("start_from", "0"))   # resume offset — skip first N rows

    if not id_field:
        raise HTTPException(status_code=422, detail="id_field is required")
    if not text_fields:
        raise HTTPException(status_code=422, detail="text_fields is required")

    raw = await file.read()
    try:
        text_content = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text_content = raw.decode("latin-1")

    job = create_job(f"CSV import → {collection}")
    background_tasks.add_task(
        _run_csv_import,
        job_id=job.id,
        text_content=text_content,
        collection=collection,
        id_field=id_field,
        text_fields=text_fields,
        text_sep=text_sep,
        batch_size=batch_size,
        start_from=start_from,
    )
    logger.info(f"CSV import job {job.id} queued for '{collection}' by '{user.username}'")
    return {"job_id": job.id, "status": job.status}


async def _run_csv_import(
    job_id: str,
    text_content: str,
    collection: str,
    id_field: str,
    text_fields: list[str],
    text_sep: str,
    batch_size: int,
    start_from: int = 0,
) -> None:
    from datetime import datetime, timezone
    job = get_job(job_id)
    if not job:
        return
    job.status = JobStatus.RUNNING
    try:
        all_rows  = list(csv.DictReader(io.StringIO(text_content)))
        rows      = all_rows[start_from:]   # skip already-imported rows
        job.total = len(all_rows)           # total reflects full file
        job.imported = start_from           # count skipped rows as already done
        col       = get_collection(collection)

        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            ids, texts, metas = [], [], []
            for row in batch:
                doc_id = str(row.get(id_field, "")).strip()
                text   = text_sep.join(
                    str(row.get(f, "")).strip()
                    for f in text_fields if row.get(f, "").strip()
                )
                if not doc_id or not text:
                    job.skipped += 1
                    continue
                meta = {k: str(v).strip() for k, v in row.items()
                        if k != id_field and k not in text_fields and str(v).strip()}
                ids.append(doc_id)
                texts.append(text)
                metas.append(meta if meta else None)

            if ids:
                has_meta = any(m is not None for m in metas)
                await safe_upsert(
                    col,
                    ids=ids,
                    documents=texts,
                    metadatas=metas if has_meta else None,
                )
                job.imported += len(ids)

            job.progress = round(((start_from + i + len(batch)) / job.total) * 100)
            await asyncio.sleep(0)

        job.status      = JobStatus.DONE
        job.progress    = 100
        job.finished_at = datetime.now(timezone.utc).isoformat()
        logger.info(f"Job {job_id} done — {job.imported} imported, {job.skipped} skipped")

    except Exception as e:
        job.status      = JobStatus.FAILED
        job.error       = str(e)
        job.finished_at = datetime.now(timezone.utc).isoformat()
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)


@router.get("/api/jobs", include_in_schema=False)
async def get_jobs(user: User = Depends(get_session_user)):
    return {"jobs": [j.to_dict() for j in list_jobs()]}


@router.get("/api/jobs/{job_id}", include_in_schema=False)
async def get_job_status(job_id: str, user: User = Depends(get_session_user)):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_dict()


# ── Live Logs SSE ──────────────────────────────────────────

@router.get("/api/logs/stream", include_in_schema=False)
async def logs_stream(user: User = Depends(get_session_user)):
    async def event_generator():
        last_count = 0
        while True:
            logs_asc = list(reversed(get_logs()))
            if len(logs_asc) > last_count:
                for line in logs_asc[last_count:]:
                    yield f"data: {json.dumps(line)}\n\n"
                last_count = len(logs_asc)
            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
