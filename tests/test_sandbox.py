import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from verifygate.sandbox import run_checks


class SandboxTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = Path(tempfile.gettempdir()) / "snapshot"
        self.policy = {
            "image": "verifygate:test", "timeout": 15,
            "memory": 256, "cpus": 0.5,
            "checks": [{"id": "unit", "type": "unittest", "minimum_tests": 2,
                        "mandatory": True}],
        }

    @patch("verifygate.sandbox.subprocess.run", side_effect=FileNotFoundError("docker"))
    def test_docker_unavailable(self, run):
        result = run_checks(self.snapshot, self.policy)[0]
        self.assertEqual(result["status"], "inconclusive")
        self.assertIsNone(result["exit_code"])

    @patch("verifygate.sandbox.subprocess.run")
    def test_zero_tests_and_failure(self, run):
        for count, failures, code in ((0, 0, 1), (2, 1, 1)):
            def invoke(argv, **kwargs):
                mount = next(
                    argv[i + 1] for i, arg in enumerate(argv[:-1])
                    if arg == "--mount" and "target=/results" in argv[i + 1]
                )
                folder = Path(mount.split("source=", 1)[1].split(",target=", 1)[0])
                (folder / "report.json").write_text(json.dumps({
                    "tests_run": count, "failures": failures, "errors": 0,
                }), encoding="utf-8")
                return subprocess.CompletedProcess(argv, code, "output", "")
            run.side_effect = invoke
            result = run_checks(self.snapshot, self.policy)[0]
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["tests_run"], count)

    @patch("verifygate.sandbox.subprocess.run")
    def test_command_arguments(self, run):
        self.policy["checks"] = [{"id": "lint", "type": "command",
                                   "argv": ["python", "-V"], "mandatory": True}]
        run.return_value = subprocess.CompletedProcess([], 0, "ok", "")
        self.assertEqual(run_checks(self.snapshot, self.policy)[0]["status"], "passed")
        argv = run.call_args.args[0]
        for part in ("--rm", "--read-only", "--network", "none", "--cap-drop",
                     "ALL", "--pids-limit", "128", "--user", "65534:65534",
                     "--tmpfs", "--mount", "--workdir", "/workspace"):
            self.assertIn(part, argv)
        self.assertEqual(argv[-3:], ["verifygate:test", "python", "-V"])
        self.assertEqual(run.call_args.kwargs["timeout"], 15)


if __name__ == "__main__":
    unittest.main()
