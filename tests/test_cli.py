"""End-to-end orchestration tests with the external Docker boundary mocked."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout, redirect_stderr
import io

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from verifygate import audit
from verifygate.cli import verify
from verifygate.cli import main


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

    @patch("verifygate.verifier.sandbox.run_checks")
    def test_failure_then_pass_has_distinct_auditable_runs(self, runner):
        runner.return_value = [
            {"id": "syntax", "status": "passed", "exit_code": 0, "tests_run": None, "output": ""},
            {"id": "unit-tests", "status": "failed", "exit_code": 1, "tests_run": 1, "output": "assertion failed"},
        ]
        rejected = verify(ROOT / "examples" / "broken", self.claim, self.rules, self.ledger, self.report)
        self.assertEqual(rejected["verdict"], "REJECTED")
        def observed(snapshot, rules, *, snapshot_hash, policy_hash, acceptance=None):
            shared = {"status": "passed", "runner": "docker", "exit_code": 0,
                      "snapshot_hash": snapshot_hash, "policy_hash": policy_hash,
                      "provenance": "synthetic_test_double", "report_provenance": "trusted_harness_stdout"}
            results = [{"id": "syntax", **shared},
                       {"id": "unit-tests", **shared, "tests_run": 1,
                        "report_sha256": "a" * 64, "test_source": "candidate"}]
            if acceptance:
                results.append({"id": "acceptance", **shared, "tests_run": 1,
                                "report_sha256": "b" * 64, "test_source": "trusted_acceptance",
                                "acceptance_suite_id": acceptance["suite_id"],
                                "acceptance_suite_version": acceptance["version"],
                                "acceptance_fingerprint": acceptance["fingerprint"]})
            return results
        runner.side_effect = observed
        accepted = verify(ROOT / "examples" / "passing", self.claim, self.rules, self.ledger, self.report)
        self.assertEqual(accepted["verdict"], "INCONCLUSIVE")
        self.assertNotEqual(rejected["artifact_hash"], accepted["artifact_hash"])
        self.assertTrue(audit.verify_ledger(self.ledger))
        self.assertEqual(json.loads(self.report.read_text())["audit_hash"], accepted["audit_hash"])
        self.assertNotIn("assertion failed", str(audit.list_events(self.ledger)))

    @patch("verifygate.verifier.sandbox.run_checks")
    def test_missing_docker_is_inconclusive_not_success(self, runner):
        runner.return_value = [{"id": "unit-tests", "status": "inconclusive", "output": "docker missing"}]
        result = verify(ROOT / "examples" / "passing", self.claim, self.rules, self.ledger, self.report)
        self.assertEqual(result["verdict"], "INCONCLUSIVE")

    def test_wrong_task_is_rejected_before_runner(self):
        wrong = self.base / "wrong.json"
        payload = json.loads(self.claim.read_text(encoding="utf-8"))
        payload["task_id"] = "OTHER"
        wrong.write_text(json.dumps(payload), encoding="utf-8")
        with patch("verifygate.verifier.sandbox.run_checks") as runner:
            with self.assertRaises(ValueError):
                verify(ROOT / "examples" / "passing", wrong, self.rules, self.ledger, self.report)
            runner.assert_not_called()

    @patch("verifygate.verifier.sandbox.run_checks")
    def test_candidate_or_policy_change_invalidates_pass(self, runner):
        candidate = self.base / "candidate"
        candidate.mkdir()
        (candidate / "calculator.py").write_text("def add(a,b): return a+b\n", encoding="utf-8")
        custom_claim = self.base / "claim.json"
        custom_claim.write_bytes(self.claim.read_bytes())
        custom_policy = self.base / "policy.json"
        custom_policy.write_bytes(self.rules.read_bytes())
        custom_policy_data = json.loads(custom_policy.read_text(encoding="utf-8"))
        custom_policy_data.pop("acceptance", None)
        custom_policy_data.pop("acceptance_fingerprint", None)
        custom_policy_data["checks"] = [check for check in custom_policy_data["checks"] if check["type"] != "acceptance"]
        custom_policy.write_text(json.dumps(custom_policy_data), encoding="utf-8")
        def mutate(snapshot, rules, **kwargs):
            (candidate / "calculator.py").write_text("def add(a,b): return a-b\n", encoding="utf-8")
            custom_policy.write_text(custom_policy.read_text(encoding="utf-8").replace('"timeout": 120', '"timeout": 121'), encoding="utf-8")
            shared = {"status": "passed", "runner": "docker", "exit_code": 0,
                      "snapshot_hash": kwargs["snapshot_hash"], "policy_hash": kwargs["policy_hash"],
                      "provenance": "live_docker", "report_provenance": "trusted_harness_stdout"}
            return [{"id": "syntax", **shared}, {"id": "unit-tests", **shared,
                    "tests_run": 1, "report_sha256": "a" * 64, "test_source": "candidate"}]
        runner.side_effect = mutate
        result = verify(candidate, custom_claim, custom_policy, self.ledger, self.report)
        self.assertEqual(result["verdict"], "INCONCLUSIVE")
        self.assertIn("workspace-integrity", [c["id"] for c in result["checks"]])
        self.assertIn("policy-integrity", [c["id"] for c in result["checks"]])

    @patch("verifygate.verifier.sandbox.run_checks")
    def test_missing_mandatory_result_and_report_tampering(self, runner):
        runner.return_value = [{"id": "syntax", "status": "passed"}]
        result = verify(ROOT / "examples" / "passing", self.claim, self.rules, self.ledger, self.report)
        self.assertEqual(result["verdict"], "INCONCLUSIVE")
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["status", "--ledger", str(self.ledger)]), 0)
            self.assertEqual(main(["report", "--ledger", str(self.ledger), "--run-id", result["run_id"]]), 0)
        self.assertIn(result["run_id"], output.getvalue())
        data = json.loads(self.report.read_text(encoding="utf-8"))
        data["verdict"] = "VERIFIED"
        self.report.write_text(json.dumps(data), encoding="utf-8")
        with redirect_stderr(io.StringIO()):
            self.assertEqual(main(["report", "--ledger", str(self.ledger), "--run-id", result["run_id"]]), 2)

    def test_actual_harness_discovers_both_demo_projects(self):
        for candidate, exit_code, failed in (("passing", 0, 0), ("broken", 1, 1)):
            nonce = "a" * 48
            proc = subprocess.run(
                [sys.executable, "-I", str(ROOT / "src" / "verifygate" / "test_harness.py"), "--nonce", nonce],
                cwd=ROOT / "examples" / candidate,
                env={"PYTHONPATH": str(ROOT / "src")},
                capture_output=True, text=True,
            )
            self.assertEqual(proc.returncode, exit_code, proc.stdout + proc.stderr)
            marker_start = f"VERIFYGATE_RESULT<{nonce}>:"
            marker_end = f":VERIFYGATE_RESULT<{nonce}>"
            records = proc.stdout.split(marker_start)
            self.assertEqual(len(records), 2)
            data = json.loads(records[1].split(marker_end, 1)[0])
            self.assertEqual(data["tests_run"], 1)
            self.assertEqual(data["failures"], failed)


if __name__ == "__main__":
    unittest.main()
