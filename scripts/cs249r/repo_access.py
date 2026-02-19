"""CS249R book repository access utilities.

Provides structured access to the CS249R ML Systems book repository:
- Chapter concepts (YAML files)
- Glossary terms (JSON files)
- TinyTorch modules (Jupytext .py files)
"""

import json
import re
from pathlib import Path
from typing import Any

import yaml


class CS249RRepo:
    """Interface to the CS249R book repository."""

    def __init__(self, repo_path: str | Path | None = None):
        """Initialize with path to cloned repository.

        Args:
            repo_path: Path to cs249r_book directory. If None, searches in standard location.
        """
        if repo_path is None:
            # Default location: sibling to cohezion
            default_path = Path.home() / "dev" / "cs249r_book"
            if not default_path.exists():
                raise FileNotFoundError(
                    f"CS249R repo not found at {default_path}. "
                    "Clone it first or pass explicit repo_path."
                )
            repo_path = default_path

        self.repo_path = Path(repo_path)
        if not self.repo_path.exists():
            raise FileNotFoundError(f"Repository not found at {self.repo_path}")

        self._book_path = self.repo_path / "book" / "quarto" / "contents"
        self._tinytorch_path = self.repo_path / "tinytorch" / "src"

    def get_core_chapters(self) -> list[dict[str, Any]]:
        """Get list of core chapter directories."""
        core_path = self._book_path / "core"
        if not core_path.exists():
            return []

        chapters = []
        for item in sorted(core_path.iterdir()):
            if item.is_dir() and item.name not in ("data", "frontmatter", "backmatter", "parts"):
                chapters.append({
                    "name": item.name,
                    "path": item,
                    "type": "core"
                })

        return chapters

    def get_advanced_chapters(self) -> list[dict[str, Any]]:
        """Get list of advanced chapter directories."""
        advanced_path = self._book_path / "advanced"
        if not advanced_path.exists():
            return []

        chapters = []
        for item in sorted(advanced_path.iterdir()):
            if item.is_dir() and item.name != "README":
                chapters.append({
                    "name": item.name,
                    "path": item,
                    "type": "advanced"
                })

        return chapters

    @property
    def chapters(self) -> list[dict[str, Any]]:
        """Get all chapters (core + advanced)."""
        return self.get_core_chapters() + self.get_advanced_chapters()

    def load_chapter_concepts(self, chapter_name: str, chapter_type: str = "core") -> dict[str, Any] | None:
        """Load concept map YAML for a chapter.

        Args:
            chapter_name: Name of the chapter directory
            chapter_type: "core" or "advanced"

        Returns:
            Parsed YAML dict or None if file doesn't exist
        """
        base_path = self._book_path / chapter_type / chapter_name
        concepts_file = base_path / f"{chapter_name}_concepts.yml"

        if not concepts_file.exists():
            return None

        with concepts_file.open() as f:
            return yaml.safe_load(f)

    def load_chapter_glossary(self, chapter_name: str, chapter_type: str = "core") -> list[dict] | None:
        """Load glossary JSON for a chapter.

        Args:
            chapter_name: Name of the chapter directory
            chapter_type: "core" or "advanced"

        Returns:
            Parsed JSON list/dict or None if file doesn't exist
        """
        base_path = self._book_path / chapter_type / chapter_name
        glossary_file = base_path / f"{chapter_name}_glossary.json"

        if not glossary_file.exists():
            return None

        with glossary_file.open() as f:
            return json.load(f)

    def load_global_glossary(self) -> dict[str, Any]:
        """Load the global glossary JSON.

        Returns:
            Parsed JSON with structure: {"metadata": {...}, "terms": [...]}
        """
        glossary_file = self._book_path / "data" / "global_glossary.json"

        if not glossary_file.exists():
            raise FileNotFoundError(f"Global glossary not found at {glossary_file}")

        with glossary_file.open() as f:
            return json.load(f)

    @property
    def glossary_term_count(self) -> int:
        """Get count of terms in global glossary."""
        glossary = self.load_global_glossary()
        # Glossary structure: {"metadata": {...}, "terms": [...]}
        terms = glossary.get("terms", glossary) if isinstance(glossary, dict) else glossary
        return len(terms)

    def get_tinytorch_modules(self) -> list[dict[str, Any]]:
        """Get list of TinyTorch module directories.

        Returns:
            List of dicts with keys: number, name, path
        """
        if not self._tinytorch_path.exists():
            return []

        modules = []
        for item in sorted(self._tinytorch_path.iterdir()):
            if item.is_dir() and re.match(r"^\d{2}_", item.name):
                # Extract module number from name like "01_tensor"
                match = re.match(r"^(\d{2})_(.+)$", item.name)
                if match:
                    modules.append({
                        "number": int(match.group(1)),
                        "name": match.group(2),
                        "path": item,
                        "main_file": item / f"{item.name}.py"
                    })

        return sorted(modules, key=lambda m: m["number"])

    @property
    def tinytorch_modules(self) -> list[dict[str, Any]]:
        """Get all TinyTorch modules."""
        return self.get_tinytorch_modules()
