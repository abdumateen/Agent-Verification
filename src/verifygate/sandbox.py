"""Run snapshot checks in disposable, restricted Docker containers."""

import json
import os
from pathlib import Path
import subprocess
import tempfile


def _bind_path(path: Path) -> str:
    """Use an absolute, Docker Desktop-compatible host bind path."""
    return path.resolve().as_posix()


def run_checks(snapshot_dir: Path, policy: dict) -> list[dict]:
    results = []
    for check in policy["checks"]:
        kind = check["type"]
        command = (list(check["argv"]) if kind == "command" else
                   ["python", "-m", "verifygate.test_harness", "--report",
                    "/results/report.json"])
        result = {"id": check["id"], "status": "inconclusive",
                  "command": command, "exit_code": None, "tests_run": None,
                  "output": ""}
        with tempfile.TemporaryDirectory(prefix="verifygate-results-") as directory:
            result_dir = Path(directory)
            if kind == "unittest":
                # Container UID 65534 needs to create the report on both POSIX
                # hosts and Docker Desktop's shared Windows filesystem.
                os.chmod(result_dir, 0o777)
            argv = [
                "docker", "run", "--rm", "--network", "none", "--read-only",
                "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                "--pids-limit", "128", "--memory", f"{check.get('memory', policy.get('memory', 512))}m",
                "--cpus", str(check.get("cpus", policy.get("cpus", 1))), "--user", "65534:65534",
                "--tmpfs", "/tmp:rw,nosuid,nodev,size=64m", "--mount",
                f"type=bind,source={_bind_path(snapshot_dir)},target=/workspace,readonly",
                "--workdir", "/workspace", "--env", "PYTHONPATH=/opt/app/src",
            ]
            if kind == "unittest":
                argv += ["--mount", f"type=bind,source={_bind_path(result_dir)},target=/results"]
            argv += [policy["image"], *command]
            try:
                completed = subprocess.run(
                    argv, capture_output=True, text=True,
                    timeout=check.get("timeout", policy.get("timeout", 180)), check=False,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                result["output"] = str(exc)
                results.append(result)
                continue
            result["exit_code"] = completed.returncode
            result["output"] = (completed.stdout or "") + (completed.stderr or "")
            if completed.returncode in (125, 126, 127):
                result["output"] += "\nDocker could not start the verification command."
                results.append(result)
                continue
            if kind == "command":
                result["status"] = "passed" if completed.returncode == 0 else "failed"
            else:
                try:
                    report = json.loads((result_dir / "report.json").read_text(encoding="utf-8"))
                    count = report["tests_run"]
                    failures = report["failures"]
                    errors = report["errors"]
                    if (type(count) is not int or count < 0 or
                            type(failures) is not int or failures < 0 or
                            type(errors) is not int or errors < 0):
                        raise ValueError("invalid unittest report counts")
                except (OSError, ValueError, KeyError, TypeError) as exc:
                    result["output"] += f"\nMissing or invalid unittest report: {exc}"
                else:
                    result["tests_run"] = count
                    result["status"] = (
                        "failed" if (completed.returncode != 0 or failures or errors or
                                     count == 0 or count < check["minimum_tests"])
                        else "passed"
                    )
            results.append(result)
    return results
