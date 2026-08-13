"""Unit tests for ACE-Step Music Engine."""

import tempfile
from pathlib import Path

from cohezion.multimodal.ace_step_music_engine import AceStepMusicEngine


def test_ace_step_music_track_generation() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        engine = AceStepMusicEngine(output_dir=tmp_dir)
        track = engine.generate_music_track(
            prompt="quantum synthwave lead synth",
            duration_s=30.0,
            bpm=128,
            genre="synthwave",
        )

        assert track.track_id.startswith("ace_step_")
        assert track.genre == "synthwave"
        assert track.bpm == 128
        assert track.duration_s == 30.0
        assert Path(track.file_path).exists()
        assert len(track.poincare_latent_12d) == 12
