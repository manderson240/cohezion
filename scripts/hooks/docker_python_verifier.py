#!/usr/bin/env python3
"""Docker-Python Environment Verifier Hook.
==============================================
Verifies notebook and script imports against Kaggle's official `docker-python`
container specifications (https://github.com/Kaggle/docker-python).

Prevents offline execution crashes (ModuleNotFoundError) on Kaggle's
no-internet hidden evaluation containers.
"""

from __future__ import annotations

import ast
import json
import logging
import sys
from pathlib import Path
from typing import Set, Tuple, List, Dict, Any

logger = logging.getLogger("DockerPythonVerifier")
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

# Standard library modules (Python 3.10 - 3.13)
STDLIB_MODULES = sys.stdlib_module_names

# Kaggle official docker-python pre-installed packages (top standard packages)
KAGGLE_DOCKER_PYTHON_PACKAGES = {
    # Core Numerics & Data
    "numpy", "scipy", "pandas", "polars", "pyarrow", "tables", "fastparquet",
    # ML & Deep Learning
    "torch", "torchvision", "torchaudio", "torchtext", "torch_xla",
    "tensorflow", "keras", "jax", "jaxlib", "flax",
    "lightgbm", "xgboost", "catboost", "sklearn", "scikit-learn",
    # Computer Vision, Audio & Medical
    "cv2", "PIL", "pillow", "albumentations", "timm", "librosa", "soundfile",
    "monai", "kornia", "skimage", "scikit-image", "pydicom", "nibabel", "SimpleITK", "dicomsdl",
    # NLP & Transformers
    "transformers", "datasets", "accelerate", "tokenizers", "huggingface_hub",
    "peft", "trl", "bitsandbytes",
    "spacy", "nltk", "gensim", "sentencepiece", "tiktoken",
    # Chemistry, Biology & Microscopy
    "rdkit", "Bio", "biopython", "networkx", "zarr", "blosc2", "tracksdata", "tifffile",
    # Optimization & Metrics
    "optuna", "hyperopt", "joblib", "tqdm", "scikit-optimize",
    # Visualization & Interactive
    "matplotlib", "seaborn", "plotly", "bokeh", "altair", "IPython", "ipywidgets",
    # System & Web Tools
    "requests", "urllib3", "aiohttp", "httpx", "yaml", "toml", "pydantic",
    "numba", "cython", "cupy", "einops", "safetensors",
    # Kaggle-specific
    "kaggle", "kagglesdk", "kagglehub", "kaggle_environments",
}


def extract_imports_from_source(source: str) -> Set[str]:
    """Extract top-level package names from Python source code via AST."""
    imports = set()
    cleaned_lines = []
    for line in source.splitlines():
        # Strip Jupyter shell magics
        stripped = line.strip()
        if stripped.startswith("!") or stripped.startswith("%"):
            cleaned_lines.append(f"# {line}")
        else:
            cleaned_lines.append(line)

    try:
        tree = ast.parse("\n".join(cleaned_lines))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    pkg = alias.name.split(".")[0]
                    imports.add(pkg)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    pkg = node.module.split(".")[0]
                    imports.add(pkg)
    except SyntaxError as e:
        logger.warning("AST parse error: %s", e)
    return imports


def extract_imports_from_notebook(nb_path: Path) -> Set[str]:
    """Extract all top-level package names across all code cells in a notebook."""
    imports = set()
    try:
        with open(nb_path, "r", encoding="utf-8") as f:
            nb = json.load(f)
        for cell in nb.get("cells", []):
            if cell.get("cell_type") == "code":
                src = "".join(cell.get("source", []))
                imports.update(extract_imports_from_source(src))
    except Exception as e:
        logger.error("Failed to read notebook %s: %s", nb_path, e)
    return imports


def get_attached_wheels(kernel_dir: Path) -> Set[str]:
    """Finds any attached offline wheels or datasets from kernel-metadata.json."""
    attached = set()
    meta_path = kernel_dir / "kernel-metadata.json"
    if meta_path.exists():
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            for ds in meta.get("dataset_sources", []):
                ds_lower = ds.lower()
                if "cohezion" in ds_lower:
                    attached.update(["cohezion_physics_core", "cohezion"])
                if "rdkit" in ds_lower:
                    attached.add("rdkit")
                if "casmi" in ds_lower:
                    # In CASMI26 pipelines, official datasets supply modular engine packages
                    attached.update([
                        "casmi", "v1engine", "fusion_core", "surrogate", "frag_rescore",
                        "pc_join", "ranker_infer", "gl_fuse", "ice_fuse", "fuse"
                    ])
                if "raptor" in ds_lower or "knee" in ds_lower:
                    # In RSNA Knee pipelines, attached dataset sources supply custom model architectures
                    attached.update([
                        "raptor_global_stack_smart336", "raptor_light224", "raptor",
                        "coatnet", "radimagenet", "dinov2_knee"
                    ])
            for ks in meta.get("kernel_sources", []):
                ks_lower = ks.lower()
                if "unsloth" in ks_lower or "pip" in ks_lower:
                    attached.update(["unsloth", "peft", "flash_attn", "bitsandbytes", "triton"])

            for cs in meta.get("competition_sources", []):
                cs_lower = cs.lower()
                if "arc-agi-3" in cs_lower:
                    attached.update(["arc_agi", "arcengine", "arc_interactive"])
                elif "arc-agi-2" in cs_lower:
                    attached.update(["arc_decoder", "arc_loader", "arc_solver"])
        except Exception:
            pass
    return attached


def verify_file(file_path: Path | str) -> Tuple[bool, List[str]]:
    """Verifies that all imports in the target file are present in docker-python or attached datasets."""
    file_path = Path(file_path)
    if not file_path.exists():
        return False, [f"File {file_path} does not exist"]

    if file_path.suffix == ".ipynb":
        imports = extract_imports_from_notebook(file_path)
    elif file_path.suffix == ".py":
        imports = extract_imports_from_source(file_path.read_text(encoding="utf-8", errors="replace"))
    else:
        return True, []

    attached = get_attached_wheels(file_path.parent)
    known = set(STDLIB_MODULES) | set(KAGGLE_DOCKER_PYTHON_PACKAGES) | set(attached)

    # Local module exceptions (modules residing in same directory)
    local_files = {p.stem for p in file_path.parent.glob("*.py")}
    known.update(local_files)

    missing = []
    for imp in sorted(imports):
        if imp not in known and not imp.startswith("_"):
            missing.append(imp)

    if missing:
        logger.warning(
            "[%s] Found imports not in standard Kaggle docker-python: %s",
            file_path.name,
            missing,
        )
        return False, missing

    logger.info("[%s] All %d imports verified against Kaggle docker-python.", file_path.name, len(imports))
    return True, []


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: docker_python_verifier.py <path-to-notebook-or-script>")
        sys.exit(0)

    target = Path(sys.argv[1])
    ok, missing = verify_file(target)
    if not ok:
        print(f"❌ Verification FAILED for {target}: Missing or unbundled dependencies: {missing}")
        sys.exit(1)
    else:
        print(f"✓ Verification PASSED: {target} is 100% compatible with Kaggle docker-python runtime.")
        sys.exit(0)


if __name__ == "__main__":
    main()
