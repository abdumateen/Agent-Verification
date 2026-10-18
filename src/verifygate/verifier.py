"""Transport-independent verification orchestration.

Only the Docker runner may execute candidate checks. AST parsing here is data
inspection, not candidate execution. A run never reuses another run's evidence.
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
from uuid import uuid4

from verifygate import audit, contracts, policy, sandbox, snapshots
from verifygate.analyzers.python import analyze


def verify(candidate: Path, claim_path: Path, policy_path: Path,
           ledger: Path, report: Path) -> dict:
    candidate = candidate.resolve(strict=True)
    rules, policy_hash = policy.load_policy(policy_path, candidate)
    claim = contracts.load_claim(claim_path, rules["task_ids"])
    for output in (ledger, report):
        if candidate == output.resolve() or candidate in output.resolve().parents:
            raise ValueError("audit ledger and report must be outside the candidate")
    if ledger.resolve() == report.resolve():
        raise ValueError("ledger and report must use distinct files")
    exclusions = rules.get("exclusions", ())
    manifest = snapshots.manifest(candidate, exclusions)
    if not manifest["files"]:
        raise ValueError("candidate snapshot has no eligible files")
    missing = sorted(set(claim["changed_files"]) - set(manifest["files"]))
    if missing:
        raise ValueError(f"claimed changed files not present in snapshot: {missing}")
    run_id = uuid4().hex
    with tempfile.TemporaryDirectory(prefix="verifygate-snapshot-") as directory:
        snapshot = Path(directory) / "source"
        before = snapshots.fingerprint(candidate, exclusions)
        artifact_hash = snapshots.create_snapshot(candidate, snapshot, exclusions)
        if snapshots.fingerprint(candidate, exclusions) != before or artifact_hash != before:
            raise ValueError("candidate changed during snapshot creation; retry")
        audit.append_event(ledger, {
            "type": "verification_started", "run_id": run_id,
            "task_id": claim["task_id"], "artifact_hash": artifact_hash,
            "policy_hash": policy_hash, "claim": claim,
            "time": datetime.now(timezone.utc).isoformat(),
        })
        static = analyze(snapshot, rules.get("stub_mode", "warn"))
        results = sandbox.run_checks(snapshot, rules, snapshot_hash=artifact_hash,
                                     policy_hash=policy_hash)
        verdict = policy.decide(results, rules, artifact_hash, policy_hash)
        if static["status"] == "failed":
            verdict = "REJECTED"
        if snapshots.fingerprint(snapshot) != artifact_hash:
            verdict = "INCONCLUSIVE"
            results.append({"id": "snapshot-integrity", "status": "inconclusive",
                            "output": "Frozen snapshot changed during verification"})
        if snapshots.fingerprint(candidate, exclusions) != artifact_hash:
            verdict = "INCONCLUSIVE"
            results.append({"id": "workspace-integrity", "status": "inconclusive",
                            "output": "Candidate changed after snapshot; reverify new artifact"})
        try:
            _, current_policy_hash = policy.load_policy(policy_path, candidate)
        except (OSError, ValueError):
            current_policy_hash = None
        if current_policy_hash != policy_hash:
            verdict = "INCONCLUSIVE"
            results.append({"id": "policy-integrity", "status": "inconclusive",
                            "output": "Trusted policy changed during verification"})
    result = {
        "run_id": run_id, "task_id": claim["task_id"], "verdict": verdict,
        "artifact_hash": artifact_hash, "policy_hash": policy_hash,
        "manifest": manifest, "static_analysis": static, "checks": results,
        "note": "VERIFIED means only configured mandatory checks passed on this artifact.",
    }
    report_digest = hashlib.sha256(json.dumps(result, sort_keys=True, separators=(",", ":"),
                                              ensure_ascii=False).encode("utf-8")).hexdigest()
    event = audit.append_event(ledger, {
        "type": "verification_completed", "run_id": run_id, "task_id": claim["task_id"],
        "artifact_hash": artifact_hash, "policy_hash": policy_hash,
        "verdict": verdict, "report_path": str(report.resolve()),
        "report_sha256": report_digest,
        "checks": [{"id": check["id"], "status": check["status"],
                    "exit_code": check.get("exit_code"), "tests_run": check.get("tests_run")}
                   for check in results],
        "time": datetime.now(timezone.utc).isoformat(),
    })
    result["audit_hash"] = event["hash"]
    report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result
