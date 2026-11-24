# Changelog

## 0.2 — verification hardening (2026-10-18)
- Strict task allowlist and safer path/policy validation; snapshot manifest and configurable exclusions; Python AST diagnostics and stub warnings.
- Bounded Docker output, timing/report evidence, timeout cleanup attempt and safer trusted script invocation with isolated Python startup.
- Transactional SQLite hash-linked ledger and report-content digest checks; shared verifier for CLI and optional MCP SDK adapter.
- CLI version/policy/status/report/demo; opt-in pre-commit and CI wrapper examples.
- Limitation: real Docker build/run and protected CI enforcement have not been observed on this host.

## 0.3 — evidence integrity milestone (2026-10-21)
- Removed the candidate-writable `/results` report mount that allowed fabricated passing counts.
- Changed the trusted harness to emit one nonce-bound result on stdout; the supervisor validates, bounds, hashes, and records it with explicit provenance.
- Added direct mount-forgery regressions, malformed/duplicate marker tests, provenance gating, and opt-in real Docker acceptance tests.
- Real Docker remains blocked on the current Windows host; no live sandbox result is claimed.

## 0.4 — trusted acceptance baseline (2026-10-21)
- Added mandatory `acceptance/` suite configuration with suite ID/version/fingerprint and trusted read-only execution.
- Candidate tests remain diagnostic; `VERIFIED` now requires the trusted acceptance check when configured.
- Added host protocol probes for print/os.write nonce attacks, independent-suite fingerprint tests, and real-Docker acceptance coverage for marker forgery.
- No Docker-capable CI or remote was available; live acceptance remains blocked.

## 0.1 — initial CLI MVP
- Claims, file snapshots, Docker command runner, JSONL ledger and basic tests.
