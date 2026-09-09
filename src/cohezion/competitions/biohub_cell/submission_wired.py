"""Biohub 3D Cell Tracking — WIRED submission kernel (real detections + lineage graph).

Reads the OME-Zarr v3 test volumes (T, Z, Y, X), detects cells per timepoint with a
classical CPU blob detector (Gaussian smooth -> adaptive threshold -> connected
components -> centroid), links consecutive timepoints with a global Hungarian bipartite
matcher that allows up to two daughters (mitosis), and writes ``submission.csv`` in the
Cell-Tracking-Challenge graph format the competition expects:

    id,dataset,row_type,node_id,t,z,y,x,source_id,target_id

    node row : one detected cell  -> node_id, (t,z,y,x) voxel coords, source_id=target_id=-1
    edge row : one lineage link   -> node_id=-1, t=z=y=x=-1, source_id -> target_id (node_ids)

CPU-only (classical Hungarian algorithm), no internet, no GPU. Every stage fails OPEN to a
minimal valid per-dataset stub so the file is never empty and always covers every dataset.

The Hungarian matcher is inlined from ``spatiotemporal_gnn.SpatiotemporalCellTracker``
because Kaggle script kernels upload a single code_file — additional repo modules are not
importable at scoring time.
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
SEARCH_RADIUS_UM = 30.0          # max frame-to-frame cell displacement for a valid link
SMOOTH_SIGMA = (1.0, 2.0, 2.0)   # Gaussian sigma (Z, Y, X) — anisotropic (Z coarser)
THRESH_PCTL = 99.0               # per-volume intensity percentile floor for the mask
MIN_VOXELS = 20                  # discard sub-nuclear noise specks
MAX_VOXELS = 20000               # discard merged/background blobs
SUBMISSION_COLUMNS = [
    "id", "dataset", "row_type", "node_id", "t", "z", "y", "x", "source_id", "target_id",
]


# ----------------------------------------------------------------------------------------
# Hungarian bipartite lineage matcher (inlined from spatiotemporal_gnn.py)
# ----------------------------------------------------------------------------------------
class SpatiotemporalCellTracker:
    """Global Hungarian bipartite matching with 2-daughter (mitosis) support."""

    def __init__(self, search_radius_um: float = SEARCH_RADIUS_UM):
        self.search_radius_um = search_radius_um
        self.feature_weights = np.array([0.5, 0.3, 0.2], dtype=np.float32)

    def compute_edge_cost(self, c0: dict[str, Any], c1: dict[str, Any]) -> float:
        p0, p1 = np.asarray(c0["centroid"]), np.asarray(c1["centroid"])
        dist = float(np.linalg.norm(p1 - p0))
        if dist > self.search_radius_um:
            return 1e6
        v0, v1 = c0.get("volume", 100.0), c1.get("volume", 100.0)
        i0, i1 = c0.get("mean_intensity", 1.0), c1.get("mean_intensity", 1.0)
        norm_dist = dist / max(1e-3, self.search_radius_um)
        norm_dvol = abs(v1 - v0) / max(1.0, v0)
        norm_dint = abs(i1 - i0) / max(0.1, i0)
        feats = np.array([norm_dist, norm_dvol, norm_dint], dtype=np.float32)
        return float(np.dot(feats, self.feature_weights))

    def resolve_lineage_matching(
        self, cells_t0: list[dict[str, Any]], cells_t1: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Globally optimal bipartite assignment t0 -> t1; returns parent/child edges."""
        from scipy.optimize import linear_sum_assignment

        if not cells_t0 or not cells_t1:
            return []
        n0, n1 = len(cells_t0), len(cells_t1)
        cost_matrix = np.full((n0 * 2, n1), 1e6, dtype=np.float32)
        for i, c0 in enumerate(cells_t0):
            for j, c1 in enumerate(cells_t1):
                cost = self.compute_edge_cost(c0, c1)
                cost_matrix[i, j] = cost
                cost_matrix[i + n0, j] = cost + 0.15  # small penalty for 2nd daughter
        row_ind, col_ind = linear_sum_assignment(cost_matrix)
        edges: list[dict[str, Any]] = []
        mother_counts: dict[Any, int] = {}
        for r, c in zip(row_ind, col_ind):
            if cost_matrix[r, c] < 1e5:
                src = cells_t0[r % n0]["id"]
                dst = cells_t1[c]["id"]
                mother_counts[src] = mother_counts.get(src, 0) + 1
                etype = "division" if mother_counts[src] == 2 else "continuation"
                edges.append({"parent": src, "child": dst, "type": etype})
        return edges


# ----------------------------------------------------------------------------------------
# Data access
# ----------------------------------------------------------------------------------------
def find_input_root() -> Path | None:
    """Locate the mounted competition data (internet-off mounts under /competitions/)."""
    candidates = [
        Path(f"/kaggle/input/competitions/{SLUG}"),
        Path(f"/kaggle/input/{SLUG}"),
    ]
    for c in candidates:
        if c.exists():
            return c
    # last resort: any /kaggle/input/* dir that contains a `test` folder with .zarr dirs
    base = Path("/kaggle/input")
    if base.exists():
        for child in base.iterdir():
            if (child / "test").exists():
                return child
    return None


def discover_datasets(root: Path) -> list[str]:
    """Dataset ids = the *.zarr directory stems under <root>/test."""
    test_dir = root / "test"
    if not test_dir.exists():
        return []
    return sorted(p.name[: -len(".zarr")] for p in test_dir.glob("*.zarr"))


def _report_environment() -> None:
    """Print which readers/decoders are available — surfaces the real Kaggle image in the log."""
    bits = []
    for name in ("zarr", "numcodecs", "blosc2", "blosc"):
        try:
            mod = __import__(name)
            bits.append(f"{name}={getattr(mod, '__version__', '?')}")
        except Exception:
            bits.append(f"{name}=MISSING")
    print("  env:", ", ".join(bits))


def _open_zarr_array(zarr_path: Path):
    """Open the level-0 array of an OME-Zarr, trying zarr>=3 then a manual blosc reader."""
    # Path 1: zarr-python (works only if the installed zarr can read a v3 store).
    try:
        import zarr

        grp = zarr.open_group(str(zarr_path), mode="r")
        arr = grp["0"]
        # Force a real read of one element so a v2-only zarr fails HERE, not mid-detection.
        _ = np.asarray(arr[0, 0, 0, 0])
        print(f"  reader=zarr v{getattr(zarr, '__version__', '?')}")
        return _ZarrArrayView(arr)
    except Exception as exc:
        print(f"  zarr path unusable ({type(exc).__name__}: {exc}); using manual reader")
    # Path 2: manual chunk reader (decode + reassemble from the chunk grid).
    return _ManualZarrReader(zarr_path / "0")


class _ZarrArrayView:
    """Thin uniform view over a zarr array."""

    def __init__(self, arr):
        self._arr = arr
        self.shape = tuple(int(s) for s in arr.shape)

    def timepoint(self, t: int) -> np.ndarray:
        return np.asarray(self._arr[t])


def _build_blosc_decoders():
    """Ordered (name, fn) blosc decoders — numcodecs is exactly what zarr's codec uses."""
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
    """Decode a zarr v3 array without zarr: blosc-decode each chunk, assemble the timepoint.

    Generalised over the chunk grid (does NOT assume one chunk per volume): a timepoint
    volume is reassembled from ALL of its (Z,Y,X) chunks. Every decode is size-validated
    against the expected chunk byte count, and a wrong/absent decoder RAISES loudly instead
    of silently reshaping still-compressed bytes (the v8 Kaggle failure mode).
    """

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
# Detection
# ----------------------------------------------------------------------------------------
def detect_cells(vol: np.ndarray, scale_zyx: np.ndarray) -> list[dict[str, Any]]:
    """Classical CPU blob detection -> list of cell dicts with voxel + micrometer coords."""
    from scipy import ndimage as ndi

    v = vol.astype(np.float32)
    sm = ndi.gaussian_filter(v, sigma=SMOOTH_SIGMA)
    thr = max(float(np.percentile(sm, THRESH_PCTL)), float(sm.mean() + 3.0 * sm.std()))
    mask = sm > thr
    lbl, n = ndi.label(mask)
    if n == 0:
        return []
    idx = np.arange(1, n + 1)
    sizes = ndi.sum(np.ones_like(lbl, dtype=np.float32), lbl, index=idx)
    coms = ndi.center_of_mass(v, lbl, index=idx)
    means = ndi.mean(v, lbl, index=idx)
    cells: list[dict[str, Any]] = []
    for sz, com, mi in zip(np.atleast_1d(sizes), np.atleast_2d(coms), np.atleast_1d(means)):
        if sz < MIN_VOXELS or sz > MAX_VOXELS:
            continue
        zyx = np.asarray(com, dtype=np.float64)
        cells.append(
            {
                "zyx": zyx,                       # voxel coords (for the CSV)
                "centroid": zyx * scale_zyx,      # micrometer coords (for the matcher)
                "volume": float(sz),
                "mean_intensity": float(mi),
            }
        )
    return cells


def _scale_zyx(zarr_path: Path) -> np.ndarray:
    """Read (Z,Y,X) micrometer voxel scale from the OME-Zarr multiscale metadata."""
    default = np.array([1.625, 0.40625, 0.40625], dtype=np.float64)
    try:
        meta = json.loads((zarr_path / "zarr.json").read_text())
        ms = meta["attributes"]["multiscales"][0]
        ct = ms["datasets"][0]["coordinateTransformations"]
        for tr in ct:
            if tr.get("type") == "scale":
                s = tr["scale"]
                return np.asarray(s[1:4], dtype=np.float64)  # drop T
    except Exception:
        pass
    return default


# ----------------------------------------------------------------------------------------
# Per-dataset graph construction
# ----------------------------------------------------------------------------------------
def build_dataset_graph(dataset: str, root: Path) -> list[dict[str, Any]]:
    """Return node+edge rows (sans global id) for one dataset."""
    zarr_path = root / "test" / f"{dataset}.zarr"
    scale = _scale_zyx(zarr_path)
    try:
        arr = _open_zarr_array(zarr_path)
        n_t = int(arr.shape[0])
    except Exception as exc:
        print(f"  [{dataset}] cannot open array ({exc}) -> stub")
        return _stub_rows(dataset)

    tracker = SpatiotemporalCellTracker(SEARCH_RADIUS_UM)
    node_rows: list[dict[str, Any]] = []
    edge_rows: list[dict[str, Any]] = []
    next_node_id = 1
    prev_cells: list[dict[str, Any]] = []  # each carries injected "id" == node_id

    for t in range(n_t):
        try:
            vol = arr.timepoint(t)
            cells = detect_cells(vol, scale)
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
    """Minimal valid 3-node / 2-edge lineage so the dataset is never absent/empty."""
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
    if root is None:
        print("No input mount found — emitting sample-shaped fallback for known datasets.")
        datasets = ["44b6_0113de3b", "44b6_0b24845f", "6bba_05b6850b", "6bba_05db0fb1"]
        rows = [r for d in datasets for r in _stub_rows(d)]
    else:
        datasets = discover_datasets(root)
        if not datasets:
            print(f"No .zarr datasets under {root}/test — sample-shaped fallback.")
            datasets = ["44b6_0113de3b", "44b6_0b24845f", "6bba_05b6850b", "6bba_05db0fb1"]
            rows = [r for d in datasets for r in _stub_rows(d)]
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
