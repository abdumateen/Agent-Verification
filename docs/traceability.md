# Requirement-to-test matrix (initial)

Status legend: TESTED = observed local test; BLOCKED = environment dependency; NOT_STARTED = planned. Tests must be re-evaluated after changes.

| Requirement / negative case | Expected | Test/command | Current evidence |
|---|---|---|---|
| Valid claim vs fabricated tests | Assertion never overrides runner | `tests/test_core.py`, `tests/test_cli.py` | TESTED with mocks |
| Wrong task, missing fields, injection | Fail closed | Additional contract tests | NOT_STARTED |
| Snapshot fingerprint/stale changes/symlink/exclusions | Different or rejected; manifest | `tests/test_core.py`; extended tests | Partial TESTED |
| Syntax and stub warnings | Structured definite error vs warning | Adapter tests | NOT_STARTED |
| Failed/unlaunchable/timeout/zero tests/malformed report | REJECTED vs INCONCLUSIVE | `tests/test_sandbox.py`; extended tests | Partial TESTED with mocks |
| Docker network, non-root, no socket/secrets, cleanup | Restricted disposable run | argv unit tests and real Docker tests | BLOCKED live Docker |
| Missing mandatory check/policy change | Never VERIFIED | policy and workflow tests | Partial TESTED |
| Large logs/report and report tamper | Bounded or INCONCLUSIVE | runner negative tests | NOT_STARTED |
| Ledger modification/deletion/reorder | Integrity failure where anchored length known | SQLite ledger tests | NOT_STARTED |
| Integration success despite rejection/nonblocking hook | Block supported path or disclose limitation | wrapper tests | NOT_STARTED |
| Passing and broken real fixture checks | VERIFIED/REJECTED under Docker | `verifygate demo` | BLOCKED live Docker; host fixture unit tests TESTED |

The full negative-case list (1–20) will be tracked in `docs/testing.md`, including explicit blocked observations.
