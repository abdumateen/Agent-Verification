"""Adapter fail-closed checks that do not require Docker or a Git commit."""

from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]


class IntegrationTests(unittest.TestCase):
    def test_hook_without_trusted_configuration_blocks(self):
        process = subprocess.run(["sh", str(ROOT / "hooks" / "pre-commit")],
                                 capture_output=True, text=True, env={})
        self.assertNotEqual(process.returncode, 0)
        self.assertIn("VERIFYGATE_HOME", process.stderr)

    def test_ci_adapter_without_trusted_configuration_blocks(self):
        process = subprocess.run(["sh", str(ROOT / "scripts" / "ci-gate.sh")],
                                 capture_output=True, text=True, env={})
        self.assertNotEqual(process.returncode, 0)
        self.assertIn("VERIFYGATE_HOME", process.stderr)
