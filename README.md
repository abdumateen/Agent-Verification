# VerifyGate — Independent Agent Verification Gate

An agent's completion claim requests a check; it is **not proof**. VerifyGate snapshots a Python candidate, binds it to an administrator-controlled JSON policy, runs mandatory checks in disposable Docker containers, evaluates observed evidence, and records a hash-linked SQLite decision. `VERIFIED` means only that the configured checks passed on that artifact and policy. This is an engineering MVP, not a hostile-code sandbox or bypass-proof merger.

## Setup (clean Linux)

1. Install Python **3.12.7**, GNU Make, Docker Engine, and permission for the **trusted verifier process** to access Docker. Do not give Docker access to candidate jobs. Docker is needed for actual verification, not for offline unit tests.
2. Clone this repository. `make test` runs the standard-library suite without network or Docker. `.python-version` pins Python; `pyproject.toml` and `uv.lock` pin the optional MCP SDK. `requirements.lock` records that the core itself has no third-party packages. If using MCP, install project-local dependencies with `uv sync --frozen --extra mcp --no-dev` (uv must be available); do not install globally.
3. From the trusted checkout run `docker build -t verifygate:local .`. The Dockerfile pins the Python and uv version tags, installs locked packages into `/opt/app/.venv`, and runs tests. **This build has not been executed on this Windows host** (Docker is absent). Offline Docker builds require the base images and locked package artifacts preloaded.
4. Run CLI from the checkout: `PYTHONPATH=src python -m verifygate.cli --help` or, in a project venv, `uv run --frozen --offline python -m verifygate.cli --help`. On Windows without GNU Make, use `PYTHONPATH=src python -m unittest discover -s tests -v` from Git Bash.

## Demo and CLI

```sh
mkdir -p .verifygate
PYTHONPATH=src python -m verifygate.cli version
PYTHONPATH=src python -m verifygate.cli policy-validate --candidate examples/passing --policy policies/python.json
PYTHONPATH=src python -m verifygate.cli demo --ledger .verifygate/audit.sqlite --output-dir .verifygate
PYTHONPATH=src python -m verifygate.cli status --ledger .verifygate/audit.sqlite
PYTHONPATH=src python -m verifygate.cli audit-verify --ledger .verifygate/audit.sqlite
```

`demo` invokes the **actual Docker runner** for broken then passing fixture; it never substitutes fake evidence. With Docker absent both runs are `INCONCLUSIVE`, and demo exits 1. With the trusted `verifygate:local` image built and Docker working, the intended outcome is broken `REJECTED` and passing `VERIFIED` (not yet observed on this host). The `tests_run` field in `examples/claim.json` is never evidence.

One candidate at a time:

```sh
PYTHONPATH=src python -m verifygate.cli verify \
  --candidate examples/broken --claim examples/claim.json \
  --policy policies/python.json --ledger .verifygate/audit.sqlite \
  --report .verifygate/broken.report.json
```

Exit 0 = `VERIFIED`; exit 1 = `REJECTED`, `INCONCLUSIVE`, or `NEEDS_REVIEW`; exit 2 = invalid input or failed report storage (`UNVERIFIED`). `status`, `report --run-id ID`, and `audit-verify` read recorded runs. Output files and policy must be outside the candidate. A claim's task ID must occur in the trusted policy's `task_ids` list. The policy image tag is administrator-controlled but mutable; use a trusted build and protected CI settings, not an agent-provided image. Reports are bounded and their content hash is tied to the audit event.

## Integrations and deployment

- Optional MCP: `uv sync --frozen --extra mcp --no-dev`, then configure a trusted host with `VERIFYGATE_CANDIDATE`, `VERIFYGATE_CLAIM`, `VERIFYGATE_POLICY`, `VERIFYGATE_LEDGER`, and `VERIFYGATE_REPORT` paths **outside candidate control**. Start `uv run --frozen --offline verifygate-mcp`. The stdio SDK exposes six tools; MCP cannot itself block other agent tools. See `docs/architecture.md`.
- Opt-in Git sample hook: copy `hooks/pre-commit` into a **trusted hooks directory**, provide `VERIFYGATE_HOME` (trusted verifier checkout), `VERIFYGATE_CLAIM`, `VERIFYGATE_POLICY`, `VERIFYGATE_LEDGER`, `VERIFYGATE_REPORT`, and configure the target repo's hook path yourself. The hook exits nonzero on rejected or inconclusive verification; Git hooks can be bypassed with `--no-verify` and are not a strong boundary. No hook installation is automatic.
- CI-ready wrapper: set the same trusted variables plus `VERIFYGATE_CANDIDATE` in a protected verifier job and execute `sh scripts/ci-gate.sh`. Build the image and load policy from protected sources, then require the CI status on the branch. The repository does **not** configure branch protection or cloud CI. Do not run a candidate Dockerfile or give candidate code the Docker socket.

## Tests, security and limits

`make test` is the single offline Linux test command. Tests mock the Docker boundary; no live Docker check/build was possible on this Windows host. Python AST parsing is a deterministic syntax check; optional stub warnings do not prove semantic correctness. The runner no longer exposes a writable report mount: the trusted harness emits one nonce-bound record to stdout, and the supervisor validates it against exit status and the complete channel. Candidate tests remain untrusted, can alter their own test suite, and may inspect the visible nonce or attempt direct stdout injection; extra control bytes fail closed. The sample policy also requires a separately stored, fingerprinted acceptance suite under `acceptance/`; candidate tests cannot change its files or selection through the candidate workspace. That baseline is stronger evidence, not a mathematical correctness proof. Command output may contain secrets; use test credentials only, restrict access to reports, and review output before publishing. A local SQLite hash chain detects retained-row modification/reordering, not deletion of its tail without external anchoring. See `docs/testing.md`, `docs/threat-model.md`, `docs/security.md`, and `docs/limitations.md` for precise evidence and unresolved work.
