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
| 13 | Malformed/inconsistent/duplicate nonce record | INCONCLUSIVE | `test_valid_duplicate_malformed_and_fabricated_records` TESTED with mocks |
| 14 | Oversized log/report | Bounded/inconclusive | `test_streaming_process_bounds_real_output`, report tests TESTED |
| 15 | Ledger row modified/deleted | Integrity fails for interior edits | `test_tampering`, `test_audit_chain` TESTED; suffix deletion cannot be detected |
| 16 | Adapter says success after rejection | Must not override core | MCP delegates to core, `test_tools_use_trusted_paths...` TESTED with mock; real client flow UNTESTED |
| 17 | Hook cannot block | Declare limitation | Missing-config hook/CI tests block; `--no-verify` bypass is KNOWN, not prevented |
| 18 | Docker socket/secrets/trusted evidence access | No socket/ledger/report/policy mount by design | `test_attack_has_no_results_mount_and_cannot_forge_pass` and argv tests TESTED; actual isolation BLOCKED |
| 19 | Cleanup fails/interruption | INCONCLUSIVE and disclose | timeout cleanup and evidence-workspace cleanup-failure tests TESTED; actual daemon cleanup failure UNTESTED |
| 20 | One pass, other mandatory missing | INCONCLUSIVE | `test_missing_mandatory_result...` TESTED |
| E01/E02 | Candidate prints or discovers nonce and emits a fake record | Never accept candidate record as trusted | `tests/test_protocol.py`, sandbox fake-executor tests TESTED on host; real Docker BLOCKED |
| E03/E04/E05 | Duplicate, missing, malformed, or exit-inconsistent record | INCONCLUSIVE | `tests/test_sandbox.py` TESTED with synthetic executor |
| E06/E08/E18 | Candidate tests change while trusted acceptance suite remains fixed; trusted failure overrides candidate pass | Baseline fingerprint unchanged; REJECTED/INCONCLUSIVE | `tests/test_acceptance.py` TESTED; real Docker BLOCKED |
| E19/E20 | Candidate cannot write trusted storage; evidence cannot move to another run/task | No trusted mount; hash/task binding | unit/integration tests TESTED; real Docker BLOCKED |

Passing/broken sample `unittest` harness actually ran on host as a **fixture test only** (one pass and one failure). Host execution does not constitute sandbox verification. `demo` attempts the real runner and currently yields INCONCLUSIVE for both fixtures. The opt-in `tests/test_real_docker.py` covers real passing/broken fixtures and a candidate nonce-marker forgery, but is skipped here because Docker is unavailable. Docker acceptance and protected CI status are BLOCKED/UNTESTED. A single mock test is not a security guarantee.

The `acceptance/` suite is independently maintained outside candidate fixture directories, and its content fingerprint is included in the trusted policy hash. The acceptance tests import candidate implementation code but not candidate test files. A candidate can still make an independently written assertion pass through a malicious implementation; the baseline protects the assertion source and required selection, not all semantic intent.
