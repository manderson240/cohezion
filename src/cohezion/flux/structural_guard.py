"""Item 145: FLUX provider↔consumer metadata-contract guard — report-only (2026-06-08).

Structural-before-behavioral check (L366): for the vibe specifier consumer that reads
``block.metadata["workflow_id"]`` / ``["template_name"]``, determines which registered
``FluxProvider`` subclasses CAN ever satisfy it by inspecting their source code.

The check: does the provider's ``get_context`` method construct ``FluxBlock`` with a
``metadata=`` keyword argument?

  - YES → the provider CAN populate metadata → ``can_satisfy_specifier = True``
  - NO  → ``FluxBlock`` is constructed without ``metadata=`` → metadata stays ``{}``
          → the specifier can never extract ``workflow_id``/``template_name`` → False

This catches the 2026-06-07 bug (``CacheFlux`` did not set ``metadata=``, so the vibe
specifier always saw empty metadata — wasted a FLUX lookup) at harness time, before
any runtime plumbing is needed.

NON-FABRICATED: derived entirely from source inspection of each provider's
``get_context`` method.  No live instantiation, no asyncio, no writes.
"""

from __future__ import annotations

import inspect
import re


# Pattern to find `metadata=` as a keyword argument in a FluxBlock constructor call
# within get_context. We look for the literal `metadata=` in the source (not as part
# of a larger identifier like `metadata_field=`).
_METADATA_KWARG_PATTERN = re.compile(r"\bmetadata\s*=")


def flux_provider_metadata_guard(
    providers: dict[str, type],
) -> dict[str, bool]:
    """Return ``{provider_name: can_satisfy_vibe_specifier}`` via source inspection.

    For each provider class, inspects the source of its ``get_context`` method and
    checks whether ``metadata=`` appears as a keyword argument — i.e. whether the
    provider ever produces ``FluxBlock``s with non-empty metadata that could satisfy
    the vibe specifier consumer (``block.metadata.get("workflow_id")`` /
    ``["template_name"]``).

    Args:
        providers:
            ``{name: provider_class}`` mapping.  The class must have a
            ``get_context`` method whose source is accessible via ``inspect``.

    Returns:
        ``{name: bool}`` — ``True`` when the provider sets ``metadata=`` in its
        ``FluxBlock`` construction; ``False`` otherwise.

    Pure — source inspection only; no instantiation, no asyncio, no writes.
    Report-only / structural guard.
    """
    result: dict[str, bool] = {}
    for name, cls in providers.items():
        try:
            source = inspect.getsource(cls.get_context)
            result[name] = bool(_METADATA_KWARG_PATTERN.search(source))
        except (OSError, TypeError, AttributeError):
            # Source not available (C extension, dynamic class, etc.) — fail-safe False.
            result[name] = False
    return result
