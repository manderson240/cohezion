---
name: lemonade-embeddable-integration-prime
description: "Expert in integrating private, portable Lemonade server instances into existing application workspaces. Specializes in isolated hardware acceleration (gfx1151/ROCm) without requiring system-level installation or root access."
---

# SKILL: LEMONADE_EMBEDDABLE_INTEGRATION_PRIME

## DOMAIN EXPERTISE
Expert in integrating private, portable Lemonade server instances into existing application workspaces. Specializes in isolated hardware acceleration (gfx1151/ROCm) without requiring system-level installation or root access.

## KEY TEXTS & CONCEPTS
- **Isolated Runtime**: Bundle the `lemond` service in `vendor/` to prevent OS-level dependency conflicts.
- **Library Side-loading**: Placing optimized `.so` files in a private `bin/` directory and using `LD_LIBRARY_PATH` during subprocess spawning.
- **Subprocess Lifecycle**: Programmatically starting/stopping the server via a manager class (e.g., `LemonadeManager`).

## INSTRUCTION
1. **Download Artifact**: Get the `lemonade-embeddable-*-ubuntu-x64.tar.gz`.
2. **Setup Tree**: Extract to `vendor/lemonade` and create `bin/`, `models/`, and `extra_models/`.
3. **Configure**: Use `lemonade config set` or write `config.json` directly to set a private port (e.g., 13307) and enable hardware backends (`backend: rocm`).
4. **Spawn lemond**: Use `subprocess.Popen` with `cwd` set to the private directory and `LD_LIBRARY_PATH` pointing to the private `bin/`.
5. **Health Check**: Ping `/api/v1/models` to verify readiness before routing requests.

## VERSION
v1.0

## SEE ALSO
- HARDWARE_ACCELERATION_PRIME.md
- GFX1151_OPTIMIZATION_PRIME.md
