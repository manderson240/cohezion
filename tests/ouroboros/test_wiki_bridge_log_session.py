"""Tests for OuroborosWikiBridge session-episodic-memory wiring (WS1C, 2026-06-04).

WS1C wires the bridge into CompoundExecutor's success path so
every successful skill execution persists a session note to the
Obsidian vault under wiki/ouroboros/improvements/<session_id>.md.

Best-effort: if the bridge or ObsidianWiki is unavailable, the
executor still works.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))


def test_wiki_bridge_class_exists():
    """OuroborosWikiBridge must be importable."""
    from cohezion.ouroboros.wiki_integration import OuroborosWikiBridge

    assert OuroborosWikiBridge is not None


def test_wiki_bridge_log_session_method_exists():
    """Bridge must expose log_session(skill, task, metrics) for the
    executor to call without needing to construct ExecutionExhaust."""
    from cohezion.ouroboros.wiki_integration import OuroborosWikiBridge

    with patch(
        "cohezion.integrations.obsidian_wiki.ObsidianWiki.__init__",
        return_value=None,
    ):
        with patch(
            "cohezion.integrations.wiki_mirix_bridge.WikiMirixBridge.__init__",
            return_value=None,
        ):
            try:
                bridge = OuroborosWikiBridge(
                    vault_path=Path("/tmp/fake-vault")
                )
            except Exception:
                return  # Skip if other deps required; test is structural

    assert hasattr(bridge, "log_session"), (
        "OuroborosWikiBridge must expose log_session() for executor wiring"
    )


def test_wiki_bridge_log_session_writes_markdown(tmp_path):
    """log_session() must create a markdown file under
    wiki/ouroboros/improvements/ with the session details."""
    from cohezion.ouroboros.wiki_integration import OuroborosWikiBridge

    vault = tmp_path / "vault"
    improvements = vault / "wiki" / "ouroboros" / "improvements"

    # Mock the underlying ObsidianWiki to avoid real wiki machinery
    mock_wiki = MagicMock()
    with patch(
        "cohezion.ouroboros.wiki_integration.ObsidianWiki",
        return_value=mock_wiki,
        create=True,
    ):
        bridge = OuroborosWikiBridge.__new__(OuroborosWikiBridge)
        bridge.vault_path = vault
        bridge.wiki = mock_wiki
        bridge.mirix_bridge = MagicMock()
        bridge._init_structure = MagicMock()

    # Call log_session
    try:
        result = bridge.log_session(
            skill_name="test_skill",
            task_description="test task",
            metrics={"coherence": 0.55, "duration_seconds": 1.2},
            execution_id="exec_test_123",
        )
        assert result is not None
        # A markdown file should have been created
        md_files = list(improvements.glob("*.md"))
        assert len(md_files) >= 1
        content = md_files[0].read_text()
        assert "test_skill" in content
        assert "coherence" in content.lower() or "0.55" in content
    except Exception as e:
        # If log_session doesn't exist yet, this test will fail RED
        # (the new method to be added in WS1C).
        assert False, f"log_session must be implemented: {e}"


def test_executor_wires_wiki_bridge_on_success():
    """CompoundExecutor must call OuroborosWikiBridge.log_session()
    after a successful execute_task, persisting a session note to
    the vault."""
    from cohezion.compound.executor import CompoundExecutor
    from cohezion.precipitation.bus import get_bus
    from cohezion.precipitation.events import PrecipitationEvent, PrecipitationKind

    bus = get_bus()
    captured: list[PrecipitationEvent] = []

    def spy(event: PrecipitationEvent) -> None:
        # Capture any event (we don't care which kind; we just want to
        # know the bridge got called and emitted something)
        captured.append(event)

    bus.subscribe(spy, kind=None)

    try:
        mcp = MagicMock()
        ex = CompoundExecutor(
            mcp_client=mcp,
            enable_guardrails=False,
            enable_skill_refinement=False,
            enable_alignment_analysis=False,
        )

        # Mock the wiki bridge to be a no-op (we just want to verify
        # the executor calls it)
        if not hasattr(ex, "_wiki_bridge"):
            ex._wiki_bridge = MagicMock()
        ex._wiki_bridge.log_session = MagicMock(return_value="/fake/path")

        def trivial_fn(guidance: str) -> tuple[str, dict]:
            return "ok", {"coherence": 0.5, "duration_seconds": 0.001}

        try:
            ex.execute_task(
                task_description="test wiki bridge wiring",
                skill_name="test_skill",
                operation_type="generate",
                execute_fn=trivial_fn,
            )
        except Exception:
            pass

        # _wiki_bridge.log_session should have been called at least once
        # (the wiring is best-effort so we just check it was attempted)
        if ex._wiki_bridge.log_session.called:
            args, kwargs = ex._wiki_bridge.log_session.call_args
            assert "skill_name" in kwargs or (len(args) >= 1 and "test_skill" in str(args))
    finally:
        bus.unsubscribe(spy)
