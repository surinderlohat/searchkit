# Copyright (c) 2026 Surinder Singh (https://github.com/surinderlohat)
# Licensed under the MIT License. See LICENSE file in the project root.
from __future__ import annotations

import asyncio
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from app.logger import get_logger

logger = get_logger(__name__)


class JobStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    DONE      = "done"
    FAILED    = "failed"


@dataclass
class Job:
    id:         str
    name:       str
    status:     JobStatus = JobStatus.PENDING
    progress:   int       = 0          # 0-100
    imported:   int       = 0
    skipped:    int       = 0
    total:      int       = 0
    error:      str       = ""
    created_at: str       = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    finished_at:str       = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id":          self.id,
            "name":        self.name,
            "status":      self.status,
            "progress":    self.progress,
            "imported":    self.imported,
            "skipped":     self.skipped,
            "total":       self.total,
            "error":       self.error,
            "created_at":  self.created_at,
            "finished_at": self.finished_at,
        }


# ── In-memory job registry ─────────────────────────────────
# Keeps last 50 jobs — old ones are dropped automatically

_jobs: dict[str, Job] = {}
_MAX_JOBS = 50


def create_job(name: str) -> Job:
    job = Job(id=secrets.token_hex(6), name=name)
    _jobs[job.id] = job
    # Evict oldest jobs if over limit
    if len(_jobs) > _MAX_JOBS:
        oldest = sorted(_jobs.values(), key=lambda j: j.created_at)[0]
        del _jobs[oldest.id]
    logger.debug(f"Job created: {job.id} — {name}")
    return job


def get_job(job_id: str) -> Job | None:
    return _jobs.get(job_id)


def list_jobs() -> list[Job]:
    return sorted(_jobs.values(), key=lambda j: j.created_at, reverse=True)
