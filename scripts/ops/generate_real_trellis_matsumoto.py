#!/usr/bin/env python3
"""Run real 3D generation with Lemonade TRELLIS-3D model on Matsumoto / Shoulders plates."""

from __future__ import annotations

import base64
import json
import time
import urllib.request
from pathlib import Path


plate_path = Path("/home/mike-anderson/dev/cohezion/docs/assets/matsumoto_plates/track_photo_page_139.png")
out_dir = Path("/home/mike-anderson/dev/cohezion/docs/assets/renderings/trellis_generated_assets")
out_dir.mkdir(parents=True, exist_ok=True)

print("=" * 80)
print(f"  🎨 INGESTING IMAGE INTO LOCAL TRELLIS-3D MODEL: {plate_path.name}")
print("=" * 80)

# Encode image to base64
with open(plate_path, "rb") as f:
    img_b64 = base64.b64encode(f.read()).decode("utf-8")

payload = {
    "model": "TRELLIS-3D",
    "image": f"data:image/png;base64,{img_b64}",
    "ss_sampling_steps": 35,
    "slat_sampling_steps": 35,
    "mesh_simplify": 0.90,
}

endpoints_to_try = [
    "http://localhost:13305/v1/images/generations",
    "http://localhost:13305/v1/3d/generate",
    "http://localhost:13305/api/v1/trellis/generate",
    "http://localhost:13305/trellis/generate",
    "http://localhost:13305/v1/chat/completions"
]

for ep in endpoints_to_try:
    print(f"\nAttempting Lemonade 3D endpoint: {ep}...")
    t0 = time.perf_counter()
    req = urllib.request.Request(
        ep,
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload).encode("utf-8")
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            dt = time.perf_counter() - t0
            print(f"  ✓ Success ({dt:.2f}s)! Response Code: {resp.status}")
            data = resp.read()
            out_file = out_dir / "trellis_matsumoto_plate_139.glb"
            with open(out_file, "wb") as f_out:
                f_out.write(data)
            print(f"  ✓ Saved generated 3D asset to: {out_file} ({out_file.stat().st_size} bytes)")
            break
    except Exception as e:
        print(f"  ✗ Endpoint returned: {e}")

print("=" * 80)
