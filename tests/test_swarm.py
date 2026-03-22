"""Tests for Swarm Agents and Debate Workflow."""

from cohezion.swarm.swarm_types import Perspective, SwarmConfig, ThoughtVector


class TestSwarmTypes:
    """Test swarm type definitions."""

    def test_perspective_enum(self):
        """Perspectives are defined."""
        assert Perspective.TECHNICAL is not None
        assert Perspective.ETHICAL is not None
        assert Perspective.HISTORICAL is not None

    def test_swarm_config_defaults(self):
        """SwarmConfig has sensible defaults."""
        config = SwarmConfig()
        assert config.analyst_model is not None
        assert config.critic_model is not None
        assert config.synthesizer_model is not None

    def test_thought_vector_shape(self):
        """ThoughtVector has correct dimensions."""
        tv = ThoughtVector(
            perspective=Perspective.TECHNICAL,
            content="test",
            embedding=[0.0] * 256,
            confidence=0.8,
        )
        assert len(tv.embedding) == 256
        assert 0 <= tv.confidence <= 1


class TestModelManager:
    """Test Ollama Model Manager."""

    def test_manager_loads(self):
        """Model manager initializes."""
        from cohezion.swarm.model_manager import get_manager

        manager = get_manager()
        assert manager is not None

    def test_role_assignments(self):
        """Role assignments are defined."""
        from cohezion.swarm.model_manager import get_manager

        manager = get_manager()
        roles = manager.get_role_assignments()
        assert "analysis" in roles
        assert "critique" in roles
        assert "synthesis" in roles


class TestSelfHealing:
    """Test Self-Healing System."""

    def test_system_loads(self):
        """Self-healing system initializes."""
        from cohezion.healing import get_healing_system

        system = get_healing_system()
        assert system is not None
        assert system.detector is not None
        assert system.diagnostician is not None
        assert system.corrector is not None

    def test_drift_detection(self):
        """Drift detection works."""
        from cohezion.healing import get_healing_system

        system = get_healing_system()

        # Set baseline
        system.detector.set_baseline("test", "latency", 100.0)

        # Check healthy
        status = system.detector.check("test", "latency", 105.0)
        assert status.status == "healthy"

        # Check degraded (>20% drift)
        status = system.detector.check("test", "latency", 130.0)
        assert status.status == "degraded"


class TestSkillGenerator:
    """Test Skill Generator."""

    def test_generator_loads(self):
        """Skill generator initializes."""
        from cohezion.learning import get_skill_generator

        gen = get_skill_generator()
        assert gen is not None

    def test_pattern_recording(self):
        """Can record patterns."""
        from cohezion.learning import get_skill_generator

        gen = get_skill_generator()

        pattern = gen.detector.record(
            "test_pattern",
            "A test pattern",
            "Example usage",
            ["test", "pattern"],
        )
        assert pattern.occurrences >= 1
