"""Obsidian-aware operations: links, tags, templates."""

import re
from datetime import UTC, datetime
from pathlib import Path

import yaml

from .vault_ops import VaultOps


class ObsidianOps:
    """Operations that understand Obsidian's wiki-link and tag conventions."""

    # Matches [[note]] and [[note|alias]]
    WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")
    # Matches #tag (not in frontmatter)
    INLINE_TAG_RE = re.compile(r"(?:^|\s)#([a-zA-Z][a-zA-Z0-9_/-]*)")

    def __init__(self, vault: VaultOps):
        self.vault = vault

    def backlinks(self, path: str) -> list[dict]:
        """Find all notes linking to the given note."""
        target_name = Path(path).stem
        results = []

        for filepath in self.vault.vault_path.rglob("*.md"):
            if self.vault._is_hidden(filepath):
                continue
            rel = str(filepath.relative_to(self.vault.vault_path))
            if rel == path:
                continue

            content = filepath.read_text(encoding="utf-8")
            links = self.WIKILINK_RE.findall(content)

            for link in links:
                link_target = link.split("/")[-1] if "/" in link else link
                if link_target == target_name or link == path.replace(".md", ""):
                    results.append(
                        {
                            "source": rel,
                            "link_text": link,
                        }
                    )
                    break

        return results

    def forward_links(self, path: str) -> list[dict]:
        """Find all notes that a given note links to."""
        content = self.vault.read(path)
        links = self.WIKILINK_RE.findall(content)

        results = []
        for link in links:
            # Try to resolve the link to an actual file
            resolved = self._resolve_wikilink(link)
            results.append(
                {
                    "link": link,
                    "resolved_path": resolved,
                    "exists": resolved is not None,
                }
            )
        return results

    def tags(self, path: str | None = None) -> list[str]:
        """List all tags in the vault, or tags for a specific note."""
        if path:
            return self._tags_for_note(path)
        return self._all_tags()

    def create_from_template(
        self,
        template_name: str,
        target_path: str,
        variables: dict[str, str],
    ) -> str:
        """Create a new note from a template with variable substitution."""
        # Find the template - look in each directory for _template.md
        template_path = self._find_template(template_name)
        if not template_path:
            raise FileNotFoundError(f"Template not found: {template_name}")

        template_content = self.vault.read(template_path)

        # Apply variable substitution
        content = template_content
        variables.setdefault("date", datetime.now(UTC).strftime("%Y-%m-%d"))

        for key, value in variables.items():
            content = content.replace("{{" + key + "}}", value)

        self.vault.write(target_path, content)
        return f"Created {target_path} from template {template_name}"

    def _tags_for_note(self, path: str) -> list[str]:
        """Extract tags from a specific note."""
        content = self.vault.read(path)
        tags = set()

        # Frontmatter tags
        fm = self.vault._extract_frontmatter(content)
        if fm:
            try:
                data = yaml.safe_load(fm)
                if isinstance(data, dict):
                    fm_tags = data.get("tags", [])
                    if isinstance(fm_tags, list):
                        tags.update(str(t) for t in fm_tags)
                    elif isinstance(fm_tags, str):
                        tags.add(fm_tags)
            except yaml.YAMLError:
                pass

        # Inline tags
        body = content
        if content.startswith("---"):
            end = content.find("---", 3)
            if end != -1:
                body = content[end + 3 :]

        for match in self.INLINE_TAG_RE.finditer(body):
            tags.add(match.group(1))

        return sorted(tags)

    def _all_tags(self) -> list[str]:
        """Collect all tags across the vault."""
        all_tags = set()

        for filepath in self.vault.vault_path.rglob("*.md"):
            if self.vault._is_hidden(filepath):
                continue
            rel = str(filepath.relative_to(self.vault.vault_path))
            try:
                note_tags = self._tags_for_note(rel)
                all_tags.update(note_tags)
            except (FileNotFoundError, UnicodeDecodeError):
                continue

        return sorted(all_tags)

    def _resolve_wikilink(self, link: str) -> str | None:
        """Try to resolve a wikilink to a vault path."""
        # Direct path match
        if (self.vault.vault_path / f"{link}.md").is_file():
            return f"{link}.md"

        # Search by filename
        name = link.split("/")[-1] if "/" in link else link
        for filepath in self.vault.vault_path.rglob(f"{name}.md"):
            if not self.vault._is_hidden(filepath):
                return str(filepath.relative_to(self.vault.vault_path))

        return None

    def _find_template(self, template_name: str) -> str | None:
        """Find a template by name. Searches for _template.md in named directories."""
        # Direct path
        if (self.vault.vault_path / template_name).is_file():
            return template_name

        # Look for _template.md in a directory matching the name
        candidate = self.vault.vault_path / template_name / "_template.md"
        if candidate.is_file():
            return f"{template_name}/_template.md"

        # Search all _template.md files
        for filepath in self.vault.vault_path.rglob("_template.md"):
            if filepath.parent.name == template_name:
                return str(filepath.relative_to(self.vault.vault_path))

        return None
