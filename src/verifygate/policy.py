"""Strict policy validation and conservative outcome selection."""

import hashlib
import json
import math
from pathlib import Path


def _positive(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and value > 0


def load_policy(path: Path, candidate_dir: Path) -> tuple[dict, str]:
    candidate = candidate_dir.resolve(strict=True)
    location = path.resolve(strict=True)
    if location == candidate or candidate in location.parents:
        raise ValueError("policy must be outside candidate directory")
    with path.open(encoding="utf-8") as stream:
        policy = json.load(stream)
    if not isinstance(policy, dict) or not {"version", "image", "checks"} <= policy.keys() or not policy.keys() <= {
        "version", "image", "checks", "timeout", "memory", "cpus", "require_review"
    }:
        raise ValueError("invalid policy fields")
    if type(policy["version"]) is not int or policy["version"] != 1:
        raise ValueError("unsupported policy version")
    if not isinstance(policy["image"], str) or not policy["image"].strip():
        raise ValueError("image must be nonempty")
    checks = policy["checks"]
    if not isinstance(checks, list) or not checks:
        raise ValueError("checks must be nonempty")
    ids = set()
    mandatory = 0
    for check in checks:
        if not isinstance(check, dict) or not {"id", "type"} <= check.keys():
            raise ValueError("check requires id and type")
        kind = check["type"]
        allowed = {"id", "type", "mandatory", "timeout", "memory", "cpus"}
        if kind == "command":
            allowed.add("argv")
        elif kind == "unittest":
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
        elif type(check.get("minimum_tests")) is not int or check["minimum_tests"] < 1:
            raise ValueError("minimum_tests must be a positive integer")
        _limits(check)
    if not mandatory:
        raise ValueError("at least one mandatory check is required")
    _limits(policy)
    if "require_review" in policy and type(policy["require_review"]) is not bool:
        raise ValueError("require_review must be boolean")
    canonical = json.dumps(policy, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return policy, hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _limits(settings: dict) -> None:
    for name in ("timeout", "memory", "cpus"):
        if name in settings and not _positive(settings[name]):
            raise ValueError(f"{name} must be a positive finite number")


def decide(results: list[dict], policy: dict) -> str:
    checks = policy.get("checks", [])
    if not checks:
        return "INCONCLUSIVE"
    by_id = {}
    for result in results:
        if isinstance(result, dict) and result.get("id") not in by_id:
            by_id[result.get("id")] = result.get("status")
    if any(by_id.get(check["id"]) == "failed" and check.get("mandatory", True) for check in checks):
        return "REJECTED"
    if any(by_id.get(check["id"]) != "passed" and check.get("mandatory", True) for check in checks):
        return "INCONCLUSIVE"
    return "NEEDS_REVIEW" if policy.get("require_review", False) else "VERIFIED"
