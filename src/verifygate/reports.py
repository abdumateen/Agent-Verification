"""Read a report only when its content matches the audited event."""

import hashlib
import json
from pathlib import Path

from verifygate import audit


def get_report(ledger: Path, run_id: str) -> dict:
    events = audit.list_events(ledger, run_id=run_id)
    completed = next((record for record in events
                      if record["event"].get("type") == "verification_completed"), None)
    if completed is None:
        raise ValueError("completed run not found")
    event = completed["event"]
    raw = Path(event["report_path"]).read_bytes()
    if len(raw) > 8 * 1024 * 1024:
        raise ValueError("report is too large")
    data = json.loads(raw)
    if not isinstance(data, dict) or data.get("run_id") != run_id or data.get("audit_hash") != completed["hash"]:
        raise ValueError("report does not match audit event")
    unsigned = {key: value for key, value in data.items() if key != "audit_hash"}
    digest = hashlib.sha256(json.dumps(unsigned, sort_keys=True, separators=(",", ":"),
                                       ensure_ascii=False).encode("utf-8")).hexdigest()
    if digest != event.get("report_sha256"):
        raise ValueError("report content differs from audited evidence")
    return data
