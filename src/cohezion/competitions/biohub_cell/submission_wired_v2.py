"""Biohub 3D Cell Tracking — WIRED submission kernel v2 (quantile-normalized peak detection).

Improvements over ``submission_wired.py`` (which scored 0.423), grounded in the OFFICIAL
scorer (``royerlab/kaggle-cell-tracking-competition`` ``metrics.py``):

    Final score = adjusted_edge_jaccard + 0.1 * division_jaccard
    - a predicted NODE matches a GT node by centroid distance <= 7 um (bipartite),
      with the physical voxel scale (Z,Y,X)=(1.625,0.40625,0.40625) applied by the scorer;
    - a predicted EDGE is TP iff both endpoints match GT nodes joined by a GT edge AND the
      link is correct; a link to the wrong target is FP; edges not touching a GT-edge node
      are IGNORED (no penalty); GT is SPARSE;
    - adj = jaccard * (1 - 0.1 * (N_pred - N_true) / N_true) penalizes over-detection.

Two changes, both evidence-backed:

1. DETECTION — quantile-normalize each volume by its OWN baked ``image_statistics.quantiles``
   (``norm=(v-q001)/(q999-q001)``) then take anisotropic local-max peaks. This replaces v1's
   single GLOBAL 99th-percentile raw-intensity threshold, which collapsed to ~1 detection on
   ``44b6_0b24845f`` (a volume whose intensity distribution is shifted high/compressed:
   q0.1=1095, q0.99=2902, max=3867 — the global percentile landed near the max). Verified
   locally on all 4 test volumes: 44b6_0b24845f goes 1 -> ~120 detections; the other three
   stay near their v1 density, and every peak sits at a nucleus centre (better than v1's
   connected-component blob centroids, which merge touching nuclei). This mirrors the royerlab
   reference detector, which normalizes by q001/q999 before peak extraction.

2. LINKING — v1 duplicated EVERY t0 cell (always 2 daughters), manufacturing a spurious
   second-daughter edge whenever a cheap 2nd assignment existed. Under this metric a second
   edge from a non-dividing (continuation) parent is a FALSE POSITIVE edge, so indiscriminate
   duplication directly inflates edge FP. v2 does a distance-gated 1-to-1 Hungarian assignment
   (each t+1 node gets at most ONE parent, no merges), then a CONSERVATIVE division pass that
   only adds a second daughter when a still-unmatched t+1 cell lies within a tight radius of a
   parent — keeping division recall without flooding edge FP.

CPU-only, no internet, no GPU. Every stage fails OPEN to a minimal valid per-dataset stub so
the file is never empty and always covers every dataset. Reads OME-Zarr v3 via a manual
blosc decoder (the Kaggle image ships blosc2 only).

Submission columns (Cell-Tracking-Challenge graph format):

    id,dataset,row_type,node_id,t,z,y,x,source_id,target_id
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


# ----------------------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------------------
SLUG = "biohub-cell-tracking-during-development"

# --- detection ---
SMOOTH_SIGMA = (1.0, 2.0, 2.0)   # Gaussian sigma (Z, Y, X) — anisotropic (Z coarser)
DET_THRESH_NORM = 0.50           # threshold on the quantile-normalized, smoothed image
#   PRIMARY UNMEASURED KNOB: raise -> fewer, higher-confidence detections (lower N_pred,
#   safer adjustment term, sparse-GT philosophy); lower -> higher recall. Sweep on Kaggle.
#   Local single-frame counts @0.5: 138 / 123 / 34 / 258 across the 4 test volumes.
PEAK_SEP_UM = 5.0                # min physical separation between peaks (< 7um match radius)
FALLBACK_Q_LO_PCTL = 0.1         # per-volume quantile fallback when baked stats are absent
FALLBACK_Q_HI_PCTL = 99.9

# --- linking ---
LINK_GATE_UM = 10.0              # max frame-to-frame centroid displacement for a 1-1 link
DIVISION_RADIUS_UM = 6.0         # tight radius for a conservative 2nd-daughter (division)

# Debug/validation knob only: cap frames per dataset. None == all frames (the kernel default).
# Overridable via env for local smoke tests; NEVER set in the Kaggle kernel.
import os as _os  # noqa: E402
MAX_FRAMES: int | None = (
    int(_os.environ["COHEZION_BIOHUB_MAX_FRAMES"])
    if _os.environ.get("COHEZION_BIOHUB_MAX_FRAMES")
    else None
)

SUBMISSION_COLUMNS = [
    "id", "dataset", "row_type", "node_id", "t", "z", "y", "x", "source_id", "target_id",
]
DEFAULT_SCALE = np.array([1.625, 0.40625, 0.40625], dtype=np.float64)  # (Z, Y, X) micrometers


# ----------------------------------------------------------------------------------------
# Lineage linking — distance-gated 1-1 Hungarian + conservative division
# ----------------------------------------------------------------------------------------
class SpatiotemporalCellTracker:
    """Distance-only bipartite linker.

    Stage 1: globally optimal 1-to-1 assignment (t0 -> t1) gated at ``LINK_GATE_UM`` — each
    t1 cell receives at most one parent (no merges), each t0 at most one primary child.
    Stage 2: a conservative division pass adds a SECOND daughter for a t0 cell only when a
    still-unmatched t1 cell lies within ``DIVISION_RADIUS_UM`` — so speculative second edges
    (which are FP under this metric for non-dividing cells) stay rare.
    """

    def __init__(
        self, gate_um: float = LINK_GATE_UM, division_radius_um: float = DIVISION_RADIUS_UM
    ):
        self.gate_um = gate_um
        self.division_radius_um = division_radius_um

    @staticmethod
    def _pairwise_um(cells_t0: list[dict[str, Any]], cells_t1: list[dict[str, Any]]) -> np.ndarray:
        p0 = np.asarray([c["centroid"] for c in cells_t0], dtype=np.float64)  # (n0, 3) um
        p1 = np.asarray([c["centroid"] for c in cells_t1], dtype=np.float64)  # (n1, 3) um
        # (n0, n1) euclidean distance in micrometers
        return np.linalg.norm(p0[:, None, :] - p1[None, :, :], axis=2)

    def resolve_lineage_matching(
        self, cells_t0: list[dict[str, Any]], cells_t1: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        from scipy.optimize import linear_sum_assignment

        if not cells_t0 or not cells_t1:
            return []
        dist = self._pairwise_um(cells_t0, cells_t1)
        _, n1 = dist.shape
        big = 1e6
        # Gate: distances beyond the gate become effectively infinite so they are never chosen.
        cost = np.where(dist <= self.gate_um, dist, big).astype(np.float64)

        # --- Stage 1: optimal 1-1 assignment ---
        row_ind, col_ind = linear_sum_assignment(cost)
        edges: list[dict[str, Any]] = []
        matched_t1: set[int] = set()
        parent_of_col: dict[int, int] = {}
        for r, c in zip(row_ind, col_ind):
            if cost[r, c] < big:
                edges.append({"parent": cells_t0[r]["id"], "child": cells_t1[c]["id"],
                              "type": "continuation"})
                matched_t1.add(c)
                parent_of_col[c] = r

        # --- Stage 2: conservative division (second daughter) ---
        # A still-unmatched t1 cell that is within DIVISION_RADIUS of an already-parented t0
        # cell, and closer to that parent than to any other t0 cell, becomes a 2nd daughter.
        # The division radius is clamped to the link gate so a division can never exceed it.
        div_radius = min(self.division_radius_um, self.gate_um)
        for c in range(n1):
            if c in matched_t1:
                continue
            r = int(np.argmin(dist[:, c]))
            if dist[r, c] > div_radius:
                continue
            if r not in set(parent_of_col.values()):
                continue  # parent must already have a (continuation) child to be a division
            edges.append({"parent": cells_t0[r]["id"], "child": cells_t1[c]["id"],
                          "type": "division"})
            matched_t1.add(c)
        return edges


# ----------------------------------------------------------------------------------------
# Data access  (manual blosc reader — Kaggle image ships blosc2 only)
# ----------------------------------------------------------------------------------------
def find_input_root() -> Path | None:
    candidates = [
        Path(f"/kaggle/input/competitions/{SLUG}"),
        Path(f"/kaggle/input/{SLUG}"),
    ]
    for c in candidates:
        if c.exists():
            return c
    base = Path("/kaggle/input")
    if base.exists():
        for child in base.iterdir():
            if (child / "test").exists():
                return child
    return None


def discover_datasets(root: Path) -> list[str]:
    test_dir = root / "test"
    if not test_dir.exists():
        return []
    return sorted(p.name[: -len(".zarr")] for p in test_dir.glob("*.zarr"))


def _report_environment() -> None:
    bits = []
    for name in ("zarr", "numcodecs", "blosc2", "blosc"):
        try:
            mod = __import__(name)
            bits.append(f"{name}={getattr(mod, '__version__', '?')}")
        except Exception:
            bits.append(f"{name}=MISSING")
    print("  env:", ", ".join(bits))


def _open_zarr_array(zarr_path: Path):
    try:
        import zarr

        grp = zarr.open_group(str(zarr_path), mode="r")
        arr = grp["0"]
        _ = np.asarray(arr[0, 0, 0, 0])
        print(f"  reader=zarr v{getattr(zarr, '__version__', '?')}")
        return _ZarrArrayView(arr)
    except Exception as exc:
        print(f"  zarr path unusable ({type(exc).__name__}: {exc}); using manual reader")
    return _ManualZarrReader(zarr_path / "0")


class _ZarrArrayView:
    def __init__(self, arr):
        self._arr = arr
        self.shape = tuple(int(s) for s in arr.shape)

    def timepoint(self, t: int) -> np.ndarray:
        return np.asarray(self._arr[t])


def _build_blosc_decoders():
    decoders = []
    try:
        from numcodecs import Blosc

        _b = Blosc()
        decoders.append(("numcodecs", _b.decode))
    except Exception:
        pass
    try:
        import blosc2

        decoders.append(("blosc2", blosc2.decompress2))
    except Exception:
        pass
    try:
        import blosc

        decoders.append(("python-blosc", blosc.decompress))
    except Exception:
        pass
    return decoders


class _ManualZarrReader:
    """Decode a zarr v3 array without zarr: blosc-decode each chunk, assemble the timepoint."""

    def __init__(self, array_dir: Path):
        meta = json.loads((array_dir / "zarr.json").read_text())
        self.array_dir = array_dir
        self.shape = tuple(int(s) for s in meta["shape"])
        self.chunk = tuple(int(s) for s in meta["chunk_grid"]["configuration"]["chunk_shape"])
        self.dtype = np.dtype(meta["data_type"])
        self.sep = (
            meta.get("chunk_key_encoding", {}).get("configuration", {}).get("separator", "/")
        )
        self._chunk_nbytes = int(np.prod(self.chunk)) * self.dtype.itemsize
        has_blosc = any(c.get("name") == "blosc" for c in meta.get("codecs", []))
        self._decoders = _build_blosc_decoders() if has_blosc else [("raw", bytes)]
        print(f"  manual reader: chunk={self.chunk} decoders={[d[0] for d in self._decoders]}")
        if not self._decoders:
            raise RuntimeError("no blosc decoder available (need numcodecs, blosc2, or blosc)")

    def _decode_chunk(self, comp: bytes) -> np.ndarray:
        last = None
        for name, fn in self._decoders:
            try:
                out = bytes(fn(comp))
            except Exception as exc:
                last = f"{name}: {exc}"
                continue
            if len(out) == self._chunk_nbytes:
                return np.frombuffer(out, dtype=self.dtype).reshape(self.chunk)
            last = f"{name}: got {len(out)} bytes, expected {self._chunk_nbytes}"
        raise RuntimeError(f"chunk decode failed with all decoders ({last})")

    def timepoint(self, t: int) -> np.ndarray:
        _, cz, cy, cx = self.chunk
        _, z, y, x = self.shape
        vol = np.zeros((z, y, x), dtype=self.dtype)
        t_idx = t // self.chunk[0]
        n_kz, n_ky, n_kx = -(-z // cz), -(-y // cy), -(-x // cx)  # ceil-div chunk counts
        for kz in range(n_kz):
            for ky in range(n_ky):
                for kx in range(n_kx):
                    key = self.sep.join(["c", str(t_idx), str(kz), str(ky), str(kx)])
                    path = self.array_dir / key
                    if not path.exists():
                        continue  # missing chunk -> fill_value 0
                    block = self._decode_chunk(path.read_bytes())[0]  # drop T axis
                    z0, y0, x0 = kz * cz, ky * cy, kx * cx
                    zs, ys, xs = min(cz, z - z0), min(cy, y - y0), min(cx, x - x0)
                    vol[z0:z0 + zs, y0:y0 + ys, x0:x0 + xs] = block[:zs, :ys, :xs]
        return vol


# ----------------------------------------------------------------------------------------
# Detection — quantile-normalized anisotropic local-max peaks
# ----------------------------------------------------------------------------------------
def _peak_kernel(scale_zyx: np.ndarray, sep_um: float) -> tuple[int, int, int]:
    """Odd per-axis voxel kernel for a physical peak-separation of ``sep_um`` micrometers."""
    k = []
    for s in scale_zyx:
        v = max(1, int(round(sep_um / float(s))))
        if v % 2 == 0:
            v += 1
        k.append(v)
    return (k[0], k[1], k[2])


def detect_cells(
    vol: np.ndarray, scale_zyx: np.ndarray, q_lo: float, q_hi: float
) -> list[dict[str, Any]]:
    """Quantile-normalize -> smooth -> anisotropic local-max peaks. One peak == one nucleus."""
    from scipy import ndimage as ndi

    v = vol.astype(np.float32)
    denom = float(q_hi - q_lo)
    if denom <= 1e-6:  # degenerate stats -> fall back to this volume's own spread
        q_lo = float(np.percentile(v, FALLBACK_Q_LO_PCTL))
        q_hi = float(np.percentile(v, FALLBACK_Q_HI_PCTL))
        denom = max(1e-6, float(q_hi - q_lo))
    norm = (v - q_lo) / denom
    np.clip(norm, 0.0, None, out=norm)

    sm = ndi.gaussian_filter(norm, sigma=SMOOTH_SIGMA)
    ksz = _peak_kernel(scale_zyx, PEAK_SEP_UM)
    mx = ndi.maximum_filter(sm, size=ksz, mode="nearest")
    peaks = (sm == mx) & (sm > DET_THRESH_NORM)
    coords = np.argwhere(peaks)  # (N, 3) voxel (z, y, x)
    if coords.shape[0] == 0:
        return []

    cells: list[dict[str, Any]] = []
    for zyx in coords:
        zyx_f = zyx.astype(np.float64)
        cells.append(
            {
                "zyx": zyx_f,                       # voxel coords (for the CSV)
                "centroid": zyx_f * scale_zyx,      # micrometer coords (for the matcher)
                "intensity": float(sm[zyx[0], zyx[1], zyx[2]]),
            }
        )
    return cells


def _read_zarr_meta(zarr_path: Path) -> tuple[np.ndarray, float, float]:
    """Return (scale_zyx, q001, q999) from the OME-Zarr metadata; robust defaults on failure."""
    scale = DEFAULT_SCALE.copy()
    q_lo, q_hi = float("nan"), float("nan")
    try:
        meta = json.loads((zarr_path / "zarr.json").read_text())
        attrs = meta.get("attributes", {})
        ms = attrs["multiscales"][0]
        ct = ms["datasets"][0]["coordinateTransformations"]
        for tr in ct:
            if tr.get("type") == "scale":
                scale = np.asarray(tr["scale"][1:4], dtype=np.float64)  # drop T
        q = attrs.get("image_statistics", {}).get("quantiles", {})
        if "0.001" in q and "0.999" in q:
            q_lo, q_hi = float(q["0.001"]), float(q["0.999"])
    except Exception:
        pass
    return scale, q_lo, q_hi


# ----------------------------------------------------------------------------------------
# Per-dataset graph construction
# ----------------------------------------------------------------------------------------
def build_dataset_graph(dataset: str, root: Path) -> list[dict[str, Any]]:
    zarr_path = root / "test" / f"{dataset}.zarr"
    scale, q_lo, q_hi = _read_zarr_meta(zarr_path)
    have_stats = q_lo == q_lo and q_hi == q_hi  # not NaN
    try:
        arr = _open_zarr_array(zarr_path)
        n_t = int(arr.shape[0])
        if MAX_FRAMES is not None:
            n_t = min(n_t, MAX_FRAMES)
    except Exception as exc:
        print(f"  [{dataset}] cannot open array ({exc}) -> stub")
        return _stub_rows(dataset)

    tracker = SpatiotemporalCellTracker()
    node_rows: list[dict[str, Any]] = []
    edge_rows: list[dict[str, Any]] = []
    next_node_id = 1
    prev_cells: list[dict[str, Any]] = []

    for t in range(n_t):
        try:
            vol = arr.timepoint(t)
            if not have_stats:  # per-volume fallback quantiles
                q_lo = float(np.percentile(vol, FALLBACK_Q_LO_PCTL))
                q_hi = float(np.percentile(vol, FALLBACK_Q_HI_PCTL))
            cells = detect_cells(vol, scale, q_lo, q_hi)
        except Exception as exc:
            print(f"  [{dataset}] t={t} detection failed ({exc})")
            cells = []
        for c in cells:
            c["id"] = next_node_id
            z, y, x = (int(np.rint(v)) for v in c["zyx"])
            node_rows.append(
                {
                    "dataset": dataset, "row_type": "node", "node_id": next_node_id,
                    "t": t, "z": z, "y": y, "x": x, "source_id": -1, "target_id": -1,
                }
            )
            next_node_id += 1
        if prev_cells and cells:
            for e in tracker.resolve_lineage_matching(prev_cells, cells):
                edge_rows.append(
                    {
                        "dataset": dataset, "row_type": "edge", "node_id": -1,
                        "t": -1, "z": -1, "y": -1, "x": -1,
                        "source_id": e["parent"], "target_id": e["child"],
                    }
                )
        prev_cells = cells

    if not node_rows:
        print(f"  [{dataset}] no detections at all -> stub")
        return _stub_rows(dataset)
    print(f"  [{dataset}] {len(node_rows)} nodes, {len(edge_rows)} edges over {n_t} frames")
    return node_rows + edge_rows


def _stub_rows(dataset: str) -> list[dict[str, Any]]:
    nodes = [
        {"dataset": dataset, "row_type": "node", "node_id": k, "t": k - 1,
         "z": 32, "y": 128, "x": 128, "source_id": -1, "target_id": -1}
        for k in (1, 2, 3)
    ]
    edges = [
        {"dataset": dataset, "row_type": "edge", "node_id": -1, "t": -1, "z": -1,
         "y": -1, "x": -1, "source_id": 1, "target_id": 2},
        {"dataset": dataset, "row_type": "edge", "node_id": -1, "t": -1, "z": -1,
         "y": -1, "x": -1, "source_id": 2, "target_id": 3},
    ]
    return nodes + edges


# ----------------------------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------------------------
def build_submission(root: Path | None = None) -> pd.DataFrame:
    _report_environment()
    root = root or find_input_root()
    known = ["44b6_0113de3b", "44b6_0b24845f", "6bba_05b6850b", "6bba_05db0fb1"]
    if root is None:
        print("No input mount found — emitting sample-shaped fallback for known datasets.")
        rows = [r for d in known for r in _stub_rows(d)]
    else:
        datasets = discover_datasets(root)
        if not datasets:
            print(f"No .zarr datasets under {root}/test — sample-shaped fallback.")
            rows = [r for d in known for r in _stub_rows(d)]
        else:
            print(f"Datasets: {datasets}")
            rows = []
            for d in datasets:
                rows.extend(build_dataset_graph(d, root))
    df = pd.DataFrame(rows)
    df.insert(0, "id", np.arange(len(df)))
    return df[SUBMISSION_COLUMNS]


def main() -> None:
    df = build_submission()
    out = "submission.csv"
    df.to_csv(out, index=False)
    n_nodes = int((df["row_type"] == "node").sum())
    n_edges = int((df["row_type"] == "edge").sum())
    print(f"Wrote {out}: {len(df)} rows ({n_nodes} nodes, {n_edges} edges) "
          f"across {df['dataset'].nunique()} datasets.")


if __name__ == "__main__":
    sys.exit(main())
