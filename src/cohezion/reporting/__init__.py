"""Report generation utilities -- package marker."""

# Wiring sweep (2026-06-06): re-export NightlyReporter so it is reachable by a STATIC import edge
# (was tests-only — no prod importer, empty __init__). `X as X` is the ruff-safe re-export form;
# imports are light (no load-time cost at package init).
from cohezion.reporting.nightly import NightlyReporter as NightlyReporter
