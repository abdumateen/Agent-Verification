# Engineering decisions

## D-001 — Preserve the existing Python standard-library core
Alternatives: replace with Pydantic/Typer/pytest immediately, or incrementally harden current modules. Select incremental hardening: no dependency/API uncertainty and existing tests remain offline. Trade-off: hand-written strict validation needs more negative tests. Security: no implicit package install or changes to user's machine.

## D-002 — Treat Docker absence as INCONCLUSIVE
Alternatives: run candidate code on host, silently simulate, or block live verification. Select blocking live verification while allowing explicit mocks for orchestration tests. Security: no host fallback can issue VERIFIED. Linux Docker acceptance stays BLOCKED on this machine.

## D-003 — Policy must be outside candidate and version/fingerprint bound
Alternatives: candidate `.verifygate.yml` or trusted path supplied by verifier. Select trusted external path and digest; CI must protect that path independently. Security: path separation alone does not authorize who may modify the external file; deployment ownership remains essential.

## D-004 — SQLite hash chain is tamper-evident, not immutable
Alternatives: existing JSONL ledger, SQLite, remote transparency log. Select SQLite transactional events with hash links and local integrity validation. A privileged operator can rewrite/truncate/recompute all records; external signed checkpoints are deferred.

## D-005 — Keep optional MCP project-scoped
Alternatives: manual JSON-RPC, globally installed SDK, or official SDK optional extra. Select official `mcp==2.1.1` via `uv.lock` and host-configured paths. Official build-server docs were consulted; stdio API registration was tested locally. Trade-off: no live client handshake; MCP can request verification but cannot enforce other agent actions.

## D-006 — Run trusted Python harness scripts with `-I`
Alternatives: `python -m verifygate...` from candidate cwd or absolute trusted scripts with isolated startup. Select latter to prevent a candidate `verifygate` package from shadowing the trusted harness. The harness adds candidate cwd only after trusted imports to discover tests. Candidate tests still run in Docker, not on host.

## D-007 — Report digest in audited event
Alternatives: rely on report run ID/hash alone or bind full report content. Select SHA-256 of canonical result without the circular audit hash, stored in the SQLite event. The report reader recomputes and checks it. Local ledger truncation/rewrite remains possible without an external anchor.

## D-008 — Remove the candidate-writable report mount
Problem: the old unittest runner mounted a `0777` host temp directory at `/results`; candidate tests could fabricate `report.json` and obtain passing counts. Select no evidence-directory mount. The trusted harness emits one nonce-delimited count record on stdout; the supervisor validates exactly one record, checks it against the observed exit code, and hashes the canonical record. Trade-off: stdout is still an untrusted process channel and a malicious in-process test can attempt a targeted nonce spoof; duplicate records fail closed. A trusted acceptance-test baseline remains future work.

## D-009 — Explicit evidence provenance
Production verification requires `provenance=live_docker`, trusted harness stdout provenance, matching artifact/policy hashes, and complete mandatory evidence. Synthetic test doubles are accepted only by an explicit `allow_simulated=True` pure-policy test option. This prevents mock evidence from being mislabeled as a production sandbox result.

## D-010 — Trusted acceptance suite is an external read-only baseline
Alternatives: candidate tests only, copy candidate tests after modification, or a separately stored suite mounted read-only. Select the repository's `acceptance/` directory referenced by the trusted policy and copied into the trusted image, with policy-relative path validation, regular-file-only manifest, suite fingerprint, version/ID, and a read-only container mount. The suite imports candidate implementation code but owns its assertions and selection. It is stronger than candidate tests, not a complete semantic or kernel-isolation proof.
