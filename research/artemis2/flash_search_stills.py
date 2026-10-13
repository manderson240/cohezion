"""Search crew still frames taken around the impact-flash call-outs for point sources on the dark Moon.

During the eclipse the disk is dark, apart from Earthshine and the corona around it. No star
can appear in front of the Moon. So a point source inside the disk has three possible causes:
  * a persistent surface feature, at the same position relative to the disk in every frame;
  * a sensor artefact (hot pixel, cosmic ray), at a fixed or random position on the sensor;
  * a transient, present in one exposure only, at a position relative to the disk.

For each browse PNG, the script:
  1. locates the disk as the large dark, round region inside the corona;
  2. subtracts a median-filtered background inside 0.95 R;
  3. lists compact peaks above ``--k`` robust sigma.
Peaks are then grouped across frames in disk-relative coordinates. A peak seen in one frame
only is reported as a candidate for visual inspection, with a crop written to ``--crops``.

Usage:
    python research/artemis2/flash_search_stills.py PNG [PNG ...] [--k 8] [--out PATH] [--crops DIR]

Browse PNGs: https://d1ejlg980osaur.cloudfront.net/archive/artemis/artemis2/artemis2_crew_camera/browse/fd06/<id>_prc_v01.png
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage


Image.MAX_IMAGE_PIXELS = None
WORK = 2000  # px; frames are analysed at this width (keeps a 1-px flash at >=1/4 of its peak)
MATCH = 0.02  # disk radii; peaks closer than this across frames are the same feature


def grey(path: Path) -> tuple[np.ndarray, float]:
    im = Image.open(path).convert("L")
    scale = WORK / im.width
    im = im.resize((WORK, round(im.height * scale)), Image.Resampling.BOX)
    return np.asarray(im, dtype=float), scale


def find_disk(g: np.ndarray) -> tuple[float, float, float] | None:
    """Centre and radius of the dark disk, or None when no round dark region is present."""
    smooth = ndimage.uniform_filter(g, 15)
    corona = np.percentile(smooth, 99)
    if corona < 20:  # too dark to separate disk from sky
        return None
    dark = smooth < 0.25 * corona
    lab, _ = ndimage.label(dark)
    best = None
    for i, sl in enumerate(ndimage.find_objects(lab), start=1):
        h, w = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        touches = (
            sl[0].start == 0
            or sl[1].start == 0
            or sl[0].stop == g.shape[0]
            or sl[1].stop == g.shape[1]
        )
        if touches or min(h, w) < 100 or not 0.8 < h / w < 1.25:
            continue
        area = int((lab[sl] == i).sum())
        fill = area / (np.pi * h * w / 4)
        if fill > 0.85 and (best is None or area > best[0]):
            ys, xs = np.nonzero(lab == i)
            best = (area, float(xs.mean()), float(ys.mean()), float(np.sqrt(area / np.pi)))
    return None if best is None else best[1:]


def peaks(g: np.ndarray, disk: tuple[float, float, float], k: float) -> list[dict]:
    cx, cy, r = disk
    yy, xx = np.mgrid[: g.shape[0], : g.shape[1]]
    inside = np.hypot(xx - cx, yy - cy) < 0.95 * r
    resid = g - ndimage.median_filter(g, size=9)
    vals = resid[inside]
    mad = float(np.median(np.abs(vals - np.median(vals)))) * 1.4826 or 1.0
    mask = inside & (resid > k * mad) & (resid > 3)
    lab, _ = ndimage.label(mask)
    out = []
    for i, sl in enumerate(ndimage.find_objects(lab), start=1):
        blob = lab[sl] == i
        if blob.sum() > 25:  # extended structure, not a point
            continue
        sub = np.where(blob, resid[sl], 0)
        y, x = np.unravel_index(int(sub.argmax()), sub.shape)
        x, y = sl[1].start + int(x), sl[0].start + int(y)
        out.append({
            "x": x, "y": y, "excess": round(float(resid[y, x]), 1), "sigma": round(float(resid[y, x] / mad), 1),
            "u": round((x - cx) / r, 4), "v": round((y - cy) / r, 4),
        })  # fmt: skip
    return out


def group(frames: list[dict]) -> list[dict]:
    """Count, for each peak, frames sharing its disk spot and its sensor pixel.

    A peak repeated at the same sensor pixel is a hot pixel, even when the camera moved
    and its disk-relative position changed. Candidates must be unique in both frames.
    """
    pts = [(fi, p) for fi, f in enumerate(frames) for p in f["peaks"]]
    for _fi, p in pts:
        seen = {fj for fj, q in pts if np.hypot(p["u"] - q["u"], p["v"] - q["v"]) < MATCH}
        p["frames_with_same_disk_spot"] = len(seen)
        p["frames_with_same_sensor_px"] = len({
            fj for fj, q in pts if abs(p["x"] - q["x"]) <= 2 and abs(p["y"] - q["y"]) <= 2
        })  # fmt: skip
    return [
        dict(frame=frames[fi]["file"], **p)
        for fi, p in pts
        if p["frames_with_same_disk_spot"] == 1 and p["frames_with_same_sensor_px"] == 1
    ]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("pngs", type=Path, nargs="+")
    ap.add_argument("--k", type=float, default=8.0)
    ap.add_argument(
        "--out", type=Path, default=Path(__file__).resolve().parent / "flash_search_stills.json"
    )
    ap.add_argument("--crops", type=Path, default=None)
    ap.add_argument("--full", action="store_true", help="also write every peak in every frame")
    args = ap.parse_args()

    frames = []
    for path in sorted(args.pngs):
        g, _ = grey(path)
        disk = find_disk(g)
        rec = {
            "file": path.name,
            "disk": None if disk is None else [round(v, 1) for v in disk],
            "peaks": [],
        }
        if disk is not None:
            rec["peaks"] = peaks(g, disk, args.k)
        frames.append(rec)
        print(path.name, rec["disk"], len(rec["peaks"]))
    singles = group(frames)
    if args.crops:
        args.crops.mkdir(parents=True, exist_ok=True)
        for c in singles:
            g, _ = grey(next(p for p in args.pngs if p.name == c["frame"]))
            x, y = c["x"], c["y"]
            crop = g[max(0, y - 40) : y + 40, max(0, x - 40) : x + 40]
            crop = np.clip((crop - crop.min()) * 255 / max(1.0, np.ptp(crop)), 0, 255).astype(
                np.uint8
            )
            Image.fromarray(crop).resize((240, 240), Image.Resampling.NEAREST).save(
                args.crops / f"{Path(c['frame']).stem}_{x}_{y}.png"
            )
    if not args.full:  # per-frame peak lists are bulky; keep counts plus the candidates
        frames = [
            {**{k: v for k, v in f.items() if k != "peaks"}, "n_peaks": len(f["peaks"])}
            for f in frames
        ]
    result = {
        "k_sigma": args.k,
        "frames": frames,
        "frames_with_disk": sum(f["disk"] is not None for f in frames),
        "single_frame_peaks": singles,
    }
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    print(
        "frames with disk:",
        result["frames_with_disk"],
        "of",
        len(frames),
        "| single-frame peaks:",
        len(singles),
    )


if __name__ == "__main__":
    main()
