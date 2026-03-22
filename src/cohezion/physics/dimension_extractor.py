"""
Dimension Extractor - Extract 12D physics dimensions from text/embeddings.

Maps semantic content to physical coordinates for visualization:
- Spatial (x, y, z): Derived from UMAP/PCA reduction of embeddings
- Temporal: Document age or temporal references
- Mass: Importance/centrality in knowledge graph
- Sentiment: Emotional tone (-1 to 1)
- Complexity: Linguistic complexity measure
- Factuality: Confidence in factual claims
- Connectivity: How related to other content
- Stability: Consistency over time
- Novelty: Uniqueness compared to corpus
- Coherence: Internal logical coherence
"""

import logging
import re
from datetime import datetime
from typing import Any


try:
    import numpy as np
except ImportError:
    np = None

from cohezion.core.persistence.surreal_client import PhysicsState


logger = logging.getLogger(__name__)


class DimensionExtractor:
    """
    Extracts 12 physics dimensions from text and embeddings.

    The extracted dimensions are used for:
    1. Manim 3D visualization (x, y, z projected)
    2. Physics simulation interactions (mass, stability)
    3. Semantic clustering and search
    """

    # Common question words for factuality detection
    QUESTION_WORDS = {"who", "what", "when", "where", "why", "how"}

    # Words indicating uncertainty
    UNCERTAINTY_WORDS = {
        "maybe",
        "perhaps",
        "possibly",
        "might",
        "could",
        "uncertain",
        "unclear",
        "unknown",
        "debatable",
    }

    # Words indicating confidence
    CONFIDENCE_WORDS = {
        "definitely",
        "certainly",
        "clearly",
        "obviously",
        "proven",
        "known",
        "established",
        "confirmed",
    }

    def __init__(
        self,
        embedding_dim: int = 768,
        use_pca: bool = True,
        random_state: int = 42,
    ):
        """
        Initialize the dimension extractor.

        Args:
            embedding_dim: Expected embedding dimension (default 768 for nomic)
            use_pca: Whether to use PCA for spatial projection
            random_state: Random state for reproducibility
        """
        self.embedding_dim = embedding_dim
        self.use_pca = use_pca
        self.random_state = random_state
        self._projection_matrix: np.ndarray | None = None

    def extract(
        self,
        text: str,
        embedding: np.ndarray | list[float] | None = None,
        created_at: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PhysicsState:
        """
        Extract 12D physics state from text and optional embedding.

        Args:
            text: The content to analyze
            embedding: Optional pre-computed embedding vector
            created_at: Creation timestamp for temporal dimension
            metadata: Additional metadata for extraction

        Returns:
            PhysicsState with all 12 dimensions populated
        """
        # Convert embedding if provided
        if embedding is not None and isinstance(embedding, list):
            embedding = np.array(embedding)

        # Extract spatial dimensions from embedding
        x, y, z = self._extract_spatial(embedding)

        # Extract temporal dimension
        time_dim = self._extract_temporal(created_at, text)

        # Extract semantic dimensions
        mass = self._extract_mass(text, metadata)
        sentiment = self._extract_sentiment(text)
        complexity = self._extract_complexity(text)
        factuality = self._extract_factuality(text)

        # Extract relational dimensions
        connectivity = self._extract_connectivity(metadata)
        stability = self._extract_stability(metadata)

        # Extract abstract dimensions
        novelty = self._extract_novelty(embedding)
        coherence = self._extract_coherence(text)

        return PhysicsState(
            x=x,
            y=y,
            z=z,
            time=time_dim,
            mass=mass,
            sentiment=sentiment,
            complexity=complexity,
            factuality=factuality,
            connectivity=connectivity,
            stability=stability,
            novelty=novelty,
            coherence=coherence,
        )

    def _extract_spatial(
        self,
        embedding: np.ndarray | None,
    ) -> tuple[float, float, float]:
        """
        Project high-dimensional embedding to 3D space.

        Uses PCA or random projection to reduce dimensions.
        """
        if embedding is None:
            # Random position for documents without embeddings
            rng = np.random.RandomState(self.random_state)
            return (
                float(rng.uniform(-1, 1)),
                float(rng.uniform(-1, 1)),
                float(rng.uniform(-1, 1)),
            )

        # Initialize projection matrix if needed
        if self._projection_matrix is None:
            rng = np.random.RandomState(self.random_state)
            self._projection_matrix = rng.randn(len(embedding), 3)
            # Orthogonalize
            self._projection_matrix, _ = np.linalg.qr(self._projection_matrix)

        # Project to 3D
        if len(embedding) != self._projection_matrix.shape[0]:
            # Dimension mismatch - reinitialize
            rng = np.random.RandomState(self.random_state)
            self._projection_matrix = rng.randn(len(embedding), 3)
            self._projection_matrix, _ = np.linalg.qr(self._projection_matrix)

        coords = embedding @ self._projection_matrix

        # Normalize to [-1, 1] range
        coords = np.tanh(coords)

        return float(coords[0]), float(coords[1]), float(coords[2])

    def _extract_temporal(
        self,
        created_at: datetime | None,
        text: str,
    ) -> float:
        """
        Extract temporal dimension from timestamp or text.

        Returns a normalized time value in [0, 1].
        """
        if created_at:
            # Days since epoch, normalized
            days = (created_at - datetime(2020, 1, 1)).days
            return min(1.0, max(0.0, days / 2000))  # ~5 years range

        # Try to find temporal markers in text
        temporal_patterns = [
            r"\b(today|now|current|recently)\b",
            r"\b(yesterday|last week|previous)\b",
            r"\b(historical|ancient|old)\b",
            r"\b(future|upcoming|next)\b",
        ]

        for i, pattern in enumerate(temporal_patterns):
            if re.search(pattern, text.lower()):
                return [0.9, 0.6, 0.2, 0.95][i]

        return 0.5  # Default to middle

    def _extract_mass(
        self,
        text: str,
        metadata: dict[str, Any] | None,
    ) -> float:
        """
        Extract mass (importance) from text length and metadata.

        Longer, more detailed content has more "mass".
        """
        # Base mass from text length (log scale)
        word_count = len(text.split())
        length_mass = min(1.0, np.log1p(word_count) / 10)

        # Boost from metadata (e.g., citations, links)
        if metadata:
            citations = metadata.get("citation_count", 0)
            links = metadata.get("link_count", 0)
            boost = min(0.5, (citations + links) / 50)
            length_mass = min(1.0, length_mass + boost)

        return length_mass

    def _extract_sentiment(self, text: str) -> float:
        """
        Extract sentiment from text.

        Simple lexicon-based approach. Returns [-1, 1].
        """
        text_lower = text.lower()

        # Simple positive/negative word lists
        positive = {
            "good",
            "great",
            "excellent",
            "amazing",
            "wonderful",
            "positive",
            "success",
            "benefit",
            "improve",
            "best",
            "love",
            "happy",
            "joy",
            "beautiful",
            "innovative",
        }
        negative = {
            "bad",
            "terrible",
            "awful",
            "poor",
            "worst",
            "negative",
            "failure",
            "harm",
            "decline",
            "problem",
            "hate",
            "sad",
            "fear",
            "ugly",
            "outdated",
        }

        words = set(re.findall(r"\w+", text_lower))

        pos_count = len(words & positive)
        neg_count = len(words & negative)
        total = pos_count + neg_count

        if total == 0:
            return 0.0

        return (pos_count - neg_count) / total

    def _extract_complexity(self, text: str) -> float:
        """
        Extract linguistic complexity.

        Based on average word length and sentence structure.
        """
        words = text.split()
        if not words:
            return 0.0

        # Average word length (normalized)
        avg_word_len = sum(len(w) for w in words) / len(words)
        word_complexity = min(1.0, avg_word_len / 10)

        # Sentence count and length variation
        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) > 1:
            lengths = [len(s.split()) for s in sentences]
            variation = np.std(lengths) / (np.mean(lengths) + 1)
            sentence_complexity = min(1.0, variation)
        else:
            sentence_complexity = 0.3

        return (word_complexity + sentence_complexity) / 2

    def _extract_factuality(self, text: str) -> float:
        """
        Extract factuality confidence.

        Higher for texts with confident, factual language.
        """
        text_lower = text.lower()
        words = set(re.findall(r"\w+", text_lower))

        uncertainty = len(words & self.UNCERTAINTY_WORDS)
        confidence = len(words & self.CONFIDENCE_WORDS)
        questions = len(words & self.QUESTION_WORDS)

        # Start at neutral
        score = 0.5

        # Adjust based on language
        score += confidence * 0.1
        score -= uncertainty * 0.1
        score -= questions * 0.05  # Questions reduce factuality

        return max(0.0, min(1.0, score))

    def _extract_connectivity(
        self,
        metadata: dict[str, Any] | None,
    ) -> float:
        """
        Extract connectivity from metadata.

        Measures how connected this node is to others.
        """
        if not metadata:
            return 0.5  # Default medium connectivity

        # Look for link/reference counts
        outlinks = metadata.get("outlink_count", 0)
        inlinks = metadata.get("inlink_count", 0)
        mentions = metadata.get("mention_count", 0)

        connections = outlinks + inlinks + mentions

        # Log scale, normalized
        return min(1.0, np.log1p(connections) / 5)

    def _extract_stability(
        self,
        metadata: dict[str, Any] | None,
    ) -> float:
        """
        Extract stability from metadata.

        Measures how stable/consistent this content is.
        """
        if not metadata:
            return 0.7  # Default fairly stable

        # Look for edit/version counts
        edit_count = metadata.get("edit_count", 0)
        metadata.get("version_count", 1)

        # More edits = less stable
        instability = min(1.0, edit_count / 20)

        return 1.0 - instability

    def _extract_novelty(
        self,
        embedding: np.ndarray | None,
    ) -> float:
        """
        Extract novelty from embedding.

        Placeholder - would compare against corpus in production.
        """
        if embedding is None:
            return 0.5

        # Use embedding magnitude as proxy for distinctiveness
        magnitude = np.linalg.norm(embedding)

        # Normalize (embeddings are typically ~1.0 magnitude)
        return min(1.0, abs(magnitude - 1.0) * 2)

    def _extract_coherence(self, text: str) -> float:
        """
        Extract internal coherence.

        Measures how internally consistent the text is.
        """
        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) < 2:
            return 0.8  # Single sentence = fairly coherent

        # Check for transition words (indicates structure)
        transitions = {
            "however",
            "therefore",
            "thus",
            "moreover",
            "furthermore",
            "consequently",
            "meanwhile",
            "similarly",
            "additionally",
            "first",
            "second",
            "finally",
            "in conclusion",
        }

        text_lower = text.lower()
        transition_count = sum(1 for t in transitions if t in text_lower)

        # More transitions = more coherent structure
        coherence = min(1.0, 0.5 + transition_count * 0.1)

        return coherence

    def batch_extract(
        self,
        texts: list[str],
        embeddings: list[np.ndarray] | None = None,
    ) -> list[PhysicsState]:
        """
        Extract physics states for a batch of texts.

        More efficient for bulk processing.
        """
        results = []

        for i, text in enumerate(texts):
            embedding = embeddings[i] if embeddings and i < len(embeddings) else None
            results.append(self.extract(text, embedding))

        return results
