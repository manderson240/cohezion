"""Lunar viewing geometry from the Artemis II trajectory kernels (NAIF SPICE), replacing JPL Horizons.

The flash map needs, for a given UTC: the point on the Moon directly below Orion (sub-observer
longitude and latitude), Orion's distance from the Moon's centre, and the same sub-observer point
for Earth. These used to be typed in from JPL Horizons queries. This module computes them from:

  * ``art002_rec_260402_260410_jsc_bet_revf.bsp``: the reconstructed Orion trajectory (NAIF ID -24,
    JSC/FOD/NAV best-estimated trajectory rev F), plus its gap-fill companion. The main file has an
    11-second gap at 2026-04-07 00:54:48-00:55:00, inside the eclipse;
  * NAIF generic kernels: leap seconds, the DE440 planetary ephemeris, and the DE440 lunar
    orientation (binary PCK + frame kernel) that defines the Mean Earth/polar axis frame MOON_ME,
    the frame in which lunar longitudes are quoted.

Each kernel is downloaded once into the git-ignored ``data/spice/`` and checked against a pinned
SHA-256. NAIF publishes no checksums, so the pins were recorded on first download (2026-11-05).

Usage:
    python research/artemis2/spice_geometry.py      # prints the geometry and the Horizons comparison
"""

from __future__ import annotations

import hashlib
import urllib.request
from pathlib import Path

import spiceypy as sp


HERE = Path(__file__).resolve().parent
SPICE_DIR = HERE / "data" / "spice"
NAIF = "https://naif.jpl.nasa.gov/pub/naif/"
ORION = "-24"  # NAIF ID of the Artemis II Orion spacecraft in the trajectory kernel

# Load order matters: for overlapping coverage the LATER kernel wins, so the gap-fill SPK is
# loaded before the main one and only supplies the intervals the main one lacks.
KERNELS = {
    "naif0012.tls": NAIF + "generic_kernels/lsk/naif0012.tls",
    "de440s.bsp": NAIF + "generic_kernels/spk/planets/de440s.bsp",
    "pck00011.tpc": NAIF + "generic_kernels/pck/pck00011.tpc",
    "moon_pa_de440_200625.bpc": NAIF + "generic_kernels/pck/moon_pa_de440_200625.bpc",
    "moon_de440_250416.tf": NAIF + "generic_kernels/fk/satellites/moon_de440_250416.tf",
    "art002_rec_260402_260410_jsc_bet_revf_gapfill.bsp": NAIF
    + "ARTEMIS/kernels/spk/art002_rec_260402_260410_jsc_bet_revf_gapfill.bsp",
    "art002_rec_260402_260410_jsc_bet_revf.bsp": NAIF
    + "ARTEMIS/kernels/spk/art002_rec_260402_260410_jsc_bet_revf.bsp",
}
SHA256 = {  # recorded on first download, 2026-11-05
    "naif0012.tls": "678e32bdb5a744117a467cd9601cd6b373f0e9bc9bbde1371d5eee39600a039b",
    "de440s.bsp": "c1c7feeab882263fc493a9d5a5b2ddd71b54826cdf65d8d17a76126b260a49f2",
    "pck00011.tpc": "3dff7b1dbeceaa01f25467767d3fa25816051c85d162d1edf04acb310ee28bb1",
    "moon_pa_de440_200625.bpc": "60cd55aa401ea2ea97360636f567554bfe4e37bb829f901b4460a455dfaf783f",
    "moon_de440_250416.tf": "a47c71e9c9f33796bdafb2c9d69a7ee447b6016ecad80f71cd6f3e479f9cf768",
    "art002_rec_260402_260410_jsc_bet_revf_gapfill.bsp": "ac9e3f21302a6a510757fff41a9f8a55df907b75fb2142b8fdfc44a599ddc9b9",
    "art002_rec_260402_260410_jsc_bet_revf.bsp": "b8b3ebc4d703c3a73c9651b9da36114c3ef0b2c75f92873dd4970f32367aa7be",
}
MAX_BYTES = 60_000_000


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch() -> list[Path]:
    """Download any missing kernel and verify every kernel against its pinned SHA-256."""
    SPICE_DIR.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, url in KERNELS.items():
        path = SPICE_DIR / name
        if not path.exists():
            part = path.with_suffix(path.suffix + ".part")
            with urllib.request.urlopen(url, timeout=300) as resp:  # noqa: S310 -- fixed https URL
                body = resp.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                raise ValueError(f"{name}: larger than {MAX_BYTES} bytes")
            part.write_bytes(body)
            if name in SHA256 and _sha256(part) != SHA256[name]:
                part.unlink()
                raise ValueError(f"{name}: SHA-256 mismatch on download")
            part.replace(path)
        if name in SHA256 and _sha256(path) != SHA256[name]:
            raise ValueError(f"{name}: SHA-256 mismatch; delete {path} and re-run")
        paths.append(path)
    return paths


_loaded = False


def load() -> None:
    global _loaded
    if not _loaded:
        for path in fetch():
            sp.furnsh(str(path))
        _loaded = True


def sub_observer(utc: str, observer: str) -> dict:
    """Sub-observer point on the Moon (deg E, deg N, MOON_ME frame) and range to the Moon's centre.

    Light time and stellar aberration are corrected (``LT+S``), as for an apparent view.
    """
    load()
    et = sp.str2et(utc)
    point, _trgepc, _srfvec = sp.subpnt(
        "INTERCEPT/ELLIPSOID", "MOON", et, "MOON_ME", "LT+S", observer
    )
    _radius, lon, lat = sp.reclat(point)
    pos, _lt = sp.spkpos("MOON", et, "J2000", "LT+S", observer)
    return {
        "utc": utc,
        "sub_lon": float(sp.dpr() * lon) % 360,
        "sub_lat": float(sp.dpr() * lat),
        "range_km": float(sp.vnorm(pos)),
    }


def orion_view(utc: str) -> dict:
    return sub_observer(utc, ORION)


def earth_view(utc: str) -> dict:
    return sub_observer(utc, "EARTH")


def kernel_digests() -> dict[str, str]:
    return {p.name: _sha256(p) for p in fetch()}


if __name__ == "__main__":
    for t in ("2026-04-07T00:45", "2026-04-07T01:00", "2026-04-07T01:04", "2026-04-07T01:05"):
        o, e = orion_view(t), earth_view(t)
        print(f"{t}  Orion sub {o['sub_lon']:.4f}E {o['sub_lat']:.4f} range {o['range_km']:.1f} km"
              f" | Earth sub {e['sub_lon']:.4f}E {e['sub_lat']:.4f}")  # fmt: skip
    for name, digest in kernel_digests().items():
        print(f"    {name!r}: {digest!r},")
