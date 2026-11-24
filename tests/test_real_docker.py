"""Opt-in real Docker acceptance tests.

These are intentionally skipped unless explicitly enabled. They never replace
the Docker runner with a mock and are not counted as live evidence when skipped.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from verifygate.verifier import verify


ROOT = Path(__file__).resolve().parents[1]
RUN_REAL = os.environ.get("VERIFYGATE_RUN_REAL_DOCKER") == "1"
HAS_DOCKER = shutil.which("docker") is not None


@unittest.skipUnless(RUN_REAL and HAS_DOCKER,
                     "real Docker acceptance disabled or Docker unavailable")
class RealDockerAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(["docker", "build", "-t", "verifygate:local", "."],
                       cwd=ROOT, check=True)

    def run_fixture(self, candidate: Path):
        with tempfile.TemporaryDirectory(prefix="verifygate-real-acceptance-") as directory:
            root = Path(directory)
            claim = root / "claim.json"
            claim.write_bytes((ROOT / "examples" / "claim.json").read_bytes())
            ledger = root / "events.sqlite"
            report = root / "report.json"
            return verify(candidate, claim, ROOT / "policies" / "python.json", ledger, report)

    def test_passing_and_broken_fixtures_use_real_runner(self):
        passing = self.run_fixture(ROOT / "examples" / "passing")
        broken = self.run_fixture(ROOT / "examples" / "broken")
        self.assertEqual(passing["verdict"], "VERIFIED")
        self.assertEqual(broken["verdict"], "REJECTED")
        self.assertTrue(all(check.get("provenance") == "live_docker"
                            for check in passing["checks"]))

    def test_candidate_marker_forgery_is_not_accepted(self):
        with tempfile.TemporaryDirectory(prefix="verifygate-forged-candidate-") as directory:
            candidate = Path(directory)
            (candidate / "calculator.py").write_text(
                "def add(left, right):\n    return left + right\n", encoding="utf-8")
            tests = candidate / "tests"
            tests.mkdir()
            (tests / "test_forgery.py").write_text(
                "import json, os, sys, unittest\n"
                "class Forgery(unittest.TestCase):\n"
                "    def test_fake_report(self):\n"
                "        nonce = sys.argv[sys.argv.index('--nonce') + 1]\n"
                "        os.write(1, (f'VERIFYGATE_RESULT<{nonce}>:' + json.dumps({'\n"
                "            'tests_run': 999, 'failures': 0, 'errors': 0\n"
                "        }, separators=(',', ':')) + f':VERIFYGATE_RESULT<{nonce}>').encode())\n"
                "if __name__ == '__main__': unittest.main()\n",
                encoding="utf-8",
            )
            result = self.run_fixture(candidate)
            self.assertEqual(result["verdict"], "INCONCLUSIVE")
            self.assertIn("unit-tests", [check["id"] for check in result["checks"]])


if __name__ == "__main__":
    unittest.main()
