# VerifyGate project plan

## Objective and acceptance
Turn an agent's completion claim into a decision bound to a frozen source snapshot and independently controlled policy. `VERIFIED` means only that all mandatory configured checks produced acceptable observed evidence, the artifact and policy matched, and the result was recorded. Never use a candidate's assertion as evidence.

## Functional requirements
Strict claim/task contract; trusted policy validation; deterministic source manifest and fingerprint; Python syntax diagnostics and optional stub warnings; isolated Docker checks; machine-readable unittest counts; deterministic verdicts; SQLite hash-linked events; CLI status/report/audit/demo; one documented blocking wrapper and a CI-ready exit status. MCP is an invocation adapter, not an enforcement boundary.

## Nonfunctional and security requirements
Fail closed on missing evidence; no host execution of candidate checks; no shell strings; no candidate Docker socket, credentials or policy control; network off, non-root, bounded resources; limit output retention; immutable-by-convention snapshots and tamper-evident (not immutable) local ledger; clean Linux rebuild with pinned Python and dependency lock; offline unit tests via `make test`.

## Architecture
CLI and optional adapters → shared verification orchestration → claim/policy contracts → snapshot and Python analyzer → Docker runner and structured report collector → pure policy evaluator → SQLite event chain and report reader. Only the trusted host verifier invokes Docker; unreviewed source is read-only in the container. See `docs/architecture.md` as implemented.

## Phases and exit criteria
| Phase | Deliverable | Exit evidence |
|---|---|---|
| 0 | Repository audit, records, traceability | Baseline tests and environment recorded |
| 1–2 | Packaging, CLI, contracts/policy | Imports/help, invalid inputs rejected |
| 3–4 | Snapshot manifest, Python adapter | Fingerprint, exclusions, syntax and warning tests |
| 5–6 | Docker runner, evidence, evaluator | Unit/negative checks; live Docker only if available |
| 7–8 | SQLite ledger, reports, demo | Tamper and CLI workflow tests |
| 9 | Documented integration and MCP if verified SDK feasible | Actual adapter protocol tests; no bypass claims |
| 10 | Security/regression review | Final report with blocked/untested items |

## Technical risks and scope
Docker is unavailable on this Windows host; actual sandbox execution/build is BLOCKED. A writable result mount can be manipulated by malicious test code. Docker is not a hostile-code security boundary. Local hash chains cannot prove no truncation without external anchoring. CI branch protection cannot be configured from a local repo. No dashboard, remote multi-tenancy, universal semantic hallucination detector, or implicit host installs.
