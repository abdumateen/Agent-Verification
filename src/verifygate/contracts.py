"""Validation of the candidate's completion claim."""

import json
from pathlib import Path
import re


TASK_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z", re.ASCII)


def safe_path(value: str) -> bool:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value or value.startswith("/") or ":" in value:
        return False
    return all(part not in ("", ".", "..") and part.strip() == part and not part.endswith(".") for part in value.split("/"))


def load_claim(path: Path, expected_task_ids=None) -> dict:
    with path.open(encoding="utf-8") as stream:
        claim = json.load(stream)
    if not isinstance(claim, dict) or set(claim) != {
        "task_id", "status", "summary", "changed_files", "tests_run"
    }:
        raise ValueError("claim must contain exactly the required fields")
    for name in ("task_id", "summary"):
        if not isinstance(claim[name], str) or not claim[name].strip():
            raise ValueError(f"{name} must be a nonempty string")
    if not TASK_ID.fullmatch(claim["task_id"]):
        raise ValueError("invalid task_id")
    if expected_task_ids is not None and claim["task_id"] not in expected_task_ids:
        raise ValueError("task_id is not authorized by policy")
    if claim["status"] != "done":
        raise ValueError("status must be done")
    for name in ("changed_files", "tests_run"):
        if not isinstance(claim[name], list) or not all(
            isinstance(item, str) for item in claim[name]
        ):
            raise ValueError(f"{name} must be a list of strings")
    if not all(safe_path(item) for item in claim["changed_files"]):
        raise ValueError("changed_files must contain safe relative paths")
    return claim
