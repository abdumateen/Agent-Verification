# Current limitations

- Docker and GNU Make are absent on this Windows host. Dockerfile build and actual sandbox verification have **not** passed here; `make test` was replaced by the equivalent Python unittest command for local evidence.
- Candidate-written unittest report is readable from a writable mount. Hashing after execution catches later modifications but cannot prove a malicious candidate did not forge it before collection. Use a stronger reporting channel and hostile-code isolation before high-assurance use.
- Python adapter does AST syntax and configurable stub warnings, not full import/type/reference or semantic verification. No C#/VB.NET/TypeScript adapter.
- The SQLite chain detects retained-row modification and interior deletion, not tail deletion or full rewrite. No external checkpoint or signatures.
- Report stdout/stderr may contain sensitive values; limits are size bounds, not comprehensive secret redaction.
- Docker tag `verifygate:local` can be replaced, and Docker itself is not a microVM. Image digest/attestation is not yet enforced.
- Local hook can be skipped/changed and MCP is voluntary. CI wrapper exits nonzero, but no protected branch or actual CI environment is configured/tested.
- No concurrency coordination, retry/status state machine, cancellation API, JUnit XML parser, full task registry, guaranteed file deletion handling, or production retention policy. `CHECKING` is not persisted.
