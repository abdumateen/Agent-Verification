"""Validation of the candidate's completion claim."""

import json
from pathlib import Path


def load_claim(path: Path) -> dict:
    with path.open(encoding="utf-8") as stream:
        claim = json.load(stream)
    if not isinstance(claim, dict) or set(claim) != {
        "task_id", "status", "summary", "changed_files", "tests_run"
    }:
        raise ValueError("claim must contain exactly the required fields")
    for name in ("task_id", "summary"):
        if not isinstance(claim[name], str) or not claim[name].strip():
            raise ValueError(f"{name} must be a nonempty string")
    if claim["status"] != "done":
        raise ValueError("status must be done")
    for name in ("changed_files", "tests_run"):
        if not isinstance(claim[name], list) or not all(
            isinstance(item, str) for item in claim[name]
        ):
            raise ValueError(f"{name} must be a list of strings")
    return claim
