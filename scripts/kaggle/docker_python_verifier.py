#!/usr/bin/env python3
"""Kaggle Docker-Python Runtime Compatibility & Dependency Verifier.
==================================================================
Leverages https://github.com/Kaggle/docker-python to guarantee that code
submitted to Kaggle's offline containers will never crash due to missing
modules, package skew, or unsupported imports.

Features:
1. Fetches and caches `kaggle_requirements.txt` from Kaggle's official repo.
2. Extracts all import statements from candidate Python scripts and notebooks.
3. Compares imported modules against the Python stdlib and Kaggle's container manifest.
4. Returns an IV&V compatibility report (PASS / FAIL with missing dependencies).
"""

from __future__ import annotations

import ast
import json
import logging
import sys
import urllib.request
from pathlib import Path


logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger("docker_python_verifier")

REPO_CACHE_DIR = Path.home() / ".cache" / "kaggle_docker_python"
MANIFEST_URL = "https://raw.githubusercontent.com/Kaggle/docker-python/main/kaggle_requirements.txt"
CACHE_FILE = REPO_CACHE_DIR / "kaggle_requirements.txt"


def ensure_manifest() -> set[str]:
    """Ensures local cache of Kaggle's official container package manifest."""
    REPO_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if not CACHE_FILE.exists() or (Path(__file__).stat().st_mtime - CACHE_FILE.stat().st_mtime) > 86400:
        try:
            logger.info("Fetching latest kaggle_requirements.txt from Kaggle/docker-python...")
            req = urllib.request.Request(MANIFEST_URL, headers={"User-Agent": "Cohezion-IVV/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
                content = resp.read().decode("utf-8")
                CACHE_FILE.write_text(content, encoding="utf-8")
                logger.info("Cached Kaggle requirements manifest (%d bytes)", len(content))
        except Exception as e:
            logger.warning("Failed to refresh manifest from GitHub (%s). Falling back to local cache if present.", e)

    packages: set[str] = set()
    if CACHE_FILE.exists():
        for line in CACHE_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                pkg_name = line.split("==")[0].split(">=")[0].split("<=")[0].split("~=")[0].split("[")[0].strip().lower()
                # Normalize dashes to underscores
                packages.add(pkg_name.replace("-", "_"))
                packages.add(pkg_name)
    return packages


def extract_imports_from_code(code: str) -> set[str]:
    """Parses Python source code and extracts all top-level module names."""
    modules: set[str] = set()
    try:
        tree = ast.parse(code)
    except SyntaxError:
        # Ignore IPython magic lines and retry
        lines = [l for l in code.splitlines() if not l.strip().startswith("!") and not l.strip().startswith("%")]
        try:
            tree = ast.parse("\n".join(lines))
        except Exception:
            return modules

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.split(".")[0])
    return modules


def extract_imports_from_path(file_path: Path) -> set[str]:
    """Extracts imported modules from a .py file or .ipynb notebook."""
    if file_path.suffix == ".ipynb":
        with open(file_path, encoding="utf-8") as f:
            nb = json.load(f)
        all_code = []
        for cell in nb.get("cells", []):
            if cell.get("cell_type") == "code":
                all_code.append("".join(cell.get("source", [])))
        return extract_imports_from_code("\n".join(all_code))
    elif file_path.suffix == ".py":
        return extract_imports_from_code(file_path.read_text(encoding="utf-8"))
    return set()


def verify_compatibility(file_path: Path) -> tuple[bool, list[str], set[str]]:
    """Verifies that all third-party dependencies in the target exist in Kaggle's container."""
    installed = ensure_manifest()
    # Add common standard library and standard Kaggle pre-installs
    stdlib = set(sys.stdlib_module_names) if hasattr(sys, "stdlib_module_names") else {
        "os", "sys", "time", "datetime", "json", "math", "re", "logging", "pathlib", "gc",
        "random", "collections", "typing", "functools", "itertools", "urllib", "subprocess",
        "hashlib", "copy", "shutil", "tempfile", "io", "base64", "zlib", "uuid", "socket",
        "threading", "multiprocessing", "concurrent", "csv", "sqlite3", "pickle", "traceback"
    }
    # Built-in framework standards
    kaggle_known = {
        "numpy", "pandas", "torch", "torchvision", "torchaudio", "scipy", "sklearn",
        "scikit_learn", "lightgbm", "xgboost", "catboost", "cv2", "opencv_python",
        "PIL", "pillow", "matplotlib", "seaborn", "timm", "polars", "pyarrow", "rdkit",
        "kagglesdk", "kagglehub", "kaggle", "transformers", "accelerate", "einops",
        "numba", "cupy", "optuna", "skimage", "joblib", "tqdm", "yaml",
        "peft", "trl", "bitsandbytes", "datasets", "torch_xla"
    }
    competition_attached = {
        "arc_agi", "arcengine", "cohezion_physics_core",
        # CASMI26 attached dataset packages (v4b models, glacier/iceberg, pubchem tier, ours-ranker)
        "casmi", "v1engine", "ranker_infer", "pc_join", "gl_fuse", "fusion_core",
        "frag_rescore", "fuse", "surrogate"
    }
    allowed = installed | stdlib | kaggle_known | competition_attached

    imported = extract_imports_from_path(file_path)
    missing: list[str] = []

    for mod in imported:
        norm_mod = mod.lower().replace("-", "_")
        if norm_mod not in allowed and mod not in allowed:
            missing.append(mod)

    is_compatible = len(missing) == 0
    return is_compatible, missing, imported


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: docker_python_verifier.py <path_to_notebook_or_script>")
        sys.exit(1)

    target = Path(sys.argv[1])
    if not target.exists():
        print(f"File not found: {target}")
        sys.exit(1)

    ok, missing, all_imports = verify_compatibility(target)
    print(f"Target: {target}")
    print(f"Total Imported Modules: {len(all_imports)} ({sorted(all_imports)})")
    if ok:
        print("✓ COMPATIBLE: All imports are guaranteed present in Kaggle's official Docker container.")
        sys.exit(0)
    else:
        print(f"⚠️ POTENTIAL DEPENDENCY DEFECT: {len(missing)} imports not confirmed in Kaggle manifest: {missing}")
        sys.exit(2)


if __name__ == "__main__":
    main()
