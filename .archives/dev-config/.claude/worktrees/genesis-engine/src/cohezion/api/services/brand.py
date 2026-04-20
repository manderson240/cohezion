"""Brand API Service.

Single source of truth for Cohezion identity, derived from branding.py.
Serves the canonical theme for the Anima Dashboard including the
HIHO-reactive color palette used by the CSS bridge.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from cohezion.branding import Colors, Identity


brand_router = APIRouter(tags=["brand"])


class HIHOPalette(BaseModel):
    critical_low: str
    warning: str
    stable: str
    critical_high: str


class BrandColors(BaseModel):
    nexus_green: str
    matte_black: str
    silicon_silver: str
    earth_blue: str
    critical_red: str
    warning_gold: str
    plasma_blue: str
    neon_cyan: str


class BrandIdentity(BaseModel):
    name: str
    tagline: str
    philosophy: str
    sign_off: str


class BrandThemeResponse(BaseModel):
    colors: BrandColors
    identity: BrandIdentity
    hiho_palette: HIHOPalette


@brand_router.get("/theme", response_model=BrandThemeResponse)
async def get_brand_theme() -> BrandThemeResponse:
    """Return the canonical Cohezion brand theme."""
    return BrandThemeResponse(
        colors=BrandColors(
            nexus_green=Colors.NEXUS_GREEN,
            matte_black=Colors.MATTE_BLACK,
            silicon_silver=Colors.SILICON_SILVER,
            earth_blue=Colors.EARTH_BLUE,
            critical_red=Colors.CRITICAL_RED,
            warning_gold=Colors.WARNING_GOLD,
            plasma_blue=Colors.PLASMA_BLUE,
            neon_cyan=Colors.NEON_CYAN,
        ),
        identity=BrandIdentity(
            name=Identity.NAME,
            tagline=Identity.TAGLINE,
            philosophy=Identity.PHILOSOPHY,
            sign_off=Identity.SIGN_OFF,
        ),
        hiho_palette=HIHOPalette(
            critical_low=Colors.CRITICAL_RED,
            warning=Colors.WARNING_GOLD,
            stable=Colors.NEXUS_GREEN,
            critical_high=Colors.EARTH_BLUE,
        ),
    )
