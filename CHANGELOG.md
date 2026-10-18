# Changelog

## 0.2 — verification hardening (2026-10-18)
- Strict task allowlist and safer path/policy validation; snapshot manifest and configurable exclusions; Python AST diagnostics and stub warnings.
- Bounded Docker output, timing/report evidence, timeout cleanup attempt and safer trusted script invocation with isolated Python startup.
- Transactional SQLite hash-linked ledger and report-content digest checks; shared verifier for CLI and optional MCP SDK adapter.
- CLI version/policy/status/report/demo; opt-in pre-commit and CI wrapper examples.
- Limitation: real Docker build/run and protected CI enforcement have not been observed on this host.

## 0.1 — initial CLI MVP
- Claims, file snapshots, Docker command runner, JSONL ledger and basic tests.
