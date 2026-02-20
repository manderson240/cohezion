"""Link resolver for mapping broken wiki-links to existing files using fuzzy matching."""

import re
from typing import Any, List, Dict


class LinkResolver:
    """Resolver for broken wiki-links using fuzzy matching strategies."""

    def __init__(self, existing_files: List[str]):
        """
        Initialize resolver with existing file stems.

        Args:
            existing_files: List of existing file stems (normalized to lowercase)
        """
        self.existing_files = set(f.lower() for f in existing_files)

    def _normalize_slug(self, text: str) -> str:
        """
        Normalize text to slug format.

        - Convert to lowercase
        - Replace spaces and underscores with hyphens
        - Remove special characters (keep only alphanumeric and hyphens)

        Args:
            text: Text to normalize

        Returns:
            Normalized slug
        """
        slug = text.lower()
        slug = re.sub(r'[\s_]+', '-', slug)  # spaces/underscores to hyphens
        slug = re.sub(r'[^a-z0-9-]+', '', slug)  # remove special chars
        slug = re.sub(r'-+', '-', slug)  # collapse multiple hyphens
        slug = slug.strip('-')  # remove leading/trailing hyphens
        return slug

    def _strip_date_prefix(self, text: str) -> str:
        """
        Strip date prefix (YYYY-MM-DD-) from text.

        Args:
            text: Text potentially with date prefix

        Returns:
            Text without date prefix
        """
        return re.sub(r'^\d{4}-\d{2}-\d{2}-', '', text)

    def resolve_link(self, link_text: str) -> List[Dict[str, Any]]:
        """
        Resolve a broken link to possible matches.

        Strategies (in priority order):
        1. Case-insensitive exact match (confidence: 1.0)
        2. Slug normalization (confidence: 0.9)
        3. Date prefix stripping (confidence: 0.85)
        4. Constrained partial match (confidence: 0.5-0.7)

        Args:
            link_text: The broken link text

        Returns:
            List of matches sorted by confidence descending.
            Each match is a dict with 'target' and 'confidence' keys.
        """
        matches = []
        link_lower = link_text.lower()

        # Strategy 1: Case-insensitive exact match
        if link_lower in self.existing_files:
            matches.append({"target": link_lower, "confidence": 1.0})
            return matches  # Perfect match, no need to continue

        # Strategy 2: Slug normalization
        normalized_link = self._normalize_slug(link_text)
        if normalized_link in self.existing_files:
            matches.append({"target": normalized_link, "confidence": 0.9})
            return matches  # High confidence match found

        # Strategy 3: Date prefix stripping
        stripped_link = self._strip_date_prefix(link_lower)
        if stripped_link in self.existing_files:
            matches.append({"target": stripped_link, "confidence": 0.85})

        # Also try stripping date prefix from existing files
        for existing in self.existing_files:
            stripped_existing = self._strip_date_prefix(existing)
            if stripped_existing == stripped_link and existing not in [m["target"] for m in matches]:
                matches.append({"target": existing, "confidence": 0.85})

        if matches:
            return matches

        # Strategy 4: Constrained partial match
        # Link text must match a full hyphen-delimited segment
        link_segments = set(normalized_link.split('-'))

        for existing in self.existing_files:
            existing_segments = set(existing.split('-'))

            # Check if any link segment matches an existing segment completely
            common_segments = link_segments & existing_segments

            if common_segments:
                # Calculate confidence based on segment overlap
                # More overlap = higher confidence
                overlap_ratio = len(common_segments) / max(len(link_segments), len(existing_segments))

                # Only suggest if overlap is meaningful
                if overlap_ratio > 0.3:
                    confidence = 0.5 + (overlap_ratio * 0.2)  # 0.5 to 0.7 range
                    matches.append({"target": existing, "confidence": confidence})

        # Sort by confidence descending
        matches.sort(key=lambda x: x["confidence"], reverse=True)

        return matches
