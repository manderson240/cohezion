"""Simulation entrypoints -- package marker."""

import contextlib


with contextlib.suppress(Exception):
    from cohezion.simulations.regime_benchmark import RegimeBenchmark as RegimeBenchmark

with contextlib.suppress(Exception):
    from cohezion.simulations.surgical_benchmark import (
        SurgicalRegimeBenchmark as SurgicalRegimeBenchmark,
    )

with contextlib.suppress(Exception):
    from cohezion.simulations.symphony_max_benchmark import (
        SymphonyMaxBenchmark as SymphonyMaxBenchmark,
    )

with contextlib.suppress(Exception):
    from cohezion.simulations.sundarbans_restoration import MockRegimeProvider as MockRegimeProvider
