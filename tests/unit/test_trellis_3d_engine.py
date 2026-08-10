"""Unit tests for TRELLIS 3D Engine."""

import tempfile
from pathlib import Path

from cohezion.multimodal.trellis_3d_engine import Trellis3DEngine


def test_trellis_3d_asset_generation() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        engine = Trellis3DEngine(output_dir=tmp_dir)
        asset = engine.generate_3d_asset(
            image_or_text="a futuristic quantum computer crystal node",
            output_format="gltf",
        )

        assert asset.asset_id.startswith("trellis_3d_")
        assert asset.format == "gltf"
        assert asset.face_count > 0
        assert asset.vertex_count > 0
        assert Path(asset.file_path).exists()
        assert len(asset.poincare_latent_12d) == 12
