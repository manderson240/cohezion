"""Cohezion patterns — hermetic design patterns and fractal component protocols."""

import contextlib

# Wiring-sweep 2026-06-22: hermetic_design_patterns.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.patterns.hermetic_design_patterns import (
        CorrespondencePattern as CorrespondencePattern,
    )
    from cohezion.patterns.hermetic_design_patterns import (
        DesignIntention as DesignIntention,
    )
    from cohezion.patterns.hermetic_design_patterns import (
        FractalPattern as FractalPattern,
    )
    from cohezion.patterns.hermetic_design_patterns import (
        IntentionalClass as IntentionalClass,
    )
    from cohezion.patterns.hermetic_design_patterns import (
        MentalismPattern as MentalismPattern,
    )
