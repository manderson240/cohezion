#!/usr/bin/env python3
"""Run real 3D generation with exact Lemonade specification (resolution=512, seed=42)."""

from __future__ import annotations

import base64
import json
import time
import urllib.request
from pathlib import Path


plate_path = Path("/home/mike-anderson/dev/cohezion/docs/assets/matsumoto_plates/track_photo_page_139.png")
out_dir = Path("/home/mike-anderson/dev/cohezion/docs/assets/renderings/trellis_generated_assets")
out_dir.mkdir(parents=True, exist_ok=True)
out_file = out_dir / "matsumoto_ring_exact_trellis.glb"

print("=" * 80)
print("  🎨 DISPATCHING REAL TRELLIS-3D GENERATION")
print(f"  Input Plate: {plate_path}")
print(f"  Target File: {out_file}")
print("=" * 80)

with open(plate_path, "rb") as f:
    img_b64 = base64.b64encode(f.read()).decode("utf-8")

payload = {
    "model": "TRELLIS-3D",
    "image": img_b64,
    "resolution": 512,
    "seed": 42
}

req = urllib.request.Request(
    "http://localhost:13305/v1/3d/generations",
    headers={"Content-Type": "application/json"},
    data=json.dumps(payload).encode("utf-8")
)

t0 = time.perf_counter()
print("Connecting to trellis-server (PID 3971566) on GPU... (Executing dense 3D sparse latent flow diffusion)...")
try:
    with urllib.request.urlopen(req, timeout=600) as resp:
        dt = time.perf_counter() - t0
        print(f"  ✓ 3D Neural Diffusion Succeeded in {dt:.2f} seconds! (HTTP {resp.status})")
        data = resp.read()
        with open(out_file, "wb") as f_out:
            f_out.write(data)
        print(f"  ✓ Preserved 3D Textured Mesh (.glb): {out_file} ({out_file.stat().st_size} bytes)")
except urllib.error.HTTPError as e:
    print(f"  ✗ HTTP Error {e.code}: {e.read().decode('utf-8')}")
except Exception as e:
    print(f"  ✗ Error: {e}")

print("=" * 80)
