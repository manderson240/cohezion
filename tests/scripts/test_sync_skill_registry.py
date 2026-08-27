"""Tests for scripts/ci/sync_skill_registry.py entry construction.

The point of registering a skill is to make it *routable*. An entry whose
description is a placeholder satisfies the validator while leaving the skill
undiscoverable -- CI turns green and nothing improves. 15 of the 40 skills
registered on 2026-08-27 carry no YAML frontmatter at all (they use a
``# SKILL: NAME`` / ``## DOMAIN EXPERTISE`` body), so the body fallback is what
makes the fix real rather than cosmetic.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


_SYNC = Path(__file__).resolve().parents[2] / "scripts" / "ci" / "sync_skill_registry.py"

_NO_FRONTMATTER = """# SKILL: CATEGORY_THEORETIC_AGI_MONADS_PRIME

## DOMAIN EXPERTISE
Category-Theoretic Monads (State, Reader, Either, and Free Monads) and
GFlowNet Probabilistic Sampling for Provably Sound AGI Swarms.

## KEY TEXTS
- something else entirely
"""

_WITH_FRONTMATTER = """---
name: surrealdb-mcp-prime
description: "Exposing SurrealDB multi-model capabilities as executable agent tools."
---

# SKILL: SURREALDB_MCP_PRIME
"""


def _load():
    spec = importlib.util.spec_from_file_location("sync_skill_registry", _SYNC)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_frontmatter_description_is_used(tmp_path: Path) -> None:
    path = tmp_path / "SURREALDB_MCP_PRIME.md"
    path.write_text(_WITH_FRONTMATTER, encoding="utf-8")
    entry = _load().build_entry("SURREALDB_MCP_PRIME", path)
    assert entry["description"].startswith("Exposing SurrealDB multi-model")


def test_body_prose_used_when_no_frontmatter(tmp_path: Path) -> None:
    """DISCRIMINATING: red if the fallback is a placeholder string."""
    path = tmp_path / "CATEGORY_THEORETIC_AGI_MONADS_PRIME.md"
    path.write_text(_NO_FRONTMATTER, encoding="utf-8")
    entry = _load().build_entry("CATEGORY_THEORETIC_AGI_MONADS_PRIME", path)
    assert "Category-Theoretic Monads" in entry["description"], (
        "a skill with no frontmatter must still get a real description from its "
        "body, otherwise registering it turns CI green without making it routable"
    )
    assert "no description" not in entry["description"].lower()


def test_body_fallback_skips_headings(tmp_path: Path) -> None:
    """The heading is not the description; the prose beneath it is."""
    path = tmp_path / "X.md"
    path.write_text(_NO_FRONTMATTER, encoding="utf-8")
    description = _load().build_entry("X", path)["description"]
    assert not description.startswith("#")
    assert "DOMAIN EXPERTISE" not in description


def test_keywords_derived_from_real_description(tmp_path: Path) -> None:
    """Keywords must come from the recovered prose, not the placeholder."""
    path = tmp_path / "CATEGORY_THEORETIC_AGI_MONADS_PRIME.md"
    path.write_text(_NO_FRONTMATTER, encoding="utf-8")
    keywords = _load().build_entry("CATEGORY_THEORETIC_AGI_MONADS_PRIME", path)["keywords"]
    assert "gflownet" in keywords or "monads" in keywords
    assert "description" not in keywords, "placeholder wording must not leak into the index"


def test_truncation_does_not_split_a_word(tmp_path: Path) -> None:
    """Descriptions are capped; the cap must land on a word boundary."""
    module = _load()
    long_prose = "# SKILL: X\n\n## DOMAIN EXPERTISE\n" + ("alpha bravo " * 80) + "\n"
    path = tmp_path / "X.md"
    path.write_text(long_prose, encoding="utf-8")
    description = module.build_entry("X", path)["description"]
    assert len(description) <= module.DESCRIPTION_MAX
    assert not description.endswith(" ")
    assert description.split()[-1] in {"alpha", "bravo"}


def test_unreadable_file_still_yields_an_entry(tmp_path: Path) -> None:
    """Fail-soft: a missing file must not abort a whole sync run."""
    entry = _load().build_entry("GHOST", tmp_path / "absent.md")
    assert entry["name"] == "GHOST"
    assert entry["description"]


# --- merge-blocking finding from adversarial review (kimi-k3), 2026-08-27 -----
# discover_skills() returns {} for a missing directory. That is right for the
# READ path (a bad path reads as "0 on disk", not a traceback) and catastrophic
# for the WRITE path: orphaned = registry - {} = every entry. A renamed dir, a
# wrong cwd or a mount hiccup would wipe the registry.


def test_prune_aborts_when_nothing_is_discovered(tmp_path: Path, monkeypatch, capsys) -> None:
    """DISCRIMINATING: red while an empty scan is allowed to prune.

    Reproduces the reported footgun exactly: point the scan at a directory that
    does not exist, then --prune --apply.
    """
    module = _load()
    registry = tmp_path / "skill_registry.json"
    registry.write_text(
        json.dumps({f"SKILL_{i}": {"path": f"p{i}.md"} for i in range(275)}),
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "SKILLS_DIR", tmp_path / "does_not_exist")
    monkeypatch.setattr(module, "REGISTRY_FILE", registry)
    monkeypatch.setattr(module, "load_registry", lambda: json.loads(registry.read_text()))

    exit_code = module.main(["--prune", "--apply"])

    survived = json.loads(registry.read_text())
    assert len(survived) == 275, "an empty scan must never be allowed to empty the registry"
    assert exit_code != 0, "the run must fail loudly rather than report success"
    assert "abort" in capsys.readouterr().out.lower()


def test_add_still_works_when_scan_is_empty(tmp_path: Path, monkeypatch) -> None:
    """The guard must block deletion only -- a no-op --add is harmless."""
    module = _load()
    registry = tmp_path / "skill_registry.json"
    registry.write_text(json.dumps({"KEEP": {"path": "keep.md"}}), encoding="utf-8")
    monkeypatch.setattr(module, "SKILLS_DIR", tmp_path / "does_not_exist")
    monkeypatch.setattr(module, "REGISTRY_FILE", registry)
    monkeypatch.setattr(module, "load_registry", lambda: json.loads(registry.read_text()))

    assert module.main(["--add", "--apply"]) == 0
    assert json.loads(registry.read_text()) == {"KEEP": {"path": "keep.md"}}


def test_registry_write_is_atomic(tmp_path: Path, monkeypatch) -> None:
    """A crash mid-write must not leave a truncated, unparseable registry."""
    module = _load()
    registry = tmp_path / "skill_registry.json"
    original = {"KEEP": {"path": "keep.md"}}
    registry.write_text(json.dumps(original), encoding="utf-8")

    skills = tmp_path / "skills"
    skills.mkdir()
    (skills / "NEW.md").write_text("---\ndescription: new\n---\n", encoding="utf-8")
    monkeypatch.setattr(module, "SKILLS_DIR", skills)
    monkeypatch.setattr(module, "REGISTRY_FILE", registry)
    monkeypatch.setattr(module, "load_registry", lambda: json.loads(registry.read_text()))

    # Fail during the rename that publishes the new file.
    def boom(*_args, **_kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(module.os, "replace", boom)
    with pytest.raises(KeyboardInterrupt):
        module.main(["--add", "--apply"])

    assert json.loads(registry.read_text()) == original, (
        "the original registry must survive an interrupted write"
    )
