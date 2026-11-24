# VerifyGate checkpoint report — 2026-10-21

## A. Executive summary
VerifyGate now removes the directly writable report mount that allowed fabricated counts. The trusted harness emits a nonce-bound result on stdout; the supervisor validates it against the observed exit code, hashes the canonical record, and records explicit provenance. The product is **not release-ready**: this Windows host has no Docker or Make, so a real isolated passing/rejected end-to-end run and Linux Docker build have not been observed. The demo correctly refuses to claim success when Docker is absent.

## B. Implemented features and evidence
| Capability | Status | Evidence |
|---|---|---|
| Claims/task policy/path validation | TESTED | contract and wrong-task negative tests |
| Independent acceptance baseline | IMPLEMENTED, locally TESTED; live BLOCKED | `acceptance/`, policy fingerprint/version, read-only acceptance check |
| Snapshot manifest/fingerprint, exclusions, stale detection | TESTED subset | core and workflow tests; deletion/large tree not fully handled |
| Python syntax and stub warning adapter | TESTED subset | AST diagnostics tests, no full type/reference checker |
| Docker runner and structured unittest counts | IMPLEMENTED, mocked TESTED; live BLOCKED | runner tests for argv, timeout, bounds, nonce/malformed records |
| Report-forgery mitigation | TESTED with fake executor; live BLOCKED | no `/results` mount, direct forgery regression, real marker test skipped |
| Mandatory verdict and report integrity | TESTED with mocks | provenance, failure/missing evidence/stale artifact/report tamper tests |
| SQLite audit | TESTED for retained rows | chain/transaction/tamper tests; no external checkpoint |
| CLI and MCP transport | CLI TESTED; MCP registration TESTED | CLI help/policy/status/report tests, SDK 2.1.1 registration; no live client handshake |
| Hook and CI examples | missing-config fail-closed TESTED | no installed hook, actual commit block or protected CI test |

## C. Architecture delivered
`cli.py` / `mcp_server.py` call `verifier.verify`. Contracts and trusted policy validate inputs, `snapshots` freezes regular files, Python AST adapter inspects without executing, `sandbox` uses policy argv in constrained disposable Docker containers, `policy.decide` requires mandatory evidence with matching hashes, `audit` appends SQLite events, and `reports` checks a digest bound to the final event. MCP cannot intercept other tools. `docs/architecture.md` and `docs/threat-model.md` detail boundaries.

## D. Actual test report
- `PYTHONPATH=src python -m unittest discover -s tests -v` — exit 0, **48 tests OK, 2 explicit skips** (mocked/host protocol boundary; fixture harness exercises one passing and one failing candidate on host as test fixtures only).
- `uv run --frozen --offline --extra mcp python -m unittest discover -s tests -v` — exit 0, **48 tests OK, 2 explicit skips** in the project-local environment.
- `uv run python -m pytest -q` — exit 1: `No module named pytest`; pytest is not declared/installed, and no dependency or global installation was added.
- `uv build --offline` — exit 0, wheel and sdist built after the mitigation.
- `PYTHONPATH=src python -m verifygate.cli audit-verify --ledger <milestone-ledger>` — `VALID`, exit 0. Policy validation — `valid`, exit 0.
- `PYTHONPATH=src python -m unittest discover -s tests -p test_real_docker.py -v` — exit 0 with 2 explicit skips; `sh scripts/real-docker-acceptance.sh` — blocked at `docker: command not found` before build.
- `uv sync --frozen --offline --extra mcp --no-dev` — exit 0, checked 30 packages.
- `PYTHONPATH=src python -m verifygate.cli policy-validate --candidate examples/passing --policy policies/python.json` — exit 0, valid policy digest `6780c9ce4463d0307b0797c8703c8f4f66f28f453d2c136c978fabd842abea70`.
- `make test` — could not launch (`make` absent). `docker --version` — could not launch (`docker` absent); Dockerfile build and live isolation acceptance BLOCKED.
- `git diff --check` — exit 0; no whitespace errors. This milestone intentionally has uncommitted changes per instruction.

## E. Demonstration results (actual observed, not simulated)
`PYTHONPATH=src python -m verifygate.cli demo --ledger <temporary-audit.sqlite> --output-dir <temporary-directory>` exited **1**. The actual Docker runner was attempted; Docker was missing, so neither candidate was verified:

```json
{
  "execution": "actual Docker runner; never simulated",
  "runs": {
    "broken": {"verdict": "INCONCLUSIVE", "run_id": "6144e641958f409c9a6985cf69c69a89", "artifact_hash": "19e93c7c95f53aa320cc61af4a14ad1ea91250f42ce3cd203300d3c4fde9ac09"},
    "passing": {"verdict": "INCONCLUSIVE", "run_id": "f9c4bc7ead0846658d5d0bf48b490f01", "artifact_hash": "1b9fcd04c4d3d5c4f487b7defc02330c34f891dcf94a427a560deb754ea40642"}
  }
}
```

`audit-verify` on that temporary database printed `VALID`, exit 0. **No actual successful Docker verification output exists to show.** In a separate explicitly mocked orchestration test, broken returned `REJECTED` and passing `VERIFIED`; those are simulated runner results, not sandbox evidence.

## F. Security assessment
Tested in unit scenarios: task/path rejection, symlink exclusion, frozen-hash mismatch, policy change, mandatory evidence, zero tests, malformed/oversized/duplicate nonce records, bounded log capture, timeout cleanup attempt, Docker option construction, absence of `/results`, provenance gating, independent acceptance-suite fingerprinting, candidate-test independence, audit tamper and report tamper. The direct writable evidence-mount flaw is fixed at the documented boundary. The trusted acceptance suite is outside candidate fixture directories, fingerprinted into the policy hash, mounted read-only, and required by the sample policy. Untested against a real daemon: network isolation, credential/socket absence, resource limits and cleanup. Residual issue: candidate test code remains in-process with the harness and can inspect the visible nonce or attempt direct stdout injection; duplicate/extra records fail closed, but this is not cryptographic proof. The trusted suite asserts behavior against candidate implementation code; it is not a complete semantic proof. Docker is not a hostile-code security boundary. Image tag is mutable, raw retained logs can expose secrets, and local audit suffix deletion is undetectable without external anchoring.

## G. File changes
No user source files were removed. Existing `src/verifygate/{contracts,policy,snapshots,sandbox,test_harness,audit,cli}.py`, policy, Dockerfile and tests were revised. Added `verifier.py`, `reports.py`, `syntax_check.py`, Python analyzer, `mcp_server.py`, `pyproject.toml`, `uv.lock`, `.dockerignore`, hook/CI shell wrappers, audit/integration/MCP tests, and project records and docs. The previous JSONL implementation was replaced in the same `audit.py`; historical JSONL files are not migrated. `README.md` was replaced to describe the current CLI and honest constraints. Build artifacts in ignored `dist/` are not committed.

## H. Progress assessment
Phases 0–2 local acceptance TESTED; phases 3–4 core subset TESTED but language/reference and deletion handling incomplete; phase 5 IMPLEMENTED and mock TESTED, live Docker BLOCKED; phases 6–7 TESTED with reported tamper limitations; phase 8 CLI TESTED but successful Docker demo BLOCKED; phase 9 SDK registration and fail-closed script configuration TESTED, live integration UNTESTED; phase 10 review documented, release criteria NOT MET. `PROJECT_STATUS.md` is authoritative; `docs/traceability.md` and `docs/testing.md` map requirements and negative cases.

## I. Known limitations
See `docs/limitations.md`. In particular: no real sandbox success, no protected CI deployment, no true type/reference checker, no external audit anchor, and no real MCP client handshake. Avoid interpreting mock `VERIFIED` as a product verdict.

## J. How to run
On clean Linux with Python 3.12.7, Make and Docker: `make test`, `docker build -t verifygate:local .`, `mkdir -p .verifygate`, then `PYTHONPATH=src python -m verifygate.cli demo --ledger .verifygate/audit.sqlite --output-dir .verifygate`. For a single candidate use the `verify` command in `README.md`. Optional MCP: `uv sync --frozen --extra mcp --no-dev`, set trusted `VERIFYGATE_*` paths, then `uv run --frozen --offline verifygate-mcp`. Hook/CI examples require explicit trusted setup; none are auto-installed.

## K. Next recommended task
Run `scripts/real-docker-acceptance.sh` on a clean Linux host with an authorized Docker daemon. Record actual passing/broken/forgery results. Before high-assurance use, strengthen isolation around test-result collection and consider a separate acceptance-test package/image with stronger provenance.
