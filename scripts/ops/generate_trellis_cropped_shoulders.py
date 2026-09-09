#!/usr/bin/env python3
"""Run real neural TRELLIS-3D generation on cropped Shoulders SEM Bead Ring."""

from __future__ import annotations

import base64
import json
import time
import urllib.request
from pathlib import Path


img_path = Path("/home/mike-anderson/dev/cohezion/docs/assets/shoulders_plates/crop_shoulders_fig33_bead_loop.png")
out_dir = Path("/home/mike-anderson/dev/cohezion/docs/assets/renderings/trellis_generated_assets")
out_dir.mkdir(parents=True, exist_ok=True)
out_glb = out_dir / "trellis_shoulders_fig33_bead_ring.glb"

print(f"Ingesting cropped Shoulders SEM bead loop ({img_path}) into TRELLIS-3D...")

with open(img_path, "rb") as f:
    b64 = base64.b64encode(f.read()).decode("utf-8")

payload = {
    "model": "TRELLIS-3D",
    "image": b64,
    "resolution": 512,
    "bg_removal": "birefnet",
    "seed": 42
}

req = urllib.request.Request(
    "http://localhost:13305/v1/3d/generations",
    headers={"Content-Type": "application/json"},
    data=json.dumps(payload).encode("utf-8")
)

t0 = time.perf_counter()
try:
    with urllib.request.urlopen(req, timeout=600) as resp:
        dt = time.perf_counter() - t0
        data = resp.read()
        with open(out_glb, "wb") as f_out:
            f_out.write(data)
        print(f"✓ Neural TRELLIS-3D Mesh generated in {dt:.2f}s! Saved to: {out_glb} ({len(data)} bytes)")
except Exception as e:
    print(f"✗ TRELLIS Generation Error: {e}")
