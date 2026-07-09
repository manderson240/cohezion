"""Cohezion: Agentic AI framework with 12D FLUME universe simulation."""

import contextlib


__version__ = "1.0.0"

# Wiring-sweep 2026-06-22: branding.py was a genuine import-graph orphan (top-level).
with contextlib.suppress(Exception):
    from cohezion.branding import Colors as Colors
    from cohezion.branding import Identity as Identity
    from cohezion.branding import Motifs as Motifs
    from cohezion.branding import get_theme as get_theme
