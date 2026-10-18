"""Optional stdio MCP transport; trusted file locations come from host environment."""

import os
from pathlib import Path

from verifygate import audit, contracts, policy, reports
from verifygate.verifier import verify


def _path(name: str) -> Path:
    value = os.environ.get(f"VERIFYGATE_{name}")
    if not value:
        raise ValueError(f"trusted VERIFYGATE_{name} must be configured by the host")
    return Path(value).resolve()


def submit_completion_claim() -> dict:
    """Validate the configured claim against the trusted policy; do not verify it."""
    candidate, policy_path = _path("CANDIDATE"), _path("POLICY")
    rules, _ = policy.load_policy(policy_path, candidate)
    return contracts.load_claim(_path("CLAIM"), rules["task_ids"])


def request_verification() -> dict:
    """Verify the claim using only host-configured candidate, policy and output paths."""
    return verify(_path("CANDIDATE"), _path("CLAIM"), _path("POLICY"),
                  _path("LEDGER"), _path("REPORT"))


def list_runs(limit: int = 10) -> list[dict]:
    """List latest completed runs from the validated audit chain."""
    if not isinstance(limit, int) or isinstance(limit, bool) or not 0 <= limit <= 100:
        raise ValueError("limit must be an integer between 0 and 100")
    events = audit.list_events(_path("LEDGER"))
    return [record["event"] for record in events
            if record["event"].get("type") == "verification_completed"][:limit]


def get_status(run_id: str) -> dict:
    """Return the latest audited event for a run."""
    events = audit.list_events(_path("LEDGER"), run_id=run_id, limit=1)
    if not events:
        raise ValueError("run not found")
    return events[0]["event"]


def get_report(run_id: str) -> dict:
    """Read a completed run's report and match it to its audit event."""
    return reports.get_report(_path("LEDGER"), run_id)


def check_audit_integrity() -> bool:
    """Check the hash chain of the host-configured ledger."""
    return audit.verify_ledger(_path("LEDGER"))


def create_server():
    """Register the six tools; the optional SDK is imported only when needed."""
    from mcp.server import MCPServer

    server = MCPServer("verifygate")
    for tool in (submit_completion_claim, request_verification, get_status,
                 get_report, list_runs, check_audit_integrity):
        server.tool()(tool)
    return server


def main() -> None:
    """Serve JSON-RPC over stdio without writing application output to stdout."""
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
