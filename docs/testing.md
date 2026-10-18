# Testing and negative-case register

Offline command: `make test` on Linux, or `PYTHONPATH=src python -m unittest discover -s tests -v` on this Windows host. It runs standard-library unittest; Docker is mocked in runner/orchestration tests. `uv sync --frozen --offline --extra mcp --no-dev` prepared the project environment and SDK registration tests passed against SDK 2.1.1. No live Docker engine is present.

| # | Scenario | Expected | Observed test/limit |
|---|---|---|---|
| 1 | No/invalid claim | UNVERIFIED | `test_claim_adversarial`, rejection TESTED |
| 2 | Agent claims unseen tests | Ignore assertion | `test_failure_then_pass...`, mock TESTED |
| 3 | Wrong task | Reject before runner | `test_wrong_task...` TESTED |
| 4 | Required test fails | REJECTED | `test_zero_tests_and_failure`, mocked TESTED; actual broken fixture harness failed on host, not sandbox |
| 5 | Docker command cannot launch | INCONCLUSIVE | `test_docker_unavailable` TESTED |
| 6 | Docker unavailable | INCONCLUSIVE | actual `demo` returned both INCONCLUSIVE, exit 1 |
| 7 | Timeout | INCONCLUSIVE and cleanup attempt | `test_timeout`, `test_timeout_forces_container_cleanup` TESTED with mocks |
| 8 | Zero discovered tests | REJECTED | `test_zero_tests_and_failure` TESTED |
| 9 | Shell-string input | Reject policy/claim | `test_policy_adversarial`, `test_claim_adversarial` TESTED |
| 10 | Unsafe path or symlink | Reject | `test_snapshot_exclusions_and_static_python` TESTED |
| 11 | Changed candidate | INCONCLUSIVE | `test_candidate_or_policy_change...` TESTED |
| 12 | Changed policy | INCONCLUSIVE | same test TESTED |
| 13 | Malformed/inconsistent report | INCONCLUSIVE | `test_reports_reject_oversize_and_malicious_content` TESTED with mocks |
| 14 | Oversized log/report | Bounded/inconclusive | `test_streaming_process_bounds_real_output`, report tests TESTED |
| 15 | Ledger row modified/deleted | Integrity fails for interior edits | `test_tampering`, `test_audit_chain` TESTED; suffix deletion cannot be detected |
| 16 | Adapter says success after rejection | Must not override core | MCP delegates to core, `test_tools_use_trusted_paths...` TESTED with mock; real client flow UNTESTED |
| 17 | Hook cannot block | Declare limitation | Missing-config hook/CI tests block; `--no-verify` bypass is KNOWN, not prevented |
| 18 | Docker socket/secrets access | No mount/env by design | Docker argv test TESTED; actual isolation BLOCKED |
| 19 | Cleanup fails/interruption | INCONCLUSIVE and disclose | timeout cleanup attempt TESTED; actual daemon cleanup failure UNTESTED |
| 20 | One pass, other mandatory missing | INCONCLUSIVE | `test_missing_mandatory_result...` TESTED |

Passing/broken sample `unittest` harness actually ran on host as a **fixture test only** (one pass and one failure). Host execution does not constitute sandbox verification. `demo` attempts the real runner and currently yields INCONCLUSIVE for both fixtures. Docker acceptance and protected CI status are BLOCKED/UNTESTED. A single mock test is not a security guarantee.
