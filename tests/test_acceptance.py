"""Independent acceptance-baseline and candidate-test trust checks."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from verifygate.verifier import verify


ROOT = Path(__file__).resolve().parents[1]


class AcceptanceTests(unittest.TestCase):
    def test_candidate_test_changes_do_not_change_trusted_suite_fingerprint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = root / "candidate"
            candidate.mkdir()
            (candidate / "calculator.py").write_text("def add(a, b): return a + b\n", encoding="utf-8")
            acceptance = root / "acceptance"
            acceptance.mkdir()
            (acceptance / "test_acceptance.py").write_bytes(
                (ROOT / "acceptance" / "test_calculator.py").read_bytes())
            policy_path = root / "policy.json"
            policy_data = json.loads((ROOT / "policies" / "python.json").read_text(encoding="utf-8"))
            policy_data["acceptance"]["path"] = "acceptance"
            policy_path.write_text(json.dumps(policy_data), encoding="utf-8")
            loaded_before, digest_before = __import__("verifygate.policy", fromlist=["load_policy"]).load_policy(policy_path, candidate)
            (candidate / "tests").mkdir()
            (candidate / "tests" / "test_candidate.py").write_text("def test_nothing(): pass\n", encoding="utf-8")
            loaded_after, digest_after = __import__("verifygate.policy", fromlist=["load_policy"]).load_policy(policy_path, candidate)
            self.assertEqual(loaded_before["acceptance_fingerprint"], loaded_after["acceptance_fingerprint"])
            self.assertEqual(digest_before, digest_after)

    @patch("verifygate.verifier.sandbox.run_checks")
    def test_policy_without_acceptance_gets_no_acceptance_integrity_check(self, runner):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = root / "candidate"
            candidate.mkdir()
            (candidate / "calculator.py").write_text("def add(a, b): return a + b\n", encoding="utf-8")
            data = json.loads((ROOT / "policies" / "python.json").read_text(encoding="utf-8"))
            data.pop("acceptance", None)
            data.pop("acceptance_fingerprint", None)
            data["checks"] = [check for check in data["checks"] if check["type"] != "acceptance"]
            policy_path = root / "policy.json"
            policy_path.write_text(json.dumps(data), encoding="utf-8")
            claim = root / "claim.json"
            claim.write_bytes((ROOT / "examples" / "claim.json").read_bytes())

            def observed(snapshot, rules, **kwargs):
                shared = {"status": "passed", "runner": "docker", "exit_code": 0,
                          "snapshot_hash": kwargs["snapshot_hash"], "policy_hash": kwargs["policy_hash"],
                          "provenance": "live_docker"}
                return [{"id": check["id"], **shared, "report_provenance": "trusted_harness_stdout",
                         "tests_run": 1, "report_sha256": "a" * 64, "test_source": "candidate"}
                        for check in data["checks"]]

            runner.side_effect = observed
            result = verify(candidate, claim, policy_path, root / "ledger.sqlite", root / "report.json")
            self.assertEqual(result["verdict"], "VERIFIED")
            self.assertNotIn("acceptance-integrity", [check["id"] for check in result["checks"]])

    @patch("verifygate.verifier.sandbox.run_checks")
    def test_acceptance_suite_change_during_run_is_inconclusive(self, runner):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = root / "candidate"
            candidate.mkdir()
            (candidate / "calculator.py").write_text("def add(a, b): return a + b\n", encoding="utf-8")
            suite = root / "acceptance"
            suite.mkdir()
            (suite / "test_acceptance.py").write_bytes(
                (ROOT / "acceptance" / "test_calculator.py").read_bytes())
            data = json.loads((ROOT / "policies" / "python.json").read_text(encoding="utf-8"))
            data["acceptance"]["path"] = "acceptance"
            policy_path = root / "policy.json"
            policy_path.write_text(json.dumps(data), encoding="utf-8")
            claim = root / "claim.json"
            claim.write_bytes((ROOT / "examples" / "claim.json").read_bytes())

            def mutate(snapshot, rules, **kwargs):
                (suite / "test_acceptance.py").write_text("# tampered\n", encoding="utf-8")
                shared = {"status": "passed", "runner": "docker", "exit_code": 0,
                          "snapshot_hash": kwargs["snapshot_hash"], "policy_hash": kwargs["policy_hash"],
                          "provenance": "live_docker"}
                results = []
                for check in data["checks"]:
                    if check["type"] == "acceptance":
                        results.append({"id": check["id"], **shared,
                                        "report_provenance": "trusted_harness_stdout",
                                        "tests_run": 1, "report_sha256": "b" * 64,
                                        "test_source": "trusted_acceptance",
                                        "acceptance_suite_id": "calculator",
                                        "acceptance_suite_version": "1",
                                        "acceptance_fingerprint": kwargs["acceptance"]["fingerprint"]})
                    elif check["type"] == "unittest":
                        results.append({"id": check["id"], **shared,
                                        "report_provenance": "trusted_harness_stdout",
                                        "tests_run": 1, "report_sha256": "a" * 64,
                                        "test_source": "candidate"})
                    else:
                        results.append({"id": check["id"], **shared})
                return results

            runner.side_effect = mutate
            result = verify(candidate, claim, policy_path, root / "ledger.sqlite", root / "report.json")
            self.assertEqual(result["verdict"], "INCONCLUSIVE")
            self.assertIn("acceptance-integrity", [check["id"] for check in result["checks"]])

    @patch("verifygate.verifier.sandbox.run_checks")
    def test_required_acceptance_failure_rejects_even_when_candidate_tests_pass(self, runner):
        runner.return_value = [
            {"id": "syntax", "status": "passed", "runner": "docker", "provenance": "live_docker",
             "exit_code": 0, "snapshot_hash": "x", "policy_hash": "y"},
            {"id": "unit-tests", "status": "passed", "runner": "docker", "provenance": "live_docker",
             "report_provenance": "trusted_harness_stdout", "test_source": "candidate", "exit_code": 0,
             "tests_run": 1, "report_sha256": "a" * 64, "snapshot_hash": "x", "policy_hash": "y"},
            {"id": "acceptance", "status": "failed", "runner": "docker", "provenance": "live_docker",
             "report_provenance": "trusted_harness_stdout", "test_source": "trusted_acceptance", "exit_code": 1,
             "tests_run": 1, "report_sha256": "b" * 64, "snapshot_hash": "x", "policy_hash": "y",
             "acceptance_suite_id": "calculator", "acceptance_suite_version": "1", "acceptance_fingerprint": "wrong"},
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            claim = root / "claim.json"
            claim.write_bytes((ROOT / "examples" / "claim.json").read_bytes())
            ledger = root / "events.sqlite"
            report = root / "report.json"
            result = verify(ROOT / "examples" / "passing", claim, ROOT / "policies" / "python.json", ledger, report)
            self.assertEqual(result["verdict"], "REJECTED")


if __name__ == "__main__":
    unittest.main()
