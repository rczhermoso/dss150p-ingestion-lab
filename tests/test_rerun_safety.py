"""Rerun-safety checks. Assumes `python src/run_ingest.py all` was run once."""

from pathlib import Path
import json


def test_api_raw_has_no_duplicate_event_ids():
    raw = Path("raw/api/events.jsonl").read_text(encoding="utf-8").splitlines()
    ids = [json.loads(line)["event_id"] for line in raw if line.strip()]
    assert len(ids) == len(set(ids)), "duplicate event_id in raw output"


def test_file_manifest_has_no_duplicate_hashes_per_source():
    manifest = json.loads(Path("raw/files/manifest.json").read_text())
    seen = set()
    for e in manifest["entries"]:
        key = (e["source"], e["sha256"])
        assert key not in seen, f"duplicate manifest entry: {key}"
        seen.add(key)


def test_watermark_present():
    wm = json.loads(Path("state/api_watermark.json").read_text())
    assert wm["watermark"]