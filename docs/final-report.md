# VerifyGate checkpoint report — 2026-10-18T19:14:51+05:30

## A. Executive summary
VerifyGate now has a strict task-bound claim contract, deterministic source snapshot and policy hashes, Python AST diagnostics, a Docker-oriented runner, evidence-gated verdicts, a SQLite hash chain and report digest, CLI, optional MCP SDK adapter, and opt-in hook/CI wrappers. The product is **not release-ready**: this Windows host has no Docker or Make, so a real isolated passing/rejected end-to-end run and Linux Docker build have not been observed. The demo correctly refuses to claim success when Docker is absent.

## B. Implemented features and evidence
| Capability | Status | Evidence |
|---|---|---|
| Claims/task policy/path validation | TESTED | contract and wrong-task negative tests |
| Snapshot manifest/fingerprint, exclusions, stale detection | TESTED subset | core and workflow tests; deletion/large tree not fully handled |
| Python syntax and stub warning adapter | TESTED subset | AST diagnostics tests, no full type/reference checker |
| Docker runner and structured unittest counts | IMPLEMENTED, mocked TESTED; live BLOCKED | runner tests for argv, timeout, bounds, malformed reports |
| Mandatory verdict and report integrity | TESTED with mocks | failure/missing evidence/stale policy/report tamper tests |
| SQLite audit | TESTED for retained rows | chain/transaction/tamper tests; no external checkpoint |
| CLI and MCP transport | CLI TESTED; MCP registration TESTED | CLI help/policy/status/report tests, SDK 2.1.1 registration; no live client handshake |
| Hook and CI examples | missing-config fail-closed TESTED | no installed hook, actual commit block or protected CI test |

## C. Architecture delivered
`cli.py` / `mcp_server.py` call `verifier.verify`. Contracts and trusted policy validate inputs, `snapshots` freezes regular files, Python AST adapter inspects without executing, `sandbox` uses policy argv in constrained disposable Docker containers, `policy.decide` requires mandatory evidence with matching hashes, `audit` appends SQLite events, and `reports` checks a digest bound to the final event. MCP cannot intercept other tools. `docs/architecture.md` and `docs/threat-model.md` detail boundaries.

## D. Actual test report
- `PYTHONPATH=src python -m unittest discover -s tests -v` — exit 0, **31 tests OK** (mocked Docker boundary; fixture harness exercises one passing and one failing candidate on host as test fixtures only).
- `uv run --frozen --offline --extra mcp python -m unittest discover -s tests -v` — exit 0, **31 tests OK** in project-local environment.
- `uv sync --frozen --offline --extra mcp --no-dev` — exit 0, checked 30 packages.
- `uv build --offline` — exit 0, wheel and sdist built; **not** a Docker build.
- `PYTHONPATH=src python -m verifygate.cli policy-validate --candidate examples/passing --policy policies/python.json` — exit 0, valid policy digest `ff3dcfff84bb5b4128667027768eb60bf93b2bb8f85ce69c02ac302bd4df54a6`.
- `make test` — could not launch (`make` absent). `docker --version` — could not launch (`docker` absent); Dockerfile build and live isolation acceptance BLOCKED.
- `git diff --check` — exit 0 before commit; no whitespace errors. Working tree clean after `e473cae` before this report.

## E. Demonstration results (actual observed, not simulated)
`PYTHONPATH=src python -m verifygate.cli demo --ledger <temporary-audit.sqlite> --output-dir <temporary-directory>` exited **1**. The actual Docker runner was attempted; Docker was missing, so neither candidate was verified:

```json
{
  "execution": "actual Docker runner; never simulated",
  "runs": {
    "broken": {"verdict": "INCONCLUSIVE", "run_id": "a577b959959f4f87b1fd0cc47dab73fa", "artifact_hash": "19e93c7c95f53aa320cc61af4a14ad1ea91250f42ce3cd203300d3c4fde9ac09"},
    "passing": {"verdict": "INCONCLUSIVE", "run_id": "d7643ad94e374389916176fe69f7d8a4", "artifact_hash": "1b9fcd04c4d3d5c4f487b7defc02330c34f891dcf94a427a560deb754ea40642"}
  }
}
```

`audit-verify` on that temporary database printed `VALID`, exit 0. **No actual successful Docker verification output exists to show.** In a separate explicitly mocked orchestration test, broken returned `REJECTED` and passing `VERIFIED`; those are simulated runner results, not sandbox evidence.

## F. Security assessment
Tested in unit scenarios: task/path rejection, symlink exclusion, frozen-hash mismatch, policy change, mandatory evidence, zero tests, malformed/oversized reports, bounded log capture, timeout cleanup attempt, Docker option construction, audit tamper and report tamper. Untested against a real daemon: network isolation, credential/socket absence, resource limits and cleanup. Critical residual issue: candidate test code can write its own report mount; report hash proves what was collected, not that a malicious test did not forge it. Docker is not a hostile-code security boundary. Image tag is mutable, raw retained logs can expose secrets, and local audit suffix deletion is undetectable without external anchoring. Require protected policy/image, trusted job and branch protection for merge enforcement; hooks and MCP are voluntary paths.

## G. File changes
No user source files were removed. Existing `src/verifygate/{contracts,policy,snapshots,sandbox,test_harness,audit,cli}.py`, policy, Dockerfile and tests were revised. Added `verifier.py`, `reports.py`, `syntax_check.py`, Python analyzer, `mcp_server.py`, `pyproject.toml`, `uv.lock`, `.dockerignore`, hook/CI shell wrappers, audit/integration/MCP tests, and project records and docs. The previous JSONL implementation was replaced in the same `audit.py`; historical JSONL files are not migrated. `README.md` was replaced to describe the current CLI and honest constraints. Build artifacts in ignored `dist/` are not committed.

## H. Progress assessment
Phases 0–2 local acceptance TESTED; phases 3–4 core subset TESTED but language/reference and deletion handling incomplete; phase 5 IMPLEMENTED and mock TESTED, live Docker BLOCKED; phases 6–7 TESTED with reported tamper limitations; phase 8 CLI TESTED but successful Docker demo BLOCKED; phase 9 SDK registration and fail-closed script configuration TESTED, live integration UNTESTED; phase 10 review documented, release criteria NOT MET. `PROJECT_STATUS.md` is authoritative; `docs/traceability.md` and `docs/testing.md` map requirements and negative cases.

## I. Known limitations
See `docs/limitations.md`. In particular: no real sandbox success, no true type/reference checker, no report forgery resistance against a malicious candidate, no external audit anchor, no protected CI deployment, and no real MCP client handshake. Avoid interpreting mock `VERIFIED` as a product verdict.

## J. How to run
On clean Linux with Python 3.12.7, Make and Docker: `make test`, `docker build -t verifygate:local .`, `mkdir -p .verifygate`, then `PYTHONPATH=src python -m verifygate.cli demo --ledger .verifygate/audit.sqlite --output-dir .verifygate`. For a single candidate use the `verify` command in `README.md`. Optional MCP: `uv sync --frozen --extra mcp --no-dev`, set trusted `VERIFYGATE_*` paths, then `uv run --frozen --offline verifygate-mcp`. Hook/CI examples require explicit trusted setup; none are auto-installed.

## K. Next recommended task
On a clean Linux host with an authorized Docker daemon, build the trusted image and run `make test` plus the real passing/broken demo. Record the actual exit codes and report hashes. Before claiming high-assurance adversarial verification, redesign test-count collection so candidate code cannot forge its own report.
