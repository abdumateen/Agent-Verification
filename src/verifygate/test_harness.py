"""Trusted unittest runner executed inside the verification image."""

import argparse
import json
from pathlib import Path
import sys
import unittest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    # -I keeps candidate files from shadowing the trusted harness on startup.
    # Only after trusted imports do we expose the candidate root to its tests.
    sys.path.insert(0, str(Path.cwd()))
    start = "tests" if Path("tests").is_dir() else "."
    suite = unittest.defaultTestLoader.discover(start_dir=start, pattern="test*.py")
    outcome = unittest.TextTestRunner(stream=sys.stdout).run(suite)
    args.report.write_text(json.dumps({
        "tests_run": outcome.testsRun,
        "failures": len(outcome.failures),
        "errors": len(outcome.errors),
    }), encoding="utf-8")
    return 0 if outcome.wasSuccessful() and outcome.testsRun else 1


if __name__ == "__main__":
    sys.exit(main())
