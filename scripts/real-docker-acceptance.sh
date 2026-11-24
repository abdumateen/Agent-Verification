#!/bin/sh
# Explicit opt-in Linux acceptance path. Requires an authorized Docker daemon.
set -eu
docker build -t verifygate:local .
VERIFYGATE_RUN_REAL_DOCKER=1 PYTHONPATH=src python -m unittest discover -s tests -p test_real_docker.py -v
