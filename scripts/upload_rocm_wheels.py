import os
import subprocess
import json
from pathlib import Path


def download_wheels(packages, output_dir):
    """Download wheels for offline installation."""
    os.makedirs(output_dir, exist_ok=True)
    for pkg in packages:
        print(f"Downloading {pkg}...")
        subprocess.run(
            [
                "pip",
                "download",
                "--no-deps",
                "--platform",
                "manylinux2014_x86_64",
                "--only-binary=:all:",
                "-d",
                output_dir,
                pkg,
            ],
            check=True,
        )


def create_kaggle_dataset(output_dir, dataset_name):
    """Create a Kaggle dataset from a directory of wheels."""
    metadata = {
        "title": dataset_name,
        "id": f"manderson240/{dataset_name.lower().replace(' ', '-')}",
        "licenses": [{"name": "CC0-1.0"}]
    }


    with open(os.path.join(output_dir, "dataset-metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"Initializing Kaggle dataset in {output_dir}...")
    subprocess.run(["kaggle", "datasets", "create", "-p", output_dir, "--public"], check=True)


if __name__ == "__main__":
    WHEELS_DIR = "rocm_wheels_v1"
    PACKAGES = ["trl", "bitsandbytes"]

    try:
        download_wheels(PACKAGES, WHEELS_DIR)
        create_kaggle_dataset(WHEELS_DIR, "ROCm Training Wheels")
        print("Successfully uploaded ROCm wheels to Kaggle.")
    except Exception as e:
        print(f"Error: {e}")
