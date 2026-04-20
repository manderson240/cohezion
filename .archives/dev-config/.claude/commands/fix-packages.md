Fix missing __init__.py files across the source tree.

Find all directories under src/cohezion/ (excluding __pycache__) that are missing __init__.py and create them. Then verify the fix by running a quick import check.

After fixing, run `uv run ruff check src/cohezion/` to ensure no import issues.
