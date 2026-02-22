## Summary

<!-- What does this PR do and why? Keep it to 1-3 bullet points. -->

-

## Change Type

<!-- Check one: -->

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] Feature (non-breaking change that adds functionality)
- [ ] Refactor (no functional changes)
- [ ] Breaking change (fix or feature that would cause existing functionality to change)
- [ ] Documentation
- [ ] CI/Tooling

## Test Plan

<!-- How was this tested? Include commands run or describe manual verification. -->

- [ ] `uv run pytest tests/ -q` passes
- [ ] `uv run ruff check src/ tests/` passes
- [ ] Manual verification: <!-- describe -->

## Checklist

- [ ] Code follows project conventions (type hints, NumPy docstrings)
- [ ] No new `continue-on-error: true` added to CI steps without justification
- [ ] No secrets or credentials in committed files
- [ ] No files > 1MB committed (use git-lfs or external storage)
- [ ] Related issue linked (if applicable)

## Related Issues

<!-- Closes #123, Fixes #456 -->
