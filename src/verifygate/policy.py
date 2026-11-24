"""Strict policy validation and conservative outcome selection."""

import hashlib
import json
import math
from pathlib import Path
from verifygate.contracts import TASK_ID, safe_path


def _positive(value: object) -> bool:
    if type(value) not in (int, float):
        return False
    assert isinstance(value, (int, float))
    return math.isfinite(value) and value > 0


def load_policy(path: Path, candidate_dir: Path) -> tuple[dict, str]:
    candidate = candidate_dir.resolve(strict=True)
    location = path.resolve(strict=True)
    if location == candidate or candidate in location.parents:
        raise ValueError("policy must be outside candidate directory")
    with path.open(encoding="utf-8") as stream:
        policy = json.load(stream)
    if not isinstance(policy, dict) or not {"version", "image", "checks", "task_ids", "language"} <= policy.keys() or not policy.keys() <= {
        "version", "image", "checks", "task_ids", "language", "stub_mode", "exclusions", "timeout", "memory", "cpus", "require_review", "acceptance", "acceptance_fingerprint"
    }:
        raise ValueError("invalid policy fields")
    task_ids = policy["task_ids"]
    if not isinstance(task_ids, list) or not task_ids or any(not isinstance(item, str) or not TASK_ID.fullmatch(item) for item in task_ids) or len(set(task_ids)) != len(task_ids):
        raise ValueError("task_ids must be unique valid nonempty identifiers")
    if policy["language"] != "python":
        raise ValueError("language must be python")
    if policy.get("stub_mode", "warn") not in ("warn", "off"):
        raise ValueError("stub_mode must be warn or off")
    exclusions = policy.get("exclusions", [])
    if not isinstance(exclusions, list) or any(not isinstance(item, str) or not safe_path(item.replace("*", "x")) or any(char in item for char in "?[]{}") or ("*" in item and not (item.endswith("/*") or item.startswith("*."))) for item in exclusions):
        raise ValueError("exclusions must be safe relative names or patterns")
    if type(policy["version"]) is not int or policy["version"] != 1:
        raise ValueError("unsupported policy version")
    if not isinstance(policy["image"], str) or not policy["image"].strip():
        raise ValueError("image must be nonempty")
    checks = policy["checks"]
    if not isinstance(checks, list) or not checks or len(checks) > 16:
        raise ValueError("checks must contain between 1 and 16 entries")
    ids = set()
    mandatory = 0
    for check in checks:
        if not isinstance(check, dict) or not {"id", "type"} <= check.keys():
            raise ValueError("check requires id and type")
        kind = check["type"]
        allowed = {"id", "type", "mandatory", "timeout", "memory", "cpus"}
        if kind == "command":
            allowed.add("argv")
        elif kind in ("unittest", "acceptance"):
            allowed.add("minimum_tests")
        else:
            raise ValueError("unknown check type")
        if not check.keys() <= allowed:
            raise ValueError("unknown check fields")
        identifier = check["id"]
        if not isinstance(identifier, str) or not identifier.strip() or identifier in ids:
            raise ValueError("check ids must be unique nonempty strings")
        ids.add(identifier)
        if "mandatory" in check and type(check["mandatory"]) is not bool:
            raise ValueError("mandatory must be boolean")
        mandatory += check.get("mandatory", True)
        if kind == "command":
            argv = check.get("argv")
            if not isinstance(argv, list) or not argv or not all(isinstance(arg, str) for arg in argv) or not argv[0]:
                raise ValueError("command argv must be a nonempty list of strings")
            if Path(argv[0]).name.lower() in {"sh", "bash", "dash", "zsh", "cmd", "cmd.exe", "powershell", "pwsh"} or any(arg in ("-c", "--command") for arg in argv[1:]):
                raise ValueError("shell commands and inline code are not allowed")
        elif type(check.get("minimum_tests")) is not int or check["minimum_tests"] < 1:
            raise ValueError("minimum_tests must be a positive integer")
        _limits(check)
    if not mandatory:
        raise ValueError("at least one mandatory check is required")
    _limits(policy)
    if "require_review" in policy and type(policy["require_review"]) is not bool:
        raise ValueError("require_review must be boolean")
    acceptance = policy.get("acceptance")
    if acceptance is None:
        if any(check["type"] == "acceptance" for check in checks):
            raise ValueError("acceptance check requires acceptance configuration")
        canonical = json.dumps(policy, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
        return policy, hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    if not isinstance(acceptance, dict) or not {"required", "suite_id", "version", "path", "container_path", "minimum_tests"} <= acceptance.keys():
        raise ValueError("acceptance config is required")
    if type(acceptance["required"]) is not bool or acceptance["container_path"] != "/opt/app/acceptance":
        raise ValueError("invalid acceptance metadata")
    if any(not isinstance(acceptance[k], str) or not acceptance[k].strip() for k in ("suite_id", "version", "path")):
        raise ValueError("invalid acceptance metadata")
    if type(acceptance["minimum_tests"]) is not int or acceptance["minimum_tests"] < 1:
        raise ValueError("invalid acceptance minimum_tests")
    suite = (location.parent / acceptance["path"]).resolve(strict=True)
    if (candidate == suite or candidate in suite.parents or suite in candidate.parents or
            not suite.is_dir() or suite.is_symlink()):
        raise ValueError("acceptance suite must be outside candidate and be a directory")
    entries = []
    for item in sorted(suite.rglob("*")):
        if item.is_symlink():
            raise ValueError("acceptance suite may contain regular files only")
        if item.is_dir():
            continue
        if not item.is_file():
            raise ValueError("acceptance suite may contain regular files only")
        if "__pycache__" in item.parts or item.suffix == ".pyc":
            continue
        entries.append((item.relative_to(suite).as_posix(), hashlib.sha256(item.read_bytes()).hexdigest()))
    if not entries:
        raise ValueError("acceptance suite must not be empty")
    fingerprint = hashlib.sha256(json.dumps(entries, separators=(",", ":")).encode()).hexdigest()
    acceptance["fingerprint"] = fingerprint
    policy["acceptance_fingerprint"] = fingerprint
    canonical = json.dumps(policy, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return policy, hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _limits(settings: dict) -> None:
    for name in ("timeout", "memory", "cpus"):
        if name in settings and not _positive(settings[name]):
            raise ValueError(f"{name} must be a positive finite number")


def decide(results: list[dict], policy: dict, artifact_hash: str | None = None,
           policy_hash: str | None = None, *, report_hash: str | None = None,
           allow_simulated: bool = False) -> str:
    checks = policy.get("checks", [])
    if not checks:
        return "INCONCLUSIVE"
    by_id = {}
    for result in results:
        if not isinstance(result, dict) or result.get("id") in by_id or result.get("status") not in {"passed", "failed", "inconclusive"}:
            return "INCONCLUSIVE"
        by_id[result["id"]] = result["status"]
    if any(by_id.get(check["id"]) == "failed" and check.get("mandatory", True) for check in checks):
        return "REJECTED"
    if any(by_id.get(check["id"]) != "passed" and check.get("mandatory", True) for check in checks):
        return "INCONCLUSIVE"
    for check in checks:
        if not check.get("mandatory", True):
            continue
        evidence = next(item for item in results if item["id"] == check["id"])
        if ((not allow_simulated and evidence.get("provenance") != "live_docker") or
                evidence.get("runner") != "docker" or evidence.get("exit_code") != 0 or
                not artifact_hash or evidence.get("snapshot_hash") != artifact_hash or
                not policy_hash or evidence.get("policy_hash") != policy_hash):
            return "INCONCLUSIVE"
        if check["type"] == "unittest":
            if (evidence.get("report_provenance") != "trusted_harness_stdout" or
                    evidence.get("test_source", "candidate") != check.get("test_source", "candidate")):
                return "INCONCLUSIVE"
            count = evidence.get("tests_run")
            evidence_report_hash = evidence.get("report_sha256")
            if (type(count) is not int or count < check["minimum_tests"] or
                    not isinstance(evidence_report_hash, str) or len(evidence_report_hash) != 64 or
                    any(char not in "0123456789abcdef" for char in evidence_report_hash)):
                return "INCONCLUSIVE"
            if report_hash is not None and evidence_report_hash != report_hash:
                return "INCONCLUSIVE"
        if check["type"] == "acceptance":
            if (evidence.get("report_provenance") != "trusted_harness_stdout" or
                    evidence.get("test_source") != "trusted_acceptance" or
                    evidence.get("acceptance_suite_id") != policy["acceptance"]["suite_id"] or
                    evidence.get("acceptance_suite_version") != policy["acceptance"]["version"] or
                    evidence.get("acceptance_fingerprint") != policy["acceptance_fingerprint"] or
                    type(evidence.get("tests_run")) is not int or
                    evidence["tests_run"] < policy["acceptance"]["minimum_tests"]):
                return "INCONCLUSIVE"
            evidence_report_hash = evidence.get("report_sha256")
            if (not isinstance(evidence_report_hash, str) or len(evidence_report_hash) != 64 or
                    any(char not in "0123456789abcdef" for char in evidence_report_hash)):
                return "INCONCLUSIVE"
    return "NEEDS_REVIEW" if policy.get("require_review", False) else "VERIFIED"
