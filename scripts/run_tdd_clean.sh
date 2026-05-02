#!/bin/bash
export PYTHONPATH=""
# Standard lib should come first
echo "=== Running AIMO TDD Tests (Sanitized Env) ==="
AIMO_FORCE_CPU=1 uv run python -m tests.test_aimo_predict_tdd
AIMO_FORCE_CPU=1 uv run python -m tests.test_aimo_symbolic_verifier
