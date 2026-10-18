# Threat model

## Assets and actors
Assets: developer workstation, credentials, Docker daemon, trusted policy/image, source snapshot, test evidence, audit ledger and report. The agent controls candidate source, claim text and possibly its own test suite; the administrator controls verifier process, policy, image and evidence location. The model does not assume an agent exposes hidden reasoning or memory.

## Boundaries and controls
Claim validation rejects malformed task IDs and unsafe relative changed-file paths. Policy is outside candidate and task-allowlisted; its hash is rechecked after execution. Snapshot copies regular files and rejects symlinks, excludes common secret/cache entries, records manifest and verifies post-run workspace fingerprint. Docker options specify non-root UID, read-only snapshot/root, no network, dropped caps, no-new-privileges, PID/CPU/memory/time and tmpfs limits; the candidate never receives the Docker socket or host credentials intentionally. A timeout attempts `docker rm -f` using a container ID file outside the candidate mount. Logs and structured reports have bounded reads. The ledger detects modification of retained rows; reports carry a digest in the ledger.

## Residual threats
Docker is not microVM isolation. The untrusted test process can modify its writable report mount and possibly spoof counts; this MVP is **not** an adversarial proof of test discovery. Command outputs can carry arbitrary secrets and are not comprehensively redacted; never inject real secrets into candidate containers. Image tags are mutable; pin/attest the trusted image in production. A privileged operator can truncate/recompute the local chain; use external signed checkpoints. Local hooks are bypassable, MCP does not intercept other tools, and CI enforcement requires protected branch settings. No live container test has been observed in this environment.
