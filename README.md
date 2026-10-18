# Independent Agent Verification Gate (Python MVP)

A completion **claim** triggers independent checks; it never counts as evidence. The CLI snapshots a candidate, runs policy-controlled commands in disposable Docker containers, and returns `VERIFIED`, `REJECTED`, `INCONCLUSIVE`, or `NEEDS_REVIEW` with a snapshot and policy hash. Only `VERIFIED` exits 0. This MVP is a local workflow gate, **not** a bypass-proof security boundary.

## Requirements and setup

- Linux: Python **3.12.7** (see `.python-version`), GNU Make and Docker Engine with permission to run containers. Docker is required for actual verification, but not for offline tests.
- There are no Python packages to download: `requirements.lock` documents the standard-library-only dependency set. Do not install global packages.
- From a clean checkout, run `make test` (offline), then `docker build -t verifygate:local .` to prepare the trusted runner image. The Dockerfile contains the verifier and its Python runtime and runs the tests at build time. For fully air-gapped builds, preload `python:3.12.7-slim` in Docker's local image store first; Docker will not download it if present.
- The host-side CLI runs with `PYTHONPATH=src python -m verifygate.cli --help`. No `.env` file or credentials are needed. `.env.example` is a placeholder for future optional integrations.

## Run the demo

The policy is in `policies/python.json`, **outside both candidate trees**. Keep trusted policies in a protected location that the candidate agent cannot change. The claim's `tests_run` is informational, not evidence.

```sh
mkdir -p .verifygate
PYTHONPATH=src python -m verifygate.cli verify \
  --candidate examples/broken --claim examples/claim.json \
  --policy policies/python.json --ledger .verifygate/audit.jsonl \
  --report .verifygate/broken.report.json
# exit 1: REJECTED; a real assertion failure appears in the report

PYTHONPATH=src python -m verifygate.cli verify \
  --candidate examples/passing --claim examples/claim.json \
  --policy policies/python.json --ledger .verifygate/audit.jsonl \
  --report .verifygate/passing.report.json
# exit 0: VERIFIED on a different artifact hash

PYTHONPATH=src python -m verifygate.cli audit-verify --ledger .verifygate/audit.jsonl
# VALID / exit 0, or INVALID / exit 1 after alteration
```

When Docker is unavailable or a check times out, verification returns `INCONCLUSIVE` and exits 1. Malformed input or an untrusted policy path exits 2 as `UNVERIFIED`. The CLI requires the report and ledger outside the candidate tree; use separate storage with an existing parent directory. If the candidate changes while checking, the previous verdict cannot be reused for the changed workspace.

## Test and deploy

`make test` is the single offline test command. It runs 10 standard-library unit/integration tests, including real execution of the passing and broken sample suites; the Docker boundary is mocked because the host may have no Docker daemon. On Windows without `make`, run `PYTHONPATH=src python -m unittest discover -s tests -v` in a Bash shell.

To deploy as a required CI check, build the trusted runner image outside the unreviewed candidate branch, store the policy in a protected branch or administrator-controlled location, and invoke `verifygate verify` with a CI-produced claim and candidate checkout. Require the resulting CI status on the protected branch. Do not grant a candidate job a Docker socket or privileged Docker access; the **trusted verifier job** alone needs access to its container service. This repository does not provision branch protection or ship an agent lifecycle hook; a local CLI alone cannot stop an agent that uses another path.

## Evidence and limits

The policy's `syntax` check parses Python files without writing to the read-only source; `unit-tests` uses a trusted `unittest` harness and requires at least one discovered test. Each run records the claim, artifact hash, policy hash, actual command, exit code and test count. The JSONL ledger chains event hashes; `audit-verify` detects modification or reordering of retained entries, **not** truncation or a fully rewritten chain without an external checkpoint. The report contains command output for useful diagnostics; do not run tests with secrets or publish unreviewed reports. A `VERIFIED` verdict means the configured checks passed, not that all product requirements are correct. Docker restrictions (non-root, no network, read-only candidate, dropped capabilities, CPU/memory/PID/time limits) reduce risk but are not sufficient isolation for hostile code; use microVMs or a hardened remote service in that setting. The test-report directory is writable by the test process, so a malicious candidate can tamper with local reports; the current MVP is for cooperative or moderately untrusted agent mistakes, not an adversarial proof system.
