"""Trusted unittest runner executed inside the verification image."""

import argparse
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
import sys
import unittest
from typing import cast, TextIO


def _record_markers(nonce: str) -> tuple[str, str]:
    return f"VERIFYGATE_RESULT<{nonce}>:", f":VERIFYGATE_RESULT<{nonce}>"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nonce", required=True)
    parser.add_argument("--start-dir", default=None)
    args = parser.parse_args()
    if not args.nonce or any(char not in "0123456789abcdef-" for char in args.nonce):
        parser.error("nonce must be a verifier-generated hex token")
    # -I keeps candidate files from shadowing the trusted harness on startup.
    # Only after trusted imports do we expose the candidate root to its tests.
    sys.path.insert(0, str(Path.cwd()))
    start = args.start_dir or ("tests" if Path("tests").is_dir() else ".")
    suite = unittest.defaultTestLoader.discover(start_dir=start, pattern="test*.py")
    # Candidate output is diagnostics, never part of the control channel.  Both
    # Python streams are captured until the trusted runner has finished.
    candidate_stdout = StringIO()
    candidate_stderr = StringIO()
    with redirect_stdout(candidate_stdout), redirect_stderr(candidate_stderr):
        outcome = unittest.TextTestRunner(stream=candidate_stdout).run(suite)
    record = json.dumps({
        "tests_run": outcome.testsRun,
        "failures": len(outcome.failures),
        "errors": len(outcome.errors),
    }, sort_keys=True, separators=(",", ":"))
    start_marker, end_marker = _record_markers(args.nonce)
    # The control record is the sole stdout payload.  Direct os.write(1, ...)
    # from candidate code can bypass redirect_stdout; the verifier therefore
    # rejects any extra/malformed bytes on this channel.
    control = cast(TextIO, sys.__stdout__)
    control.write(f"{start_marker}{record}{end_marker}\n")
    control.flush()
    # Preserve captured diagnostics on stderr only, after the control record.
    diagnostics = candidate_stdout.getvalue() + candidate_stderr.getvalue()
    if diagnostics:
        diagnostic_stream = cast(TextIO, sys.__stderr__)
        diagnostic_stream.write(diagnostics)
        diagnostic_stream.flush()
    return 0 if outcome.wasSuccessful() and outcome.testsRun else 1


if __name__ == "__main__":
    sys.exit(main())
