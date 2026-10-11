"""Search the Orion SAW3 eclipse video for single-event optical transients (impact flashes).

The two SAW3 recordings ``art002m1010962338`` (channel 1) and ``art002m1020962338``
(channel 2) run from 2026-04-06 23:38:11 to 2026-04-07 01:37:5x UTC. That span covers the
whole solar eclipse seen from Orion (~00:35 to ~01:32 UTC), which is when the crew reported
five impact flashes. Both channels carry the same camera view, so a real flash has to
appear in both at the same moment. Compression or downlink artefacts are independent per
channel and cannot pass that test.

Detector:
  * Decode greyscale frames with ffmpeg and pool them 2x (3x3 dilation, then subsample),
    so point sources keep their peak value.
  * Reference for frame k = per-pixel MAX over frames k-12..k-6 and k+6..k+12. A transient
    shorter than about 6 frames (100 ms at 59.94 fps) is brighter than everything around
    it. Steady stars, Earthshine and slow drifts are not.
  * excess = frame - reference. A candidate is a connected blob with excess >= ``--thr`` DN
    and area <= ``MAX_AREA`` pooled pixels. Frames with more than ``MAX_BLOBS`` blobs are
    logged as scene changes (slews, exposure steps) rather than as flashes.
  * Cross-match: a candidate is CORROBORATED only when the other channel has one within
    +/-3 frames and 4 pooled pixels.

Usage:
    python research/artemis2/flash_search_video.py CH1.mp4 CH2.mp4 \
        [--start 00:35:00] [--stop 01:33:00] [--thr 20] [--out PATH]

The videos are 2.9 GB each and are not downloaded by this script. URLs are in VIDEO_URLS.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
from scipy import ndimage


BASE = "https://d1ejlg980osaur.cloudfront.net/archive/artemis/artemis2/artemis2_orion_camera/data_video/fd06/"
VIDEO_URLS = {
    "ch1": BASE + "channel1/art002m1010962338_saw3_raw_v01.mp4",
    "ch2": BASE + "channel2/art002m1020962338_saw3_raw_v01.mp4",
}
VIDEO_START = datetime(2026, 4, 6, 23, 38, 11, tzinfo=UTC)  # label start_date_time (whole seconds)
FPS = 60000 / 1001
W, H = 1280, 720
POOL = 2
NEAR, FAR = 6, 12  # reference window: frames k-FAR..k-NEAR and k+NEAR..k+FAR
MAX_AREA = 40  # pooled px; impact flashes are unresolved points
MAX_BLOBS = 15  # more blobs than this in one frame = global change, not a flash
CHUNK = 1800  # frames per decoded block (~30 s)
MATCH_FRAMES, MATCH_PX = 3, 4


def utc_at(frame: int) -> datetime:
    return VIDEO_START + timedelta(seconds=frame / FPS)


def frame_at(t: datetime) -> int:
    return round((t - VIDEO_START).total_seconds() * FPS)


def decode(path: Path, first: int, count: int) -> np.ndarray:
    """Decode `count` greyscale frames from frame index `first`, pooled by POOL.

    A 3x3 dilation (local max) followed by 2x nearest-neighbour subsampling keeps every
    pixel's value represented, so a one-pixel flash keeps its peak brightness.
    """
    cmd = [
        "ffmpeg", "-v", "error", "-ss", f"{first / FPS:.4f}", "-i", str(path),
        "-frames:v", str(count), "-map", "0:v:0", "-an",
        "-vf", f"format=gray,dilation,scale={W // POOL}:{H // POOL}:flags=neighbor", "-f", "rawvideo", "-",
    ]  # fmt: skip
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    w, h = W // POOL, H // POOL
    n = len(raw) // (w * h)
    return np.frombuffer(raw[: n * w * h], np.uint8).reshape(n, h, w)


def transients(frames: np.ndarray, offset: int, thr: int) -> tuple[list[dict], list[int]]:
    """Candidates for frames FAR..len-FAR-1 of the block; `offset` is the block's first frame."""
    width = FAR - NEAR + 1
    side_max = ndimage.maximum_filter1d(frames, size=width, axis=0, mode="nearest")
    shift = (FAR + NEAR) // 2
    found, busy = [], []
    for k in range(FAR, len(frames) - FAR):
        ref = np.maximum(side_max[k - shift], side_max[k + shift])
        excess = frames[k].astype(np.int16) - ref
        mask = excess >= thr
        if not mask.any():
            continue
        lab, n = ndimage.label(mask)
        if n > MAX_BLOBS:
            busy.append(offset + k)
            continue
        for i, sl in enumerate(ndimage.find_objects(lab), start=1):
            blob = lab[sl] == i
            area = int(blob.sum())
            if area > MAX_AREA:
                continue
            ex = np.where(blob, excess[sl], 0)
            yy, xx = np.unravel_index(int(ex.argmax()), ex.shape)
            found.append(
                {
                    "frame": offset + k,
                    "x": (sl[1].start + int(xx)) * POOL,
                    "y": (sl[0].start + int(yy)) * POOL,
                    "excess": int(ex.max()),
                    "peak": int(frames[k][sl][blob].max()),
                    "area_px": area * POOL * POOL,
                }
            )
    return found, busy


def scan(path: Path, start: int, stop: int, thr: int) -> dict:
    cands, busy, means = [], [], []
    first = start - FAR
    while first < stop - FAR:
        n = min(CHUNK + 2 * FAR, stop + FAR - first)
        block = decode(path, first, n)
        if len(block) <= 2 * FAR:
            break
        c, b = transients(block, first, thr)
        cands += [x for x in c if start <= x["frame"] < stop]
        busy += [f for f in b if start <= f < stop]
        means += [(first + i, float(block[i].mean())) for i in range(FAR, len(block) - FAR, 60)]
        first += len(block) - 2 * FAR
    return {"candidates": cands, "busy_frames": busy, "mean_level_1hz": means}


def cross_match(a: list[dict], b: list[dict]) -> list[dict]:
    out = []
    for x in a:
        for y in b:
            if (
                abs(x["frame"] - y["frame"]) <= MATCH_FRAMES
                and np.hypot(x["x"] - y["x"], x["y"] - y["y"]) <= MATCH_PX * POOL
            ):
                out.append(
                    {
                        "ch1": x,
                        "ch2": y,
                        "utc": utc_at(x["frame"]).isoformat(timespec="milliseconds"),
                    }
                )
                break
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("ch1", type=Path)
    ap.add_argument("ch2", type=Path)
    ap.add_argument("--start", default="00:35:00", help="UTC on 2026-04-07")
    ap.add_argument("--stop", default="01:33:00", help="UTC on 2026-04-07")
    ap.add_argument("--thr", type=int, default=20)
    ap.add_argument(
        "--out", type=Path, default=Path(__file__).resolve().parent / "flash_search_video.json"
    )
    args = ap.parse_args()

    day = datetime(2026, 4, 7, tzinfo=UTC)
    t0 = day + timedelta(
        hours=int(args.start[:2]), minutes=int(args.start[3:5]), seconds=int(args.start[6:8])
    )
    t1 = day + timedelta(
        hours=int(args.stop[:2]), minutes=int(args.stop[3:5]), seconds=int(args.stop[6:8])
    )
    f0, f1 = frame_at(t0), frame_at(t1)
    with ProcessPoolExecutor(max_workers=2) as pool:
        jobs = {
            ch: pool.submit(scan, p, f0, f1, args.thr)
            for ch, p in (("ch1", args.ch1), ("ch2", args.ch2))
        }
        res = {ch: j.result() for ch, j in jobs.items()}
    matched = cross_match(res["ch1"]["candidates"], res["ch2"]["candidates"])
    for ch in res:
        for c in res[ch]["candidates"]:
            c["utc"] = utc_at(c["frame"]).isoformat(timespec="milliseconds")
    summary = {
        "window_utc": [t0.isoformat(), t1.isoformat()],
        "frames_scanned": f1 - f0,
        "threshold_dn": args.thr,
        "detector": {
            "pool": POOL,
            "near": NEAR,
            "far": FAR,
            "max_area": MAX_AREA,
            "max_blobs": MAX_BLOBS,
        },
        "per_channel": {
            ch: {"candidates": len(r["candidates"]), "busy_frames": len(r["busy_frames"])}
            for ch, r in res.items()
        },
        "corroborated": matched,
        "channels": res,
        "sources": VIDEO_URLS,
    }
    args.out.write_text(json.dumps(summary, indent=1) + "\n")
    print(
        json.dumps(
            {k: summary[k] for k in ("window_utc", "frames_scanned", "per_channel")}, indent=1
        )
    )
    print("corroborated:", len(matched))
    for m in matched[:40]:
        print(m["utc"], m["ch1"], m["ch2"]["excess"])


if __name__ == "__main__":
    main()
