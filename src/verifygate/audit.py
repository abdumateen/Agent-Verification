"""SQLite-backed, hash-linked audit events.

The chain detects changes to retained rows; without an external checkpoint it
cannot detect deletion of a suffix (including deletion of the entire database).
"""

import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path


def _canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path, timeout=30)
    connection.execute("""CREATE TABLE IF NOT EXISTS events (
        seq INTEGER PRIMARY KEY,
        run_id TEXT,
        event TEXT NOT NULL,
        prev_hash TEXT,
        hash TEXT NOT NULL
    )""")
    return connection


def _records(connection: sqlite3.Connection) -> list[dict]:
    rows = connection.execute("SELECT seq, run_id, event, prev_hash, hash FROM events ORDER BY seq").fetchall()
    previous = None
    records = []
    for expected, (seq, run_id, payload, prev_hash, digest) in enumerate(rows, 1):
        event = json.loads(payload)
        if not isinstance(event, dict) or _canonical(event).decode("utf-8") != payload:
            raise ValueError("invalid event serialization")
        if seq != expected or prev_hash != previous or run_id != event.get("run_id"):
            raise ValueError("invalid event sequence")
        record = {"seq": seq, "event": event, "prev_hash": prev_hash}
        if not isinstance(digest, str) or hashlib.sha256(_canonical(record)).hexdigest() != digest:
            raise ValueError("invalid event hash")
        record["hash"] = digest
        records.append(record)
        previous = digest
    return records


def append_event(path: Path, event: dict) -> dict:
    if not isinstance(event, dict):
        raise ValueError("event must be an object")
    payload = _canonical(event).decode("utf-8")
    run_id = event.get("run_id")
    if run_id is not None and not isinstance(run_id, str):
        raise ValueError("run_id must be a string")
    with closing(_connect(path)) as connection:
        with connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                records = _records(connection)
            except (ValueError, TypeError, sqlite3.Error) as exc:
                raise ValueError("existing ledger is invalid") from exc
            record = {"seq": len(records) + 1, "event": json.loads(payload),
                      "prev_hash": records[-1]["hash"] if records else None}
            record["hash"] = hashlib.sha256(_canonical(record)).hexdigest()
            connection.execute("INSERT INTO events(seq, run_id, event, prev_hash, hash) VALUES (?, ?, ?, ?, ?)",
                               (record["seq"], run_id, payload, record["prev_hash"], record["hash"]))
    return record


def verify_ledger(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        with closing(sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)) as connection:
            _records(connection)
        return True
    except (OSError, ValueError, TypeError, sqlite3.Error):
        return False


def list_events(path: Path, run_id: str | None = None, limit: int = 100) -> list[dict]:
    """Return the latest verified events, newest first."""
    if not isinstance(limit, int) or limit < 0:
        raise ValueError("limit must be a nonnegative integer")
    if run_id is not None and not isinstance(run_id, str):
        raise ValueError("run_id must be a string")
    if not path.exists():
        return []
    with closing(sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)) as connection:
        records = _records(connection)
    return [record for record in reversed(records) if run_id is None or record["event"].get("run_id") == run_id][:limit]
