## Summary
<!-- What does this change? -->

## Fixes
<!-- Reference issues: Fixes #XX -->

## Verified
- [ ] `ruff format --check` passes
- [ ] `ruff check src/ tests/` passes
- [ ] `uv run pytest tests/unit/ -q` passes
- [ ] `uv run python scripts/ci/validate_skills.py` passes
- [ ] No new hardcoded paths or secrets

## V-Model Gate
<!-- Check after merge -->
- [ ] CI Pipeline: lint ✅ validate ✅ test ✅ ci-status ✅
- [ ] Branch auto-deleted after squash merge
