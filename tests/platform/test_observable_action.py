"""
Tests for ObservableActionProposer - Observable AI transparency.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from cohezion.platform.coherence_tracker import CoherenceMetrics
from cohezion.platform.observable_action import (
    ActionProposal,
    ObservableActionProposer,
    get_observable_proposer,
    reset_observable_proposer,
)


@pytest.fixture
def mock_coherence_tracker():
    """Mock CoherenceTracker."""
    mock_tracker = AsyncMock()
    mock_tracker.measure_system_coherence = AsyncMock(
        return_value=CoherenceMetrics(
            timestamp=datetime.now(),
            internal_state=0.8,
            external_alignment=0.7,
            coherence=0.5,
            hiho_stable=True,
            hiho_delta=0.0,
            stability_score=1.0,
        )
    )
    return mock_tracker


@pytest.fixture
def mock_journey_logger():
    """Mock JourneyLogger."""
    mock_logger = AsyncMock()
    mock_logger.log_decision = AsyncMock()
    return mock_logger


@pytest.fixture
def mock_vae_encoder():
    """Mock FLUME VAE encoder."""
    mock_encoder = MagicMock()
    mock_encoder.encode = MagicMock(return_value=np.zeros(256))
    return mock_encoder


@pytest.fixture
def observable_proposer(mock_coherence_tracker, mock_journey_logger, mock_vae_encoder):
    """Create ObservableActionProposer with mocked dependencies."""
    with (
        patch(
            "cohezion.platform.observable_action.get_coherence_tracker",
            return_value=mock_coherence_tracker,
        ),
        patch(
            "cohezion.platform.observable_action.get_journey_logger",
            return_value=mock_journey_logger,
        ),
        patch(
            "cohezion.platform.observable_action.get_encoder",
            return_value=mock_vae_encoder,
        ),
    ):
        proposer = ObservableActionProposer()
        yield proposer


class TestActionProposal:
    """Test ActionProposal model."""

    def test_action_proposal_creation(self):
        """Test creating ActionProposal."""
        proposal = ActionProposal(
            action_id="test-123",
            action_type="update",
            description="Update configuration",
            rationale="Improve performance",
            confidence=0.95,
            coherence_impact=0.01,
            flume_state=[0.1] * 256,
            risks=["Might break existing configs"],
            benefits=["Better performance", "Cleaner code"],
            reversible=True,
            auto_approvable=True,
        )

        assert proposal.action_id == "test-123"
        assert proposal.action_type == "update"
        assert proposal.confidence == 0.95
        assert proposal.coherence_impact == 0.01
        assert len(proposal.flume_state) == 256
        assert len(proposal.risks) == 1
        assert len(proposal.benefits) == 2
        assert proposal.reversible is True
        assert proposal.auto_approvable is True


class TestObservableActionProposer:
    """Test ObservableActionProposer class."""

    def test_initialization(self, observable_proposer):
        """Test ObservableActionProposer initialization."""
        assert observable_proposer.coherence_tracker is not None
        assert observable_proposer.journey_logger is not None
        assert observable_proposer.vae is not None
        assert observable_proposer._current_journey_id is None

    def test_set_current_journey(self, observable_proposer):
        """Test setting current journey."""
        observable_proposer.set_current_journey("journey-123")
        assert observable_proposer.get_current_journey_id() == "journey-123"

    @pytest.mark.asyncio
    async def test_estimate_coherence_impact_update(self, observable_proposer):
        """Test coherence impact estimation for update actions."""
        impact = await observable_proposer._estimate_coherence_impact("update", "Update database schema", 0.5)
        assert impact == 0.01

    @pytest.mark.asyncio
    async def test_estimate_coherence_impact_refactor(self, observable_proposer):
        """Test coherence impact estimation for refactor actions."""
        impact = await observable_proposer._estimate_coherence_impact("refactor", "Refactor legacy code", 0.5)
        assert impact == 0.05

    @pytest.mark.asyncio
    async def test_estimate_coherence_impact_delete(self, observable_proposer):
        """Test coherence impact estimation for delete actions."""
        impact = await observable_proposer._estimate_coherence_impact("delete", "Delete unused files", 0.5)
        assert impact == -0.02

    @pytest.mark.asyncio
    async def test_estimate_coherence_impact_neutral(self, observable_proposer):
        """Test coherence impact estimation for neutral actions."""
        impact = await observable_proposer._estimate_coherence_impact("read", "Read configuration", 0.5)
        assert impact == 0.0

    @pytest.mark.asyncio
    async def test_propose_action_auto_approved(self, observable_proposer, mock_coherence_tracker):
        """Test proposing action that gets auto-approved."""
        action_executed = False

        async def test_action():
            nonlocal action_executed
            action_executed = True

        # High confidence, reversible, low impact → auto-approve
        approved = await observable_proposer.propose_action(
            action_type="update",
            description="Update cache settings",
            rationale="Improve performance",
            confidence=0.95,
            action_fn=test_action,
            reversible=True,
        )

        assert approved is True
        assert action_executed is True
        mock_coherence_tracker.measure_system_coherence.assert_called_once()

    @pytest.mark.asyncio
    async def test_propose_action_requires_approval(self, observable_proposer, mock_coherence_tracker):
        """Test proposing action that requires approval."""
        action_executed = False

        async def test_action():
            nonlocal action_executed
            action_executed = True

        # Low confidence → requires approval
        # Mock approval callback to approve
        def mock_approval(proposal):
            return True

        approved = await observable_proposer.propose_action(
            action_type="delete",
            description="Delete old data",
            rationale="Clean up",
            confidence=0.6,
            action_fn=test_action,
            approval_callback=mock_approval,
        )

        assert approved is True
        assert action_executed is True

    @pytest.mark.asyncio
    async def test_propose_action_rejected(self, observable_proposer, mock_coherence_tracker):
        """Test proposing action that gets rejected."""
        action_executed = False

        async def test_action():
            nonlocal action_executed
            action_executed = True

        # Low confidence → requires approval
        # Mock approval callback to reject
        def mock_approval(proposal):
            return False

        approved = await observable_proposer.propose_action(
            action_type="delete",
            description="Delete important data",
            rationale="Cleanup",
            confidence=0.6,
            action_fn=test_action,
            approval_callback=mock_approval,
        )

        assert approved is False
        assert action_executed is False

    @pytest.mark.asyncio
    async def test_propose_action_with_journey_logging(self, observable_proposer, mock_journey_logger):
        """Test that approved actions are logged to journey."""

        async def test_action():
            pass

        observable_proposer.set_current_journey("journey-123")

        def mock_approval(proposal):
            return True

        await observable_proposer.propose_action(
            action_type="update",
            description="Update config",
            rationale="Performance",
            confidence=0.8,
            action_fn=test_action,
            approval_callback=mock_approval,
        )

        # Verify decision was logged
        mock_journey_logger.log_decision.assert_called_once_with(
            journey_id="journey-123", decision="Update config", rationale="Performance"
        )

    @pytest.mark.asyncio
    async def test_propose_action_without_journey(self, observable_proposer, mock_journey_logger):
        """Test that actions work without active journey."""

        async def test_action():
            pass

        def mock_approval(proposal):
            return True

        # No journey set - should still work
        approved = await observable_proposer.propose_action(
            action_type="update",
            description="Update config",
            rationale="Performance",
            confidence=0.8,
            action_fn=test_action,
            approval_callback=mock_approval,
        )

        assert approved is True
        # No decision logged (no journey)
        mock_journey_logger.log_decision.assert_not_called()

    @pytest.mark.asyncio
    async def test_propose_action_with_risks_and_benefits(self, observable_proposer, mock_vae_encoder):
        """Test proposing action with risks and benefits."""

        async def test_action():
            pass

        def mock_approval(proposal):
            assert len(proposal.risks) == 2
            assert len(proposal.benefits) == 3
            return True

        approved = await observable_proposer.propose_action(
            action_type="refactor",
            description="Refactor authentication",
            rationale="Security improvement",
            confidence=0.8,
            action_fn=test_action,
            risks=["Might break existing auth", "Requires testing"],
            benefits=["Better security", "Cleaner code", "Easier to maintain"],
            approval_callback=mock_approval,
        )

        assert approved is True

    @pytest.mark.asyncio
    async def test_display_proposal(self, observable_proposer, mock_coherence_tracker, capsys):
        """Test proposal display (Observable AI)."""
        coherence_metrics = await mock_coherence_tracker.measure_system_coherence()

        proposal = ActionProposal(
            action_id="test-123",
            action_type="update",
            description="Update database schema",
            rationale="Add new columns",
            confidence=0.85,
            coherence_impact=0.01,
            flume_state=[0.1, 0.2, 0.3, 0.4, 0.5] + [0.0] * 251,
            risks=["Schema migration risk"],
            benefits=["New features enabled"],
            reversible=True,
            auto_approvable=False,
        )

        await observable_proposer._display_proposal(proposal, coherence_metrics)

        captured = capsys.readouterr()
        assert "OBSERVABLE AI: ACTION PROPOSAL" in captured.out
        assert "Update database schema" in captured.out
        assert "Confidence: 85.00%" in captured.out
        assert "HIHO Stable" in captured.out
        assert "Schema migration risk" in captured.out
        assert "New features enabled" in captured.out

    @pytest.mark.asyncio
    async def test_numpy_array_conversion(self, observable_proposer, mock_vae_encoder):
        """Test that numpy arrays are converted to lists."""
        mock_vae_encoder.encode.return_value = np.array([0.1] * 256)

        async def test_action():
            pass

        def mock_approval(proposal):
            # Verify flume_state is a list, not numpy array
            assert isinstance(proposal.flume_state, list)
            assert len(proposal.flume_state) == 256
            return True

        await observable_proposer.propose_action(
            action_type="update",
            description="Test",
            rationale="Test",
            confidence=0.8,
            action_fn=test_action,
            approval_callback=mock_approval,
        )

    @pytest.mark.asyncio
    async def test_request_approval_non_interactive(self, observable_proposer):
        """Test approval request in non-interactive environment."""
        proposal = ActionProposal(
            action_id="test-123",
            action_type="update",
            description="Test",
            rationale="Test",
            confidence=0.8,
            coherence_impact=0.01,
            flume_state=[0.0] * 256,
            risks=[],
            benefits=[],
            reversible=True,
            auto_approvable=False,
        )

        # In non-interactive environment (no stdin), should return False
        with patch("builtins.input", side_effect=EOFError):
            approved = await observable_proposer._request_approval(proposal)
            assert approved is False


class TestSingletonAccessor:
    """Test singleton accessor functions."""

    def test_get_observable_proposer(self):
        """Test getting global observable proposer."""
        reset_observable_proposer()

        proposer1 = get_observable_proposer()
        proposer2 = get_observable_proposer()

        assert proposer1 is proposer2

    def test_reset_observable_proposer(self):
        """Test resetting global observable proposer."""
        proposer1 = get_observable_proposer()
        reset_observable_proposer()
        proposer2 = get_observable_proposer()

        assert proposer1 is not proposer2
