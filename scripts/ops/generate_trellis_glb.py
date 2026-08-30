#!/usr/bin/env python3
"""Generate true 3D GLB mesh using Lemonade TRELLIS-3D via POST /v1/3d/generations."""

from __future__ import annotations

import base64
import json
import time
import urllib.request
from pathlib import Path


plate_path = Path("/home/mike-anderson/dev/cohezion/docs/assets/matsumoto_plates/track_photo_page_139.png")
out_dir = Path("/home/mike-anderson/dev/cohezion/docs/assets/renderings/trellis_generated_assets")
out_dir.mkdir(parents=True, exist_ok=True)
out_file = out_dir / "matsumoto_ring_trellis.glb"

print("=" * 80)
print("  🎨 RUNNING REAL TRELLIS-3D INFERENCE (POST /v1/3d/generations)")
print(f"  Input Plate: {plate_path}")
print("=" * 80)

# Encode image to base64
with open(plate_path, "rb") as f:
    img_b64 = base64.b64encode(f.read()).decode("utf-8")

payload = {
    "model": "TRELLIS-3D",
    "image": f"data:image/png;base64,{img_b64}"
}

req = urllib.request.Request(
    "http://localhost:13305/v1/3d/generations",
    headers={"Content-Type": "application/json"},
    data=json.dumps(payload).encode("utf-8")
)

t0 = time.perf_counter()
print("Sending request to Lemonade server (this will take 20-60+ seconds for real 3D latent flow diffusion)...")
try:
    with urllib.request.urlopen(req, timeout=300) as resp:
        dt = time.perf_counter() - t0
        print(f"  ✓ Finished in {dt:.2f} seconds! Response HTTP {resp.status}")
        data = resp.read()
        with open(out_file, "wb") as f_out:
            f_out.write(data)
        print(f"  ✓ Successfully saved 3D GLB mesh: {out_file} ({out_file.stat().st_size} bytes)")
except urllib.error.HTTPError as e:
    print(f"  ✗ HTTP Error {e.code}: {e.read().decode('utf-8')}")
except Exception as e:
    print(f"  ✗ Error: {e}")

print("=" * 80)
