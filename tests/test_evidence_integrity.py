"""Provenance and evidence integrity checks."""

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from verifygate import policy


class EvidenceIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.rules = {"checks": [{"id": "unit", "type": "unittest", "minimum_tests": 1}],
                      "acceptance": {"suite_id": "suite", "version": "1", "minimum_tests": 1},
                      "acceptance_fingerprint": "suite-hash"}

    def evidence(self):
        return {"id": "unit", "status": "passed", "provenance": "live_docker",
                "runner": "docker", "exit_code": 0, "tests_run": 1,
                "report_sha256": "a" * 64, "snapshot_hash": "artifact",
                "policy_hash": "policy", "report_provenance": "trusted_harness_stdout",
                "test_source": "candidate"}

    def acceptance(self):
        return {"id": "acceptance", "status": "passed", "provenance": "live_docker",
                "runner": "docker", "exit_code": 0, "tests_run": 1,
                "report_sha256": "b" * 64, "snapshot_hash": "artifact",
                "policy_hash": "policy", "report_provenance": "trusted_harness_stdout",
                "test_source": "trusted_acceptance", "acceptance_suite_id": "suite",
                "acceptance_suite_version": "1", "acceptance_fingerprint": "suite-hash"}

    def test_live_evidence_is_verified(self):
        self.assertEqual(policy.decide([self.evidence(), self.acceptance()], self.rules, "artifact", "policy"), "VERIFIED")

    def test_synthetic_requires_explicit_opt_in(self):
        synthetic = self.evidence()
        synthetic.pop("provenance")
        self.assertEqual(policy.decide([synthetic, self.acceptance()], self.rules, "artifact", "policy"), "INCONCLUSIVE")
        self.assertEqual(policy.decide([synthetic, self.acceptance()], self.rules, "artifact", "policy",
                                       allow_simulated=True), "VERIFIED")

    def test_stale_hashes_and_report_are_inconclusive(self):
        for field, value in (("snapshot_hash", "stale"), ("policy_hash", "stale"),
                             ("report_sha256", "b" * 64), ("tests_run", 0)):
            evidence = self.evidence()
            evidence[field] = value
            self.assertEqual(policy.decide([evidence, self.acceptance()], self.rules, "artifact", "policy",
                                           report_hash="a" * 64),
                             "INCONCLUSIVE", field)

    def test_failed_evidence_is_rejected(self):
        evidence = self.evidence()
        evidence.update(status="failed", exit_code=1)
        self.assertEqual(policy.decide([evidence, self.acceptance()], self.rules, "artifact", "policy"), "REJECTED")


if __name__ == "__main__":
    unittest.main()
