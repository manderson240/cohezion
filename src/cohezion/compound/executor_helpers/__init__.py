"""Executor helper modules extracted from executor.py (Wave 2D).

These modules are imported by executor.py to keep the main pipeline file
focused on the 11-step orchestration logic. Public API of CompoundExecutor
is preserved — these are internal helpers.
"""

import contextlib

with contextlib.suppress(Exception):
    from cohezion.compound.executor_helpers.guardrail_runner import (
        run_async_guardrail as run_async_guardrail,
    )

with contextlib.suppress(Exception):
    from cohezion.compound.executor_helpers.template_matcher import (
        try_template_match as try_template_match,
    )

with contextlib.suppress(Exception):
    from cohezion.compound.executor_helpers.vault_integration import (
        fetch_experience_guidance as fetch_experience_guidance,
    )

with contextlib.suppress(Exception):
    from cohezion.compound.executor_helpers.refinement_reader import (
        load_refined_guidance as load_refined_guidance,
    )
