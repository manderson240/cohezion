#!/usr/bin/env python3
"""Extract high-resolution image plates from Matsumoto's SDENC book for Vision Model analysis."""

from __future__ import annotations

from pathlib import Path

from pdf2image import convert_from_path


pdf_path = "/home/mike-anderson/Downloads/SDENC-Screen-MichaelAnderson.pdf"
out_dir = Path("/home/mike-anderson/dev/cohezion/docs/assets/matsumoto_plates")
out_dir.mkdir(parents=True, exist_ok=True)

# Key photograph pages: review papers, ICCF-3/ICCF-6 photographic plates, micro-ball lightning, ring tracks
# Let's render key pages across the book
key_pages = [15, 16, 17, 18, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 98, 100, 101, 102, 110, 115, 120, 130, 150, 180, 200, 220, 240, 260, 270, 280]

print(f"Converting {len(key_pages)} key pages to PNG images for Vision Model...")
for page_num in key_pages:
    out_file = out_dir / f"page_{page_num:03d}.png"
    if not out_file.exists():
        images = convert_from_path(pdf_path, first_page=page_num, last_page=page_num, dpi=150)
        if images:
            images[0].save(out_file, "PNG")
            print(f"  ✓ Saved page {page_num} -> {out_file.name} ({out_file.stat().st_size} bytes)")
    else:
        print(f"  ✓ Already exists: {out_file.name}")

print("Plate extraction complete!")
