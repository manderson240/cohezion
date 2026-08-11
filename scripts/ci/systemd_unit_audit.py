#!/usr/bin/env python3
"""Audit systemd USER units: does every ExecStart target actually resolve, and can a broken unit
fail visibly?

WHY THIS EXISTS (2026-07-25): five units were found pointing at things that do not exist —
`smart-loader.service` (missing shell script), `cohezion-resource-guard.service` (missing Python
module, which burned ~891MB + ~15s CPU every 10s indefinitely), plus memory-shepherd-{memory,
workspace} and openclaw-session-cleanup. Together they produced ~10,000 journal failure events in
24 hours. NOTHING detected this: the units were "enabled", systemd dutifully restarted them
forever, and no monitoring noticed, because only 7 of 45 units set StartLimitBurst — so a broken
unit retries indefinitely instead of entering FAILED where `systemctl --user --failed` would show it.

Two checks, both deterministic, no LLM, no systemd bus required (reads unit FILES):
  1. TARGET RESOLVES — handles BOTH forms: an absolute ExecStart path, and `<python> -m pkg.module`
     (the module form is what broke resource-guard and is invisible to a naive path check).
  2. FAILS VISIBLY — a unit with Restart= but no StartLimitBurst can loop forever silently.

Exit 1 on any missing target (hard error); missing StartLimitBurst is reported as a warning so this
can land without failing on 38 pre-existing units. Tighten to fail mode once they are remediated.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

UNIT_DIR = Path.home() / ".config/systemd/user"


def _expand(raw: str) -> str:
    """Expand systemd specifiers we can resolve statically."""
    return raw.replace("%h", str(Path.home())).replace("%u", os.environ.get("USER", ""))


# Wrappers that EXEC a real interpreter rather than being one. `uv run python -m pkg` must resolve
# the module against the venv python, not against `uv` — treating the wrapper as the interpreter
# produced a false positive on cohezion-compound.service.
_WRAPPERS = {"uv", "uvx", "poetry", "pdm", "hatch", "env", "nice", "ionice"}


def _module_target(tokens: list[str]) -> tuple[str, str] | None:
    """If ExecStart runs `… <interpreter> -m pkg.module`, return (interpreter, module).

    Returns None when the real interpreter cannot be identified statically (e.g. a wrapper that
    resolves `python` from its own managed environment) — UNKNOWN must not be reported as BROKEN.
    """
    if "-m" not in tokens:
        return None
    i = tokens.index("-m")
    if i + 1 >= len(tokens):
        return None
    module = tokens[i + 1]

    venv = Path.home() / "dev/cohezion/.venv/bin/python"

    # Walk left from -m to the nearest token that looks like an interpreter.
    for tok in reversed(tokens[:i]):
        base = Path(tok).name.strip("\"'")
        if base in _WRAPPERS or base == "run":
            continue
        if "python" not in base:
            break
        # A BARE `python` (as in `uv run python -m X`) is resolved by the wrapper's environment,
        # not by PATH — reporting it as a missing interpreter is a false positive. Resolve it
        # against the repo venv, which is what the wrapper selects here.
        if not tok.startswith("/"):
            return (str(venv), module) if venv.exists() else None
        return tok, module

    return None


def _module_importable(interpreter: str, module: str) -> bool | None:
    """None = could not determine (interpreter missing); else True/False."""
    if not Path(interpreter).exists():
        return None
    try:
        r = subprocess.run(  # noqa: S603
            [interpreter, "-c", f"import importlib.util,sys; "
                                f"sys.exit(0 if importlib.util.find_spec('{module}') else 1)"],
            capture_output=True, timeout=60, check=False,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    return r.returncode == 0


def audit(check_modules: bool = True) -> tuple[list[str], list[str]]:
    missing: list[str] = []
    no_limit: list[str] = []

    for unit in sorted(UNIT_DIR.glob("*.service")):
        try:
            text = unit.read_text()
        except OSError:
            continue

        m = re.search(r"^ExecStart=(.+)$", text, re.M)
        if m:
            tokens = _expand(m.group(1).strip()).split()
            if tokens:
                exe = tokens[0].lstrip("-@+!").strip("\"'")  # prefix chars + systemd quoting
                mod = _module_target(tokens)
                if mod and check_modules:
                    interp, module = mod
                    ok = _module_importable(interp, module)
                    if ok is False:
                        missing.append(f"{unit.name}: module '{module}' not importable by {interp}")
                    elif ok is None and not Path(interp).exists():
                        missing.append(f"{unit.name}: interpreter '{interp}' does not exist")
                elif exe.startswith("/"):
                    if not Path(exe).exists():
                        missing.append(f"{unit.name}: ExecStart target '{exe}' does not exist")
                elif shutil.which(exe) is None:
                    missing.append(f"{unit.name}: '{exe}' not found on PATH")

        # A unit that restarts but cannot give up loops forever without ever showing as failed.
        if re.search(r"^Restart=(always|on-failure)", text, re.M) and "StartLimitBurst" not in text:
            no_limit.append(unit.name)

    return missing, no_limit


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true", help="never exit non-zero")
    ap.add_argument("--skip-modules", action="store_true", help="skip the slower import check")
    a = ap.parse_args()

    if not UNIT_DIR.is_dir():
        print(f"no unit dir at {UNIT_DIR} — nothing to audit")
        return 0

    missing, no_limit = audit(check_modules=not a.skip_modules)

    print(f"systemd unit audit — {UNIT_DIR}")
    if missing:
        print(f"\n  BROKEN ExecStart ({len(missing)}):")
        for x in missing:
            print(f"    ✗ {x}")
    else:
        print("\n  ✅ every ExecStart target resolves")

    if no_limit:
        print(f"\n  WARN — Restart= without StartLimitBurst ({len(no_limit)}): these retry forever")
        print("         instead of entering FAILED, so a break stays invisible:")
        for x in no_limit[:12]:
            print(f"    ! {x}")
        if len(no_limit) > 12:
            print(f"    … and {len(no_limit) - 12} more")

    return 1 if (missing and not a.report) else 0


if __name__ == "__main__":
    raise SystemExit(main())
