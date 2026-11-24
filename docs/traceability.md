# Requirement-to-test matrix

Status legend: TESTED = observed local test; BLOCKED = environment dependency; NOT_STARTED = planned. Updated for the evidence-integrity milestone; `docs/testing.md` tracks all 20 negative cases.

| Requirement / negative case | Expected | Test/command | Current evidence |
|---|---|---|---|
| Valid claim vs fabricated tests | Assertion never overrides runner | `tests/test_core.py`, `tests/test_cli.py` | TESTED with mocks |
| Independent acceptance baseline | Required suite outside candidate; fingerprint/version recorded | `acceptance/`, `tests/test_acceptance.py`, policy/core tests | TESTED locally; real Docker BLOCKED |
| Wrong task, missing fields, injection | Fail closed | `tests/test_core.py`, `tests/test_cli.py` | TESTED |
| Snapshot fingerprint/stale changes/symlink/exclusions | Different or rejected; manifest | `tests/test_core.py`, `tests/test_cli.py` | TESTED subset |
| Syntax and stub warnings | Structured definite error vs warning | `test_snapshot_exclusions_and_static_python` | TESTED subset; no typecheck |
| Failed/unlaunchable/timeout/zero tests/malformed report | REJECTED vs INCONCLUSIVE | `tests/test_sandbox.py` | TESTED with mocks |
| Docker network, non-root, no socket/secrets, cleanup | Restricted disposable run | argv unit tests and real Docker tests | TESTED args; BLOCKED live Docker |
| Missing mandatory check/policy change | Never VERIFIED | `tests/test_cli.py` | TESTED with mocks |
| Large logs/report and report tamper | Bounded or INCONCLUSIVE | sandbox/report tests | TESTED subset |
| Ledger modification/deletion/reorder | Integrity failure for retained rows | `tests/test_audit.py` | TESTED; suffix deletion not detectable |
| Integration success despite rejection/nonblocking hook | Block supported path or disclose limitation | `tests/test_integration.py` | TESTED missing config; actual hook UNTESTED |
| Passing and broken real fixture checks | VERIFIED/REJECTED under Docker | `verifygate demo` | BLOCKED live Docker; host fixture unit tests TESTED |
| Direct report-mount forgery | No `/results` mount; fabricated report cannot pass | `test_attack_has_no_results_mount_and_cannot_forge_pass` | TESTED with fake executor; real container BLOCKED |
| Nonce/malformed/duplicate evidence | INCONCLUSIVE, never pass | `test_valid_duplicate_malformed_and_fabricated_records` | TESTED with fake executor |
| Synthetic evidence provenance | Production path rejects; pure evaluator requires explicit opt-in | `tests/test_evidence_integrity.py` | TESTED |
| Real marker-forgery candidate | INCONCLUSIVE under actual Docker | `tests/test_real_docker.py` | BLOCKED/skipped without Docker |
| Acceptance metadata in audit | ID/version/fingerprint carried with check evidence | verifier audit event fields | IMPLEMENTED; live audit under Docker BLOCKED |

The full negative-case list (1–20) is tracked in `docs/testing.md`, including explicit blocked observations.
