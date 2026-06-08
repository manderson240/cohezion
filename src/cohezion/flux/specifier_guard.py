"""FLUX provider↔consumer metadata-contract guard (backlog item 145, 2026-06-08).

Structural-before-behavioral (L366): the regression guard for the CacheFlux/specifier mismatch
found in the 2026-06-07 build tick. The vibe specifier consumer reads
``block.metadata["workflow_id"]`` / ``["template_name"]`` when filtering FLUX context — so a
provider whose ``get_context`` never populates ``metadata=`` can NEVER satisfy it (CacheFlux blocks
carried empty metadata, and the specifier silently matched nothing).

``flux_specifier_satisfiability`` inspects each registered ``FluxProvider``'s ``get_context``
SOURCE and reports whether it constructs a block with a populated ``metadata=`` (so it CAN carry
the specifier keys). CacheFlux → False (no metadata set), HistoryFlux/SurrealFlux/ToolFlux/VaultFlux
→ True. Report-only, $0, pure source inspection — catches the contract gap at harness time instead
of by manual tracing. NON-FABRICATED: derived from each provider's actual ``get_context`` source.
"""

from __future__ import annotations

import inspect
from typing import Any


def _populates_metadata(get_context_fn: Any) -> bool:
    """True iff the ``get_context`` source constructs a block with a populated ``metadata=``.

    A provider that sets no ``metadata=`` at all, or only an empty ``metadata={}`` /
    ``metadata=None``, can never carry the specifier's ``workflow_id``/``template_name`` keys.
    """
    try:
        src = inspect.getsource(get_context_fn)
    except (OSError, TypeError):
        return False
    return "metadata=" in src and "metadata={}" not in src and "metadata=None" not in src


def flux_specifier_satisfiability(providers: list[type] | None = None) -> dict[str, bool]:
    """Per ``FluxProvider``, can its ``get_context`` EVER satisfy the vibe specifier's metadata read?

    Returns ``{provider_class_name: can_satisfy}``. ``can_satisfy`` is True iff ``get_context``
    populates ``FluxBlock.metadata=`` (so it can carry ``workflow_id``/``template_name``).
    ``providers=None`` discovers the live ``FluxProvider`` subclasses. Report-only, pure source
    inspection (no instantiation, no I/O).
    """
    if providers is None:
        import importlib
        import pkgutil

        import cohezion.flux.providers as _pkg

        for mod in pkgutil.iter_modules(_pkg.__path__):
            importlib.import_module(f"cohezion.flux.providers.{mod.name}")
        from cohezion.flux.provider import FluxProvider

        providers = list(FluxProvider.__subclasses__())

    return {cls.__name__: _populates_metadata(cls.get_context) for cls in providers}
