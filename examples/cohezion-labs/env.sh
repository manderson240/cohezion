#!/usr/bin/env bash
# Shared environment for cohezion-labs — the durable home for the showcase,
# eval, and coherence demonstrators built across sessions.
#
# Import root is the MAIN checkout's src (permanent, editable-install root, and
# verified to import all 13 demo dependencies including the merged Phase-18
# physics modules). We deliberately do NOT vendor a copy of src here — repointing
# to the live checkout keeps the demos honest against the real code.
#
# Source this from any runner:  source "$(dirname "$0")/../env.sh"
#
# Repo-relative: examples/cohezion-labs/ -> repo root is two levels up. Works for
# anyone who clones, no hardcoded machine path. Override CZ_REPO to point elsewhere.

export CZ_LABS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export CZ_REPO="${CZ_REPO:-$(cd "$CZ_LABS/../.." && pwd)}"
export CZ_SRC="${CZ_REPO}/src"

# Venv: prefer this checkout's, else the canonical main checkout's (worktrees
# don't carry a .venv), else whatever python3 is on PATH.
if [ -x "${CZ_REPO}/.venv/bin/python" ]; then
  export CZ_VENV_PY="${CZ_REPO}/.venv/bin/python"
elif [ -x "/home/mike-anderson/dev/cohezion/.venv/bin/python" ]; then
  export CZ_VENV_PY="/home/mike-anderson/dev/cohezion/.venv/bin/python"
else
  export CZ_VENV_PY="$(command -v python3)"
fi

# Convenience: run a labs python script with the correct PYTHONPATH + venv.
cz_run() {
  PYTHONPATH="${CZ_SRC}" "${CZ_VENV_PY}" "$@"
}
export -f cz_run 2>/dev/null || true
