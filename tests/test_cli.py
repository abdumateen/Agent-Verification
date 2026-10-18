"""End-to-end orchestration tests with the external Docker boundary mocked."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from verifygate import audit
from verifygate.cli import verify


ROOT = Path(__file__).resolve().parents[1]


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.claim = ROOT / "examples" / "claim.json"
        self.rules = ROOT / "policies" / "python.json"
        self.ledger = self.base / "audit.jsonl"
        self.report = self.base / "result.json"

    @patch("verifygate.cli.sandbox.run_checks")
    def test_failure_then_pass_has_distinct_auditable_runs(self, runner):
        runner.return_value = [
            {"id": "syntax", "status": "passed", "exit_code": 0, "tests_run": None, "output": ""},
            {"id": "unit-tests", "status": "failed", "exit_code": 1, "tests_run": 1, "output": "assertion failed"},
        ]
        rejected = verify(ROOT / "examples" / "broken", self.claim, self.rules, self.ledger, self.report)
        self.assertEqual(rejected["verdict"], "REJECTED")
        runner.return_value[1] = {"id": "unit-tests", "status": "passed", "exit_code": 0,
                                  "tests_run": 1, "output": ""}
        accepted = verify(ROOT / "examples" / "passing", self.claim, self.rules, self.ledger, self.report)
        self.assertEqual(accepted["verdict"], "VERIFIED")
        self.assertNotEqual(rejected["artifact_hash"], accepted["artifact_hash"])
        self.assertTrue(audit.verify_ledger(self.ledger))
        self.assertEqual(json.loads(self.report.read_text())["audit_hash"], accepted["audit_hash"])
        self.assertNotIn("assertion failed", self.ledger.read_text())

    @patch("verifygate.cli.sandbox.run_checks")
    def test_missing_docker_is_inconclusive_not_success(self, runner):
        runner.return_value = [{"id": "unit-tests", "status": "inconclusive", "output": "docker missing"}]
        result = verify(ROOT / "examples" / "passing", self.claim, self.rules, self.ledger, self.report)
        self.assertEqual(result["verdict"], "INCONCLUSIVE")

    def test_actual_harness_discovers_both_demo_projects(self):
        for candidate, exit_code, failed in (("passing", 0, 0), ("broken", 1, 1)):
            report = self.base / f"{candidate}.json"
            proc = subprocess.run(
                [sys.executable, "-m", "verifygate.test_harness", "--report", str(report)],
                cwd=ROOT / "examples" / candidate,
                env={"PYTHONPATH": str(ROOT / "src")},
                capture_output=True, text=True,
            )
            self.assertEqual(proc.returncode, exit_code, proc.stdout + proc.stderr)
            data = json.loads(report.read_text())
            self.assertEqual(data["tests_run"], 1)
            self.assertEqual(data["failures"], failed)


if __name__ == "__main__":
    unittest.main()
