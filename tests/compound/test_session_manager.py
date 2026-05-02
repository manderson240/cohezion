"""Tests for inference session management."""

import asyncio
import tempfile

import pytest

from cohezion.compound.session_manager import (
    InferenceSession,
    SessionConfig,
    SessionState,
    VaultCheckpointManager,
    close_session,
    create_session,
    get_session,
    list_sessions,
)


class TestSessionState:
    """Test session state dataclass."""

    def test_create_session_state(self):
        """Create session state."""
        state = SessionState(
            session_id="test_session",
            skill_name="test_skill",
            current_step=0,
            total_steps=10,
            context="test context",
        )
        assert state.session_id == "test_session"
        assert state.skill_name == "test_skill"
        assert state.current_step == 0


class TestSessionConfig:
    """Test session configuration."""

    def test_default_config(self):
        """Create default config."""
        config = SessionConfig()
        assert config.checkpoint_interval_steps == 5
        assert config.max_session_duration_sec == 7200.0

    def test_custom_config(self):
        """Create custom config."""
        config = SessionConfig(
            checkpoint_interval_steps=2,
            max_session_duration_sec=1800.0,
        )
        assert config.checkpoint_interval_steps == 2
        assert config.max_session_duration_sec == 1800.0


class TestVaultCheckpointManager:
    """Test checkpoint persistence."""

    @pytest.fixture
    def temp_checkpoint_dir(self):
        """Create temporary checkpoint directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.mark.asyncio
    async def test_save_and_load_checkpoint(self, temp_checkpoint_dir):
        """Save and load checkpoint from disk."""
        manager = VaultCheckpointManager(temp_checkpoint_dir)

        state = SessionState(
            session_id="test_session",
            skill_name="test_skill",
            current_step=5,
            total_steps=10,
            context="test",
        )

        # Save
        success = await manager.save(state)
        assert success is True

        # Load
        loaded = await manager.load("test_session")
        assert loaded is not None
        assert loaded.session_id == "test_session"
        assert loaded.current_step == 5

    @pytest.mark.asyncio
    async def test_delete_checkpoint(self, temp_checkpoint_dir):
        """Delete checkpoint file."""
        manager = VaultCheckpointManager(temp_checkpoint_dir)

        state = SessionState(
            session_id="to_delete",
            skill_name="test",
            current_step=0,
            total_steps=1,
            context="",
        )

        # Save
        await manager.save(state)

        # Delete
        success = await manager.delete("to_delete")
        assert success is True

        # Verify deleted
        loaded = await manager.load("to_delete")
        assert loaded is None

    @pytest.mark.asyncio
    async def test_load_nonexistent_checkpoint(self, temp_checkpoint_dir):
        """Load non-existent checkpoint returns None."""
        manager = VaultCheckpointManager(temp_checkpoint_dir)
        loaded = await manager.load("nonexistent")
        assert loaded is None


class TestInferenceSession:
    """Test inference session lifecycle."""

    def test_create_session(self):
        """Create new session."""
        session = InferenceSession("test_session")
        assert session.session_id == "test_session"
        assert session.state is None

    def test_session_config(self):
        """Session with custom config."""
        config = SessionConfig(checkpoint_interval_steps=3)
        session = InferenceSession("test", config)
        assert session.config.checkpoint_interval_steps == 3

    @pytest.mark.asyncio
    async def test_execute_with_checkpoints_basic(self):
        """Execute steps and yield progress events."""
        session = InferenceSession("test")

        async def mock_execute_fn(step_index, state):
            await asyncio.sleep(0.01)
            return f"output_{step_index}", {"tokens": 10}

        # Collect events
        events = []
        async for event in session.execute_with_checkpoints(
            "test_skill",
            "test_input",
            mock_execute_fn,
            total_steps=3,
        ):
            events.append(event)

        # Verify event types
        event_types = [e["type"] for e in events]
        assert "start" in event_types
        assert "step" in event_types
        assert "complete" in event_types

    @pytest.mark.asyncio
    async def test_session_cancellation(self):
        """Test graceful cancellation."""
        session = InferenceSession("test")
        step_count = 0

        async def mock_execute_fn(step_index, state):
            nonlocal step_count
            step_count += 1
            await asyncio.sleep(0.01)
            if step_index == 2:
                session.cancel()
            return "output", {"tokens": 10}

        events = []
        async for event in session.execute_with_checkpoints(
            "test_skill",
            "test_input",
            mock_execute_fn,
            total_steps=10,
        ):
            events.append(event)

        # Should have cancelled event
        event_types = [e["type"] for e in events]
        assert "cancelled" in event_types

    @pytest.mark.asyncio
    async def test_session_timeout(self):
        """Test timeout enforcement."""
        config = SessionConfig(max_session_duration_sec=0.1)
        session = InferenceSession("test", config)

        async def mock_execute_fn(step_index, state):
            await asyncio.sleep(0.05)
            return "output", {"tokens": 10}

        events = []
        async for event in session.execute_with_checkpoints(
            "test_skill",
            "test_input",
            mock_execute_fn,
            total_steps=100,
        ):
            events.append(event)

        # Should have timeout event
        event_types = [e["type"] for e in events]
        assert "timeout" in event_types

    @pytest.mark.asyncio
    async def test_step_event_structure(self):
        """Verify step event has required fields."""
        session = InferenceSession("test")

        async def mock_execute_fn(step_index, state):
            return "test_output", {"tokens": 42}

        events = []
        async for event in session.execute_with_checkpoints(
            "test_skill",
            "test_input",
            mock_execute_fn,
            total_steps=1,
        ):
            events.append(event)

        # Find step event
        step_events = [e for e in events if e["type"] == "step"]
        assert len(step_events) > 0

        step_event = step_events[0]
        assert "step_index" in step_event
        assert "output" in step_event
        assert "tokens" in step_event
        assert "total_tokens" in step_event

    @pytest.mark.asyncio
    async def test_complete_event_structure(self):
        """Verify complete event has required fields."""
        session = InferenceSession("test")

        async def mock_execute_fn(step_index, state):
            return "final_output", {"tokens": 20}

        events = []
        async for event in session.execute_with_checkpoints(
            "test_skill",
            "test_input",
            mock_execute_fn,
            total_steps=1,
        ):
            events.append(event)

        # Find complete event
        complete_events = [e for e in events if e["type"] == "complete"]
        assert len(complete_events) == 1

        event = complete_events[0]
        assert "session_id" in event
        assert "final_output" in event
        assert "total_tokens" in event

    @pytest.mark.asyncio
    async def test_intermediate_results_accumulation(self):
        """Verify intermediate results are accumulated."""
        session = InferenceSession("test")

        async def mock_execute_fn(step_index, state):
            return f"output_{step_index}", {"tokens": 10 * (step_index + 1)}

        async for _ in session.execute_with_checkpoints(
            "test_skill",
            "test_input",
            mock_execute_fn,
            total_steps=3,
        ):
            pass

        # Check accumulated results
        assert session.state is not None
        assert len(session.state.intermediate_results) == 3
        assert session.state.intermediate_results[0]["step"] == 0
        assert session.state.intermediate_results[2]["step"] == 2

    @pytest.mark.asyncio
    async def test_model_usage_tracking(self):
        """Verify model usage is tracked."""
        session = InferenceSession("test")

        async def mock_execute_fn(step_index, state):
            model = "phi3" if step_index % 2 == 0 else "qwen"
            return "output", {"tokens": 50, "model": model}

        async for _ in session.execute_with_checkpoints(
            "test_skill",
            "test_input",
            mock_execute_fn,
            total_steps=4,
        ):
            pass

        assert session.state is not None
        assert session.state.model_usage["phi3"] == 100  # 2 steps * 50
        assert session.state.model_usage["qwen"] == 100  # 2 steps * 50


class TestSessionRegistry:
    """Test session registry functions."""

    def test_create_and_get_session(self):
        """Create and retrieve session from registry."""
        session = create_session("registry_test")
        assert session.session_id == "registry_test"

        retrieved = get_session("registry_test")
        assert retrieved is session

    def test_list_sessions(self):
        """List active sessions."""
        create_session("session_1")
        create_session("session_2")

        sessions = list_sessions()
        assert "session_1" in sessions
        assert "session_2" in sessions

    def test_close_session(self):
        """Close session removes from registry."""
        create_session("to_close")
        assert get_session("to_close") is not None

        success = close_session("to_close")
        assert success is True
        assert get_session("to_close") is None

    def test_close_nonexistent_session(self):
        """Close non-existent session returns False."""
        success = close_session("nonexistent")
        assert success is False

    def test_auto_generated_session_id(self):
        """Session ID is generated if not provided."""
        session = create_session()
        assert session.session_id is not None
        assert session.session_id.startswith("session_")
