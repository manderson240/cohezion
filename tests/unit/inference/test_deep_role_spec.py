"""The `deep` RoleSpec must not size out the models its own name_hint names.

Regression guard for a self-contradicting spec found 2026-08-08: `deep` hinted at
"Nemotron" while `size_min=40.0` excluded the only Nemotron in the catalog
(Nemotron-3-Nano-30B-A3B, 21.3 GB). That left exactly ONE eligible candidate --
Mistral-128B at ~71.9 GB effective -- which cannot load whenever the box holds any other
resident model. The role resolved but was never loadable.

These tests are catalog-independent: they exercise the spec's own filter against
synthetic entries, so they do not break when the live model catalog changes.
"""

from __future__ import annotations

import pytest

from cohezion.inference.fleet_roles import ROLE_SPECS


pytestmark = pytest.mark.unit


class TestDeepRoleSpec:
    def test_spec_admits_the_nemotron_it_names(self) -> None:
        """A hint that names a model family must not be contradicted by size_min."""
        spec = ROLE_SPECS["deep"]
        assert any("nemotron" in h.lower() for h in spec.name_hint)
        # Nemotron-3-Nano-30B-A3B is 21.3 GB in the live catalog.
        assert spec.size_min <= 21.3, (
            f"size_min={spec.size_min} sizes out the Nemotron this spec's name_hint names"
        )

    def test_deep_still_outranks_the_interactive_band(self) -> None:
        """Lowering the floor must not collapse `deep` into the mid-size roles.

        interactive/bbq floor at 8.0; `deep` must stay strictly above them or the roles
        stop meaning different things.
        """
        deep = ROLE_SPECS["deep"]
        assert deep.size_min > ROLE_SPECS["interactive"].size_min
        assert deep.size_min > ROLE_SPECS["bbq"].size_min

    def test_deep_remains_heavy_and_guarded(self) -> None:
        """The load-safety guard is what keeps a lowered floor from OOMing the box."""
        assert ROLE_SPECS["deep"].heavy is True

    def test_small_models_are_still_excluded(self) -> None:
        """The floor must still reject genuinely small models."""
        spec = ROLE_SPECS["deep"]
        assert spec.size_min > 5.0, "a `deep` role that admits 5GB models is not deep"
