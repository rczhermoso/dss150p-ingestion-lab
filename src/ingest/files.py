"""File ingestion (Task 3.1)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .common import (
    RAW_DIR,
    atomic_write_json,
    sha256_file,
    utcnow_iso,
)

FILES_RAW = RAW_DIR / "files"
MANIFEST = FILES_RAW / "manifest.json"

SOURCES = [
    ("customers", Path("data/customers.csv")),
    ("orders", Path("data/orders.json")),
    ("products", Path("data/products.parquet")),
]


@dataclass
class FileIngestResult:
    source: str
    path: str
    sha256: str
    size: int
    written: bool
    skipped_reason: str | None = None


def _load_manifest() -> dict:
    if not MANIFEST.exists():
        return {"version": 1, "entries": []}
    import json

    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _save_manifest(manifest: dict) -> None:
    atomic_write_json(MANIFEST, manifest)


def ingest_file(source: str, path: Path, run_id: str) -> FileIngestResult:
    """Copy one file into raw/files/<source>/ only if its hash is new."""
    if not path.exists():
        raise FileNotFoundError(f"source file not found: {path}")

    digest = sha256_file(path)
    size = path.stat().st_size
    manifest = _load_manifest()

    already = any(
        e["source"] == source and e["sha256"] == digest
        for e in manifest["entries"]
    )
    if already:
        return FileIngestResult(
            source=source, path=str(path), sha256=digest, size=size,
            written=False, skipped_reason="hash already ingested",
        )

    dest_dir = FILES_RAW / source / f"ingest_date={utcnow_iso()[:10]}" / f"run_id={run_id}"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / path.name

    # Copy bytes exactly.
    dest.write_bytes(path.read_bytes())

    manifest["entries"].append({
        "source": source,
        "original_path": str(path),
        "raw_path": str(dest.relative_to(FILES_RAW)),
        "sha256": digest,
        "size": size,
        "ingested_at": utcnow_iso(),
        "run_id": run_id,
    })
    _save_manifest(manifest)

    return FileIngestResult(
        source=source, path=str(path), sha256=digest, size=size, written=True,
    )


def ingest_all_files(run_id: str) -> list[FileIngestResult]:
    return [ingest_file(name, path, run_id) for name, path in SOURCES]