"""IV&V Suite Manifest & Cryptographic Integrity Anchor.

Computes and verifies SHA256 hashes of verifier-owned independent test suites
to ensure adversarial test suites cannot be tampered with by creators.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, List


def get_ivv_suite_dir() -> Path:
    """Returns the absolute path to the tests/ivv directory."""
    return Path(__file__).resolve().parent


def compute_suite_hash(suite_name: str = "ivv") -> str:
    """Computes SHA256 of all test files in tests/ivv/.

    Parameters
    ----------
    suite_name : str
        The name of the test suite (defaults to 'ivv').

    Returns
    -------
    str
        Hex-encoded SHA256 digest of concatenated filenames and contents.
    """
    suite_dir = get_ivv_suite_dir()
    if not suite_dir.exists():
        raise FileNotFoundError(f"Suite directory does not exist: {suite_dir}")

    test_files: List[Path] = sorted(
        [
            f
            for f in suite_dir.glob("*.py")
            if not f.name.startswith((".", "_#"))
        ],
        key=lambda p: p.name,
    )

    hasher = hashlib.sha256()
    hasher.update(suite_name.encode("utf-8"))

    for f in test_files:
        rel_name = f.name
        content = f.read_bytes()
        hasher.update(rel_name.encode("utf-8"))
        hasher.update(content)

    return hasher.hexdigest()


def get_suite_inventory() -> Dict[str, Dict[str, Any]]:
    """Returns inventory of test files and sizes in the IV&V suite."""
    suite_dir = get_ivv_suite_dir()
    inventory: Dict[str, Dict[str, Any]] = {}
    for f in sorted(suite_dir.glob("test_*.py")):
        inventory[f.name] = {
            "size_bytes": f.stat().st_size,
            "line_count": len(f.read_text(encoding="utf-8").splitlines()),
        }
    return inventory
