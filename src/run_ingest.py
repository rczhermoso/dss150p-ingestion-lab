"""CLI entry point: run file + API ingestion and log the result."""

from __future__ import annotations

import argparse
import sys
import traceback

from ingest.common import new_run_id, utcnow_iso
from ingest.files import ingest_all_files
from ingest.api import ingest_api
from ingest.runlog import append_run_log_row


def run(target: str) -> int:
    run_id = new_run_id()
    started = utcnow_iso()
    status = "success"
    error_message = ""
    records_read = 0
    records_written = 0
    duplicates_removed = 0
    wm_before = None
    wm_after = None

    try:
        if target in ("files", "all"):
            results = ingest_all_files(run_id)
            written = sum(1 for r in results if r.written)
            print(f"files: {written} written, {len(results) - written} skipped")
        if target in ("api", "all"):
            res = ingest_api(run_id)
            records_read = res.records_read
            records_written = res.records_written
            duplicates_removed = res.duplicates_removed
            wm_before = res.watermark_before
            wm_after = res.watermark_after
            print(
                f"api: read={records_read} written={records_written} "
                f"dups={duplicates_removed} "
                f"watermark {wm_before} -> {wm_after}"
            )
    except Exception as exc:
        status = "failure"
        error_message = str(exc)
        traceback.print_exc()

    ended = utcnow_iso()
    append_run_log_row({
        "run_id": run_id,
        "started_at": started,
        "ended_at": ended,
        "status": status,
        "source": target,
        "records_read": records_read,
        "records_written": records_written,
        "duplicates_removed": duplicates_removed,
        "watermark_before": wm_before or "",
        "watermark_after": wm_after or "",
        "error_message": error_message,
    })
    return 0 if status == "success" else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("target", choices=["files", "api", "all"])
    args = ap.parse_args()
    return run(args.target)


if __name__ == "__main__":
    sys.exit(main())