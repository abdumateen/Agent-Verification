#!/bin/sh
# Invoke only from a trusted CI job with a protected policy and runner image.
set -eu
: "${VERIFYGATE_HOME:?set trusted verifier checkout path}"
: "${VERIFYGATE_CANDIDATE:?set candidate checkout path}"
: "${VERIFYGATE_CLAIM:?set CI-produced claim path}"
: "${VERIFYGATE_POLICY:?set protected policy path}"
: "${VERIFYGATE_LEDGER:?set audit database path}"
: "${VERIFYGATE_REPORT:?set report path}"
PYTHONPATH="$VERIFYGATE_HOME/src" exec python -m verifygate.cli verify \
  --candidate "$VERIFYGATE_CANDIDATE" --claim "$VERIFYGATE_CLAIM" \
  --policy "$VERIFYGATE_POLICY" --ledger "$VERIFYGATE_LEDGER" \
  --report "$VERIFYGATE_REPORT"
