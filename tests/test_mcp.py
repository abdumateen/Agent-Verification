"""MCP transport tests also run without the optional SDK installed."""

import importlib.util
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from verifygate import audit
from verifygate import mcp_server


class AdapterTests(unittest.TestCase):
    def test_tools_use_trusted_paths_and_validate_without_verifying(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = root / "candidate"
            candidate.mkdir()
            claim = root / "claim.json"
            claim.write_text(json.dumps({"task_id": "task-1", "status": "done",
                                         "summary": "complete", "changed_files": [],
                                         "tests_run": []}), encoding="utf-8")
            policy_file = root / "policy.json"
            ledger = root / "events.sqlite"
            report = root / "report.json"
            values = {"VERIFYGATE_CANDIDATE": str(candidate), "VERIFYGATE_CLAIM": str(claim),
                      "VERIFYGATE_POLICY": str(policy_file), "VERIFYGATE_LEDGER": str(ledger),
                      "VERIFYGATE_REPORT": str(report)}
            with patch.dict(os.environ, values), patch.object(mcp_server.policy, "load_policy", return_value=({"task_ids": ["task-1"]}, "hash")), patch.object(mcp_server, "verify", return_value={"verdict": "INCONCLUSIVE"}) as verifier:
                self.assertEqual(mcp_server.submit_completion_claim()["task_id"], "task-1")
                verifier.assert_not_called()
                self.assertEqual(mcp_server.request_verification()["verdict"], "INCONCLUSIVE")
                verifier.assert_called_once_with(candidate, claim, policy_file, ledger, report)

    def test_audit_reads(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "events.sqlite"
            report = Path(directory) / "report.json"
            with patch.dict(os.environ, {"VERIFYGATE_LEDGER": str(ledger)}):
                self.assertFalse(mcp_server.check_audit_integrity())
                self.assertEqual(mcp_server.list_runs(), [])
                unsigned = {"run_id": "run-1"}
                digest = hashlib.sha256(json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
                event = audit.append_event(ledger, {"type": "verification_completed", "run_id": "run-1", "report_path": str(report), "report_sha256": digest})
                report.write_text(json.dumps({**unsigned, "audit_hash": event["hash"]}), encoding="utf-8")
                self.assertTrue(mcp_server.check_audit_integrity())
                self.assertEqual(mcp_server.get_status("run-1")["type"], "verification_completed")
                self.assertEqual(mcp_server.get_report("run-1")["audit_hash"], event["hash"])
                self.assertEqual(len(mcp_server.list_runs()), 1)
                report.write_text(json.dumps({**unsigned, "verdict": "VERIFIED", "audit_hash": event["hash"]}), encoding="utf-8")
                with self.assertRaises(ValueError):
                    mcp_server.get_report("run-1")

    @unittest.skipUnless(importlib.util.find_spec("mcp"), "optional MCP SDK unavailable")
    def test_real_sdk_registration(self):
        server = mcp_server.create_server()
        self.assertEqual({tool.name for tool in server._tool_manager.list_tools()}, {
            "submit_completion_claim", "request_verification", "get_status",
            "get_report", "list_runs", "check_audit_integrity"})


if __name__ == "__main__":
    unittest.main()
