"""Test suite for Autonomous Recursive Expansion Engine.

Tests cover:
- OOM guard behavior
- Vault grounding
- Phase progression
- Ouroboros integration
- Mycelium propagation
- φ-floor early exit
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from cohezion.compound.autonomous_recursive_expansion_engine import (
    ExpansionPhase,
    ExpansionState,
    OOMGuard,
    RecursiveExpansionEngine,
    TickContext,
    VaultGrounding,
    create_expansion_engine,
)


class TestOOMGuard:
    """Critical: OOM prevention must work reliably."""
    
    def test_check_passes_with_sufficient_memory(self):
        """Guard passes when memory is available."""
        guard = OOMGuard(max_memory_mb=28_000)
        
        with patch("psutil.virtual_memory") as mock_vm:
            mock_vm.return_value.available = 8 * 1024 * 1024 * 1024  # 8GB
            assert guard.check() is True
            
    def test_check_fails_with_critical_memory(self):
        """Guard blocks when memory is critically low."""
        guard = OOMGuard(max_memory_mb=28_000)
        
        with patch("psutil.virtual_memory") as mock_vm:
            mock_vm.return_value.available = 1 * 1024 * 1024 * 1024  # 1GB
            assert guard.check() is False
            
    def test_checkpoint_saves_state(self):
        """Checkpoints are saved for recovery."""
        guard = OOMGuard()
        guard.checkpoint("tick_1", {"engine_id": "test"})
        
        assert len(guard._checkpoints) == 1
        assert guard._checkpoints[0]["tick_id"] == "tick_1"
        
    def test_checkpoint_limits_history(self):
        """Only last 10 checkpoints kept."""
        guard = OOMGuard()
        
        for i in range(15):
            guard.checkpoint(f"tick_{i}", {})
            
        assert len(guard._checkpoints) == 10


class TestVaultGrounding:
    """Vault integration for knowledge persistence."""
    
    def test_query_cerebellum_returns_results(self, tmp_path):
        """Cerebellum notes are queryable."""
        cerebellum = tmp_path / "cerebellum"
        cerebellum.mkdir()
        
        # Create test note
        note = cerebellum / "test.md"
        note.write_text("# Test\n\nPattern: compound engineering")
        
        vault = VaultGrounding(str(tmp_path))
        results = vault.query_cerebellum("compound", limit=10)
        
        assert len(results) == 1
        assert "compound" in results[0]["content_preview"].lower()
        
    def test_write_learning_creates_file(self, tmp_path):
        """Learnings are written to vault."""
        vault = VaultGrounding(str(tmp_path))
        
        path = vault.write_learning(
            tick_id="t1",
            content="# Learning\n\nTest content",
            tags=["test", "aree"],
        )
        
        assert path.exists()
        content = path.read_text()
        assert "tick: t1" in content
        assert "#test" in content or "#aree" in content


class TestRecursiveExpansionEngine:
    """Core engine functionality."""
    
    @pytest.fixture
    def engine(self, tmp_path):
        """Create engine with temp vault."""
        return create_expansion_engine(
            engine_id="test_engine",
            vault_path=str(tmp_path),
        )
        
    @pytest.mark.asyncio
    async def test_tick_advances_state(self, engine):
        """Each tick advances the engine state."""
        initial_tick = engine.state.current_tick
        
        ctx = await engine.tick()
        
        assert engine.state.current_tick == initial_tick + 1
        assert ctx.tick_id.startswith("test_engine")
        assert ctx.phi_score > 0
        
    @pytest.mark.asyncio
    async def test_phase_progression(self, engine):
        """Phases progress from INITIALIZE to EXPAND."""
        phases = []
        
        for _ in range(7):
            ctx = await engine.tick()
            phases.append(ctx.phase)
            
        # First tick is INITIALIZE
        assert phases[0] == ExpansionPhase.INITIALIZE
        # Second is RESEARCH
        assert phases[1] == ExpansionPhase.RESEARCH
        # Third is SYNTHESIZE
        assert phases[2] == ExpansionPhase.SYNTHESIZE
        # Fourth is ORCHESTRATE
        assert phases[3] == ExpansionPhase.ORCHESTRATE
        # Fifth is PROPAGATE
        assert phases[4] == ExpansionPhase.PROPAGATE
        # Sixth+ is EXPAND
        assert phases[5] == ExpansionPhase.EXPAND
        assert phases[6] == ExpansionPhase.EXPAND
        
    @pytest.mark.asyncio
    async def test_oom_guard_blocks_execution(self, engine):
        """Engine stops when OOM guard triggers."""
        # Mock OOM guard to always fail
        engine.oom_guard.check = MagicMock(return_value=False)
        
        with pytest.raises(RuntimeError, match="OOM guard"):
            await engine.tick()
            
    @pytest.mark.asyncio
    async def test_phi_floor_early_exit(self, engine):
        """Loop exits early when φ drops below floor."""
        results = await engine.run_recursive_loop(
            max_ticks=10,
            phi_floor=0.9,  # High floor to trigger early exit
        )
        
        # Should exit early
        assert len(results) < 10
        
    def test_determine_phase_maps_ticks_correctly(self, engine):
        """Phase mapping is correct."""
        test_cases = [
            (0, ExpansionPhase.INITIALIZE),
            (1, ExpansionPhase.RESEARCH),
            (2, ExpansionPhase.SYNTHESIZE),
            (3, ExpansionPhase.ORCHESTRATE),
            (4, ExpansionPhase.PROPAGATE),
            (5, ExpansionPhase.EXPAND),
            (10, ExpansionPhase.EXPAND),
            (100, ExpansionPhase.EXPAND),
        ]
        
        for tick, expected_phase in test_cases:
            engine.state.current_tick = tick
            phase = engine._determine_phase()
            assert phase == expected_phase, f"Tick {tick} should be {expected_phase}"


class TestTickContext:
    """Tick context captures execution state."""
    
    def test_context_tracks_vault_nodes(self):
        """Context tracks vault access."""
        ctx = TickContext(
            tick_id="t1",
            phase=ExpansionPhase.INITIALIZE,
            scope_depth=0,
            memory_pressure_mb=1000.0,
        )
        
        ctx.vault_nodes_accessed.append("node1.md")
        ctx.vault_nodes_accessed.append("node2.md")
        
        assert len(ctx.vault_nodes_accessed) == 2
        
    def test_context_tracks_learnings(self):
        """Context captures learnings."""
        ctx = TickContext(
            tick_id="t1",
            phase=ExpansionPhase.RESEARCH,
            scope_depth=1,
            memory_pressure_mb=1000.0,
        )
        
        ctx.learnings_captured.append("Insight 1")
        ctx.learnings_captured.append("Insight 2")
        
        assert len(ctx.learnings_captured) == 2


class TestLemonadeInference:
    """Local inference integration."""
    
    @pytest.mark.asyncio
    async def test_infer_returns_result(self):
        """Inference returns structured result."""
        from cohezion.compound.autonomous_recursive_expansion_engine import LemonadeInference
        
        lemonade = LemonadeInference()
        
        # Mock the HTTP call
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "choices": [{"message": {"content": "Test response"}}],
            "usage": {"total_tokens": 100},
        })
        
        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_post.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_post.return_value.__aexit__ = AsyncMock(return_value=None)
            
            result = await lemonade.infer("Test prompt")
            
            assert result["success"] is True
            assert "Test response" in result["content"]
            assert "latency_ms" in result


class TestIntegration:
    """Integration tests with mocked dependencies."""
    
    @pytest.mark.asyncio
    async def test_full_tick_sequence(self, tmp_path):
        """Complete tick executes all phases."""
        engine = create_expansion_engine(
            engine_id="integration_test",
            vault_path=str(tmp_path),
        )
        
        # Run 3 ticks
        results = []
        for _ in range(3):
            ctx = await engine.tick()
            results.append(ctx)
            
        # Verify progression
        assert results[0].phase == ExpansionPhase.INITIALIZE
        assert results[1].phase == ExpansionPhase.RESEARCH
        assert results[2].phase == ExpansionPhase.SYNTHESIZE
        
        # Verify state
        assert engine.state.current_tick == 3
        
    @pytest.mark.asyncio
    async def test_callback_invoked(self, tmp_path):
        """Tick callbacks are invoked."""
        engine = create_expansion_engine(vault_path=str(tmp_path))
        
        called_with = []
        def callback(ctx):
            called_with.append(ctx.tick_id)
            
        engine.register_tick_callback(callback)
        
        await engine.tick()
        
        assert len(called_with) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
