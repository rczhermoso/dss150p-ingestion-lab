"""Append-only run log (Task 3.5)."""

from __future__ import annotations

import csv
from pathlib import Path

from .common import LOGS_DIR

LOG_PATH = LOGS_DIR / "pipeline_runs.csv"

# Column order matches templates/pipeline_run_log_template.csv (verify!).
HEADER = [
    "run_id",
    "started_at",
    "ended_at",
    "status",
    "source",
    "records_read",
    "records_written",
    "duplicates_removed",
    "watermark_before",
    "watermark_after",
    "error_message",
]


def append_run_log_row(row: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_header = not LOG_PATH.exists()
    with LOG_PATH.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=HEADER)
        if write_header:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in HEADER})