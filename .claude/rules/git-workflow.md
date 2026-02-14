---
paths:
  - ".git/**"
  - ".pre-commit-config.yaml"
  - ".gitlab-ci.yml"
  - "CONTRIBUTING.md"
---

# Git Workflow Rules

- Never commit directly to `main` — always use feature branches
- Branch naming: `feature/*`, `fix/*`, `refactor/*`, `docs/*`, `improve/*`, `session-*`
- Conventional commit messages required: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`, `perf:`, `ci:`
- No emoji in commit messages
- Subject line under 72 characters, imperative mood
- Always run `uv run pytest -q` before pushing (use `-q` for quiet output)
- AI-generated commits must include the `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>` trailer
- Never force-push to `main`
- Remote: Local GitLab instance (http://localhost:8929/root/cohezion.git)
