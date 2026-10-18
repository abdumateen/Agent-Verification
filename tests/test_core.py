"""Focused tests for the verification primitives."""

import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from verifygate import audit, contracts, policy, snapshots


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.candidate = self.root / "candidate"
        self.candidate.mkdir()

    def write_json(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_claim(self):
        claim = dict(task_id="t", status="done", summary="complete", changed_files=[], tests_run=[])
        path = self.write_json("claim.json", claim)
        self.assertEqual(contracts.load_claim(path), claim)
        claim["status"] = "pending"
        self.write_json("claim.json", claim)
        with self.assertRaises(ValueError):
            contracts.load_claim(path)

    def test_policy_and_decision(self):
        data = dict(version=1, image="python:3.12", checks=[dict(id="unit", type="unittest", minimum_tests=1)], require_review=True)
        path = self.write_json("policy.json", data)
        loaded, digest = policy.load_policy(path, self.candidate)
        self.assertEqual(len(digest), 64)
        self.assertEqual(policy.decide([dict(id="unit", status="passed")], loaded), "NEEDS_REVIEW")
        self.assertEqual(policy.decide([], loaded), "INCONCLUSIVE")
        self.assertEqual(policy.decide([dict(id="unit", status="failed")], loaded), "REJECTED")
        self.write_json("candidate/policy.json", data)
        with self.assertRaises(ValueError):
            policy.load_policy(self.candidate / "policy.json", self.candidate)
        data["checks"].append(dict(id="unit", type="command", argv=["true"]))
        self.write_json("policy.json", data)
        with self.assertRaises(ValueError):
            policy.load_policy(path, self.candidate)

    def test_snapshot(self):
        (self.candidate / "file.txt").write_bytes(b"hello")
        (self.candidate / ".git").mkdir()
        (self.candidate / ".git" / "ignored").write_bytes(b"private")
        snapshot = self.root / "snapshot"
        digest = snapshots.create_snapshot(self.candidate, snapshot)
        self.assertEqual(digest, snapshots.fingerprint(snapshot))
        (snapshot / "file.txt").write_bytes(b"changed")
        self.assertNotEqual(digest, snapshots.fingerprint(snapshot))
        with self.assertRaises(ValueError):
            snapshots.create_snapshot(self.candidate, self.candidate / "nested")

    def test_audit_chain(self):
        ledger = self.root / "audit.jsonl"
        audit.append_event(ledger, {"step": 1})
        audit.append_event(ledger, {"step": 2})
        self.assertTrue(audit.verify_ledger(ledger))
        lines = ledger.read_text(encoding="utf-8").splitlines()
        ledger.write_text("\n".join(reversed(lines)) + "\n", encoding="utf-8")
        self.assertFalse(audit.verify_ledger(ledger))


if __name__ == "__main__":
    unittest.main()
