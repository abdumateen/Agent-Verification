import subprocess
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from verifygate.sandbox import _execute, MAX_LOG_BYTES, run_checks


class SandboxTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = Path(tempfile.gettempdir()) / "snapshot"
        self.policy = {"image": "verifygate:test", "timeout": 15, "memory": 256,
                       "cpus": 0.5, "checks": [{"id": "unit", "type": "unittest",
                       "minimum_tests": 2, "mandatory": True}]}

    @patch("verifygate.sandbox._execute", side_effect=FileNotFoundError("docker"))
    def test_docker_unavailable(self, run):
        result = run_checks(self.snapshot, self.policy)[0]
        self.assertEqual(result["status"], "inconclusive")

    @patch("verifygate.sandbox._execute")
    def test_attack_has_no_results_mount_and_cannot_forge_pass(self, run):
        def invoke(argv, timeout):
            self.assertFalse(any("target=/results" in value for value in argv))
            return 0, "", "", False
        run.side_effect = invoke
        result = run_checks(self.snapshot, self.policy)[0]
        self.assertEqual(result["status"], "inconclusive")

    @patch("verifygate.sandbox._execute")
    def test_valid_duplicate_malformed_and_fabricated_records(self, run):
        def valid(argv, timeout):
            n = argv[-1]
            return 0, f'VERIFYGATE_RESULT<{n}>:{{"tests_run":2,"failures":0,"errors":0}}:VERIFYGATE_RESULT<{n}>', "", False
        run.side_effect = valid
        result = run_checks(self.snapshot, self.policy)[0]
        self.assertEqual(result["status"], "passed")
        for output in ("fabricated", "VERIFYGATE_RESULT<wrong>:{}:VERIFYGATE_RESULT<wrong>"):
            run.side_effect = lambda argv, timeout, output=output: (0, output, "", False)
            self.assertEqual(run_checks(self.snapshot, self.policy)[0]["status"], "inconclusive")
        def duplicate(argv, timeout):
            n = argv[-1]; record = '{"tests_run":2,"failures":0,"errors":0}'
            return 0, f"VERIFYGATE_RESULT<{n}>:{record}:VERIFYGATE_RESULT<{n}>VERIFYGATE_RESULT<{n}>:{record}:VERIFYGATE_RESULT<{n}>", "", False
        run.side_effect = duplicate
        self.assertEqual(run_checks(self.snapshot, self.policy)[0]["status"], "inconclusive")

    @patch("verifygate.sandbox._execute")
    def test_acceptance_check_emits_trusted_report_provenance(self, run):
        with tempfile.TemporaryDirectory() as directory:
            suite = Path(directory)
            (suite / "test_acceptance.py").write_text("", encoding="utf-8")
            self.policy["checks"] = [{"id": "acceptance", "type": "acceptance", "minimum_tests": 1}]
            run.return_value = (0, "", "", False)
            result = run_checks(self.snapshot, self.policy, acceptance={
                "suite_id": "s", "version": "1", "fingerprint": "f",
                "host_path": str(suite)})[0]
            self.assertEqual(result["report_provenance"], "trusted_harness_stdout")
            self.assertEqual(result["test_source"], "trusted_acceptance")
            self.assertEqual(result["acceptance_fingerprint"], "f")

    @patch("verifygate.sandbox._execute", return_value=(0, "", "", False))
    def test_synthetic_provenance(self, run):
        self.assertEqual(run_checks(self.snapshot, self.policy, execution_provenance="synthetic_test_double")[0]["provenance"], "synthetic_test_double")

    @patch("verifygate.sandbox._execute")
    def test_command_arguments(self, run):
        self.policy["checks"] = [{"id": "lint", "type": "command", "argv": ["python", "-V"], "mandatory": True}]
        run.return_value = (0, "ok", "", False)
        argv = run_checks(self.snapshot, self.policy)[0]
        actual = run.call_args.args[0]
        self.assertEqual(actual[-3:], ["verifygate:test", "python", "-V"])
        self.assertIn("--read-only", actual); self.assertIn("--network", actual)
        self.assertEqual(argv["status"], "passed")

    @patch("verifygate.sandbox._execute", side_effect=subprocess.TimeoutExpired("docker", 1))
    def test_timeout(self, run):
        self.assertEqual(run_checks(self.snapshot, self.policy)[0]["status"], "inconclusive")

    @patch("verifygate.sandbox._execute", return_value=(0, "", "", False))
    @patch("verifygate.sandbox.tempfile.TemporaryDirectory")
    def test_evidence_cleanup_failure_is_inconclusive(self, temp_directory, run):
        class BrokenTemporaryDirectory:
            def __enter__(self):
                self.path = tempfile.mkdtemp(prefix="verifygate-broken-cleanup-")
                return self.path

            def __exit__(self, exc_type, exc, traceback):
                Path(self.path).rmdir()
                raise OSError("cleanup failed")

        temp_directory.return_value = BrokenTemporaryDirectory()
        result = run_checks(self.snapshot, self.policy)[0]
        self.assertEqual(result["status"], "inconclusive")
        self.assertIn("cleanup failed", result["output"])

    @patch("verifygate.sandbox.subprocess.run")
    @patch("verifygate.sandbox._execute")
    def test_timeout_forces_container_cleanup(self, execute, cleanup):
        def timed_out(argv, timeout):
            Path(argv[argv.index("--cidfile") + 1]).write_text("a" * 64, encoding="ascii")
            raise subprocess.TimeoutExpired("docker", timeout)
        execute.side_effect = timed_out
        run_checks(self.snapshot, self.policy)
        cleanup.assert_called_once_with(["docker", "rm", "-f", "a" * 64], capture_output=True, timeout=10, check=True)

    @patch("verifygate.sandbox._execute", return_value=(0, "x" * 70000, "err", True))
    def test_bounded_log(self, run):
        self.policy["checks"] = [{"id": "cmd", "type": "command", "argv": ["python", "-V"]}]
        result = run_checks(self.snapshot, self.policy)[0]
        self.assertTrue(result["output_truncated"])
        self.assertLessEqual(len(result["output"].encode()), MAX_LOG_BYTES)

    def test_streaming_process_bounds_real_output(self):
        code, stdout, stderr, truncated = _execute([sys.executable, "-c", 'import sys;sys.stdout.write("a"*200000);sys.stderr.write("b"*200000)'], 10)
        self.assertEqual((code, len(stdout), len(stderr), truncated), (0, MAX_LOG_BYTES, MAX_LOG_BYTES, True))


if __name__ == "__main__":
    unittest.main()
