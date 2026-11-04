# physics/ is research

This package holds physics-inspired and exploratory research: spinors, gauge and fiber-bundle
models, cosmogony, LENR, consciousness (Orch-OR) and similar ideas. It is not a claim about
physics, and the agent platform's guarantees (CI gates, review, routing, sandboxing) do not
depend on it being right.

A few modules are plain math the platform uses, such as `hiho_kernel.py` (4x(1-x), the scaled
variance of a Bernoulli variable). Some core packages still import research modules, mostly
from non-blocking telemetry steps in the compound executor.
[`tests/architecture/test_research_boundary.py`](../../../tests/architecture/test_research_boundary.py)
freezes that list so it can only shrink. See [`docs/architecture.md`](../../../docs/architecture.md),
section 7.
