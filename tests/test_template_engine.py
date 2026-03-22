"""Tests for the Adaptive Template Engine."""

from __future__ import annotations

from pathlib import Path

import pytest

from cohezion.core.template_engine import SkillSpec, TemplateEngine


SKILLS_DIR = Path(__file__).resolve().parent.parent / "src" / "cohezion" / "skills"


@pytest.fixture
def engine() -> TemplateEngine:
    """Create a TemplateEngine pointing at the real skills directory."""
    return TemplateEngine(skills_dir=SKILLS_DIR)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def test_parse_single_skill(engine: TemplateEngine) -> None:
    """Parse COMPOUND_ENGINEERING_PRIME.md and verify fields."""
    path = SKILLS_DIR / "COMPOUND_ENGINEERING_PRIME.md"
    assert path.exists(), f"Missing fixture: {path}"

    spec = engine.parse_skill(path)

    assert spec.name == "COMPOUND_ENGINEERING_PRIME"
    assert (
        "orchestration" in spec.domain_expertise.lower()
        or "engineering" in spec.domain_expertise.lower()
    )
    assert len(spec.concepts) >= 3, f"Expected >= 3 concepts, got {spec.concepts}"
    assert len(spec.instructions) >= 3, f"Expected >= 3 instructions, got {spec.instructions}"
    assert spec.version != "unknown"
    assert len(spec.see_also) >= 1
    assert "# SKILL:" in spec.raw_content
    assert spec.source_path == path


def test_parse_skill_key_concepts_variant(engine: TemplateEngine) -> None:
    """Parse RELIABILITY_PRIME.md which uses KEY CONCEPTS (not KEY TEXTS & CONCEPTS)."""
    path = SKILLS_DIR / "RELIABILITY_PRIME.md"
    if not path.exists():
        pytest.skip("RELIABILITY_PRIME.md not found")

    spec = engine.parse_skill(path)

    assert spec.name == "RELIABILITY_PRIME"
    assert len(spec.concepts) >= 2


def test_parse_all_skills(engine: TemplateEngine) -> None:
    """Parse all skills without raising, verify count >= 100."""
    specs = engine.parse_all()
    assert len(specs) >= 100, f"Expected >= 100 skills, got {len(specs)}"
    # Every spec should have a non-empty name
    for spec in specs:
        assert spec.name, f"Empty name for {spec.source_path}"


# ---------------------------------------------------------------------------
# Code Generation
# ---------------------------------------------------------------------------


def test_generate_config(engine: TemplateEngine) -> None:
    """Generate config for a skill and compile to verify valid Python."""
    path = SKILLS_DIR / "COMPOUND_ENGINEERING_PRIME.md"
    spec = engine.parse_skill(path)

    source = engine.generate_config_class(spec)
    assert "class CompoundEngineeringConfig" in source
    assert "@dataclass" in source

    # Must be valid Python
    compile(source, "<generated-config>", "exec")


def test_generate_agent_stub(engine: TemplateEngine) -> None:
    """Generate agent stub and compile to verify valid Python."""
    path = SKILLS_DIR / "COMPOUND_ENGINEERING_PRIME.md"
    spec = engine.parse_skill(path)

    source = engine.generate_agent_stub(spec)
    assert "class CompoundEngineeringAgent" in source
    assert "BaseAgent" in source
    assert "SYSTEM_PROMPT" in source

    # Must be valid Python
    compile(source, "<generated-agent>", "exec")


def test_generate_config_for_skill_without_concepts(engine: TemplateEngine) -> None:
    """Skills with no concepts should still produce a valid config class."""
    # Create a minimal spec with no concepts
    spec = SkillSpec(name="EMPTY_PRIME", domain_expertise="Test", raw_content="")
    source = engine.generate_config_class(spec)
    assert "class EmptyConfig" in source
    compile(source, "<generated-empty>", "exec")


def test_generate_all_skills_produce_valid_python(engine: TemplateEngine) -> None:
    """Every skill's generated agent and config must be valid Python."""
    specs = engine.parse_all()
    for spec in specs:
        agent_src = engine.generate_agent_stub(spec)
        config_src = engine.generate_config_class(spec)
        compile(agent_src, f"<agent-{spec.name}>", "exec")
        compile(config_src, f"<config-{spec.name}>", "exec")


# ---------------------------------------------------------------------------
# SkillGenerator integration
# ---------------------------------------------------------------------------


def test_skill_generator_integration() -> None:
    """SkillGenerator delegates to TemplateEngine for a named skill."""
    from cohezion.learning import SkillGenerator

    gen = SkillGenerator()
    # Override engine to point at real skills dir
    gen._engine = TemplateEngine(skills_dir=SKILLS_DIR)
    gen.engine.parse_all()

    agent_src = gen.generate("COMPOUND_ENGINEERING_PRIME")
    assert "class CompoundEngineeringAgent" in agent_src
    compile(agent_src, "<gen-agent>", "exec")

    config_src = gen.generate_config("COMPOUND_ENGINEERING_PRIME")
    assert "class CompoundEngineeringConfig" in config_src
    compile(config_src, "<gen-config>", "exec")


# ---------------------------------------------------------------------------
# ConfigTemplateManager
# ---------------------------------------------------------------------------


def test_config_template_manager() -> None:
    """ConfigTemplateManager looks up and generates for a skill name."""
    from cohezion.core.config_templates import ConfigTemplateManager

    mgr = ConfigTemplateManager(engine=TemplateEngine(skills_dir=SKILLS_DIR))
    mgr.engine.parse_all()

    config_src = mgr.get_config_for_skill("COMPOUND_ENGINEERING_PRIME")
    assert "class CompoundEngineeringConfig" in config_src
    compile(config_src, "<mgr-config>", "exec")

    agent_src = mgr.get_agent_for_skill("COMPOUND_ENGINEERING_PRIME")
    assert "class CompoundEngineeringAgent" in agent_src
    compile(agent_src, "<mgr-agent>", "exec")


def test_config_template_manager_missing_skill() -> None:
    """ConfigTemplateManager raises KeyError for unknown skill."""
    from cohezion.core.config_templates import ConfigTemplateManager

    mgr = ConfigTemplateManager(engine=TemplateEngine(skills_dir=SKILLS_DIR))
    mgr.engine.parse_all()

    with pytest.raises(KeyError, match="NONEXISTENT_SKILL"):
        mgr.get_config_for_skill("NONEXISTENT_SKILL")
