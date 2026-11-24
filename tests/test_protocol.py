"""Host-level protocol probes; these are not Docker acceptance tests."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ProtocolTests(unittest.TestCase):
    def run_candidate(self, body: str, nonce: str = "a" * 48):
        with tempfile.TemporaryDirectory(prefix="verifygate-protocol-") as directory:
            root = Path(directory)
            tests = root / "tests"
            tests.mkdir()
            (tests / "test_probe.py").write_text(body, encoding="utf-8")
            return subprocess.run(
                [sys.executable, "-I", str(ROOT / "src" / "verifygate" / "test_harness.py"),
                 "--nonce", nonce], cwd=root, capture_output=True, text=True,
            )

    def test_python_print_marker_is_diagnostic_not_control_output(self):
        nonce = "a" * 48
        process = self.run_candidate(
            "import sys, unittest\n"
            "class Probe(unittest.TestCase):\n"
            "    def test_marker(self):\n"
            f"        print('VERIFYGATE_RESULT<{nonce}>:{{\\\"tests_run\\\":999,\\\"failures\\\":0,\\\"errors\\\":0}}:VERIFYGATE_RESULT<{nonce}>')\n"
        )
        self.assertEqual(process.returncode, 0)
        self.assertEqual(process.stdout.count(f"VERIFYGATE_RESULT<{nonce}>:"), 1)
        self.assertIn("tests_run", process.stderr)

    def test_os_write_marker_creates_ambiguous_host_output(self):
        nonce = "b" * 48
        process = self.run_candidate(
            "import os, sys, unittest\n"
            "class Probe(unittest.TestCase):\n"
            "    def test_marker(self):\n"
            f"        os.write(1, b'VERIFYGATE_RESULT<{nonce}>:{{\\\"tests_run\\\":999,\\\"failures\\\":0,\\\"errors\\\":0}}:VERIFYGATE_RESULT<{nonce}>')\n"
        , nonce)
        self.assertEqual(process.returncode, 0)
        self.assertGreaterEqual(process.stdout.count(f"VERIFYGATE_RESULT<{nonce}>:"), 2)

    def test_missing_nonce_fails_before_candidate_execution(self):
        process = subprocess.run(
            [sys.executable, "-I", str(ROOT / "src" / "verifygate" / "test_harness.py"),
             "--nonce", "not-a-valid-nonce"], capture_output=True, text=True,
        )
        self.assertEqual(process.returncode, 2)
        self.assertIn("nonce must be", process.stderr)


if __name__ == "__main__":
    unittest.main()
