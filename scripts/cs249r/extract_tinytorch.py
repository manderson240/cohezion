"""Extract code cells from TinyTorch Jupytext files into clean Python modules.

Reads Jupytext percent-format .py files and extracts only the code cells,
skipping markdown cells, nbgrader metadata, and jupytext headers.
"""

from __future__ import annotations

import re
from pathlib import Path


TINYTORCH_SRC = Path.home() / "dev" / "cs249r_book" / "tinytorch" / "src"

# Map module number to (source_dir, output_name)
CORE_MODULES = {
    "01": ("01_tensor", "tensor"),
    "02": ("02_activations", "activations"),
    "03": ("03_layers", "layers"),
    "04": ("04_losses", "losses"),
    "05": ("05_dataloader", "dataloader"),
    "06": ("06_autograd", "autograd"),
    "07": ("07_optimizers", "optimizers"),
    "08": ("08_training", "training"),
    "09": ("09_convolutions", "convolutions"),
}

ADVANCED_MODULES = {
    "10": ("10_tokenization", "tokenization"),
    "11": ("11_embeddings", "embeddings"),
    "12": ("12_attention", "attention"),
    "13": ("13_transformers", "transformers"),
    "14": ("14_profiling", "profiling"),
    "15": ("15_quantization", "quantization"),
    "16": ("16_compression", "compression"),
    "17": ("17_acceleration", "acceleration"),
    "18": ("18_memoization", "memoization"),
    "19": ("19_benchmarking", "benchmarking"),
}


def extract_code_cells(source_path: Path) -> list[str]:
    """Extract code cells from a Jupytext percent-format file.

    Returns list of code blocks (strings), skipping:
    - Jupytext header (# --- block)
    - Markdown cells (# %% [markdown])
    - nbgrader directives (#| lines)
    - Inline test/exercise blocks
    """
    lines = source_path.read_text().splitlines()
    code_blocks: list[str] = []
    current_block: list[str] = []
    in_code = False
    in_markdown = False
    in_header = False
    in_docstring = False

    for line in lines:
        # Skip jupytext header
        if line.strip() == "# ---":
            in_header = not in_header
            continue
        if in_header:
            continue

        # Cell boundary
        if line.startswith("# %%"):
            # Save previous code block
            if in_code and current_block:
                code_blocks.append("\n".join(current_block))
                current_block = []

            if "[markdown]" in line:
                in_code = False
                in_markdown = True
            else:
                in_code = True
                in_markdown = False
            continue

        if in_markdown:
            continue

        if not in_code:
            continue

        # Skip nbgrader/export directives
        if line.startswith("#|"):
            continue

        # Track docstrings in markdown cells that leak into code cells
        stripped = line.strip()
        if stripped == '"""' or stripped == "'''":
            in_docstring = not in_docstring
            # If this is a standalone docstring delimiter in a code cell,
            # check if the previous/next line suggests it's a markdown block
            if not current_block and not in_docstring:
                continue  # Skip closing of empty docstring
            if in_docstring and not current_block:
                # Opening of docstring at start of code cell - likely markdown
                in_docstring = True
                continue

        if in_docstring:
            continue

        current_block.append(line)

    # Don't forget the last block
    if in_code and current_block:
        code_blocks.append("\n".join(current_block))

    return code_blocks


def clean_code_block(block: str) -> str:
    """Clean a code block: remove test assertions, print demos, etc."""
    lines = block.splitlines()
    cleaned = []
    skip_block = False

    for line in lines:
        stripped = line.strip()

        # Skip standalone test/demo blocks
        if stripped.startswith("# Test") or stripped.startswith("# Quick test"):
            skip_block = True
            continue
        if stripped.startswith("# Demo") or stripped.startswith("# Let's"):
            skip_block = True
            continue
        if stripped.startswith("print(") and "test" in stripped.lower():
            continue

        # Resume on next function/class definition
        if skip_block and (stripped.startswith("def ") or stripped.startswith("class ")):
            skip_block = False

        if skip_block:
            # Keep blank lines (could be between test blocks)
            if not stripped:
                continue
            # Skip assertion lines
            if stripped.startswith("assert ") or stripped.startswith("print("):
                continue
            # Non-test code = end of skip
            if not stripped.startswith("#"):
                skip_block = False

        if not skip_block:
            cleaned.append(line)

    return "\n".join(cleaned)


def rewrite_imports(code: str, module_name: str) -> str:
    """Rewrite tinytorch imports to use cohezion.tinytorch namespace."""
    # Replace tinytorch.core.X imports
    code = re.sub(
        r"from tinytorch\.core\.(\w+)",
        r"from cohezion.tinytorch.\1",
        code,
    )
    code = re.sub(
        r"from tinytorch\.perf\.(\w+)",
        r"from cohezion.tinytorch.\1",
        code,
    )
    code = re.sub(
        r"import tinytorch\.core\.(\w+)",
        r"import cohezion.tinytorch.\1",
        code,
    )
    return code


def build_module(
    module_num: str,
    source_dir: str,
    output_name: str,
    output_base: Path,
) -> dict:
    """Extract and build a single TinyTorch module.

    Returns dict with stats about the extraction.
    """
    # Find the source file
    src_dir = TINYTORCH_SRC / source_dir
    src_files = list(src_dir.glob("*.py"))
    if not src_files:
        return {"module": output_name, "status": "no_source", "lines": 0}

    src_file = src_files[0]

    # Extract code cells
    blocks = extract_code_cells(src_file)

    # Clean and combine
    cleaned_blocks = []
    for block in blocks:
        cleaned = clean_code_block(block)
        if cleaned.strip():
            cleaned_blocks.append(cleaned)

    combined = "\n\n".join(cleaned_blocks)

    # Rewrite imports
    combined = rewrite_imports(combined, output_name)

    # Add module docstring
    header = f'"""TinyTorch {output_name} module.\n\nExtracted from CS249R Module {module_num}: {source_dir}.\nNumPy-only implementation for educational purposes.\n"""\n\n'

    # Ensure numpy import is present
    if "import numpy" not in combined:
        header += "import numpy as np\n\n"

    full_code = header + combined

    # Remove excessive blank lines
    full_code = re.sub(r"\n{4,}", "\n\n\n", full_code)

    # Write output
    output_path = output_base / f"{output_name}.py"
    output_path.write_text(full_code)

    line_count = len(full_code.splitlines())
    return {
        "module": output_name,
        "status": "ok",
        "lines": line_count,
        "source": str(src_file),
    }


def extract_all(
    modules: dict[str, tuple[str, str]],
    output_base: Path,
    dry_run: bool = False,
) -> list[dict]:
    """Extract all modules from TinyTorch source."""
    output_base.mkdir(parents=True, exist_ok=True)
    results = []

    for num, (src_dir, out_name) in sorted(modules.items()):
        if dry_run:
            src_path = TINYTORCH_SRC / src_dir
            src_files = list(src_path.glob("*.py"))
            src_lines = sum(f.read_text().count("\n") for f in src_files)
            print(f"  Module {num} ({out_name}): {src_lines} source lines")
            results.append({"module": out_name, "status": "dry_run", "lines": src_lines})
        else:
            result = build_module(num, src_dir, out_name, output_base)
            print(f"  Module {num} ({result['module']}): {result['lines']} lines -> {result['status']}")
            results.append(result)

    return results


if __name__ == "__main__":
    import sys

    dry_run = "--dry-run" in sys.argv
    which = "all"
    if "--core" in sys.argv:
        which = "core"
    elif "--advanced" in sys.argv:
        which = "advanced"

    output_base = Path("src/cohezion/tinytorch")

    if which in ("all", "core"):
        print("Extracting core modules (01-09):")
        extract_all(CORE_MODULES, output_base, dry_run=dry_run)

    if which in ("all", "advanced"):
        print("\nExtracting advanced modules (10-19):")
        extract_all(ADVANCED_MODULES, output_base, dry_run=dry_run)

    if not dry_run:
        print(f"\nOutput: {output_base}/")
