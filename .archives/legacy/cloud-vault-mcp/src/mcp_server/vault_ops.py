"""Core vault file operations."""

import re
from pathlib import Path

from mcp_server.search_cache import SearchCache


class VaultOps:
    """Low-level vault file operations with path safety."""

    def __init__(
        self, vault_path: str, cache_enabled: bool = True, cache_ttl_seconds: float = 60
    ):
        self.vault_path = Path(vault_path).resolve()
        if not self.vault_path.is_dir():
            raise ValueError(f"Vault path does not exist: {self.vault_path}")

        self._cache_enabled = cache_enabled
        self._search_cache = (
            SearchCache(ttl_seconds=cache_ttl_seconds) if cache_enabled else None
        )

    def _resolve(self, path: str) -> Path:
        """Resolve a vault-relative path safely, preventing directory traversal.

        Security:
        - Rejects paths with .. components
        - Resolves symlinks and validates final location
        - Ensures final path is within vault directory
        - Prevents symlink escape attacks
        """
        # Reject obvious traversal attempts
        if ".." in path or path.startswith("/"):
            raise ValueError(f"Invalid path (traversal attempt): {path}")

        # Construct candidate path
        candidate = self.vault_path / path

        # Resolve all symlinks to get real path
        try:
            resolved = candidate.resolve(strict=False)
        except (OSError, RuntimeError) as e:
            raise ValueError(f"Cannot resolve path: {path}") from e

        # Verify resolved path is within vault
        vault_str = str(self.vault_path.resolve())
        resolved_str = str(resolved)

        # Use startswith with trailing slash to prevent partial prefix matches
        if not (resolved_str.startswith(vault_str + "/") or resolved_str == vault_str):
            raise ValueError(f"Path escapes vault: {path} -> {resolved_str}")

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
        Caches results when enabled.
        """
        # Check cache first
        if self._cache_enabled:
            cache_key = SearchCache.generate_key(query, scope, folder)
            cached_results = self._search_cache.get(cache_key)
            if cached_results is not None:
                return cached_results

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
                            "context": "\n".join(lines[context_start:context_end]),
                        }
                    )

        # Cache the results before returning
        if self._cache_enabled:
            cache_key = SearchCache.generate_key(query, scope, folder)
            self._search_cache.set(cache_key, results)

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
        return f"#{tag_clean}" in content

    def _extract_frontmatter(self, content: str) -> str:
        """Extract YAML frontmatter from content."""
        if content.startswith("---"):
            end = content.find("---", 3)
            if end != -1:
                return content[3:end].strip()
        return ""

    def invalidate_search_cache(self, key: str | None = None) -> int:
        """Invalidate search cache.

        Args:
            key: Specific cache key to invalidate. If None, clears all cache.

        Returns:
            Number of entries removed
        """
        if not self._cache_enabled or self._search_cache is None:
            return 0

        if key is None:
            return self._search_cache.clear()
        return 1 if self._search_cache.invalidate(key) else 0

    def invalidate_search_cache_for_file(self, file_path: str) -> int:
        """Invalidate cache entries related to a file.

        Clears all search cache since any file change could affect any search.

        Args:
            file_path: Path of the changed file (for logging)

        Returns:
            Number of entries removed
        """
        if not self._cache_enabled:
            return 0

        return self._search_cache.clear() if self._search_cache else 0

    def get_search_cache_stats(self) -> dict:
        """Get search cache statistics.

        Returns:
            Dictionary with cache stats or empty dict if cache disabled
        """
        if not self._cache_enabled or self._search_cache is None:
            return {"enabled": False}

        stats = self._search_cache.get_stats()
        stats["enabled"] = True
        return stats
