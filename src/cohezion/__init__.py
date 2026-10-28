"""Cohezion: Agentic AI framework with 12D FLUME universe simulation."""

import contextlib
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _dist_version


# Derived, never hand-maintained. A literal here is a second source of truth that decays the
# moment pyproject.toml is bumped and nothing forces the edit: commit 9c3e33ed9 ("semver
# alignment ... version sync") set it to 1.0.2, pyproject then went 1.0.2 -> 1.1.0 -> 1.2.0,
# and this string never followed. Reading the installed dist metadata removes the duplicate
# rather than adding a guard over two numbers.
try:
    __version__ = _dist_version("cohezion")
except PackageNotFoundError:  # source tree with no install (e.g. bare PYTHONPATH=src)
    __version__ = "0+unknown"

# Secret redaction is process-wide and order-independent: every LogRecord is redacted at
# creation. Cheap (logging + re only). See cohezion/_redaction.py for why this is not a filter.
from cohezion._redaction import install_record_redaction as _install_record_redaction


_install_record_redaction()

# Wiring-sweep 2026-06-22: branding.py was a genuine import-graph orphan (top-level).
with contextlib.suppress(Exception):
    from cohezion.branding import Colors as Colors
    from cohezion.branding import Identity as Identity
    from cohezion.branding import Motifs as Motifs
    from cohezion.branding import get_theme as get_theme
