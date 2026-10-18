"""Parse Python snapshots without importing or executing candidate code."""

import ast
from pathlib import Path

from verifygate.snapshots import manifest


def analyze(snapshot: Path, stub_mode: str = "warn") -> dict:
    if stub_mode not in ("warn", "off"):
        raise ValueError("stub_mode must be warn or off")
    diagnostics = []
    for name in manifest(snapshot)["files"]:
        if not name.endswith(".py"):
            continue
        source = snapshot.joinpath(*name.split("/"))
        try:
            tree = ast.parse(source.read_bytes(), filename=name)
        except (SyntaxError, UnicodeError, ValueError) as exc:
            diagnostics.append({"file": name, "line": getattr(exc, "lineno", None), "severity": "error", "code": "syntax", "message": str(exc)})
            continue
        if stub_mode == "warn":
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                    diagnostics.append({"file": name, "line": node.lineno, "severity": "warning", "code": "stub", "message": f"empty function: {node.name}"})
    return {"status": "failed" if any(item["severity"] == "error" for item in diagnostics) else "passed", "diagnostics": diagnostics}
