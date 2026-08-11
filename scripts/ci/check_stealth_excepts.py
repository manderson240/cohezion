#!/usr/bin/env python3
"""Gate for Learning-359 stealth bare-excepts (GitHub issue #94).

WHY THIS EXISTS. Issue #94 is titled "regression: Learning-359 except-tuple violations
REINTRODUCED". A working detector — `cohezion.compound.simplicity_audit.stealth_bare_excepts` —
already existed when the violation came back, but it had no CI consumer. A detector nothing calls
cannot prevent a regression; it only documents one after the fact. This script is that consumer.

SCOPE IS DELIBERATE AND NARROW. The detector reports three kinds; measured across 1,661 files:

    Exception       2311   single `except Exception:`   <- NOT gated (see below)
    stealth-tuple      1   `except (ValueError, Exception):`
    bare               1   `except:`                    <- vendored, excluded

Gating on the 2,311 `except Exception:` sites would fail every run forever, and a gate that always
fails is one people learn to skip — it never becomes a real gate. So this blocks ONLY the two kinds
that are genuinely at zero in first-party code (`stealth-tuple` and `bare`) and REPORTS the
`Exception` count as a tracked backlog number rather than pretending it is enforced.

VENDOR EXCLUSION IS LOAD-BEARING. The one `bare` hit was
`src/web/anima_dashboard/node_modules/flatted/python/flatted.py:81` — third-party code we neither
own nor should edit. Without the exclusion below this gate would report someone else's code on
every run, which is the same permanent-noise failure in a different costume.

Run:  python scripts/ci/check_stealth_excepts.py            # gate (exit 1 on violation)
      python scripts/ci/check_stealth_excepts.py --report   # always exit 0, print findings
      python scripts/ci/check_stealth_excepts.py --self-test # prove it can go RED before trusting GREEN
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]

# Blocking kinds. `Exception` is intentionally absent — see the module docstring.
GATED_KINDS = frozenset({"stealth-tuple", "bare"})

# Path fragments that mark code we did not write and must not gate on.
VENDOR_MARKERS = ("node_modules", "site-packages", "/vendor/", "/.venv/", "third_party")


def is_vendored(path: Path) -> bool:
    p = str(path).replace("\\", "/")
    return any(m in p for m in VENDOR_MARKERS)


def first_party_files(root: Path) -> list[Path]:
    return [p for p in root.rglob("*.py") if not is_vendored(p)]


def scan(root: Path) -> tuple[list[tuple[str, str]], int]:
    """Returns (gated violations, count of non-gated `Exception` catch-alls).

    The detector is imported lazily so this file needs no module-level ``sys.path`` surgery,
    which is what made the import block unsortable.
    """
    if str(REPO / "src") not in sys.path:
        sys.path.insert(0, str(REPO / "src"))
    from cohezion.compound.simplicity_audit import stealth_bare_excepts

    hits = stealth_bare_excepts(first_party_files(root))
    gated = [(loc, kind) for loc, kind in hits if kind in GATED_KINDS]
    catchalls = sum(1 for _, kind in hits if kind not in GATED_KINDS)
    return gated, catchalls


def self_test() -> int:
    """The gate must be able to go RED, and must not fire on the clean or vendored cases."""
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        dirty = root / "dirty.py"
        dirty.write_text(
            "def f():\n    try:\n        pass\n    except (ValueError, Exception):\n        pass\n"
        )
        gated, _ = scan(root)
        if not any(kind == "stealth-tuple" for _, kind in gated):
            print("SELF-TEST FAILED: did not flag a stealth tuple — it cannot go red.")
            ok = False
        dirty.unlink()

        clean = root / "clean.py"
        clean.write_text(
            "def f():\n    try:\n        pass\n    except (ValueError, KeyError):\n        pass\n"
        )
        gated, _ = scan(root)
        if gated:
            print(f"SELF-TEST FAILED: false-flagged a clean sibling-only tuple: {gated}")
            ok = False

        # A vendored copy of the SAME defect must be ignored, or the gate reports foreign code.
        vend = root / "node_modules" / "pkg"
        vend.mkdir(parents=True)
        (vend / "bad.py").write_text(
            "def f():\n    try:\n        pass\n    except:\n        pass\n"
        )
        gated, _ = scan(root)
        if gated:
            print(f"SELF-TEST FAILED: gated a vendored file: {gated}")
            ok = False

    if ok:
        print(
            "SELF-TEST OK: flags a stealth tuple, passes a sibling-only tuple, and ignores "
            "vendored code."
        )
        return 0
    return 1


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()
    report_only = "--report" in argv

    gated, catchalls = scan(REPO / "src")
    if gated:
        print(f"STEALTH-EXCEPT SCAN: {len(gated)} blocking violation(s):")
        for loc, kind in gated:
            print(f"  {loc}: [{kind}]")
        print(
            "\nL359: a tuple containing Exception/BaseException is semantically `except Exception:` "
            "— the supertype swallows its siblings. Name the 3-5 types you actually want to "
            "silence and let the rest propagate."
        )
    else:
        print("stealth-except scan OK — no bare or stealth-tuple excepts in first-party code.")
    print(f"(tracked, NOT gated: {catchalls} single `except Exception:` sites)")

    return 0 if (report_only or not gated) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
