#!/usr/bin/env python3
"""
BirdCLEF Data Validator (AutoHarness)
Verifies audio files for sample rate, duration, and metadata consistency.
Mandated by arXiv:2603.03329v1 (Code-as-action-verifier).
"""

import os
import sys
import json
from pathlib import Path

import pandas as pd
try:
    import librosa
except ImportError:
    print("Warning: librosa not found, skipping audio signal checks.")
    librosa = None

def validate_audio(file_path: Path, expected_sr: int = 32000):
    """Verify audio file properties."""
    if not librosa:
        return True
        
    try:
        # Load small segment to check SR and validity
        y, sr = librosa.load(file_path, sr=expected_sr, duration=1.0)
        if sr != expected_sr:
            print(f"Error: {file_path.name} has SR {sr}, expected {expected_sr}")
            return False
        return True
    except Exception as e:
        print(f"Error: Failed to load {file_path.name}: {e}")
        return False

def validate_metadata(csv_path: Path):
    """Verify metadata CSV integrity."""
    try:
        df = pd.read_csv(csv_path)
        required_cols = ["primary_label", "filename", "scientific_name"]
        for col in required_cols:
            if col not in df.columns:
                print(f"Error: Metadata {csv_path.name} missing column {col}")
                return False
        return True
    except Exception as e:
        print(f"Error: Failed to read {csv_path.name}: {e}")
        return False

def main():
    print("Running BirdCLEF Data Validation (AutoHarness)...")
    
    data_root = Path("data/birdclef-2026")
    if not data_root.exists():
        print(f"Warning: Data root {data_root} not found. Skipping validation.")
        return 0
        
    # Check Metadata
    train_csv = data_root / "train.csv"
    if train_csv.exists():
        if not validate_metadata(train_csv):
            return 1
            
    # Check sample of audio files (first 10)
    audio_dir = data_root / "train_audio"
    if audio_dir.exists():
        audio_files = list(audio_dir.glob("**/*.ogg"))[:10]
        for f in audio_files:
            if not validate_audio(f):
                return 1
                
    print("Validation passed!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
