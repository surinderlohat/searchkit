# Copyright (c) 2026 Surinder Singh (https://github.com/surinderlohat)
# Licensed under the MIT License. See LICENSE file in the project root.
from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.logger import get_logger

logger = get_logger(__name__)

DB_PATH = os.getenv("SEARCHKIT_DB", "/app/data/searchkit.db")


@contextmanager
def get_db():
    """Thread-safe SQLite connection context manager."""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # allow concurrent reads
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── Schema ─────────────────────────────────────────────────

def init_db() -> None:
    """Create tables if they don't exist. Safe to call on every startup."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id          TEXT PRIMARY KEY,
                username    TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role        TEXT NOT NULL DEFAULT 'readonly',  -- admin | readwrite | readonly
                created_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS api_keys (
                id          TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                key_hash    TEXT UNIQUE NOT NULL,
                key_preview TEXT NOT NULL,
                created_by  TEXT NOT NULL,
                created_at  TEXT NOT NULL
            );
        """)
    logger.info("Database initialised.")


# ── Helpers ────────────────────────────────────────────────

def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uid() -> str:
    return secrets.token_hex(8)


# ── Users ──────────────────────────────────────────────────

@dataclass
class User:
    id: str
    username: str
    role: str
    created_at: str


def create_user(username: str, password: str, role: str = "readonly") -> User:
    uid = _uid()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO users (id, username, password_hash, role, created_at) VALUES (?,?,?,?,?)",
            (uid, username.lower().strip(), _hash(password), role, _now()),
        )
    logger.info(f"User '{username}' created with role '{role}'")
    return User(id=uid, username=username, role=role, created_at=_now())


def get_user_by_credentials(username: str, password: str) -> User | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username=? AND password_hash=?",
            (username.lower().strip(), _hash(password)),
        ).fetchone()
    if row:
        return User(id=row["id"], username=row["username"], role=row["role"], created_at=row["created_at"])
    return None


def get_user_by_id(user_id: str) -> User | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if row:
        return User(id=row["id"], username=row["username"], role=row["role"], created_at=row["created_at"])
    return None


def list_users() -> list[User]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM users ORDER BY created_at").fetchall()
    return [User(id=r["id"], username=r["username"], role=r["role"], created_at=r["created_at"]) for r in rows]


def update_user_role(user_id: str, role: str) -> bool:
    with get_db() as conn:
        cur = conn.execute("UPDATE users SET role=? WHERE id=? AND role != 'admin'", (role, user_id))
    return cur.rowcount > 0


def delete_user(user_id: str) -> bool:
    with get_db() as conn:
        cur = conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    return cur.rowcount > 0


def user_exists(username: str) -> bool:
    with get_db() as conn:
        row = conn.execute("SELECT 1 FROM users WHERE username=?", (username.lower().strip(),)).fetchone()
    return row is not None


# ── API Keys ───────────────────────────────────────────────

@dataclass
class ApiKey:
    id: str
    name: str
    key_preview: str   # first 8 chars + "..." — never store full key
    created_by: str
    created_at: str


def create_api_key(name: str, created_by: str) -> tuple[ApiKey, str]:
    """
    Returns (ApiKey, raw_key). The raw_key is shown ONCE — never retrievable again.
    """
    raw_key    = "sk-" + secrets.token_hex(24)  # e.g. sk-a1b2c3...
    key_preview = raw_key[:10] + "..."
    uid        = _uid()

    with get_db() as conn:
        conn.execute(
            "INSERT INTO api_keys (id, name, key_hash, key_preview, created_by, created_at) VALUES (?,?,?,?,?,?)",
            (uid, name, _hash(raw_key), key_preview, created_by, _now()),
        )
    logger.info(f"API key '{name}' created by '{created_by}'")
    return ApiKey(id=uid, name=name, key_preview=key_preview, created_by=created_by, created_at=_now()), raw_key


def verify_api_key(raw_key: str) -> bool:
    """Check if a raw API key is valid."""
    with get_db() as conn:
        row = conn.execute("SELECT 1 FROM api_keys WHERE key_hash=?", (_hash(raw_key),)).fetchone()
    return row is not None


def list_api_keys() -> list[ApiKey]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM api_keys ORDER BY created_at DESC").fetchall()
    return [ApiKey(id=r["id"], name=r["name"], key_preview=r["key_preview"], created_by=r["created_by"], created_at=r["created_at"]) for r in rows]


def delete_api_key(key_id: str) -> bool:
    with get_db() as conn:
        cur = conn.execute("DELETE FROM api_keys WHERE id=?", (key_id,))
    return cur.rowcount > 0


# ── Bootstrap ──────────────────────────────────────────────

def bootstrap_admin() -> None:
    """
    Create the first admin user from env vars if no users exist yet.
    ADMIN_USER and ADMIN_PASSWORD must be set.
    """
    admin_user = os.getenv("ADMIN_USER", "").strip()
    admin_pass = os.getenv("ADMIN_PASSWORD", "").strip()

    if not admin_user or not admin_pass:
        logger.warning("ADMIN_USER / ADMIN_PASSWORD not set — skipping bootstrap.")
        return

    if user_exists(admin_user):
        logger.debug(f"Bootstrap skipped — user '{admin_user}' already exists.")
        return

    create_user(admin_user, admin_pass, role="admin")
    logger.info(f"Bootstrap: admin user '{admin_user}' created.")
