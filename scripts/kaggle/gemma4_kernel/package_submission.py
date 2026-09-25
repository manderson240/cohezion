#!/usr/bin/env python3
"""
package_submission.py

AutoHarness packaging and verification suite for the Google Gemma 4
Developer Agent Competition on Kaggle.

Enforces:
1. Directory traversal of submission/
2. Single base model rule across all agent yaml manifests
3. Allowed file extensions whitelist: (.yaml, .yml, .md, .txt, .py, .json, .safetensors)
4. Unpacked size ceiling (< 3 GiB)
5. Deterministic zip archive (fixed epoch timestamp 1980-01-01 00:00:00, sorted files)
6. Cryptographic SHA-256 integrity digest calculation
7. Round-trip unzipping and YAML SafeLoader validation
"""

import datetime
import hashlib
import os
import pathlib
import sys
import tempfile
import zipfile
from typing import Dict, List, Set
import yaml


ALLOWED_EXTENSIONS: Set[str] = {
    ".yaml",
    ".yml",
    ".md",
    ".txt",
    ".py",
    ".json",
    ".safetensors",
}

MAX_UNPACKED_BYTES: int = 3 * 1024 * 1024 * 1024  # 3 GiB
FIXED_ZIP_DATETIME = (1980, 1, 1, 0, 0, 0)


class SafeIncludeLoader(yaml.SafeLoader):
    """Custom YAML SafeLoader that handles !include tags safely."""
    pass


def include_constructor(loader: yaml.SafeLoader, node: yaml.Node):
    scalar = loader.construct_scalar(node)
    return f"!include {scalar}"


SafeIncludeLoader.add_constructor("!include", include_constructor)


def compute_sha256(filepath: pathlib.Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def validate_submission_source(submission_dir: pathlib.Path) -> Dict[str, any]:
    if not submission_dir.exists() or not submission_dir.is_dir():
        raise FileNotFoundError(f"Submission directory not found: {submission_dir}")

    files: List[pathlib.Path] = []
    total_size = 0
    models_found: Set[str] = set()

    for root, _, filenames in os.walk(submission_dir):
        for fname in filenames:
            fpath = pathlib.Path(root) / fname
            rel_path = fpath.relative_to(submission_dir)
            files.append(fpath)

            # Check allowed extensions
            ext = fpath.suffix.lower()
            if ext not in ALLOWED_EXTENSIONS:
                raise ValueError(
                    f"Disallowed file extension '{ext}' in submission: {rel_path}. "
                    f"Allowed: {sorted(ALLOWED_EXTENSIONS)}"
                )

            # Accumulate size
            fsize = fpath.stat().st_size
            total_size += fsize

            # Check model specification in YAMLs
            if ext in {".yaml", ".yml"}:
                with open(fpath, "r", encoding="utf-8") as yf:
                    data = yaml.load(yf, Loader=SafeIncludeLoader)
                    if isinstance(data, dict) and "model" in data:
                        models_found.add(data["model"])

    if total_size >= MAX_UNPACKED_BYTES:
        raise ValueError(
            f"Unpacked size {total_size} bytes exceeds 3 GiB ceiling ({MAX_UNPACKED_BYTES} bytes)"
        )

    if len(models_found) == 0:
        raise ValueError("No model specified in any agent YAML manifest.")
    elif len(models_found) > 1:
        raise ValueError(
            f"Single base model rule violated! Multiple models detected: {models_found}"
        )

    return {
        "files": files,
        "total_unpacked_bytes": total_size,
        "base_model": next(iter(models_found)),
    }


def create_deterministic_zip(
    submission_dir: pathlib.Path, output_zip: pathlib.Path
) -> str:
    source_info = validate_submission_source(submission_dir)
    files = source_info["files"]

    # Sort files deterministically by relative POSIX path
    sorted_files = sorted(
        files, key=lambda p: p.relative_to(submission_dir).as_posix()
    )

    if output_zip.exists():
        output_zip.unlink()

    with zipfile.ZipFile(
        output_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as zf:
        for fpath in sorted_files:
            rel_path = fpath.relative_to(submission_dir).as_posix()
            with open(fpath, "rb") as f:
                content = f.read()

            zinfo = zipfile.ZipInfo(filename=rel_path, date_time=FIXED_ZIP_DATETIME)
            zinfo.external_attr = 0o644 << 16  # standard -rw-r--r-- permissions
            zinfo.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(zinfo, content)

    return compute_sha256(output_zip)


def verify_zip_roundtrip(zip_path: pathlib.Path) -> bool:
    print(f"\n[AutoHarness] Running round-trip validation on {zip_path.name}...")
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = pathlib.Path(temp_dir)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(temp_path)

        root_agent = temp_path / "agent.yaml"
        if not root_agent.exists():
            raise FileNotFoundError("Round-trip validation failed: agent.yaml missing from zip root.")

        # Validate all YAMLs can be loaded
        yaml_count = 0
        for root, _, filenames in os.walk(temp_path):
            for fname in filenames:
                if fname.endswith((".yaml", ".yml")):
                    fpath = pathlib.Path(root) / fname
                    with open(fpath, "r", encoding="utf-8") as yf:
                        parsed = yaml.load(yf, Loader=SafeIncludeLoader)
                        assert isinstance(parsed, dict), f"Failed parsing {fpath.name} as dictionary"
                        yaml_count += 1

        print(f"[AutoHarness] Round-trip passed: {yaml_count} YAML manifests parsed successfully.")
    return True


def main():
    script_dir = pathlib.Path(__file__).parent.resolve()
    submission_dir = script_dir / "submission"
    output_zip = script_dir / "submission.zip"

    print("=================================================================")
    print("Google Gemma 4 Developer Agent Competition - Packaging Harness")
    print("=================================================================")
    print(f"Source Directory: {submission_dir}")
    print(f"Target Archive:   {output_zip}")

    try:
        source_meta = validate_submission_source(submission_dir)
        print(f"Base Model Verified: {source_meta['base_model']}")
        print(f"Total Files:         {len(source_meta['files'])}")
        print(f"Unpacked Size:       {source_meta['total_unpacked_bytes']:,} bytes")

        sha256 = create_deterministic_zip(submission_dir, output_zip)
        zip_size = output_zip.stat().st_size
        print(f"\nArchive Created:     {output_zip.name}")
        print(f"Archive Size:        {zip_size:,} bytes")
        print(f"SHA-256 Digest:      {sha256}")

        verify_zip_roundtrip(output_zip)

        print("\n=================================================================")
        print("STATUS: VERIFIED & READY FOR KAGGLE SUBMISSION")
        print("=================================================================")
        print(f"ZIP Path:    {output_zip}")
        print(f"SHA-256:     {sha256}")
        print(f"Packed Size: {zip_size} bytes")
        print("=================================================================\n")
        return 0
    except Exception as e:
        print(f"\n[ERROR] Packaging and validation failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
