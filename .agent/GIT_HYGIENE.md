# Git Hygiene Standards

## Ignore Rules
To maintain a clean repository and prevent bloat, the following patterns are globally ignored:

### Virtual Environments
- `**/venv/`: All virtual environments must be local and untracked.

### Artifacts & Data
- `*.dill`: Large serialized Python objects (often from `dill` serialization).
- `audio/`: Generated audio assets (TTS output).
- `*.zip`: Compressed archives (unless specifically required for submission).

### Challenge Submissions
- Specific challenge outputs (like `code_bundle.zip`) should be ignored if they are build artifcats.

## Maintenance
- Run `python scripts/assess_git_health.py` weekly to check for bloat and drift.
