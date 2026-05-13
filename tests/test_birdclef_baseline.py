from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from cohezion.models.birdclef_baseline import BirdCLEFBaseline


# Constants
DATA_ROOT = Path("data/birdclef-2026")
TEST_AUDIO = DATA_ROOT / "train_audio/1161364/iNat1114648.ogg"


@pytest.fixture
def baseline():
    # Use default model for baseline test
    return BirdCLEFBaseline()


def test_audio_loading(baseline):
    """Verify librosa loads audio correctly."""
    librosa = pytest.importorskip("librosa", reason="librosa not installed")

    if not TEST_AUDIO.exists():
        pytest.skip("Test audio not found")

    y, sr = librosa.load(TEST_AUDIO, sr=32000)
    assert sr == 32000
    assert len(y) > 0


def test_baseline_prediction(baseline):
    """Verify baseline prediction logic."""
    if not TEST_AUDIO.exists():
        pytest.skip("Test audio not found")

    # Mock audio data for prediction test to avoid real model loading in CI
    mock_audio = np.random.uniform(-1, 1, (1, 32000 * 5)).astype(np.float32)
    with patch.object(baseline.backbone, "extract_embeddings", return_value=np.random.randn(1, 1536)):
        probs = baseline.predict(mock_audio)
        assert isinstance(probs, np.ndarray)
        assert probs.shape == (1, 234)


def test_taxonomy_loading(baseline):
    """Verify target species loading via sample submission."""
    sample_sub = DATA_ROOT / "sample_submission.csv"
    if not sample_sub.exists():
        pytest.skip("Sample submission not found")

    baseline.set_species_columns(str(sample_sub))
    assert len(baseline.species_columns) > 0


def test_train_step(baseline):
    """Verify local training step logic."""
    # Mock audio data (2 samples, 5 seconds at 32kHz)
    mock_audio = np.random.uniform(-1, 1, (2, 32000 * 5)).astype(np.float32)
    # Mock labels (2 samples, 234 classes)
    mock_labels = np.zeros((2, 234))
    mock_labels[0, 0] = 1.0  # First class
    mock_labels[1, 1] = 1.0  # Second class

    with patch.object(baseline.backbone, "extract_embeddings", return_value=np.random.randn(2, 1536)):
        loss = baseline.train_step(mock_audio, mock_labels)
        assert isinstance(loss, float)
        assert loss > 0


def test_submission_formatting(baseline):
    """Verify multi-column submission dataframe structure."""
    sample_sub = DATA_ROOT / "sample_submission.csv"
    if not sample_sub.exists():
        pytest.skip("Sample submission not found")

    baseline.set_species_columns(str(sample_sub))

    mock_probs = np.random.rand(2, 234)
    offsets = [0, 5]
    df = baseline.format_submission(mock_probs, "test_file", offsets)

    assert "row_id" in df.columns
    # Check if a few species from sample_submission are present
    assert "1161364" in df.columns
    assert "bbwduc" in df.columns
    assert len(df.columns) == 235  # row_id + 234 species
    assert df.iloc[0]["row_id"] == "test_file_0"
    assert df.iloc[1]["row_id"] == "test_file_5"
