"""Reporting — nightly report generation."""

import contextlib


with contextlib.suppress(Exception):
    from cohezion.reporting.nightly import NightlyReporter as NightlyReporter
