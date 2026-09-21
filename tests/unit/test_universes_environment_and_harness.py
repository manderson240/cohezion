"""Unit & Property Tests for Anthropic Universes Environment & Benchmark Harness.
==============================================================================
Verifies:
1. InterruptionEngine stochastic triggering, resolution logic, and IRS metrics.
2. UltraRealisticAgentEnv sandbox isolation, action execution, and reward formulation.
3. UniversesCapabilityHarness empirical evaluation and bootstrap 95% confidence intervals.
"""

from pathlib import Path

from cohezion.environments.interruption_engine import (
    InterruptionEngine,
)
from cohezion.environments.ultra_realistic_agent_env import UltraRealisticAgentEnv
from cohezion.eval.universes_capability_harness import (
    UniversesCapabilityHarness,
)


def test_interruption_engine_triggering_and_resolution():
    """Verify interruptions are injected and resolved under expected actions."""
    engine = InterruptionEngine(
        interrupt_probability=1.0,  # Always interrupt when interval is satisfied
        min_interval_steps=1,
        seed=42,
    )

    # First step: should trigger
    irq = engine.maybe_trigger_interruption(current_step=1, current_task="Fix bug in app.py")
    assert irq is not None
    assert engine.active_interrupt is not None
    assert irq.injected_step == 1
    assert irq.is_resolved is False

    # Attempt resolution with mismatched response
    resolved, _ = engine.resolve_current_interruption(
        current_step=2, response_text="completely unrelated text"
    )
    assert resolved is False
    assert engine.active_interrupt is not None

    # Resolve with valid response
    resolved, _reason = engine.resolve_current_interruption(
        current_step=3, response_text=f"Handling active interrupt: {irq.required_action} resolved."
    )
    assert resolved is True
    assert engine.active_interrupt is None
    assert irq.is_resolved is True
    assert irq.resolution_success is True
    assert irq.steps_taken_to_resolve == 2

    # Verify metrics
    metrics = engine.compute_resilience_metrics()
    assert metrics["total_interruptions"] == 1.0
    assert metrics["resolved_interruptions"] == 1.0
    assert metrics["resolution_rate"] == 1.0
    assert metrics["interruption_resilience_score"] > 0.0


def test_ultra_realistic_agent_env_lifecycle_and_actions():
    """Verify Gymnasium interface, sandbox execution, and reward calculations."""
    env = UltraRealisticAgentEnv(max_steps=10, interruption_prob=0.0, seed=123)
    try:
        obs, info = env.reset(seed=123)
        assert "stdout" in obs
        assert obs["step_count"] == 0
        assert len(obs["poincare_state"]) == 12
        assert info["step"] == 0

        # Action: write file
        obs, _r_write, _term, _trunc, info = env.step(
            {
                "action_type": "write_file",
                "path": "greeting.txt",
                "content": "Hello Universes!",
            }
        )
        assert "Wrote" in obs["stdout"]
        assert (Path(info["sandbox_dir"]) / "greeting.txt").exists()

        # Action: run command
        obs, _r_cmd, _term, _trunc, info = env.step(
            {"action_type": "run_command", "command": "cat greeting.txt"}
        )
        assert "Hello Universes!" in obs["stdout"]
        assert obs["exit_code"] == 0

        # Action: complete task (should verify or report status)
        obs, _r_term, _term, _trunc, info = env.step({"action_type": "complete_task"})
        assert "step" in info
        assert "irs_score" in info
    finally:
        env.close()


def test_run_command_falls_back_when_bwrap_is_present_but_cannot_unshare(tmp_path, monkeypatch):
    """DISCRIMINATING: an installed-but-unusable bwrap must not swallow every command.

    Where unprivileged user namespaces are denied (e.g. inside an agent sandbox) the bwrap
    binary exists but every invocation exits 1 with empty stdout. The env used to probe only
    `shutil.which("bwrap")`, so `run_command` returned '' for every command there. The fake
    bwrap below behaves like the denied case on ANY host; neutralise the functional probe and
    this test goes red.
    """
    import shutil as _shutil

    from cohezion.environments import ultra_realistic_agent_env as env_mod

    fake = tmp_path / "bwrap"
    fake.write_text("#!/bin/sh\necho 'bwrap: No permissions to create a new namespace' >&2\nexit 1\n")
    fake.chmod(0o755)
    real_which = _shutil.which
    monkeypatch.setattr(
        _shutil, "which", lambda name, *a, **k: str(fake) if name == "bwrap" else real_which(name, *a, **k)
    )
    env_mod._bwrap_usable.cache_clear()
    env = UltraRealisticAgentEnv(max_steps=10, interruption_prob=0.0, seed=7, use_namespaces=False)
    try:
        env.reset(seed=7)
        env.step({"action_type": "write_file", "path": "g.txt", "content": "fallback works"})
        obs, *_ = env.step({"action_type": "run_command", "command": "cat g.txt"})
        assert "fallback works" in obs["stdout"]
        assert obs["exit_code"] == 0
    finally:
        env.close()
        env_mod._bwrap_usable.cache_clear()


def test_ultra_realistic_agent_env_interruption_handling():
    """Verify environment injects active interrupt and responds to handling."""
    env = UltraRealisticAgentEnv(max_steps=10, interruption_prob=1.0, seed=99)
    try:
        obs, _info = env.reset(seed=99)
        # Execute normal command
        obs, _reward, _term, _trunc, _info = env.step("ls -la")

        # Active interrupt should have triggered
        assert obs["active_interrupt"] == 1
        assert len(obs["interrupt_message"]) > 0

        # Respond to interrupt
        obs, _reward, _term, _trunc, _info = env.step(
            {
                "action_type": "respond_to_interrupt",
                "interrupt_response": "Acknowledge and resolved interrupt action.",
            }
        )
        assert obs["active_interrupt"] == 0
        assert "RESOLVED" in obs["stdout"]
    finally:
        env.close()


def test_universes_capability_harness_bootstrap_and_markdown():
    """Verify benchmark harness aggregates results and renders markdown report."""
    env = UltraRealisticAgentEnv(max_steps=5, interruption_prob=0.5, seed=42)
    harness = UniversesCapabilityHarness(env=env)

    def simple_agent_policy(obs: dict) -> dict:
        if obs.get("active_interrupt") == 1:
            return {
                "action_type": "respond_to_interrupt",
                "interrupt_response": "Handled active interrupt.",
            }
        return {"action_type": "run_command", "command": "echo test"}

    result = harness.run_benchmark(
        agent_policy=simple_agent_policy,
        n_episodes=3,
        benchmark_name="Test-Universes-Suite",
        record_steps=True,
    )

    assert result.total_episodes == 3
    assert len(result.episodes) == 3
    assert 0.0 <= result.success_rate <= 1.0
    assert 0.0 <= result.mean_irs_score <= 1.0

    # Test bootstrap CI
    assert len(result.success_rate_ci_95) == 2
    assert result.success_rate_ci_95[0] <= result.success_rate_ci_95[1]

    # Test JSON and Markdown exports
    summary = result.to_summary_dict()
    assert summary["benchmark_name"] == "Test-Universes-Suite"
    assert "mean_irs_score" in summary

    md = result.render_markdown_table()
    assert "| **Interruption Resilience Score (IRS)** |" in md
    assert "| **Task Success Rate (SR@1)** |" in md


def test_physical_environment_mutations_and_cleanup(tmp_path: Path):
    """Verify physical OS mutations are created on injection and cleaned up on resolution."""
    engine = InterruptionEngine(interrupt_probability=1.0, min_interval_steps=1, seed=42)

    # Trigger interruption with physical sandbox directory
    irq = engine.maybe_trigger_interruption(
        current_step=1, current_task="Test Task", sandbox_dir=tmp_path
    )
    assert irq is not None
    assert irq.mutated_paths is not None

    # Verify at least one physical file was created
    created_files = list(tmp_path.iterdir())
    assert len(created_files) > 0

    # Resolve interruption and verify cleanup
    resolved, _ = engine.resolve_current_interruption(
        current_step=2,
        response_text="acknowledge and log debug.log resolved",
        sandbox_dir=tmp_path,
    )
    assert resolved is True

    # Mutated transient files like .tool_fault_active or HUMAN_STEER_DIRECTIVE.txt should be cleaned up
    assert not (tmp_path / ".tool_fault_active").exists()
    assert not (tmp_path / "HUMAN_STEER_DIRECTIVE.txt").exists()


def test_pbrs_anti_exploitation_properties():
    """Verify that PBRS reward shaping penalizes camping and avoids reward inflation."""
    env = UltraRealisticAgentEnv(max_steps=20, interruption_prob=0.0, seed=42)
    try:
        env.reset(seed=42)

        # 1. Idle step / no-op camping without progress must yield negative return
        _obs, r1, _term, _trunc, _info = env.step(
            {"action_type": "run_command", "command": "echo idle"}
        )
        _obs, r2, _term, _trunc, _info = env.step(
            {"action_type": "run_command", "command": "echo idle"}
        )

        # Step penalty + potential decay ensures negative return for idle camping
        assert r1 < 0.0
        assert r2 < 0.0

        # 2. Premature task completion attempt without root-cause fix must penalize
        _obs, r_pre, _term, _trunc, _info = env.step({"action_type": "complete_task"})
        assert r_pre < -0.5
    finally:
        env.close()


def test_procedural_task_suite_generation():
    """Verify 30 diverse procedural tasks are deterministically generated."""
    suite = UltraRealisticAgentEnv.generate_procedural_task_suite(n_tasks=30, seed=42)
    assert len(suite) == 30

    task_ids = {t["task_id"] for t in suite}
    assert len(task_ids) == 30  # All unique

    # Check that canonical baseline tasks are retained at indices 0, 1, 2
    assert suite[0]["task_id"] == "debug_python_syntax"
    assert suite[1]["task_id"] == "parse_security_logs"
    assert suite[2]["task_id"] == "refactor_config_format"

    # Check that procedurally parameterized tasks are present
    assert any("debug_python_syntax_v" in t["task_id"] for t in suite[3:])
    assert any("parse_security_logs_v" in t["task_id"] for t in suite[3:])
    assert any("refactor_config_format_v" in t["task_id"] for t in suite[3:])
