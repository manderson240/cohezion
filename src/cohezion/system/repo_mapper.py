import os
from pathlib import Path


class RepositoryMapper:
    """
    Generates a high-fidelity Markdown Tree of the codebase.
    Used for context reduction and agent navigation.
    """

    EXCLUDE_DIRS = {
        "__pycache__",
        ".git",
        ".venv",
        ".idea",
        ".vscode",
        "node_modules",
        "dist",
        "build",
        "coverage",
        ".pytest_cache",
        "tmp",
        ".gemini",
        "artifacts",
        "brain",
        "data",
        ".archive",
        "logs",
    }

    EXCLUDE_FILES = {
        ".DS_Store",
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "uv.lock",
        "poetry.lock",
    }

    def __init__(self, root: str = "."):
        self.root = Path(root).resolve()
        self.output_file = self.root / "REPO_MAP.md"

    def generate_map(self):
        """Walks the directory and builds the tree."""
        tree = ["# COHEZION REPOSITORY MAP\n"]
        tree.append(f"**Generated**: {self._get_timestamp()}\n")
        tree.append("```text")

        for root, dirs, files in os.walk(self.root):
            # Filtering
            dirs[:] = [d for d in dirs if d not in self.EXCLUDE_DIRS]

            level = root.replace(str(self.root), "").count(os.sep)
            indent = "│   " * (level)
            subindent = "│   " * (level + 1)

            # Directory Name
            dirname = os.path.basename(root)
            if dirname == ".":
                dirname = self.root.name

            tree.append(f"{indent}├── {dirname}/")

            # Files
            for f in sorted(files):
                if f in self.EXCLUDE_FILES:
                    continue
                if f.endswith(".pyc") or f.endswith(".so"):
                    continue

                tree.append(f"{subindent}├── {f}")

        tree.append("```")

        self.output_file.write_text("\n".join(tree))
        print(f"✅ REPO_MAP.md generated at {self.output_file} ({len(tree)} lines)")

    def _get_timestamp(self):
        import datetime

        return datetime.datetime.now().isoformat()


if __name__ == "__main__":
    mapper = RepositoryMapper()
    mapper.generate_map()
