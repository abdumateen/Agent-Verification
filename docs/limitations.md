# Current limitations

- Docker and GNU Make are absent on this Windows host. Dockerfile build and actual sandbox verification have **not** passed here; `make test` was replaced by the equivalent Python unittest command for local evidence.
- The writable host `/results` report mount has been removed. The trusted harness now emits a nonce-bound record on stdout, and the supervisor validates exactly one record plus exit-code consistency. Python output is redirected, but direct `os.write` can bypass redirection; extra bytes fail closed. The nonce is visible in argv and is not authentication. A trusted acceptance suite now lives outside the candidate and is fingerprinted/mounted read-only, but it imports candidate code in the same container and is not a complete semantic or kernel-isolation guarantee.
- Python adapter does AST syntax and configurable stub warnings, not full import/type/reference or semantic verification. No C#/VB.NET/TypeScript adapter.
- The SQLite chain detects retained-row modification and interior deletion, not tail deletion or full rewrite. No external checkpoint or signatures.
- Report stdout/stderr may contain sensitive values; limits are size bounds, not comprehensive secret redaction.
- Docker tag `verifygate:local` can be replaced, and Docker itself is not a microVM. Image digest/attestation is not yet enforced.
- Local hook can be skipped/changed and MCP is voluntary. CI wrapper exits nonzero, but no protected branch or actual CI environment is configured/tested.
- No concurrency coordination, retry/status state machine, cancellation API, JUnit XML parser, full task registry, guaranteed file deletion handling, or production retention policy. `CHECKING` is not persisted.
