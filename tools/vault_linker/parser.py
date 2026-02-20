"""Parser module for extracting frontmatter and wiki-links from vault markdown files."""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from collections import defaultdict
import yaml


class VaultParser:
    """Parser for Obsidian vault markdown files."""

    # Regex patterns
    FRONTMATTER_PATTERN = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL | re.MULTILINE)
    WIKILINK_PATTERN = re.compile(r'\[\[([^\]|#]+)(?:[|#][^\]]*?)?\]\]')

    # Directories to exclude from parsing
    EXCLUDE_DIRS = {'.git', 'node_modules', '.obsidian', 'mcp-server',
                     'obsidian-plugin', '.claude', 'tools', 'htmlcov', 'docs', '.venv'}

    def parse_frontmatter(self, content: str) -> Dict[str, Any]:
        """
        Extract YAML frontmatter from markdown content.

        Args:
            content: Markdown file content

        Returns:
            Dictionary of frontmatter fields
        """
        match = self.FRONTMATTER_PATTERN.match(content)
        if not match:
            return {}

        frontmatter_text = match.group(1)
        try:
            # Use a custom constructor to keep dates as strings
            class StringDateLoader(yaml.SafeLoader):
                pass

            def string_constructor(loader, node):
                return loader.construct_scalar(node)

            StringDateLoader.add_constructor('tag:yaml.org,2002:timestamp', string_constructor)

            frontmatter = yaml.load(frontmatter_text, Loader=StringDateLoader)
            return frontmatter if frontmatter else {}
        except yaml.YAMLError:
            return {}

    def extract_wiki_links(self, content: str) -> List[str]:
        """
        Extract wiki-links from markdown content.

        Handles variants:
        - [[name]]
        - [[name|Display Text]]
        - [[name#heading]]

        Args:
            content: Markdown content

        Returns:
            List of unique link targets (without display text or headings)
        """
        matches = self.WIKILINK_PATTERN.findall(content)
        # Remove duplicates while preserving order
        seen: Set[str] = set()
        links = []
        for match in matches:
            link = match.strip()
            if link and link not in seen:
                seen.add(link)
                links.append(link)
        return links

    def parse_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Parse a complete markdown file.

        Args:
            file_path: Path to markdown file

        Returns:
            Dictionary containing:
                - path: Path object
                - stem: Filename without extension
                - frontmatter: Parsed frontmatter
                - wiki_links: List of wiki-links
                - similar_papers: List from frontmatter (if present)
        """
        try:
            content = file_path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            return {
                'path': file_path,
                'stem': file_path.stem,
                'frontmatter': {},
                'wiki_links': [],
                'similar_papers': []
            }

        frontmatter = self.parse_frontmatter(content)
        wiki_links = self.extract_wiki_links(content)

        return {
            'path': file_path,
            'stem': file_path.stem,
            'frontmatter': frontmatter,
            'wiki_links': wiki_links,
            'similar_papers': frontmatter.get('similar_papers') or []
        }

    def walk_vault(self, vault_path: Path) -> tuple[Dict[str, Any], Dict[str, Dict[str, Set[str]]]]:
        """
        Recursively walk vault and build files index and link graph.

        Args:
            vault_path: Root path of the vault

        Returns:
            Tuple of (files_index, link_graph):
                - files_index: Dict mapping stem -> file metadata
                - link_graph: Dict mapping stem -> {'outgoing': set, 'incoming': set}
        """
        files_index: Dict[str, Any] = {}
        link_graph: Dict[str, Dict[str, Set[str]]] = defaultdict(lambda: {'outgoing': set(), 'incoming': set()})

        # Walk vault recursively
        for md_file in vault_path.rglob('*.md'):
            # Skip excluded directories
            if any(part in self.EXCLUDE_DIRS for part in md_file.parts):
                continue

            # Parse file
            parsed = self.parse_file(md_file)
            stem = parsed['stem'].lower()  # Normalize to lowercase for matching

            # Store in index
            files_index[stem] = parsed

            # Build link graph
            for link in parsed['wiki_links']:
                link_target = link.lower()  # Normalize link target
                link_graph[stem]['outgoing'].add(link_target)
                link_graph[link_target]['incoming'].add(stem)

        return files_index, link_graph

    def classify_broken_links(
        self,
        files_index: Dict[str, Any],
        link_graph: Dict[str, Dict[str, Set[str]]]
    ) -> Dict[str, List[str]]:
        """
        Classify broken links into categories.

        Args:
            files_index: Files index from walk_vault
            link_graph: Link graph from walk_vault

        Returns:
            Dictionary of broken link categories:
                - date_prefixed: Links with YYYY-MM-DD- prefix
                - external: Links that look like external references
                - missing: All other broken links
        """
        categories: Dict[str, List[str]] = {
            'date_prefixed': [],
            'external': [],
            'missing': []
        }

        # Find all link targets
        all_targets = set()
        for node_links in link_graph.values():
            all_targets.update(node_links['outgoing'])

        # Classify broken links
        for target in all_targets:
            if target in files_index:
                continue  # Not broken

            # Check for date prefix (YYYY-MM-DD-)
            if re.match(r'^\d{4}-\d{2}-\d{2}-', target):
                categories['date_prefixed'].append(target)
            # Check for external reference patterns (underscores, no hyphens)
            elif '_' in target and '-' not in target:
                categories['external'].append(target)
            else:
                categories['missing'].append(target)

        return categories
