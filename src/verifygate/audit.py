"""Append-only JSONL audit records linked by SHA-256 digests."""

import hashlib
import json
from pathlib import Path


def _canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def append_event(path: Path, event: dict) -> dict:
    if not isinstance(event, dict):
        raise ValueError("event must be an object")
    if path.exists() and not verify_ledger(path):
        raise ValueError("existing ledger is invalid")
    previous = None
    if path.exists() and path.stat().st_size:
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                previous = json.loads(line)["hash"]
    record = {"event": event, "prev_hash": previous}
    record["hash"] = hashlib.sha256(_canonical(record)).hexdigest()
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(_canonical(record).decode("utf-8") + "\n")
    return record


def verify_ledger(path: Path) -> bool:
    try:
        previous = None
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                record = json.loads(line)
                if not isinstance(record, dict) or set(record) != {"event", "prev_hash", "hash"}:
                    return False
                digest = record["hash"]
                if record["prev_hash"] != previous or not isinstance(record["event"], dict) or not isinstance(digest, str):
                    return False
                if hashlib.sha256(_canonical({"event": record["event"], "prev_hash": previous})).hexdigest() != digest:
                    return False
                previous = digest
        return True
    except (OSError, ValueError, TypeError, KeyError):
        return False
