"""Command-line workflow for an evidence-backed completion claim."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
from uuid import uuid4

from verifygate import audit, contracts, policy, sandbox, snapshots


def verify(candidate: Path, claim_path: Path, policy_path: Path, ledger: Path, report: Path) -> dict:
    candidate = candidate.resolve(strict=True)
    claim = contracts.load_claim(claim_path)
    rules, policy_hash = policy.load_policy(policy_path, candidate)
    for output in (ledger, report):
        if candidate == output.resolve() or candidate in output.resolve().parents:
            raise ValueError("audit ledger and report must be outside the candidate")
    run_id = uuid4().hex
    with tempfile.TemporaryDirectory(prefix="verifygate-snapshot-") as directory:
        snapshot = Path(directory) / "source"
        before = snapshots.fingerprint(candidate)
        artifact_hash = snapshots.create_snapshot(candidate, snapshot)
        if snapshots.fingerprint(candidate) != before or artifact_hash != before:
            raise ValueError("candidate changed during snapshot creation; retry")
        audit.append_event(ledger, {
            "type": "verification_started", "run_id": run_id,
            "task_id": claim["task_id"], "artifact_hash": artifact_hash,
            "policy_hash": policy_hash, "claim": claim,
            "time": datetime.now(timezone.utc).isoformat(),
        })
        results = sandbox.run_checks(snapshot, rules)
        verdict = policy.decide(results, rules)
        if snapshots.fingerprint(snapshot) != artifact_hash:
            verdict = "INCONCLUSIVE"
            results.append({"id": "snapshot-integrity", "status": "inconclusive",
                            "output": "Frozen snapshot changed during verification"})
        if snapshots.fingerprint(candidate) != artifact_hash:
            verdict = "INCONCLUSIVE"
            results.append({"id": "workspace-integrity", "status": "inconclusive",
                            "output": "Candidate changed after snapshot; reverify new artifact"})
    result = {
        "run_id": run_id, "task_id": claim["task_id"], "verdict": verdict,
        "artifact_hash": artifact_hash, "policy_hash": policy_hash,
        "checks": results,
        "note": "VERIFIED means only the configured mandatory checks passed on this artifact.",
    }
    event = audit.append_event(ledger, {
        "type": "verification_completed", "run_id": run_id, "task_id": claim["task_id"],
        "artifact_hash": artifact_hash, "policy_hash": policy_hash,
        "verdict": verdict, "checks": [
            {"id": check["id"], "status": check["status"],
             "exit_code": check.get("exit_code"), "tests_run": check.get("tests_run")}
            for check in results
        ],
        "time": datetime.now(timezone.utc).isoformat(),
    })
    result["audit_hash"] = event["hash"]
    report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="verifygate")
    commands = parser.add_subparsers(dest="action", required=True)
    command = commands.add_parser("verify", help="independently check a completion claim")
    command.add_argument("--candidate", type=Path, required=True)
    command.add_argument("--claim", type=Path, required=True)
    command.add_argument("--policy", type=Path, required=True)
    command.add_argument("--ledger", type=Path, required=True)
    command.add_argument("--report", type=Path, required=True)
    ledger = commands.add_parser("audit-verify", help="check the local hash chain")
    ledger.add_argument("--ledger", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.action == "audit-verify":
        valid = audit.verify_ledger(args.ledger)
        print("VALID" if valid else "INVALID")
        return 0 if valid else 1
    try:
        result = verify(args.candidate, args.claim, args.policy, args.ledger, args.report)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"UNVERIFIED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result["verdict"] == "VERIFIED" else 1


if __name__ == "__main__":
    sys.exit(main())
