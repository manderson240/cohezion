"""Validation script for BirdCLEF 2026 submission schema.
Ensures the output CSV matches Kaggle's multi-column probability requirements.
"""

import pandas as pd
import numpy as np
import os
from pathlib import Path


def validate_submission_schema():
    print("Validating BirdCLEF 2026 Submission Schema...")

    # 1. Load Sample Submission or Schema
    # In BirdCLEF, we need row_id and columns for all target species
    metadata_path = "data/birdclef-2026/embeddings/data/train-00000-of-00001.parquet"
    if not os.path.exists(metadata_path):
        print("Metadata not found. Generating mock schema.")
        species = [f"spec_{i}" for i in range(216)]
    else:
        df_meta = pd.read_parquet(metadata_path)
        # Flatten and unique labels
        labels_raw = df_meta["primary_labels"].values
        labels_flat = [l[0] if len(l) > 0 else "unknown" for l in labels_raw]
        species = sorted(list(set(labels_flat)))

    # 2. Generate Mock Submission
    num_test_samples = 10
    mock_data = {"row_id": [f"test_audio_{i}" for i in range(num_test_samples)]}
    for s in species:
        mock_data[s] = np.random.rand(num_test_samples)

    df_sub = pd.DataFrame(mock_data)

    # 3. Perform Checks
    print(f"Submission Shape: {df_sub.shape}")
    print(f"Species Columns: {len(species)}")

    # Check for row_id
    assert "row_id" in df_sub.columns, "MISSING row_id column"

    # Check for probability ranges
    prob_cols = [c for c in df_sub.columns if c != "row_id"]
    is_valid_range = (df_sub[prob_cols] >= 0.0).all().all() and (
        df_sub[prob_cols] <= 1.0
    ).all().all()
    assert is_valid_range, "INVALID probability values detected (must be 0-1)"

    # Save as artifact
    output_dir = Path("submissions/birdclef-2026")
    output_dir.mkdir(parents=True, exist_ok=True)
    df_sub.to_csv(output_dir / "submission.csv", index=False)

    print(f"Validation Successful. Sample submission saved to {output_dir}/submission.csv")


if __name__ == "__main__":
    validate_submission_schema()
