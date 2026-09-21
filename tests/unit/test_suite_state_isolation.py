"""The suite must not write the developer's real state files (review follow-up 2026-09-21).

``SkillRefiner._APPROVALS_PATH`` is a ClassVar frozen to ``Path.home()`` at import, so
COHEZION_STATE_DIR (tests/conftest.py) never reached it and every blocked promotion a test
provoked was appended to ~/.cohezion/pending_skill_approvals.jsonl, the operator's review
queue. conftest now redirects it for the whole session.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace


_REAL_APPROVALS = Path.home() / ".cohezion" / "pending_skill_approvals.jsonl"


def _sha(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def test_blocked_promotion_is_recorded_outside_the_real_home(tmp_path_factory) -> None:
    from cohezion.compound.skill_refiner import SkillRefiner

    before = _sha(_REAL_APPROVALS)
    path = SkillRefiner._APPROVALS_PATH
    assert path != _REAL_APPROVALS, "approvals path still points at the real review queue"
    assert tmp_path_factory.getbasetemp() in path.parents

    marker = "suite-isolation-probe"
    SkillRefiner()._record_blocked_promotion(marker, SimpleNamespace(key_insight="x"), "probe")

    assert marker in path.read_text(), "the record must land in the isolated file"
    assert _sha(_REAL_APPROVALS) == before


_REAL_REGISTRY = (
    Path(__file__).resolve().parents[2] / "src" / "cohezion" / "skills" / "skill_registry.json"
)


def test_update_registry_does_not_write_the_tracked_skill_registry(tmp_path) -> None:
    """ConfigTemplateManager.update_registry wrote the cwd-relative, git-tracked
    src/cohezion/skills/skill_registry.json; test_version_header_in_generated_agent
    rewrote it on every run. conftest redirects ConfigTemplateManager.REGISTRY_PATH."""
    from cohezion.core.config_templates import ConfigTemplateManager

    before = _sha(_REAL_REGISTRY)
    spec = SimpleNamespace(
        name="SUITE_ISOLATION_PROBE_PRIME",
        version="0.0",
        concepts={},
        see_also=[],
        source_path=tmp_path / "SUITE_ISOLATION_PROBE_PRIME.md",
    )
    ConfigTemplateManager().update_registry(spec)

    assert _sha(_REAL_REGISTRY) == before, "the tracked skill registry was rewritten"
    assert "SUITE_ISOLATION_PROBE_PRIME" in ConfigTemplateManager.REGISTRY_PATH.read_text()
