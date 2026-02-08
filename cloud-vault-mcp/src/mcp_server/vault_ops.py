"""Core vault file operations."""

import os
import re
from pathlib import Path


class VaultOps:
    """Low-level vault file operations with path safety."""

    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path).resolve()
        if not self.vault_path.is_dir():
            raise ValueError(f"Vault path does not exist: {self.vault_path}")

    def _resolve(self, path: str) -> Path:
        """Resolve a vault-relative path safely, preventing directory traversal."""
        resolved = (self.vault_path / path).resolve()
        if not str(resolved).startswith(str(self.vault_path)):
            raise ValueError(f"Path escapes vault: {path}")
        return resolved

    def read(self, path: str) -> str:
        """Read a note's content."""
        target = self._resolve(path)
        if not target.is_file():
            raise FileNotFoundError(f"Note not found: {path}")
        return target.read_text(encoding="utf-8")

    def write(self, path: str, content: str) -> str:
        """Create or overwrite a note."""
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"Written: {path}"

    def edit(self, path: str, edits: list[dict]) -> str:
        """Apply surgical edits to an existing note.

        Each edit is a dict with:
          - operation: "find_replace", "append", "prepend", "insert_at_heading"
          - For find_replace: find, replace
          - For append/prepend: text
          - For insert_at_heading: heading, text
        """
        target = self._resolve(path)
        if not target.is_file():
            raise FileNotFoundError(f"Note not found: {path}")

        content = target.read_text(encoding="utf-8")
        applied = []

        for edit in edits:
            op = edit.get("operation", "")

            if op == "find_replace":
                find_str = edit["find"]
                replace_str = edit["replace"]
                if find_str in content:
                    content = content.replace(find_str, replace_str, 1)
                    applied.append(f"Replaced '{find_str[:40]}...'")
                else:
                    applied.append(f"Not found: '{find_str[:40]}...'")

            elif op == "append":
                content = content + "\n" + edit["text"]
                applied.append("Appended text")

            elif op == "prepend":
                content = edit["text"] + "\n" + content
                applied.append("Prepended text")

            elif op == "insert_at_heading":
                heading = edit["heading"]
                text = edit["text"]
                pattern = rf"(^#{{1,6}}\s+{re.escape(heading)}\s*$)"
                match = re.search(pattern, content, re.MULTILINE)
                if match:
                    insert_pos = match.end()
                    content = content[:insert_pos] + "\n" + text + content[insert_pos:]
                    applied.append(f"Inserted after heading '{heading}'")
                else:
                    applied.append(f"Heading not found: '{heading}'")

            else:
                applied.append(f"Unknown operation: {op}")

        target.write_text(content, encoding="utf-8")
        return "; ".join(applied)

    def delete(self, path: str) -> str:
        """Delete a note."""
        target = self._resolve(path)
        if not target.is_file():
            raise FileNotFoundError(f"Note not found: {path}")
        target.unlink()
        return f"Deleted: {path}"

    def list_dir(self, directory: str = "", recursive: bool = False) -> list[str]:
        """List vault contents."""
        target = self._resolve(directory) if directory else self.vault_path
        if not target.is_dir():
            raise FileNotFoundError(f"Directory not found: {directory}")

        results = []
        if recursive:
            for item in sorted(target.rglob("*")):
                if item.is_file() and not self._is_hidden(item):
                    results.append(str(item.relative_to(self.vault_path)))
        else:
            for item in sorted(target.iterdir()):
                if not self._is_hidden(item):
                    rel = str(item.relative_to(self.vault_path))
                    results.append(rel + "/" if item.is_dir() else rel)
        return results

    def search(self, query: str, scope: str = "all", folder: str = "") -> list[dict]:
        """Full-text search across vault.

        Returns list of {path, line_number, line, context} dicts.
        """
        results = []
        query_lower = query.lower()

        if scope == "folder" and folder:
            search_root = self._resolve(folder)
        else:
            search_root = self.vault_path

        if not search_root.is_dir():
            return results

        for filepath in search_root.rglob("*.md"):
            if self._is_hidden(filepath):
                continue

            rel_path = str(filepath.relative_to(self.vault_path))

            if scope == "tags":
                content = filepath.read_text(encoding="utf-8")
                if self._matches_tag(content, query):
                    results.append(
                        {
                            "path": rel_path,
                            "match_type": "tag",
                            "snippet": self._extract_frontmatter(content)[:200],
                        }
                    )
                continue

            try:
                lines = filepath.read_text(encoding="utf-8").splitlines()
            except (UnicodeDecodeError, OSError):
                continue

            for i, line in enumerate(lines):
                if query_lower in line.lower():
                    context_start = max(0, i - 1)
                    context_end = min(len(lines), i + 2)
                    results.append(
                        {
                            "path": rel_path,
                            "line_number": i + 1,
                            "line": line.strip(),
                            "context": "\n".join(
                                lines[context_start:context_end]
                            ),
                        }
                    )

        return results

    def _is_hidden(self, path: Path) -> bool:
        """Check if path is hidden or in a hidden directory."""
        parts = path.relative_to(self.vault_path).parts
        return any(part.startswith(".") for part in parts)

    def _matches_tag(self, content: str, tag: str) -> bool:
        """Check if content has a specific tag in frontmatter or inline."""
        tag_clean = tag.lstrip("#")
        # Check frontmatter tags
        fm = self._extract_frontmatter(content)
        if tag_clean.lower() in fm.lower():
            return True
        # Check inline tags
        if f"#{tag_clean}" in content:
            return True
        return False

    def _extract_frontmatter(self, content: str) -> str:
        """Extract YAML frontmatter from content."""
        if content.startswith("---"):
            end = content.find("---", 3)
            if end != -1:
                return content[3:end].strip()
        return ""
