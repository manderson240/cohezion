"""Artemis II eclipse impact-flash map: crew annotation -> approximate lunar coordinates.

The crew marked the lunar impact flashes they saw during the 2026-04-07 solar eclipse
on a OneNote base render (PDS annotation ``art002e016252_pcd_ann_v01.pdf``). Each crew
member used their own colour: Jeremy Hansen red, Reid Wiseman blue, "Ike" (Victor Glover)
green. The render is a perspective view of the Moon for 7 Apr 2026 01:04:00 UTC, and it
includes a drawn lunar equator and two meridians.

How it works:
  1. Download the PDF and check its MD5, then pull out the embedded JPEG (one DCT stream).
  2. Find the coloured markers by thresholding colour.
  3. Trace the lit limb, the drawn equator and the two drawn meridians, and fit a sphere
     projection to them. The sub-observer point is fixed from JPL Horizons (target 301,
     observer 500@-1024 Artemis II). The fit leaves free the disk centre, the disk radius,
     the roll angle and the two meridian longitudes.
  4. Invert the projection at each marker.

The fit is checked independently: with the view fixed from Horizons, the drawn meridians
come out near 90E and 180E, which is a 90-degree grid. A second model forces them to
exactly 90/180 and fits the view longitude instead. The spread between the two models is
reported as systematic uncertainty.

Flash numbers were read by eye from the handwriting. Each marker is assigned to the nearest
numbered anchor, so this step is a human transcription, not an automatic one.

Usage:
    python research/artemis2/flash_map.py [--data-dir DIR] [--out PATH]
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.optimize import least_squares


BASE = "https://d1ejlg980osaur.cloudfront.net/archive/artemis/artemis2/artemis2_mission_audio/annotations/"
PDF = "art002e016252_pcd_ann_v01.pdf"
# Pinned on first download (2026-10-11). The audio bundle publishes no MD5 manifest
# that we could reach, so this is trust-on-first-use. It still detects later drift.
PDF_MD5 = "02faddc88e725cd5e0d508eec025aa09"

# JPL Horizons, COMMAND='301' CENTER='500@-1024' QUANTITIES='13,14,17,20', fetched 2026-10-11.
# Columns: UTC, ObsSub-LON (deg E), ObsSub-LAT (deg), NP.ang (deg), delta (au)
HORIZONS = [
    ("2026-04-07T00:45", 129.274236, -3.632802, 339.0952, 0.00007288001021),
    ("2026-04-07T01:00", 124.452893, -3.595490, 338.6122, 0.00007737717301),
    ("2026-04-07T01:05", 122.966602, -3.579186, 338.4909, 0.00007893668369),
]
RENDER_FRACTION = 4 / 5  # 01:04 lies 4/5 of the way from 01:00 to 01:05
AU_KM = 149_597_870.7
MOON_RADIUS_KM = 1737.4

# Handwritten flash number -> anchor pixel (in the 1966x1310 embedded image), read by eye.
ANCHORS = {
    "1": (1103, 782),
    "2": (846, 742),
    "3": (1241, 740),
    "4": (970, 922),
    "5": (1060, 339),
}
ANCHOR_RADIUS = 80  # px; a marker farther than this from every anchor is reported unassigned
OBSERVERS = {"red": "Hansen", "blue": "Wiseman", "green": "Glover"}
NOTES = {
    "1": "one of 'these three roughly 10 min into eclipse' (~00:45 UTC)",
    "2": "one of the first three (~00:45 UTC); circled: 'likely same impacts' (two observers)",
    "3": "one of the first three (~00:45 UTC)",
    "4": "'(later)'; circled: 'likely same impacts' (three observers)",
    "5": "'towards end' of the eclipse (eclipse ended ~01:32 UTC)",
}


def _md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes(), usedforsecurity=False).hexdigest()


def fetch(data_dir: Path) -> Path:
    data_dir.mkdir(parents=True, exist_ok=True)
    dest = data_dir / PDF
    if not dest.exists():
        part = dest.with_suffix(".part")
        with urllib.request.urlopen(BASE + PDF, timeout=60) as resp:  # noqa: S310 - fixed https URL
            part.write_bytes(resp.read(5_000_000))
        part.rename(dest)
    if _md5(dest) != PDF_MD5:
        raise ValueError(f"{PDF}: MD5 mismatch")
    return dest


def embedded_jpeg(pdf: Path) -> np.ndarray:
    """Return the single embedded DCT (JPEG) image as an RGB int array."""
    raw = pdf.read_bytes()
    start = raw.index(b"\xff\xd8\xff")
    end = raw.index(b"endstream", start)
    return np.asarray(Image.open(io.BytesIO(raw[start:end])).convert("RGB")).astype(int)


def horizons_view() -> dict:
    a, b = HORIZONS[1], HORIZONS[2]
    lerp = lambda i: a[i] + (b[i] - a[i]) * RENDER_FRACTION  # noqa: E731
    return {
        "utc": "2026-04-07T01:04",
        "sub_lon": lerp(1),
        "sub_lat": lerp(2),
        "np_ang": lerp(3),
        "range_km": lerp(4) * AU_KM,
    }


# ---------------------------------------------------------------- image measurement
def markers(im: np.ndarray) -> list[dict]:
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    roi = np.zeros(r.shape, bool)
    roi[280:1050, 590:1380] = True
    masks = {
        "red": (r > 110) & (r - g > 50) & (r - b > 30),
        "blue": (b > 150) & (b - r > 60) & (g < 190),
        "green": (g > 100) & (g - r > 40) & (g - b > 20),
    }
    found = []
    for colour, m in masks.items():
        lab, n = ndimage.label(ndimage.binary_closing(m & roi, iterations=2))
        for i in range(1, n + 1):
            ys, xs = np.nonzero(lab == i)
            if len(xs) < 6:
                continue
            x, y = float(xs.mean()), float(ys.mean())
            dist = {k: np.hypot(x - ax, y - ay) for k, (ax, ay) in ANCHORS.items()}
            flash = min(dist, key=dist.get)
            found.append(
                {
                    "colour": colour,
                    "observer": OBSERVERS[colour],
                    "px": [round(x, 1), round(y, 1)],
                    "n_px": len(xs),
                    "flash": flash if dist[flash] <= ANCHOR_RADIUS else None,
                }
            )
    return found


def _ridge(row: np.ndarray, lo: int, hi: int) -> int:
    seg = row[lo:hi].astype(float)
    base = np.convolve(seg, np.ones(25) / 25, "same")
    return lo + int(np.argmax(seg - base))


def grid_points(im: np.ndarray) -> dict[str, list[tuple[float, float]]]:
    g = im.sum(2)
    lum = im.mean(2)
    limb = []
    for y in range(350, 980, 15):  # lit (left) limb only; the night limb is invisible
        idx = np.nonzero(lum[y, 575:1050] > 25)[0]
        if len(idx):
            limb.append((575.0 + idx[0], float(y)))
    eq = [(float(x), 600.0 + float(np.argmax(g[600:670, x]))) for x in range(660, 1280, 15)]
    m_left = [(float(_ridge(g[y], 740, 880)), float(y)) for y in range(440, 640, 12)]
    m_right = [(float(_ridge(g[y], 1180, 1345)), float(y)) for y in range(375, 640, 12)]
    return {"limb": limb, "equator": eq, "meridian_left": m_left, "meridian_right": m_right}


# ---------------------------------------------------------------- sphere projection
def _scale(dist):
    """Factor mapping the projected limb to unit radius (1 for an orthographic view)."""
    return 1.0 if dist is None else float(np.sqrt(1 - 1 / dist**2))


def project(lam, phi, cx, cy, radius, roll, lc, pc, dist=None):
    """Project (lon, lat) [rad] for a view centred on (lc, pc).

    dist is the observer's distance from the Moon's centre in lunar radii; None gives the
    orthographic limit. From Orion (~6.8 radii) the visible cap ends 81.5 deg from the disk
    centre, not 90, so perspective matters. `radius` is the apparent limb radius in pixels.
    Returns (X, Y, visible) where visible > 0 for points on the near cap.
    """
    x = np.cos(phi) * np.sin(lam - lc)
    y = np.cos(pc) * np.sin(phi) - np.sin(pc) * np.cos(phi) * np.cos(lam - lc)
    z = np.sin(pc) * np.sin(phi) + np.cos(pc) * np.cos(phi) * np.cos(lam - lc)
    if dist is None:
        vis, k = z, 1.0
    else:
        vis, k = z - 1 / dist, dist / (dist - z) * _scale(dist)
    xr = (x * np.cos(roll) - y * np.sin(roll)) * k
    yr = (x * np.sin(roll) + y * np.cos(roll)) * k
    return cx + radius * xr, cy - radius * yr, vis


def invert(px, py, cx, cy, radius, roll, lc, pc, dist=None):
    xr, yr = (px - cx) / radius, (cy - py) / radius
    u = xr * np.cos(roll) + yr * np.sin(roll)
    v = -xr * np.sin(roll) + yr * np.cos(roll)
    rho2 = u * u + v * v
    if rho2 > 1:
        return None
    if dist is None:
        x, y, z = u, v, np.sqrt(1 - rho2)  # z toward observer
    else:
        # ray from the observer at (0, 0, dist) through (u, v) on the image plane
        up, vp = u / _scale(dist), v / _scale(dist)
        s2, d2 = up * up + vp * vp, dist * dist
        t = (d2 - np.sqrt(max(d2 * d2 - (s2 + d2) * (d2 - 1), 0.0))) / (s2 + d2)
        x, y, z = t * up, t * vp, dist * (1 - t)
    phi = np.arcsin(np.clip(y * np.cos(pc) + z * np.sin(pc), -1, 1))
    lam = lc + np.arctan2(x, z * np.cos(pc) - y * np.sin(pc))
    return float(np.degrees(lam) % 360), float(np.degrees(phi)), float(np.sqrt(rho2))


def great_circle_deg(a, b) -> float:
    """Angular separation in degrees between two (lon_E, lat) points in degrees."""
    l1, p1, l2, p2 = map(np.radians, (a[0], a[1], b[0], b[1]))
    c = np.sin(p1) * np.sin(p2) + np.cos(p1) * np.cos(p2) * np.cos(l1 - l2)
    return float(np.degrees(np.arccos(np.clip(c, -1.0, 1.0))))


def _curve_dist(pts, lam, phi, p, lc, pc, dist):
    X, Y, v = project(lam, phi, *p, lc, pc, dist)
    X, Y = X[v > 0], Y[v > 0]
    return [float(np.min(np.hypot(X - a, Y - b))) for a, b in pts]


def residuals(pts, p, lc, pc, mer_lons, dist=None):
    cx, cy, radius = p[:3]
    t = np.linspace(-np.pi, np.pi, 3000)
    ph = np.linspace(-np.pi / 2, np.pi / 2, 3000)
    res = [np.hypot(a - cx, b - cy) - radius for a, b in pts["limb"]]
    res += _curve_dist(pts["equator"], t, np.zeros_like(t), p, lc, pc, dist)
    for key, lon in zip(("meridian_left", "meridian_right"), mer_lons, strict=True):
        res += _curve_dist(pts[key], np.full_like(ph, np.radians(lon)), ph, p, lc, pc, dist)
    return np.asarray(res)


def fit_models(pts: dict, view: dict) -> dict:
    pc = np.radians(view["sub_lat"])
    lc_h = np.radians(view["sub_lon"])
    dist = view["range_km"] / MOON_RADIUS_KM if view.get("range_km") else None
    p0 = [987.0, 658.0, 366.0, 0.0]

    # Model A: view from Horizons, meridian longitudes free (independent grid check)
    sa = least_squares(
        lambda q: residuals(pts, q[:4], lc_h, pc, (q[4], q[5]), dist),
        [*p0, 90.0, 180.0],
        loss="soft_l1",
        f_scale=3,
    )
    # Model B: meridians forced to 90E / 180E, view longitude free
    sb = least_squares(
        lambda q: residuals(pts, q[:4], q[4], pc, (90.0, 180.0), dist),
        [*p0, lc_h],
        loss="soft_l1",
        f_scale=3,
    )
    return {
        "A": {
            "params": sa.x[:4].tolist(),
            "lc": float(lc_h),
            "pc": float(pc),
            "dist": dist,
            "meridians_deg": [float(sa.x[4]), float(sa.x[5])],
            "median_abs_resid_px": float(np.median(np.abs(sa.fun))),
        },
        "B": {
            "params": sb.x[:4].tolist(),
            "lc": float(sb.x[4]),
            "pc": float(pc),
            "dist": dist,
            "meridians_deg": [90.0, 180.0],
            "median_abs_resid_px": float(np.median(np.abs(sb.fun))),
        },
    }


def locate(found: list[dict], models: dict) -> dict:
    out = {}
    for flash in sorted(ANCHORS):
        marks = [m for m in found if m["flash"] == flash]
        if not marks:  # no dot assigned: report it rather than write NaN coordinates
            out[flash] = {"observers": [], "markers": [], "note": NOTES[flash], "models": None}
            continue
        per_model = {}
        for name, mdl in models.items():
            pts = [
                invert(*m["px"], *mdl["params"], mdl["lc"], mdl["pc"], mdl["dist"]) for m in marks
            ]
            pts = [p for p in pts if p is not None]
            lons = np.unwrap(np.radians([p[0] for p in pts]))
            per_model[name] = {
                "lon_E": round(float(np.degrees(lons.mean()) % 360), 1),
                "lat": round(float(np.mean([p[1] for p in pts])), 1),
                "disk_radius_frac": round(float(np.mean([p[2] for p in pts])), 3),
            }
        lons_all = [per_model[k]["lon_E"] for k in per_model]
        lats_all = [per_model[k]["lat"] for k in per_model]
        a = models["A"]
        observer_spread = [
            invert(*m["px"], *a["params"], a["lc"], a["pc"], a["dist"]) for m in marks
        ]
        observer_spread = [p for p in observer_spread if p is not None]
        out[flash] = {
            "observers": sorted({m["observer"] for m in marks}),
            "markers": marks,
            "note": NOTES[flash],
            "models": per_model,
            "lon_E_range": [min(lons_all), max(lons_all)],
            "lat_range": [min(lats_all), max(lats_all)],
            "inter_observer_spread_deg": round(
                float(
                    max(
                        (
                            great_circle_deg(p[:2], q[:2])
                            for p in observer_spread
                            for q in observer_spread
                        ),
                        default=0.0,
                    )
                ),
                1,
            ),
        }
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    here = Path(__file__).resolve().parent
    ap.add_argument("--data-dir", type=Path, default=here / "data")
    ap.add_argument("--out", type=Path, default=here / "flash_annotations.json")
    args = ap.parse_args()

    im = embedded_jpeg(fetch(args.data_dir))
    view = horizons_view()
    found = markers(im)
    pts = grid_points(im)
    models = fit_models(pts, view)
    result = {
        "source": BASE + PDF,
        "source_md5": PDF_MD5,
        "image_px": [int(im.shape[1]), int(im.shape[0])],
        "render_time_utc": view["utc"],
        "horizons_view": {k: round(v, 4) if isinstance(v, float) else v for k, v in view.items()},
        "horizons_at_flashes_1_3": dict(
            zip(("utc", "sub_lon", "sub_lat", "np_ang", "range_au"), HORIZONS[0], strict=True)
        ),
        "grid_points_n": {k: len(v) for k, v in pts.items()},
        "models": {
            k: {
                "cx_cy_R_px": [round(x, 1) for x in v["params"][:3]],
                "roll_deg": round(float(np.degrees(v["params"][3])), 2),
                "view_lon_E": round(float(np.degrees(v["lc"]) % 360), 2),
                "meridians_deg": [round(x, 1) for x in v["meridians_deg"]],
                "median_abs_resid_px": round(v["median_abs_resid_px"], 2),
            }
            for k, v in models.items()
        },
        "flashes": locate(found, models),
        "unassigned_markers": [m for m in found if m["flash"] is None],
        "caveats": [
            "Positions are hand-placed dots on a pre-made planning render, not measurements.",
            "Model A fixes the view from Horizons; model B forces the drawn grid to 90E/180E. Their spread is systematic.",
            "Precision of the crew's hand placement is unknown and probably dominates near the limb.",
            "Flashes #1-#3 were seen ~00:45 UTC; the render is for 01:04. Surface coordinates are unaffected.",
        ],
    }
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    for k, v in result["models"].items():
        print(k, v)
    for k, v in result["flashes"].items():
        print(f"#{k} {v['observers']} lon {v.get('lon_E_range')} lat {v.get('lat_range')}")
    print("unassigned:", result["unassigned_markers"])


if __name__ == "__main__":
    main()
