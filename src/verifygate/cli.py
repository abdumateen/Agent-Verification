"""CLI transport for the shared verification engine."""

import argparse
import json
from pathlib import Path
import sys

from verifygate import audit, policy, reports
from verifygate.verifier import verify


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="verifygate")
    commands = parser.add_subparsers(dest="action", required=True)
    commands.add_parser("version", help="show the VerifyGate schema version")
    command = commands.add_parser("verify", help="independently check a completion claim")
    command.add_argument("--candidate", type=Path, required=True)
    command.add_argument("--claim", type=Path, required=True)
    command.add_argument("--policy", type=Path, required=True)
    command.add_argument("--ledger", type=Path, required=True)
    command.add_argument("--report", type=Path, required=True)
    validator = commands.add_parser("policy-validate", help="validate a trusted policy")
    validator.add_argument("--candidate", type=Path, required=True)
    validator.add_argument("--policy", type=Path, required=True)
    validator = commands.add_parser("audit-verify", help="check the SQLite hash chain")
    validator.add_argument("--ledger", type=Path, required=True)
    status = commands.add_parser("status", help="list recent completed runs")
    status.add_argument("--ledger", type=Path, required=True)
    status.add_argument("--limit", type=int, default=10)
    selected = commands.add_parser("report", help="read a run's stored report")
    selected.add_argument("--ledger", type=Path, required=True)
    selected.add_argument("--run-id", required=True)
    demo = commands.add_parser("demo", help="verify both fixtures using the actual Docker runner")
    demo.add_argument("--ledger", type=Path, required=True)
    demo.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.action == "version":
            print("VerifyGate 0.2 (policy schema 1)")
            return 0
        if args.action == "audit-verify":
            valid = audit.verify_ledger(args.ledger)
            print("VALID" if valid else "INVALID")
            return 0 if valid else 1
        if args.action == "policy-validate":
            _, digest = policy.load_policy(args.policy, args.candidate)
            print(json.dumps({"valid": True, "policy_hash": digest}))
            return 0
        if args.action == "status":
            records = audit.list_events(args.ledger, limit=args.limit * 2)
            print(json.dumps([r["event"] for r in records if r["event"].get("type") == "verification_completed"][:args.limit], indent=2))
            return 0
        if args.action == "report":
            print(json.dumps(reports.get_report(args.ledger, args.run_id), indent=2))
            return 0
        if args.action == "demo":
            root = Path(__file__).resolve().parents[2]
            if not args.output_dir.is_dir():
                raise ValueError("demo output directory must already exist")
            outcomes = {}
            for fixture in ("broken", "passing"):
                outcome = verify(root / "examples" / fixture, root / "examples" / "claim.json",
                                 root / "policies" / "python.json", args.ledger,
                                 args.output_dir / f"{fixture}.report.json")
                outcomes[fixture] = {"verdict": outcome["verdict"],
                                     "run_id": outcome["run_id"], "artifact_hash": outcome["artifact_hash"]}
            print(json.dumps({"execution": "actual Docker runner; never simulated", "runs": outcomes}, indent=2))
            return 0 if outcomes["broken"]["verdict"] == "REJECTED" and outcomes["passing"]["verdict"] == "VERIFIED" else 1
        result = verify(args.candidate, args.claim, args.policy, args.ledger, args.report)
        print(json.dumps(result, indent=2))
        return 0 if result["verdict"] == "VERIFIED" else 1
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"UNVERIFIED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
