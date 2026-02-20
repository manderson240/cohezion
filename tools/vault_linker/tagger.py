"""Tag populator for papers with null tags."""

import re
from pathlib import Path
from typing import List, Set, Optional
from collections import Counter


class TagPopulator:
    """Populates tags for papers with tags: null."""

    # Common stopwords to filter out
    STOPWORDS = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
        'before', 'after', 'above', 'below', 'between', 'under', 'again', 'further',
        'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'both',
        'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not',
        'only', 'own', 'same', 'so', 'than', 'too', 'very', 'can', 'will', 'just',
        'should', 'now', 'using', 'uses', 'used', 'via', 'shows', 'reveals', 'paper',
        'research', 'study', 'findings', 'results', 'new', 'analysis'
    }

    def __init__(self, existing_concepts: Optional[List[str]] = None,
                 existing_tags: Optional[List[List[str]]] = None,
                 files_index: Optional[dict] = None):
        """
        Initialize tag populator.

        Args:
            existing_concepts: List of existing concept file stems
            existing_tags: List of tag arrays from existing papers
            files_index: Full files index for similar_papers tag inheritance
        """
        self.existing_concepts = set(existing_concepts or [])
        self.files_index = files_index or {}
        # Flatten all existing tags into a controlled vocabulary
        self.tag_vocabulary = set()
        if existing_tags:
            for tag_list in existing_tags:
                self.tag_vocabulary.update(tag_list)

    def extract_keywords(self, text: str) -> List[str]:
        """
        Extract keywords from text.

        Args:
            text: Text to extract keywords from

        Returns:
            List of keywords (lowercase, hyphenated)
        """
        # Convert to lowercase
        text = text.lower()

        # Remove markdown formatting
        text = re.sub(r'[#*_`\[\]]', ' ', text)

        # Split into words
        words = re.findall(r'\b[a-z][a-z0-9-]*\b', text)

        # Filter stopwords and short words
        keywords = [w for w in words if w not in self.STOPWORDS and len(w) > 2]

        # Count frequency
        word_freq = Counter(keywords)

        # Also extract common bi-grams (two-word phrases)
        text_normalized = ' '.join(keywords)
        bigrams = []
        words_list = text_normalized.split()
        for i in range(len(words_list) - 1):
            bigram = f"{words_list[i]}-{words_list[i+1]}"
            bigrams.append(bigram)

        # Combine single words and bigrams, prioritize by frequency
        all_keywords = list(word_freq.keys()) + bigrams

        return all_keywords

    def generate_tags_from_keywords(self, keywords: List[str], limit: int = 5) -> List[str]:
        """
        Generate tags from keywords using controlled vocabulary.

        Args:
            keywords: List of extracted keywords
            limit: Maximum number of tags to generate

        Returns:
            List of 3-5 tags
        """
        tags = []

        # Priority 1: Match existing concepts
        for keyword in keywords:
            for concept in self.existing_concepts:
                if keyword in concept or concept in keyword:
                    if concept not in tags:
                        tags.append(concept)
                    if len(tags) >= limit:
                        return tags

        # Priority 2: Match existing tags from controlled vocabulary
        for keyword in keywords:
            if keyword in self.tag_vocabulary and keyword not in tags:
                tags.append(keyword)
            if len(tags) >= limit:
                return tags

        # Priority 3: Use high-frequency keywords
        for keyword in keywords[:10]:  # Top 10 most relevant
            if keyword not in tags and '-' not in keyword:  # Prefer single words
                tags.append(keyword)
            if len(tags) >= limit:
                return tags

        # Priority 4: Use bigrams if we still need more
        for keyword in keywords:
            if '-' in keyword and keyword not in tags:
                tags.append(keyword)
            if len(tags) >= limit:
                return tags

        # Ensure minimum of 2 tags if possible
        if len(tags) < 2 and keywords:
            for kw in keywords:
                if kw not in tags:
                    tags.append(kw)
                if len(tags) >= 2:
                    break

        return tags[:limit]

    def _inherit_from_similar_papers(self, keywords: List[str], content: str) -> List[str]:
        """Inherit common tags from similar_papers that share keyword overlap."""
        # Extract similar_papers from frontmatter in content
        similar_match = re.search(r'^similar_papers:\s*\n((?:\s*-\s*.+\n)*)', content, re.MULTILINE)
        if not similar_match:
            return []

        similar_names = re.findall(r'-\s*(.+)', similar_match.group(1))
        keyword_set = set(keywords[:20])  # Use top 20 keywords for matching
        inherited = []

        for name in similar_names:
            name_lower = name.strip().lower()
            similar_meta = self.files_index.get(name_lower, {})
            similar_tags = similar_meta.get("frontmatter", {}).get("tags") or []
            if not similar_tags or similar_tags is None:
                continue

            # Check keyword overlap: similar paper's title keywords must overlap
            similar_title = similar_meta.get("frontmatter", {}).get("title", "")
            similar_keywords = set(self.extract_keywords(str(similar_title)))
            if keyword_set & similar_keywords:
                inherited.extend(similar_tags)

        # Return unique tags, most common first
        from collections import Counter
        tag_counts = Counter(inherited)
        return [tag for tag, _ in tag_counts.most_common(3)]

    def populate_tags(self, file_path: Path) -> str:
        """
        Populate tags for a paper with tags: null.

        Args:
            file_path: Path to paper markdown file

        Returns:
            Updated file content with tags populated
        """
        content = file_path.read_text(encoding='utf-8')

        # Check if tags are null
        if "tags: null" not in content:
            return content  # Skip if tags already exist

        # Extract title from frontmatter
        title_match = re.search(r'^title:\s*(.+)$', content, re.MULTILINE)
        title = title_match.group(1).strip('"\'') if title_match else ""

        # Extract keywords from title and content
        keywords = self.extract_keywords(title)
        keywords.extend(self.extract_keywords(content))

        # Inherit tags from similar_papers that share keyword overlap
        inherited_tags = self._inherit_from_similar_papers(keywords, content)

        # Generate tags
        tags = self.generate_tags_from_keywords(keywords)

        # Merge inherited tags (deduplicated)
        for tag in inherited_tags:
            if tag not in tags and len(tags) < 5:
                tags.append(tag)

        # Ensure at least 2 tags
        if len(tags) < 2:
            # Fallback: use generic category
            tags.append("research")

        # Format tags as YAML array
        tags_str = f"tags: [{', '.join(tags)}]"

        # Surgical replacement - only replace the tags line
        updated_content = re.sub(
            r'^tags:\s*null\s*$',
            tags_str,
            content,
            count=1,
            flags=re.MULTILINE
        )

        return updated_content
