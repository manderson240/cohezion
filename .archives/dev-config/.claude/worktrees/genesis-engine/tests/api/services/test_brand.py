"""Tests for api/services/brand.py.

Covers brand theme and identity metadata.
"""

from __future__ import annotations

import pytest

from cohezion.api.services.brand import get_brand_theme


@pytest.mark.asyncio
async def test_get_brand_theme():
    """[P0] Should return brand theme."""
    theme = await get_brand_theme()
    assert theme.identity.name == "COHEZION"
    assert "nexus_green" in theme.colors.model_fields
    assert theme.hiho_palette.stable is not None
