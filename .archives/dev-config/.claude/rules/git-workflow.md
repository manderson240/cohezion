---
paths:
  - ".git/**"
  - ".pre-commit-config.yaml"
  - ".github/workflows/**"
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
- Remote: GitHub (git@github.com:manderson240/cohezion.git)
- Branching model: **GitHub Flow** — `main` is the single long-lived branch; all work happens on feature branches merged via pull requests

## Git Push Safety (L338)

- **NEVER use `git push --all`** — this pushes Entire.io shadow branches (`entire/<hash>-*`) that are designed to be local-only. Use `git push origin <branch>` for specific branches.
- **Entire.io shadow branches** are ephemeral session metadata. They may contain `.git` references or absolute paths that GitHub's server-side fsck rejects.
- **Only `entire/checkpoints/v1`** is designed for remote push (metadata JSON, not code).
- Run `entire clean --all --dry-run` if `git branch | grep entire/ | wc -l` exceeds 50.

## Git LFS (L333-L337)

- `.gitattributes` tracks: `*.so`, `*.whl`, `*.pt`, `*.pth`, `*.pkl`, `*.tar.gz`, `*.bundle`, `*.jsonl`
- LFS files are pointers in git (~130 bytes); actual content in `.git/lfs/objects/`
- After cloning, run `git lfs pull` to download actual files
- Pre-commit hook `lfs-pointer-check` blocks committing raw binaries for LFS-tracked patterns
- If LFS breaks: `git lfs install && git add --renormalize .`
