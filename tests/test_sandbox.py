import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from verifygate.sandbox import _execute, MAX_LOG_BYTES, run_checks


class SandboxTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = Path(tempfile.gettempdir()) / "snapshot"
        self.policy = {
            "image": "verifygate:test", "timeout": 15,
            "memory": 256, "cpus": 0.5,
            "checks": [{"id": "unit", "type": "unittest", "minimum_tests": 2,
                        "mandatory": True}],
        }

    @patch("verifygate.sandbox._execute", side_effect=FileNotFoundError("docker"))
    def test_docker_unavailable(self, run):
        result = run_checks(self.snapshot, self.policy)[0]
        self.assertEqual(result["status"], "inconclusive")
        self.assertIsNone(result["exit_code"])

    @patch("verifygate.sandbox._execute")
    def test_zero_tests_and_failure(self, run):
        for count, failures, code in ((0, 0, 1), (2, 1, 1)):
            def invoke(argv, timeout):
                mount = next(
                    argv[i + 1] for i, arg in enumerate(argv[:-1])
                    if arg == "--mount" and "target=/results" in argv[i + 1]
                )
                folder = Path(mount.split("source=", 1)[1].split(",target=", 1)[0])
                (folder / "report.json").write_text(json.dumps({
                    "tests_run": count, "failures": failures, "errors": 0,
                }), encoding="utf-8")
                return code, "output", "", False
            run.side_effect = invoke
            result = run_checks(self.snapshot, self.policy)[0]
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["tests_run"], count)

    @patch("verifygate.sandbox._execute")
    def test_command_arguments(self, run):
        self.policy["checks"] = [{"id": "lint", "type": "command",
                                   "argv": ["python", "-V"], "mandatory": True}]
        run.return_value = 0, "ok", "", False
        self.assertEqual(run_checks(self.snapshot, self.policy)[0]["status"], "passed")
        argv = run.call_args.args[0]
        for part in ("--rm", "--read-only", "--network", "none", "--cap-drop",
                     "ALL", "--pids-limit", "128", "--user", "65534:65534",
                     "--tmpfs", "--mount", "--workdir", "/workspace"):
            self.assertIn(part, argv)
        self.assertEqual(argv[-3:], ["verifygate:test", "python", "-V"])
        self.assertEqual(run.call_args.args[1], 15)

    @patch('verifygate.sandbox._execute', side_effect=subprocess.TimeoutExpired('docker', 1))
    def test_timeout(self, run):
        self.assertEqual(run_checks(self.snapshot, self.policy)[0]['status'], 'inconclusive')

    @patch('verifygate.sandbox.subprocess.run')
    @patch('verifygate.sandbox._execute')
    def test_timeout_forces_container_cleanup(self, execute, cleanup):
        def timed_out(argv, timeout):
            cidfile = Path(argv[argv.index('--cidfile') + 1])
            cidfile.write_text('a' * 64, encoding='ascii')
            raise subprocess.TimeoutExpired('docker', timeout)
        execute.side_effect = timed_out
        result = run_checks(self.snapshot, self.policy)[0]
        self.assertEqual(result['status'], 'inconclusive')
        cleanup.assert_called_once()
        self.assertEqual(cleanup.call_args.args[0], ['docker', 'rm', '-f', 'a' * 64])

    @patch('verifygate.sandbox._execute')
    def test_reports_reject_oversize_and_malicious_content(self, run):
        from verifygate.sandbox import MAX_REPORT_BYTES
        for content in (b'x' * (MAX_REPORT_BYTES + 1),
                        b'{"tests_run":2,"tests_run":2,"failures":0,"errors":0}',
                        b'{"tests_run":2,"failures":3,"errors":0}',
                        b'{"tests_run":2,"failures":0,"errors":0,"extra":1}'):
            def invoke(argv, timeout):
                mount = next(argv[i + 1] for i, arg in enumerate(argv[:-1])
                             if arg == '--mount' and 'target=/results' in argv[i + 1])
                folder = Path(mount.split('source=', 1)[1].split(',target=', 1)[0])
                (folder / 'report.json').write_bytes(content)
                return 0, '', '', False
            run.side_effect = invoke
            self.assertEqual(run_checks(self.snapshot, self.policy)[0]['status'], 'inconclusive')

    @patch('verifygate.sandbox._execute', return_value=(0, 'x' * 70000, 'err', True))
    def test_bounded_log_and_isolated_arguments(self, run):
        self.policy['checks'] = [{'id': 'cmd', 'type': 'command',
                                  'argv': ['python', '-c', 'print("; rm -rf /")']}]
        result = run_checks(self.snapshot, self.policy)[0]
        self.assertTrue(result['output_truncated'])
        self.assertLessEqual(len(result['output'].encode()), 65536)
        argv = run.call_args.args[0]
        self.assertEqual(argv[-4:], ['verifygate:test', 'python', '-c', 'print("; rm -rf /")'])
        self.assertIn('none', argv)
        self.assertNotIn('--privileged', argv)
        self.assertNotIn('sh', argv)

    def test_streaming_process_bounds_real_output(self):
        code, stdout, stderr, truncated = _execute(
            [sys.executable, '-c',
             'import sys; sys.stdout.write("a"*200000); sys.stderr.write("b"*200000)'], 10)
        self.assertEqual(code, 0)
        self.assertEqual(len(stdout), MAX_LOG_BYTES)
        self.assertEqual(len(stderr), MAX_LOG_BYTES)
        self.assertTrue(truncated)

    @patch('verifygate.sandbox._execute', return_value=(0, '', '', False))
    def test_missing_report_is_inconclusive(self, run):
        result = run_checks(self.snapshot, self.policy)[0]
        self.assertEqual(result['status'], 'inconclusive')
        self.assertIsNone(result['report_sha256'])


if __name__ == "__main__":
    unittest.main()
