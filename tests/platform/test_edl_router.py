"""
Tests for ExpertDomainRouter - Expert Domain Lattice consensus routing.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.platform.edl_router import (
    EDLConsensus,
    ExpertDomainRouter,
    ExpertStream,
    StreamRecommendation,
    get_edl_router,
    reset_edl_router,
)


@pytest.fixture
def mock_compound_client():
    """Mock CompoundClient."""
    mock_client = AsyncMock()
    mock_client.execute = AsyncMock(
        return_value={
            "result": (
                '{"approve": "yes", "recommendation": "Approved",'
                ' "confidence": 0.8, "coherence": 0.5,'
                ' "rationale": "Looks good"}'
            )
        }
    )
    return mock_client


@pytest.fixture
def mock_coherence_tracker():
    """Mock CoherenceTracker."""
    mock_tracker = MagicMock()
    return mock_tracker


@pytest.fixture
def edl_router(mock_compound_client, mock_coherence_tracker):
    """Create ExpertDomainRouter with mocked dependencies."""
    with (
        patch(
            "cohezion.platform.edl_router.get_compound_client",
            return_value=mock_compound_client,
        ),
        patch(
            "cohezion.platform.edl_router.get_coherence_tracker",
            return_value=mock_coherence_tracker,
        ),
    ):
        router = ExpertDomainRouter()
        yield router


class TestExpertStream:
    """Test ExpertStream enum."""

    def test_expert_stream_values(self):
        """Test expert stream enum values."""
        assert ExpertStream.ARCHITECT.value == "architect"
        assert ExpertStream.ENGINEER.value == "engineer"
        assert ExpertStream.BIOLOGIST.value == "biologist"
        assert ExpertStream.QUANTUM_HW.value == "quantum_hw"
        assert ExpertStream.QUANTUM_ALGO.value == "quantum_algo"


class TestStreamRecommendation:
    """Test StreamRecommendation model."""

    def test_stream_recommendation_creation(self):
        """Test creating StreamRecommendation."""
        rec = StreamRecommendation(
            stream=ExpertStream.ARCHITECT,
            recommendation="Approved",
            confidence=0.8,
            coherence=0.5,
            rationale="Good design",
        )

        assert rec.stream == ExpertStream.ARCHITECT
        assert rec.recommendation == "Approved"
        assert rec.confidence == 0.8
        assert rec.coherence == 0.5
        assert rec.rationale == "Good design"


class TestEDLConsensus:
    """Test EDLConsensus model."""

    def test_edl_consensus_creation(self):
        """Test creating EDLConsensus."""
        rec = StreamRecommendation(
            stream=ExpertStream.ARCHITECT,
            recommendation="Approved",
            confidence=0.8,
            coherence=0.5,
            rationale="Good design",
        )

        consensus = EDLConsensus(
            decision="Approved",
            coherence=0.5,
            hiho_stable=True,
            consensus_strength=1.0,
            stream_recommendations=[rec],
            requires_human_review=False,
            reasoning="All streams approve",
        )

        assert consensus.decision == "Approved"
        assert consensus.coherence == 0.5
        assert consensus.hiho_stable is True
        assert consensus.consensus_strength == 1.0
        assert len(consensus.stream_recommendations) == 1
        assert consensus.requires_human_review is False


class TestExpertDomainRouter:
    """Test ExpertDomainRouter class."""

    def test_initialization(self, edl_router):
        """Test ExpertDomainRouter initialization."""
        assert edl_router.client is not None
        assert edl_router.coherence_tracker is not None

    def test_select_streams_architecture(self, edl_router):
        """Test stream selection for architecture decisions."""
        streams = edl_router._select_streams("architecture")

        assert len(streams) == 2
        assert ExpertStream.ARCHITECT in streams
        assert ExpertStream.ENGINEER in streams

    def test_select_streams_security(self, edl_router):
        """Test stream selection for security decisions."""
        streams = edl_router._select_streams("security")

        assert len(streams) == 2
        assert ExpertStream.ENGINEER in streams
        assert ExpertStream.QUANTUM_HW in streams

    def test_select_streams_performance(self, edl_router):
        """Test stream selection for performance decisions."""
        streams = edl_router._select_streams("performance")

        assert len(streams) == 2
        assert ExpertStream.ENGINEER in streams
        assert ExpertStream.QUANTUM_ALGO in streams

    def test_select_streams_integration(self, edl_router):
        """Test stream selection for integration decisions."""
        streams = edl_router._select_streams("integration")

        assert len(streams) == 3
        assert ExpertStream.ARCHITECT in streams
        assert ExpertStream.ENGINEER in streams
        assert ExpertStream.BIOLOGIST in streams

    def test_select_streams_algorithm(self, edl_router):
        """Test stream selection for algorithm decisions."""
        streams = edl_router._select_streams("algorithm")

        assert len(streams) == 2
        assert ExpertStream.QUANTUM_ALGO in streams
        assert ExpertStream.ENGINEER in streams

    def test_select_streams_unknown(self, edl_router):
        """Test stream selection for unknown decision type."""
        streams = edl_router._select_streams("unknown")

        assert len(streams) == 1
        assert streams[0] == ExpertStream.ARCHITECT

    def test_get_stream_model(self, edl_router):
        """Test model selection for expert streams."""
        assert edl_router._get_stream_model(ExpertStream.ARCHITECT) == "deepseek-r1:70b"
        assert edl_router._get_stream_model(ExpertStream.ENGINEER) == "qwen3-coder:30b"
        assert edl_router._get_stream_model(ExpertStream.BIOLOGIST) == "deepseek-r1:70b"
        assert edl_router._get_stream_model(ExpertStream.QUANTUM_HW) == "qwen3-coder:30b"
        assert edl_router._get_stream_model(ExpertStream.QUANTUM_ALGO) == "deepseek-r1:70b"

    @pytest.mark.asyncio
    async def test_consult_stream_success(self, edl_router, mock_compound_client):
        """Test consulting expert stream with valid JSON response."""
        mock_compound_client.execute.return_value = {
            "result": (
                '{"approve": "yes", "recommendation": "Approved",'
                ' "confidence": 0.8, "coherence": 0.5,'
                ' "rationale": "Good design"}'
            )
        }

        rec = await edl_router._consult_stream(ExpertStream.ARCHITECT, "Test context", "Test proposal")

        assert rec.stream == ExpertStream.ARCHITECT
        assert rec.recommendation == "Approved"
        assert rec.confidence == 0.8
        assert rec.coherence == 0.5
        assert rec.rationale == "Good design"

    @pytest.mark.asyncio
    async def test_consult_stream_fallback(self, edl_router, mock_compound_client):
        """Test consulting expert stream with invalid JSON (fallback)."""
        mock_compound_client.execute.return_value = {"result": "This is not valid JSON"}

        rec = await edl_router._consult_stream(ExpertStream.ARCHITECT, "Test context", "Test proposal")

        assert rec.stream == ExpertStream.ARCHITECT
        assert rec.recommendation == "This is not valid JSON"
        assert rec.confidence == 0.5
        assert rec.coherence == 0.5
        assert rec.rationale == "Expert stream response"

    def test_merge_recommendations(self, edl_router):
        """Test merging recommendations from multiple streams."""
        recs = [
            StreamRecommendation(
                stream=ExpertStream.ARCHITECT,
                recommendation="Approved",
                confidence=0.8,
                coherence=0.5,
                rationale="Good design",
            ),
            StreamRecommendation(
                stream=ExpertStream.ENGINEER,
                recommendation="Approved with changes",
                confidence=0.7,
                coherence=0.6,
                rationale="Some concerns",
            ),
        ]

        merged = edl_router._merge_recommendations(recs)

        assert "architect (0.80): Approved" in merged
        assert "engineer (0.70): Approved with changes" in merged

    def test_generate_consensus_reasoning(self, edl_router):
        """Test generating consensus reasoning."""
        recs = [
            StreamRecommendation(
                stream=ExpertStream.ARCHITECT,
                recommendation="Approved",
                confidence=0.8,
                coherence=0.5,
                rationale="Good design",
            )
        ]

        reasoning = edl_router._generate_consensus_reasoning(
            recs, coherence=0.5, hiho_stable=True, consensus_strength=1.0
        )

        assert "EDL Consensus Analysis" in reasoning
        assert "Coherence: 0.500" in reasoning
        assert "HIHO Stable ✅" in reasoning
        assert "Consensus Strength: 1.000" in reasoning
        assert "ARCHITECT:" in reasoning

    def test_stabilize_consensus_hiho_stable(self, edl_router):
        """Test consensus stabilization with HIHO stable coherence."""
        recs = [
            StreamRecommendation(
                stream=ExpertStream.ARCHITECT,
                recommendation="Approved",
                confidence=0.8,
                coherence=0.5,
                rationale="Good design",
            ),
            StreamRecommendation(
                stream=ExpertStream.ENGINEER,
                recommendation="Approved",
                confidence=0.9,
                coherence=0.5,
                rationale="Good implementation",
            ),
        ]

        consensus = edl_router._stabilize_consensus(recs)

        assert consensus.coherence == 0.5
        assert consensus.hiho_stable is True
        assert consensus.consensus_strength == 1.0
        assert consensus.requires_human_review is False
        assert len(consensus.stream_recommendations) == 2

    def test_stabilize_consensus_outside_hiho(self, edl_router):
        """Test consensus stabilization with coherence outside HIHO range."""
        recs = [
            StreamRecommendation(
                stream=ExpertStream.ARCHITECT,
                recommendation="Approved",
                confidence=0.8,
                coherence=0.9,
                rationale="Very high coherence",
            )
        ]

        consensus = edl_router._stabilize_consensus(recs)

        assert consensus.coherence == 0.9
        assert consensus.hiho_stable is False
        assert consensus.consensus_strength < 1.0
        assert consensus.requires_human_review is True

    def test_stabilize_consensus_low_confidence(self, edl_router):
        """Test consensus stabilization with low confidence."""
        recs = [
            StreamRecommendation(
                stream=ExpertStream.ARCHITECT,
                recommendation="Uncertain",
                confidence=0.3,
                coherence=0.5,
                rationale="Not sure",
            )
        ]

        consensus = edl_router._stabilize_consensus(recs)

        assert consensus.requires_human_review is True

    def test_stabilize_consensus_rejection(self, edl_router):
        """Test consensus stabilization with rejection."""
        recs = [
            StreamRecommendation(
                stream=ExpertStream.ARCHITECT,
                recommendation="No, this is bad",
                confidence=0.8,
                coherence=0.5,
                rationale="Security concerns",
            )
        ]

        consensus = edl_router._stabilize_consensus(recs)

        assert consensus.requires_human_review is True

    @pytest.mark.asyncio
    async def test_route_decision_architecture(self, edl_router, mock_compound_client):
        """Test routing architecture decision through EDL."""
        mock_compound_client.execute.return_value = {
            "result": (
                '{"approve": "yes", "recommendation": "Approved",'
                ' "confidence": 0.8, "coherence": 0.5,'
                ' "rationale": "Good design"}'
            )
        }

        consensus = await edl_router.route_decision(
            decision_type="architecture",
            context="Building new module",
            proposal="Use microservices architecture",
        )

        assert consensus.coherence >= 0.0
        assert consensus.coherence <= 1.0
        assert len(consensus.stream_recommendations) == 2
        assert consensus.hiho_stable in [True, False]

    @pytest.mark.asyncio
    async def test_route_decision_integration(self, edl_router, mock_compound_client):
        """Test routing integration decision through EDL (3 streams)."""
        mock_compound_client.execute.return_value = {
            "result": (
                '{"approve": "yes", "recommendation": "Approved",'
                ' "confidence": 0.8, "coherence": 0.5,'
                ' "rationale": "Good integration"}'
            )
        }

        consensus = await edl_router.route_decision(
            decision_type="integration",
            context="Integrating external API",
            proposal="Use REST API with OAuth2",
        )

        assert len(consensus.stream_recommendations) == 3


class TestSingletonAccessor:
    """Test singleton accessor functions."""

    def test_get_edl_router(self):
        """Test getting global EDL router."""
        reset_edl_router()

        router1 = get_edl_router()
        router2 = get_edl_router()

        assert router1 is router2

    def test_reset_edl_router(self):
        """Test resetting global EDL router."""
        router1 = get_edl_router()
        reset_edl_router()
        router2 = get_edl_router()

        assert router1 is not router2
