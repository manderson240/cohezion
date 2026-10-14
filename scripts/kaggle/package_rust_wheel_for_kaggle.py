#!/usr/bin/env python3
"""Deterministic Rust Wheel Packaging & Kaggle Dataset Distribution Engine.

Builds `cohezion-physics-core` into an optimized release wheel and bundles it into
a self-contained Kaggle Dataset directory ready for offline competition notebooks.

Usage:
    # Build release wheel and prepare Kaggle dataset bundle:
    python3 scripts/kaggle/package_rust_wheel_for_kaggle.py

    # Build, bundle, and verify in an isolated /tmp virtual environment:
    python3 scripts/kaggle/package_rust_wheel_for_kaggle.py --verify
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import List, Optional


def find_repo_root() -> Path:
    """Resolves the repository root directory."""
    return Path(__file__).resolve().parent.parent.parent


def build_wheel(
    maturin_bin: Path,
    manifest_path: Path,
    out_dir: Path,
) -> Path:
    """Builds the release wheel using maturin. Returns the path to the generated .whl."""
    if not maturin_bin.exists():
        which_maturin = shutil.which("maturin")
        if which_maturin:
            maturin_bin = Path(which_maturin)
        else:
            raise FileNotFoundError(
                f"Maturin binary not found at '{maturin_bin}' or on PATH."
            )

    if not manifest_path.exists():
        raise FileNotFoundError(f"Cargo.toml not found at '{manifest_path}'.")

    out_dir.mkdir(parents=True, exist_ok=True)

    # Discover target interpreters: current python + available uv python versions (for Kaggle 3.11/3.12 compatibility)
    interpreters: list[str] = [sys.executable]
    uv_dir = Path.home() / ".local" / "share" / "uv" / "python"
    for py_candidate in [
        uv_dir / "cpython-3.11-linux-x86_64-gnu" / "bin" / "python3.11",
        uv_dir / "cpython-3.12.8-linux-x86_64-gnu" / "bin" / "python3.12",
        uv_dir / "cpython-3.13-linux-x86_64-gnu" / "bin" / "python3.13",
        Path("/usr/bin/python3.14"),
    ]:
        if py_candidate.exists() and str(py_candidate) not in interpreters:
            interpreters.append(str(py_candidate))

    build_env = os.environ.copy()
    cargo_bin = str(Path.home() / ".cargo" / "bin")
    local_bin = str(Path.home() / ".local" / "bin")
    current_path = build_env.get("PATH", "")
    build_env["PATH"] = f"{local_bin}:{cargo_bin}:{current_path}"

    built_wheels = []
    for interp in interpreters:
        cmd = [
            str(maturin_bin),
            "build",
            "--release",
            "--out",
            str(out_dir),
            "--manifest-path",
            str(manifest_path),
            "-i",
            interp,
        ]
        print(f"==> Building native Rust PyO3 wheel for {interp}:")
        res = subprocess.run(cmd, capture_output=True, text=True, env=build_env)
        if res.returncode != 0:
            print(f"Warning: Failed to build wheel for {interp}: {res.stderr}")
        else:
            print(f"    ✓ Success for {interp}")

    # Find generated wheels in out_dir
    wheels = sorted(
        out_dir.glob("cohezion_physics_core*.whl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not wheels:
        raise FileNotFoundError(
            f"No wheel matching 'cohezion_physics_core*.whl' found in {out_dir}."
        )

    # Pick the wheel matching current sys.version_info (e.g. cp313)
    py_tag = f"cp{sys.version_info.major}{sys.version_info.minor}"
    current_wheel = next((w for w in wheels if py_tag in w.name), wheels[0])
    print(f"✓ Selected active wheel for verification: {current_wheel.name} ({current_wheel.stat().st_size:,} bytes)")
    return current_wheel


def create_dataset_bundle(wheel_path: Path, dataset_dir: Path) -> Path:
    """Creates the Kaggle Dataset bundle directory with metadata and documentation."""
    dataset_dir.mkdir(parents=True, exist_ok=True)

    # Copy all generated wheels into dataset directory
    for whl in wheel_path.parent.glob("cohezion_physics_core*.whl"):
        dest_wheel = dataset_dir / whl.name
        shutil.copy2(whl, dest_wheel)
        print(f"✓ Copied wheel to dataset bundle: {dest_wheel.name} ({dest_wheel.stat().st_size:,} bytes)")

    # dataset-metadata.json
    metadata = {
        "title": "Cohezion Physics Core Wheel",
        "id": "manderson240/cohezion-physics-core-wheel",
        "licenses": [
            {
                "name": "apache-2.0"
            }
        ],
    }
    meta_file = dataset_dir / "dataset-metadata.json"
    meta_file.write_text(json.dumps(metadata, indent=2))
    print(f"✓ Wrote Kaggle dataset metadata: {meta_file}")

    # README.md
    readme_content = f"""# Cohezion Physics Core Wheel (Offline Kaggle Distribution)

Compiled PyO3 / Rust native wheel for Kaggle offline code competitions (Linux x86_64).

## Offline Notebook Installation

In offline Kaggle competition notebooks, attach the dataset `manderson240/cohezion-physics-core-wheel` and run:

```bash
!pip install --no-index --find-links=/kaggle/input/cohezion-physics-core-wheel cohezion_physics_core
```

Or install the wheel directly:
```bash
!pip install --no-deps /kaggle/input/cohezion-physics-core-wheel/{wheel_path.name}
```

## Available Native Symbols

- `evolve_ca_simd(state: list[int], rule: int) -> list[int]`: SIMD 1D Cellular Automata evolution
- `apply_mhd_forces_simd(vec, helicity, toroidal_moment, dt)`: Fast Magneto-Hydrodynamics forces (in-place)
- `zobrist_hash_grid(grid: list[list[int]], seed: int) -> int`: 64-bit Zobrist Hash for 2D grids (ARC-AGI state hashing)
- `d4_transform(grid: list[list[int]], k: int) -> list[list[int]]`: Dihedral group D4 (8 symmetries)
- `verify_mitotic_com(parent, d1, d2, threshold=3.5, i1=1.0, i2=1.0) -> bool`: 3D Mitotic Center-of-Mass conservation
- `verify_daughter_divergence(d1_t1, d2_t1, d1_t2, d2_t2, min_divergence: float) -> tuple[float, bool]`: Mitotic daughter divergence test
- `simulate_kaggriculture_rollouts(num_sims=10000, base_seed=42, ...) -> tuple[float, float, float, float]`: Parallel Rayon market rollout simulator
- `simulate_adversarial_kaggriculture_rollouts(...) -> tuple[float, float, float, float]`: Adversarial predatory dumping simulator
- `fast_track_cells_3d(frames_detections, ...) -> tuple[list, list]`: 3D cell tracking with spatial gating
- `fast_kahn_topological_sort(nodes, edges) -> tuple[bool, list, list]`: Kahn's DAG acyclicity & topological sort
- `verify_monad_laws_fast(states, bind_maps) -> tuple[bool, str]`: Monad identity/associativity laws verifier
- `verify_deterministic_bounds(bounds, evaluations) -> bool`: Deterministic bounds formal verifier
- `py_eval_arc_hypotheses(train_pairs, candidates) -> list[tuple[int, float]]`: Multi-threaded Rayon hypothesis evaluator
- `py_extract_connected_components(grid) -> list[list[list[int]]]`: 4-connectivity flood fill object extraction
- `fast_poincare_distance(u, v) -> float`: Native SIMD 2048D Poincare hyperbolic geodesic distance
- `fast_poincare_conformal_factor(v) -> float`: Poincare metric conformal factor lambda(x) = 2 / (1 - ||x||^2)
- `fast_poincare_mobius_add(u, v) -> list[float]`: Mobius vector addition in Poincare ball
- `fast_poincare_pairwise_distances(points) -> list[list[float]]`: Rayon multi-threaded pairwise distance matrix
"""
    readme_file = dataset_dir / "README.md"
    readme_file.write_text(readme_content)
    print(f"✓ Wrote installation README: {readme_file}")

    return dataset_dir


def verify_wheel_in_isolated_env(wheel_path: Path, venv_dir: Path) -> bool:
    """Creates an isolated virtualenv, installs the wheel, and verifies all symbols."""
    print(f"\n==> Verifying wheel in isolated environment: {venv_dir}")

    # Clean existing test venv if present
    if venv_dir.exists():
        shutil.rmtree(venv_dir)

    # Create venv with system site-packages
    cmd_create = [
        sys.executable,
        "-m",
        "venv",
        "--system-site-packages",
        str(venv_dir),
    ]
    print(f"    Creating venv: {' '.join(cmd_create)}")
    res_create = subprocess.run(cmd_create, capture_output=True, text=True)
    if res_create.returncode != 0:
        raise RuntimeError(f"Failed to create test venv:\n{res_create.stderr}")

    venv_pip = venv_dir / "bin" / "pip"
    venv_python = venv_dir / "bin" / "python"

    # Install built wheel into test venv
    cmd_install = [
        str(venv_pip),
        "install",
        "--force-reinstall",
        "--no-deps",
        str(wheel_path),
    ]
    print(f"    Installing wheel: {' '.join(cmd_install)}")
    res_install = subprocess.run(cmd_install, capture_output=True, text=True)
    if res_install.returncode != 0:
        print(res_install.stderr, file=sys.stderr)
        raise RuntimeError(f"Failed to install wheel into test venv:\n{res_install.stderr}")

    # Import and function verification script
    verify_code = '''
import sys
import cohezion_physics_core as cpc

EXPECTED_SYMBOLS = [
    "evolve_ca_simd",
    "apply_mhd_forces_simd",
    "zobrist_hash_grid",
    "d4_transform",
    "verify_mitotic_com",
    "verify_daughter_divergence",
    "simulate_kaggriculture_rollouts",
    "simulate_adversarial_kaggriculture_rollouts",
    "fast_track_cells_3d",
    "fast_kahn_topological_sort",
    "verify_monad_laws_fast",
    "verify_deterministic_bounds",
    "py_eval_arc_hypotheses",
    "py_extract_connected_components",
    "fast_poincare_distance",
    "fast_poincare_conformal_factor",
    "fast_poincare_mobius_add",
    "fast_poincare_pairwise_distances",
]

print("1. Checking exported symbols:")
missing = []
for sym in EXPECTED_SYMBOLS:
    if not hasattr(cpc, sym):
        missing.append(sym)
    else:
        print(f"   [OK] {sym}")

if missing:
    print(f"FAILED: Missing symbols: {missing}", file=sys.stderr)
    sys.exit(1)

print("\\n2. Executing functional verification:")
# evolve_ca_simd
ca_res = cpc.evolve_ca_simd([0, 1, 0], 30)
assert isinstance(ca_res, (list, bytes)) and len(ca_res) == 3, f"evolve_ca_simd failed: {ca_res}"
print("   [OK] evolve_ca_simd functional test passed")

# zobrist_hash_grid
grid = [[1, 2], [3, 4]]
h1 = cpc.zobrist_hash_grid(grid, 42)
h2 = cpc.zobrist_hash_grid(grid, 42)
assert h1 == h2 and isinstance(h1, int), f"zobrist_hash_grid failed: {h1}"
print("   [OK] zobrist_hash_grid functional test passed")

# d4_transform
rot = cpc.d4_transform(grid, 1)
assert [list(r) for r in rot] == [[3, 1], [4, 2]], f"d4_transform rot90 failed: {rot}"
print("   [OK] d4_transform functional test passed")

# fast_poincare_distance
d = cpc.fast_poincare_distance([0.01]*10, [0.02]*10)
assert d > 0.0 and isinstance(d, float), f"fast_poincare_distance failed: {d}"
print("   [OK] fast_poincare_distance functional test passed")

# fast_poincare_conformal_factor
cf = cpc.fast_poincare_conformal_factor([0.0]*10)
assert abs(cf - 2.0) < 1e-5, f"fast_poincare_conformal_factor failed: {cf}"
print("   [OK] fast_poincare_conformal_factor functional test passed")

# py_extract_connected_components
comps = cpc.py_extract_connected_components([[1, 0], [0, 2]])
assert len(comps) == 2, f"py_extract_connected_components failed: {comps}"
print("   [OK] py_extract_connected_components functional test passed")

print("\\n✓ ALL SYMBOLS & FUNCTIONAL VERIFICATIONS PASSED (100% SUCCESS)")
'''

    cmd_verify = [str(venv_python), "-c", verify_code]
    print("    Verifying imports & functions in isolated environment...")
    res_verify = subprocess.run(cmd_verify, capture_output=True, text=True)

    print(res_verify.stdout)
    if res_verify.returncode != 0:
        print(res_verify.stderr, file=sys.stderr)
        raise RuntimeError(
            f"Verification test failed with exit code {res_verify.returncode}"
        )

    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deterministic Rust Wheel Packaging & Kaggle Dataset Distribution Engine."
    )
    repo_root = find_repo_root()

    parser.add_argument(
        "--maturin-path",
        type=Path,
        default=repo_root / ".venv" / "bin" / "maturin",
        help="Path to maturin binary",
    )
    parser.add_argument(
        "--manifest-path",
        type=Path,
        default=repo_root / "src" / "cohezion-physics-core" / "Cargo.toml",
        help="Path to Cargo.toml",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=repo_root / "dist" / "kaggle_wheels",
        help="Output directory for generated wheels",
    )
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=repo_root / "dist" / "kaggle_dataset_wheel",
        help="Output directory for Kaggle dataset bundle",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify wheel by installing in /tmp/test_wheel_env and importing all symbols",
    )
    parser.add_argument(
        "--test-env",
        type=Path,
        default=Path("/tmp/test_wheel_env"),
        help="Virtualenv path used for --verify",
    )

    args = parser.parse_args()

    wheel_path = build_wheel(
        maturin_bin=args.maturin_path,
        manifest_path=args.manifest_path,
        out_dir=args.out_dir,
    )

    bundle_path = create_dataset_bundle(
        wheel_path=wheel_path,
        dataset_dir=args.dataset_dir,
    )

    if args.verify:
        verify_wheel_in_isolated_env(
            wheel_path=wheel_path,
            venv_dir=args.test_env,
        )

    print("\n" + "=" * 60)
    print("KAGGLE WHEEL PACKAGING SUMMARY:")
    print(f"  Wheel Artifact:     {wheel_path}")
    print(f"  Dataset Directory:  {bundle_path}")
    print(f"  Metadata File:      {bundle_path / 'dataset-metadata.json'}")
    print(f"  README File:        {bundle_path / 'README.md'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
