"""Offline tests for research/artemis2/flash_map.py (no network, synthetic geometry).

The tests pin the logic that the flash coordinates depend on:
  - projection and inverse projection are mutual inverses;
  - the grid fit recovers known meridian longitudes from synthetic grid points;
  - the colour-marker detector finds a dot and assigns it to the nearest flash anchor.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest


_PATH = Path(__file__).resolve().parents[3] / "research" / "artemis2" / "flash_map.py"
_spec = importlib.util.spec_from_file_location("flash_map", _PATH)
fm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fm)

VIEW = {"sub_lon": 123.26, "sub_lat": -3.58}
PARAMS = (987.0, 658.0, 367.0, 0.0)


@pytest.mark.parametrize(
    ("lon", "lat"), [(123.0, 0.0), (144.0, -22.0), (100.0, -16.0), (143.0, 55.0), (190.0, -50.0)]
)
def test_invert_is_inverse_of_project(lon, lat):
    lc, pc = np.radians(VIEW["sub_lon"]), np.radians(VIEW["sub_lat"])
    x, y, vis = fm.project(np.radians(lon), np.radians(lat), *PARAMS, lc, pc)
    assert vis > 0
    back = fm.invert(float(x), float(y), *PARAMS, lc, pc)
    assert back is not None
    assert back[0] == pytest.approx(lon, abs=1e-6)
    assert back[1] == pytest.approx(lat, abs=1e-6)


def test_invert_rejects_off_disk_pixel():
    lc, pc = np.radians(VIEW["sub_lon"]), np.radians(VIEW["sub_lat"])
    assert fm.invert(PARAMS[0] + PARAMS[2] * 1.01, PARAMS[1], *PARAMS, lc, pc) is None


def _synthetic_grid(meridians=(90.0, 180.0)):
    lc, pc = np.radians(VIEW["sub_lon"]), np.radians(VIEW["sub_lat"])
    limb_t = np.radians(np.arange(110, 250, 8))
    pts = {
        "limb": [
            (PARAMS[0] + PARAMS[2] * np.cos(t), PARAMS[1] - PARAMS[2] * np.sin(t)) for t in limb_t
        ]
    }
    lon = np.radians(np.arange(40, 210, 8))
    x, y, v = fm.project(lon, np.zeros_like(lon), *PARAMS, lc, pc)
    pts["equator"] = list(zip(x[v > 0], y[v > 0], strict=True))
    lat = np.radians(np.arange(5, 60, 5))
    for key, m in zip(("meridian_left", "meridian_right"), meridians, strict=True):
        x, y, v = fm.project(np.full_like(lat, np.radians(m)), lat, *PARAMS, lc, pc)
        pts[key] = list(zip(x[v > 0], y[v > 0], strict=True))
    return pts


def test_grid_fit_recovers_drawn_meridians():
    models = fm.fit_models(_synthetic_grid(), VIEW)
    left, right = models["A"]["meridians_deg"]
    assert left == pytest.approx(90.0, abs=0.5)
    assert right == pytest.approx(180.0, abs=0.5)
    assert np.degrees(models["B"]["lc"]) == pytest.approx(VIEW["sub_lon"], abs=0.5)


def test_grid_fit_distinguishes_a_different_grid():
    """A grid drawn at 60E/150E must not be reported as 90E/180E."""
    left, right = fm.fit_models(_synthetic_grid((60.0, 150.0)), VIEW)["A"]["meridians_deg"]
    assert left == pytest.approx(60.0, abs=0.5)
    assert right == pytest.approx(150.0, abs=0.5)


def test_marker_detection_assigns_nearest_anchor():
    im = np.zeros((1310, 1966, 3), dtype=int)
    ax, ay = fm.ANCHORS["3"]
    im[ay - 4 : ay + 4, ax - 4 : ax + 4] = (220, 30, 30)  # a red dot on flash #3
    found = fm.markers(im)
    assert len(found) == 1
    assert found[0]["colour"] == "red"
    assert found[0]["observer"] == "Hansen"
    assert found[0]["flash"] == "3"


def test_great_circle_separation():
    assert fm.great_circle_deg((0.0, 0.0), (90.0, 0.0)) == pytest.approx(90.0)
    assert fm.great_circle_deg((10.0, 89.999), (190.0, 89.999)) == pytest.approx(0.002, abs=1e-3)


DIST = 11762.1 / 1737.4  # Orion's range at 01:04 UTC, in lunar radii


@pytest.mark.parametrize(
    ("lon", "lat"), [(123.0, 0.0), (102.0, -15.0), (141.0, 52.0), (195.0, 5.0)]
)
def test_perspective_invert_is_inverse_of_project(lon, lat):
    lc, pc = np.radians(VIEW["sub_lon"]), np.radians(VIEW["sub_lat"])
    x, y, vis = fm.project(np.radians(lon), np.radians(lat), *PARAMS, lc, pc, DIST)
    assert vis > 0
    back = fm.invert(float(x), float(y), *PARAMS, lc, pc, DIST)
    assert back[0] == pytest.approx(lon, abs=1e-6)
    assert back[1] == pytest.approx(lat, abs=1e-6)


def test_perspective_limb_is_closer_than_90_degrees():
    """From ~6.8 lunar radii a point 85 deg from the disk centre is already out of sight."""
    lc, pc = np.radians(VIEW["sub_lon"]), 0.0
    _, _, vis_ortho = fm.project(lc + np.radians(85), 0.0, *PARAMS, lc, pc)
    _, _, vis_persp = fm.project(lc + np.radians(85), 0.0, *PARAMS, lc, pc, DIST)
    assert vis_ortho > 0
    assert vis_persp < 0
