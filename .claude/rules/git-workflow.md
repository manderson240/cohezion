---
paths:
  - ".git/**"
  - ".pre-commit-config.yaml"
  - ".gitlab-ci.yml"
  - "CONTRIBUTING.md"
---

# Git Workflow Rules

- Never commit directly to `main` or `develop` — always use feature branches
- Branch from `develop`, not `main`: `git checkout develop && git checkout -b feature/my-feature`
- Branch naming: `feature/*`, `fix/*`, `refactor/*`, `docs/*`, `improve/*`
- Conventional commit messages required: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`, `perf:`, `ci:`
- No emoji in commit messages
- Subject line under 72 characters, imperative mood
- Always run `uv run pytest` before pushing
- AI-generated commits must include the `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>` trailer
- Never force-push to `main` or `develop`
- PRs target `develop`, not `main`
