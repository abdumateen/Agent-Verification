"""Run the trusted AST-only Python adapter against a container snapshot."""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from verifygate.analyzers.python import analyze


def main() -> int:
    result = analyze(Path.cwd())
    print(json.dumps(result, sort_keys=True))
    return 1 if result["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
