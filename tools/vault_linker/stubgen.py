"""Concept stub generator for frequently-referenced broken links."""

import re
from pathlib import Path
from typing import Dict, List, Set, Any
from datetime import datetime
from collections import defaultdict


class StubGenerator:
    """Generates concept stub files for frequently-referenced broken links."""

    MIN_REFERENCES = 3  # Minimum references to create a stub
    EXTERNAL_PATTERNS = [
        r'_',  # Underscores (e.g., fractal_universe, enhanced_simulator)
        r'\.py$',  # Python files
        r'\.js$',  # JavaScript files
    ]

    def __init__(self, vault_path: Path = None):
        """
        Initialize stub generator.

        Args:
            vault_path: Root path of the vault (for creating stub files)
        """
        self.vault_path = vault_path

    def _is_date_prefixed(self, link: str) -> bool:
        """Check if link has date prefix (YYYY-MM-DD-)."""
        return bool(re.match(r'^\d{4}-\d{2}-\d{2}-', link))

    def _is_external_reference(self, link: str) -> bool:
        """Check if link matches external reference patterns."""
        for pattern in self.EXTERNAL_PATTERNS:
            if re.search(pattern, link):
                return True
        return False

    def identify_stub_candidates(
        self,
        link_graph: Dict[str, Dict[str, Set[str]]],
        files_index: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Identify broken links that should get stub files.

        Args:
            link_graph: Link graph from vault parser
            files_index: Files index from vault parser

        Returns:
            Dict mapping stub name -> {"ref_count": int, "references": List[str]}
        """
        # Count references to each link target
        reference_counts: Dict[str, List[str]] = defaultdict(list)

        for source_file, links in link_graph.items():
            for target in links.get("outgoing", set()):
                if target not in files_index:  # Only broken links
                    reference_counts[target].append(source_file)

        # Filter candidates
        candidates = {}
        for target, referencing_files in reference_counts.items():
            # Skip if too few references
            if len(referencing_files) < self.MIN_REFERENCES:
                continue

            # Skip date-prefixed links
            if self._is_date_prefixed(target):
                continue

            # Skip external references
            if self._is_external_reference(target):
                continue

            candidates[target] = {
                "ref_count": len(referencing_files),
                "references": referencing_files
            }

        return candidates

    def generate_stub(self, stub_name: str, referencing_files: List[str]) -> str:
        """
        Generate stub file content.

        Args:
            stub_name: Name for the stub (will be used in filename and title)
            referencing_files: List of files that reference this concept

        Returns:
            Stub file content as markdown string
        """
        # Create title from stub name
        title = stub_name.replace('-', ' ').title()

        # Get today's date
        today = datetime.now().strftime("%Y-%m-%d")

        # Build stub content
        stub_content = f"""---
title: "{title}"
date: {today}
tags: [concept]
---
## Definition

> Auto-generated stub. Expand with full content.

[Add definition here]

## Key Properties

- [Add property 1]
- [Add property 2]

## Related Papers

"""

        # Add related papers from referencing files
        for ref_file in sorted(referencing_files):
            stub_content += f"- [[{ref_file}]]\n"

        stub_content += """
## Related Concepts

- [Add related concepts]

## Relevance to Cohezion

[Describe relevance to the Cohezion framework]
"""

        return stub_content

    def generate_stubs(
        self,
        link_graph: Dict[str, Dict[str, Set[str]]],
        files_index: Dict[str, Any]
    ) -> List[str]:
        """
        Generate stub files for all candidates.

        Args:
            link_graph: Link graph from vault parser
            files_index: Files index from vault parser

        Returns:
            List of stub names that were created
        """
        if not self.vault_path:
            raise ValueError("vault_path must be set to generate stubs")

        # Identify candidates
        candidates = self.identify_stub_candidates(link_graph, files_index)

        # Ensure concepts directory exists
        concepts_dir = self.vault_path / "concepts"
        concepts_dir.mkdir(exist_ok=True)

        # Generate stubs
        stubs_created = []
        for stub_name, candidate_data in candidates.items():
            stub_file = concepts_dir / f"{stub_name}.md"

            # Skip if file already exists
            if stub_file.exists():
                continue

            # Generate and write stub content
            stub_content = self.generate_stub(stub_name, candidate_data["references"])
            stub_file.write_text(stub_content, encoding='utf-8')

            stubs_created.append(stub_name)

        return stubs_created
