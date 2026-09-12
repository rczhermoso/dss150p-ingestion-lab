"""Shared helpers for the ingestion pipeline."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "raw"
STATE_DIR = REPO_ROOT / "state"
LOGS_DIR = REPO_ROOT / "outputs" / "logs"


def utcnow_iso() -> str:
    """UTC timestamp in ISO-8601 with a Z suffix."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def new_run_id() -> str:
    return uuid.uuid4().hex[:12]


def sha256_file(path: Path, chunk_size: int = 1 << 20) -> str:
    """Compute the SHA-256 of a file without loading it all into memory."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Write bytes to `path` atomically: temp file then replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def atomic_write_json(path: Path, obj) -> None:
    data = json.dumps(obj, indent=2, sort_keys=True).encode("utf-8")
    atomic_write_bytes(path, data)


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))