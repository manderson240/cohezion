# Branching Strategy: Git Flow Lite

This repository follows a simplified Git Flow model to ensure stability while maintaining velocity.

## Branches

### `main` (Production)
- **Purpose**: Stable, production-ready code.
- **Rules**:
    - No direct commits.
    - Merges only from `develop` via Pull Request (PR).
    - Must pass all CI/CD checks (linting, tests, health check).
    - Deployments to Cloud Run are triggered from here.

### `develop` (Integration)
- **Purpose**: Active development and integration.
- **Rules**:
    - The default branch for the repository.
    - Feature branches merge into `develop`.
    - Nightly builds and experimental runs happen here.

### `feat/name` (Features)
- **Purpose**: New features, experiments, or research tasks.
- **Naming**: `feat/description`, `research/topic`, `experiment/name`.
- **Life Cycle**: Created from `develop`, merged back to `develop`, then deleted.

### `fix/name` (Bug Fixes)
- **Purpose**: Bug fixes.
- **Naming**: `fix/issue-description`.

## Workflow
1.  **Start**: `git checkout -b feat/my-feature develop`
2.  **Work**: Commit changes locally.
3.  **Sync**: `git pull origin develop` (rebase preferred).
4.  **Merge**: Create PR to `develop`.
