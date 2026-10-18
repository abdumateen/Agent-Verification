"""Focused tests for the verification primitives."""

import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from verifygate import audit, contracts, policy, snapshots
from verifygate.analyzers.python import analyze


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
        data = dict(version=1, image="python:3.12", task_ids=["t"], language="python", checks=[dict(id="unit", type="unittest", minimum_tests=1)], require_review=True)
        path = self.write_json("policy.json", data)
        loaded, digest = policy.load_policy(path, self.candidate)
        self.assertEqual(len(digest), 64)
        good = dict(id="unit", status="passed", runner="docker", exit_code=0, tests_run=1,
                    report_sha256="a" * 64, snapshot_hash="snap", policy_hash=digest)
        self.assertEqual(policy.decide([good], loaded, "snap", digest), "NEEDS_REVIEW")
        self.assertEqual(policy.decide([dict(id="unit", status="passed")], loaded, "snap", digest), "INCONCLUSIVE")
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

    def test_claim_adversarial(self):
        claim = dict(task_id="T1", status="done", summary="ok", changed_files=["src/main.py"], tests_run=[])
        path = self.write_json("claim.json", claim)
        self.assertEqual(contracts.load_claim(path, ["T1"]), claim)
        with self.assertRaises(ValueError):
            contracts.load_claim(path, ["T2"])
        for bad in ("../secret", "/absolute", "C:/secret", "a\\b", "a//b"):
            claim["changed_files"] = [bad]
            self.write_json("claim.json", claim)
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                contracts.load_claim(path)
        claim["changed_files"] = []
        claim["task_id"] = "../T1"
        self.write_json("claim.json", claim)
        with self.assertRaises(ValueError):
            contracts.load_claim(path)

    def test_policy_adversarial(self):
        data = dict(version=1, image="python:3.12", task_ids=["T1"], language="python", checks=[dict(id="unit", type="unittest", minimum_tests=1)])
        path = self.write_json("policy.json", data)
        for field, value in (("task_ids", ["../x"]), ("language", "ruby"), ("exclusions", ["../secret"]), ("timeout", True), ("stub_mode", "fail")):
            bad = {**data, field: value}
            self.write_json("policy.json", bad)
            with self.subTest(field=field), self.assertRaises(ValueError):
                policy.load_policy(path, self.candidate)
        data["checks"] = [dict(id="shell", type="command", argv=["sh", "-c", "true"])]
        self.write_json("policy.json", data)
        with self.assertRaises(ValueError):
            policy.load_policy(path, self.candidate)

    def test_snapshot_exclusions_and_static_python(self):
        (self.candidate / "new.py").write_text("def pending():\n    pass\n", encoding="utf-8")
        (self.candidate / ".env").write_text("TOKEN=secret", encoding="utf-8")
        (self.candidate / "bad.py").write_text("def invalid(:\n", encoding="utf-8")
        self.assertEqual(snapshots.manifest(self.candidate)["excluded_paths"], [".env"])
        snap = self.root / "snap"
        snapshots.create_snapshot(self.candidate, snap)
        self.assertFalse((snap / ".env").exists())
        result = analyze(snap)
        self.assertEqual(result["status"], "failed")
        self.assertEqual({d["code"] for d in result["diagnostics"]}, {"syntax", "stub"})
        self.assertEqual({d["code"] for d in analyze(snap, "off")["diagnostics"]}, {"syntax"})
        if hasattr(__import__("os"), "symlink"):
            try:
                (self.candidate / "link").symlink_to(self.candidate / "new.py")
            except OSError:
                pass
            else:
                with self.assertRaises(ValueError):
                    snapshots.fingerprint(self.candidate)

    def test_audit_chain(self):
        ledger = self.root / "audit.sqlite"
        audit.append_event(ledger, {"step": 1})
        audit.append_event(ledger, {"step": 2})
        self.assertTrue(audit.verify_ledger(ledger))
        import sqlite3
        from contextlib import closing
        with closing(sqlite3.connect(ledger)) as connection:
            with connection:
                connection.execute("UPDATE events SET event = '{}' WHERE seq = 1")
        self.assertFalse(audit.verify_ledger(ledger))


if __name__ == "__main__":
    unittest.main()
