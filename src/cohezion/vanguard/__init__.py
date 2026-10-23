"""Vanguard — source discovery, attribution, and sandbox validation."""

import contextlib


with contextlib.suppress(Exception):
    from cohezion.vanguard.attribution import AttributedRecord as AttributedRecord
    from cohezion.vanguard.attribution import AttributionEngine as AttributionEngine
    from cohezion.vanguard.attribution import AttributionMetadata as AttributionMetadata
    from cohezion.vanguard.attribution import LicenseStatus as LicenseStatus

with contextlib.suppress(Exception):
    from cohezion.vanguard.connectors import GitHubTrendingConnector as GitHubTrendingConnector
    from cohezion.vanguard.connectors import HuggingFaceConnector as HuggingFaceConnector
    from cohezion.vanguard.connectors import VanguardScoutReport as VanguardScoutReport

with contextlib.suppress(Exception):
    from cohezion.vanguard.sandbox_validation import SubstrateSandbox as SubstrateSandbox
    from cohezion.vanguard.sandbox_validation import ValidationReport as ValidationReport
    from cohezion.vanguard.sandbox_validation import ValidationVerdict as ValidationVerdict

with contextlib.suppress(Exception):
    from cohezion.vanguard.source_connector import DiscoveryRecord as DiscoveryRecord
    from cohezion.vanguard.source_connector import SourceConnector as SourceConnector
    from cohezion.vanguard.source_connector import SourceHealth as SourceHealth

# Public surface = each module's primary class (tests/vanguard/test_vanguard_wiring.py).
# Filtered so a failed guarded import above never lists a missing name.
__all__ = [
    name
    for name in ("AttributionEngine", "SourceConnector", "SubstrateSandbox", "VanguardScoutReport")
    if name in globals()
]
