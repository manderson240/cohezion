#!/bin/bash
# Package the Anthropic VLIW solution cleanly

ZIP_NAME="anthropic_submission.zip"
TARGET_DIR="research/challenges/anthropic_challenge"

echo "📦 Packaging Anthropic Submission..."

# Move to the project root (assuming we are in the script's directory or root)
# In this case, we'll just run from the research dir for simplicity if that's where zip expects it.

zip -r "$ZIP_NAME" \
    "$TARGET_DIR/perf_takehome.py" \
    "$TARGET_DIR/optimizer.py" \
    "$TARGET_DIR/problem.py" \
    "$TARGET_DIR/frozen_problem.py" \
    "$TARGET_DIR/pyproject.toml" \
    "$TARGET_DIR/SUBMISSION_README.md" \
    "$TARGET_DIR/resume.md" \
    "$TARGET_DIR/tests" \
    -x "*/__pycache__/*"

echo "✅ Created $ZIP_NAME"
echo "🔍 Contents:"
unzip -l "$ZIP_NAME"
