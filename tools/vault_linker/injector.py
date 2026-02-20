"""Cross-reference link injector for papers and concepts."""

import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any


class LinkInjector:
    """Injects cross-reference links to papers and concepts."""

    WIKILINK_PATTERN = re.compile(r'\[\[([^\]|#]+)(?:[|#][^\]]*?)?\]\]')
    RELATED_PAPERS_PATTERNS = [r'^\s*##\s+Related\s+Papers', r'^\s*##\s+Related\b']
    RELATED_CONCEPTS_PATTERNS = [r'^\s*##\s+Related\s+Concepts', r'^\s*##\s+See\s+Also']

    def __init__(self, files_index: Dict[str, Any], max_links: int = 8):
        self.files_index = files_index
        self.max_links = max_links

    def validate_similar_paper(self, source: str, target: str) -> bool:
        """Validate if similar_papers entry shares tags with source."""
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
        """Detect existing Related sections."""
        has_papers = any(re.search(p, content, re.MULTILINE | re.IGNORECASE)
                         for p in self.RELATED_PAPERS_PATTERNS)
        has_concepts = any(re.search(p, content, re.MULTILINE | re.IGNORECASE)
                          for p in self.RELATED_CONCEPTS_PATTERNS)
        return has_papers, has_concepts

    def _find_section_end(self, content: str, patterns: List[str]) -> int:
        """Find the end position of a Related section (before next heading or EOF)."""
        for pattern in patterns:
            match = re.search(pattern, content, re.MULTILINE | re.IGNORECASE)
            if match:
                # Find the next heading after this section
                rest = content[match.end():]
                next_heading = re.search(r'^\s*##\s+', rest, re.MULTILINE)
                if next_heading:
                    return match.end() + next_heading.start()
                return len(content)
        return -1

    def _build_new_links(self, candidates: List[str], existing_links: Set[str]) -> List[str]:
        """Filter candidates against existing links."""
        new_links = []
        for candidate in candidates:
            if candidate.lower() not in existing_links and len(new_links) < self.max_links:
                new_links.append(candidate)
        return new_links

    def inject_links(self, file_path: Path, file_stem: str) -> str:
        """Inject cross-reference links to file, appending to existing sections."""
        content = file_path.read_text(encoding='utf-8')
        existing_links = self.extract_all_wikilinks(content)

        file_meta = self.files_index.get(file_stem, {})
        frontmatter = file_meta.get("frontmatter", {})
        tags = set(frontmatter.get("tags", []) or [])
        similar_papers = file_meta.get("similar_papers") or frontmatter.get("similar_papers") or []

        has_papers, has_concepts = self.detect_related_sections(content)

        # Build Related Papers from validated similar_papers
        paper_candidates = []
        if similar_papers:
            for paper in similar_papers:
                paper_lower = paper.lower()
                if paper_lower not in existing_links and self.validate_similar_paper(file_stem, paper_lower):
                    paper_candidates.append(paper)
                if len(paper_candidates) >= self.max_links:
                    break

        if paper_candidates:
            links_text = "".join(f"- [[{p}]]\n" for p in paper_candidates)
            if has_papers:
                # Append to existing section
                insert_pos = self._find_section_end(content, self.RELATED_PAPERS_PATTERNS)
                if insert_pos > 0:
                    content = content[:insert_pos].rstrip('\n') + "\n" + links_text + content[insert_pos:]
            else:
                content += f"\n## Related Papers\n\n{links_text}"

        # Re-extract links after potential paper injection
        existing_links = self.extract_all_wikilinks(content)

        # Build Related Concepts from tag overlap
        concept_candidates = []
        if tags:
            similar_papers_set = set(s.lower() for s in (similar_papers or []))
            for concept_stem, concept_meta in self.files_index.items():
                if len(concept_candidates) >= self.max_links:
                    break
                if concept_stem == file_stem:
                    continue
                if concept_stem.lower() in existing_links:
                    continue
                if concept_stem.lower() in similar_papers_set:
                    continue
                concept_tags = set(concept_meta.get("frontmatter", {}).get("tags", []) or [])
                if tags & concept_tags:
                    concept_candidates.append(concept_stem)

        if concept_candidates:
            links_text = "".join(f"- [[{c}]]\n" for c in concept_candidates)
            if has_concepts:
                insert_pos = self._find_section_end(content, self.RELATED_CONCEPTS_PATTERNS)
                if insert_pos > 0:
                    content = content[:insert_pos].rstrip('\n') + "\n" + links_text + content[insert_pos:]
            else:
                content += f"\n## Related Concepts\n\n{links_text}"

        return content
