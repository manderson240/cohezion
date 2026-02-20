"""Cross-reference link injector for papers and concepts."""

import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any


class LinkInjector:
    """Injects cross-reference links to papers and concepts."""

    WIKILINK_PATTERN = re.compile(r'\[\[([^\]|#]+)(?:[|#][^\]]*?)?\]\]')
    RELATED_PAPERS_PATTERNS = [r'^\s*##\s+Related\s+Papers', r'^\s*##\s+Related']
    RELATED_CONCEPTS_PATTERNS = [r'^\s*##\s+Related\s+Concepts', r'^\s*##\s+See\s+Also']

    def __init__(self, files_index: Dict[str, Any], max_links: int = 8):
        """
        Initialize link injector.

        Args:
            files_index: Files index from vault parser
            max_links: Maximum links per section
        """
        self.files_index = files_index
        self.max_links = max_links

    def validate_similar_paper(self, source: str, target: str) -> bool:
        """
        Validate if similar_papers entry shares tags with source.

        Args:
            source: Source file stem
            target: Target file stem

        Returns:
            True if tags overlap exists
        """
        source_meta = self.files_index.get(source, {})
        target_meta = self.files_index.get(target, {})

        source_tags = set(source_meta.get("frontmatter", {}).get("tags", []) or [])
        target_tags = set(target_meta.get("frontmatter", {}).get("tags", []) or [])

        return bool(source_tags & target_tags)

    def extract_all_wikilinks(self, content: str) -> Set[str]:
        """Extract all wiki-links from content."""
        matches = self.WIKILINK_PATTERN.findall(content)
        return set(m.strip().lower() for m in matches)

    def detect_related_sections(self, content: str) -> Tuple[bool, bool]:
        """
        Detect existing Related sections.

        Returns:
            (has_related_papers, has_related_concepts)
        """
        has_papers = any(re.search(p, content, re.MULTILINE | re.IGNORECASE)
                         for p in self.RELATED_PAPERS_PATTERNS)
        has_concepts = any(re.search(p, content, re.MULTILINE | re.IGNORECASE)
                          for p in self.RELATED_CONCEPTS_PATTERNS)
        return has_papers, has_concepts

    def inject_links(self, file_path: Path, file_stem: str) -> str:
        """
        Inject cross-reference links to file.

        Args:
            file_path: Path to file
            file_stem: File stem for lookups

        Returns:
            Updated content with links injected
        """
        content = file_path.read_text(encoding='utf-8')

        # Extract existing links to avoid duplicates
        existing_links = self.extract_all_wikilinks(content)

        # Get file metadata
        file_meta = self.files_index.get(file_stem, {})
        frontmatter = file_meta.get("frontmatter", {})
        tags = set(frontmatter.get("tags", []) or [])
        similar_papers = file_meta.get("similar_papers") or frontmatter.get("similar_papers") or []

        # Check existing sections
        has_papers, has_concepts = self.detect_related_sections(content)

        # Build Related Papers list
        related_papers = []
        if similar_papers and not has_papers:
            for paper in similar_papers:
                if len(related_papers) >= self.max_links:
                    break
                paper_lower = paper.lower()
                if paper_lower not in existing_links and self.validate_similar_paper(file_stem, paper_lower):
                    related_papers.append(paper)

        # Add Related Papers section if we have links
        if related_papers:
            section = "\n## Related Papers\n\n"
            for paper in related_papers:
                section += f"- [[{paper}]]\n"
            content += section

        # Build Related Concepts list (based on tag overlap)
        related_concepts = []
        if tags and not has_concepts:
            # Don't add items that are already in similar_papers
            similar_papers_set = set(s.lower() for s in (similar_papers or []))

            for concept_stem, concept_meta in self.files_index.items():
                if len(related_concepts) >= self.max_links:
                    break
                if concept_stem == file_stem:
                    continue
                if concept_stem.lower() in existing_links:
                    continue
                if concept_stem.lower() in similar_papers_set:
                    continue  # Skip if already in similar_papers

                concept_tags = set(concept_meta.get("frontmatter", {}).get("tags", []) or [])
                if tags & concept_tags:  # Tag overlap
                    related_concepts.append(concept_stem)

        # Add Related Concepts section if we have links
        if related_concepts:
            section = "\n## Related Concepts\n\n"
            for concept in related_concepts:
                section += f"- [[{concept}]]\n"
            content += section

        return content
