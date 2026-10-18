# Requirement-to-test matrix

Status legend: TESTED = observed local test; BLOCKED = environment dependency; NOT_STARTED = planned. Updated after the 31-test regression run; `docs/testing.md` tracks all 20 negative cases.

| Requirement / negative case | Expected | Test/command | Current evidence |
|---|---|---|---|
| Valid claim vs fabricated tests | Assertion never overrides runner | `tests/test_core.py`, `tests/test_cli.py` | TESTED with mocks |
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

The full negative-case list (1–20) is tracked in `docs/testing.md`, including explicit blocked observations.
