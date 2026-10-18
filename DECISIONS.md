# Engineering decisions

## D-001 — Preserve the existing Python standard-library core
Alternatives: replace with Pydantic/Typer/pytest immediately, or incrementally harden current modules. Select incremental hardening: no dependency/API uncertainty and existing tests remain offline. Trade-off: hand-written strict validation needs more negative tests. Security: no implicit package install or changes to user's machine.

## D-002 — Treat Docker absence as INCONCLUSIVE
Alternatives: run candidate code on host, silently simulate, or block live verification. Select blocking live verification while allowing explicit mocks for orchestration tests. Security: no host fallback can issue VERIFIED. Linux Docker acceptance stays BLOCKED on this machine.

## D-003 — Policy must be outside candidate and version/fingerprint bound
Alternatives: candidate `.verifygate.yml` or trusted path supplied by verifier. Select trusted external path and digest; CI must protect that path independently. Security: path separation alone does not authorize who may modify the external file; deployment ownership remains essential.

## D-004 — SQLite hash chain is tamper-evident, not immutable
Alternatives: existing JSONL ledger, SQLite, remote transparency log. Select SQLite transactional events with hash links and local integrity validation. A privileged operator can rewrite/truncate/recompute all records; external signed checkpoints are deferred.
