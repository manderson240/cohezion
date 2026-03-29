"""Generate brand assets from branding.py single source of truth.

Produces: favicons, CSS custom properties, OG image placeholder.
Run: uv run python scripts/generate_brand_assets.py
"""

from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image

from cohezion.branding import Colors


logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOGO_SRC = PROJECT_ROOT / "apps" / "webapp" / "src" / "logo.png"
PUBLIC_DIR = PROJECT_ROOT / "src" / "web" / "anima_dashboard" / "public"


def generate_favicons() -> None:
    """Resize logo to standard favicon sizes and generate ICO."""
    img = Image.open(LOGO_SRC)
    sizes = {
        "favicon-16x16.png": 16,
        "favicon-32x32.png": 32,
        "android-chrome-192x192.png": 192,
        "android-chrome-512x512.png": 512,
    }
    for name, size in sizes.items():
        resized = img.resize((size, size), Image.Resampling.LANCZOS)
        resized.save(PUBLIC_DIR / name)
        logger.info("Generated %s", name)

    ico_img = img.resize((256, 256), Image.Resampling.LANCZOS)
    ico_img.save(
        PUBLIC_DIR / "cohezion-favicon.ico",
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48), (256, 256)],
    )
    logger.info("Generated cohezion-favicon.ico")


def generate_css_tokens() -> None:
    """Emit CSS custom properties from Colors class."""
    tokens = []
    for attr in dir(Colors):
        if attr.startswith("_"):
            continue
        value = getattr(Colors, attr)
        if isinstance(value, str) and value.startswith("#"):
            css_name = attr.lower().replace("_", "-")
            tokens.append(f"  --color-{css_name}: {value};")

    css = ":root {\n" + "\n".join(sorted(tokens)) + "\n}\n"
    out = PUBLIC_DIR / "brand-tokens.css"
    out.write_text(css)
    logger.info("Generated brand-tokens.css with %d tokens", len(tokens))


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    generate_favicons()
    generate_css_tokens()
    logger.info("Brand asset pipeline complete.")


if __name__ == "__main__":
    main()
