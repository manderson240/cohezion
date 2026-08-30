#!/usr/bin/env python3
"""Generate true 3D Topographical Impact Crater Relief Meshes from Ken Shoulders Fig 5:13 & Matsumoto Fig 6 Superstar Explosions."""

from __future__ import annotations

from pathlib import Path

from PIL import Image


out_dir = Path("/home/mike-anderson/dev/cohezion/docs/assets/renderings/plate_3d_surfaces")
out_dir.mkdir(parents=True, exist_ok=True)


def generate_micrograph_crater_mesh(image_path: Path, output_obj: Path, grid_res: int = 160, z_scale: float = 4.0, invert: bool = True) -> None:
    img = Image.open(image_path).convert("L")
    img = img.resize((grid_res, grid_res), Image.Resampling.LANCZOS)
    pixels = img.load()

    w, h = img.size
    vertices = []
    faces = []

    for y in range(h):
        for x in range(w):
            norm_x = (x / (w - 1) - 0.5) * 12.0
            norm_y = (0.5 - y / (h - 1)) * 12.0
            raw_val = pixels[x, y] / 255.0
            if invert:
                # Invert so dark hole pixels become deep negative Z depressions (boreholes)
                elevation = - ((1.0 - raw_val) ** 1.8) * z_scale
            else:
                elevation = ((raw_val) ** 1.5) * z_scale
            vertices.append((norm_x, norm_y, elevation))

    for y in range(h - 1):
        for x in range(w - 1):
            p1 = y * w + x + 1
            p2 = (y + 1) * w + x + 1
            p3 = (y + 1) * w + (x + 1) + 1
            p4 = y * w + (x + 1) + 1
            faces.append((p1, p2, p3))
            faces.append((p1, p3, p4))

    with open(output_obj, "w", encoding="utf-8") as f:
        f.write(f"# Micro-Impact Crater 3D Topographical Surface from {image_path.name}\n")
        for v in vertices:
            f.write(f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f}\n")
        for face in faces:
            f.write(f"f {face[0]} {face[1]} {face[2]}\n")

    print(f"✓ Generated 3D Micro-Impact Surface: {output_obj.name} ({len(vertices)} vertices, {len(faces)} faces, {output_obj.stat().st_size} bytes)")


def main() -> None:
    # 1. Ken Shoulders Figure 5:13 Deep Micro-Borehole Impact Craters
    sh_crop = Path("/home/mike-anderson/dev/cohezion/docs/assets/shoulders_plates/crop_shoulders_fig513_boreholes.png")
    sh_obj = out_dir / "shoulders_sem_fig513_deep_borehole_craters_3d.obj"
    generate_micrograph_crater_mesh(sh_crop, sh_obj, grid_res=160, z_scale=4.5, invert=True)

    # 2. Matsumoto Plate 142 Superstar Clustered Explosion Impact
    mat_plate = Path("/home/mike-anderson/dev/cohezion/docs/assets/matsumoto_plates/track_photo_page_142.png")
    mat_obj = out_dir / "matsumoto_plate142_superstar_explosions_3d.obj"
    generate_micrograph_crater_mesh(mat_plate, mat_obj, grid_res=160, z_scale=3.8, invert=True)


if __name__ == "__main__":
    main()
