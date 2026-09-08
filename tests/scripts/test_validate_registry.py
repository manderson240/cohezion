"""Tests for scripts/ci/validate_registry.py skill-file discovery.

Guards the 2026-08-27 finding: the validator's disk scan was non-recursive
(``glob("*.md")``), so subdirectory skill bundles were outside the audit's
frame entirely -- neither "registered" nor "unregistered", simply uncounted.

Two skill layouts are legitimate, and the scan must model both:
  * flat      -- ``NAME.md`` at the top level; the skill name is the stem
  * bundle    -- ``NAME/SKILL.md``; the skill name is the DIRECTORY, and the
                 bundle's ``README.md`` / ``references/*.md`` are supporting
                 material, NOT separate skills

The fixtures are adversarial in three directions, because the first fix here
was wrong in the third one:
  * ``Bundle`` must be found          -> red if the scan is not recursive
  * ``Archived`` must NOT be found    -> red if it recurses without excluding
                                         archive directories
  * ``some-reference`` must NOT be    -> red if it promotes every nested .md to
    found                                a skill (the real tree has 12 such
                                         files; a clean fixture hid this)
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


_VALIDATOR = Path(__file__).resolve().parents[2] / "scripts" / "ci" / "validate_registry.py"


def _load_validator():
    """Import the CI script by path (it lives outside the package tree)."""
    spec = importlib.util.spec_from_file_location("validate_registry", _VALIDATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _make_tree(root: Path) -> None:
    """Mirror the real layout: flat skills, a bundle with support files, archive."""
    (root / "TopLevel.md").write_text("# top", encoding="utf-8")

    bundle = root / "Bundle"
    (bundle / "references").mkdir(parents=True)
    (bundle / "SKILL.md").write_text("# bundle skill", encoding="utf-8")
    (bundle / "README.md").write_text("# bundle readme", encoding="utf-8")
    (bundle / "references" / "some-reference.md").write_text("# ref", encoding="utf-8")

    (root / ".archive").mkdir()
    (root / ".archive" / "Archived.md").write_text("# archived", encoding="utf-8")


def test_scan_finds_top_level_files(tmp_path: Path) -> None:
    """Baseline: the original flat-layout behaviour is preserved."""
    _make_tree(tmp_path)
    found = _load_validator().scan_skill_files(tmp_path)
    assert "TopLevel" in found


def test_scan_finds_bundle_skills_by_directory_name(tmp_path: Path) -> None:
    """DISCRIMINATING: red under the original ``glob("*.md")``.

    Also pins that the bundle is named for its DIRECTORY -- a scan keyed on the
    file stem would report the useless name ``SKILL``.
    """
    _make_tree(tmp_path)
    found = _load_validator().scan_skill_files(tmp_path)
    assert "Bundle" in found, "a NAME/SKILL.md bundle is a skill named NAME"
    assert "SKILL" not in found, "bundles must not be registered under the stem 'SKILL'"


def test_scan_excludes_archive_directories(tmp_path: Path) -> None:
    """DISCRIMINATING: red under a naive ``rglob`` with no exclusion."""
    _make_tree(tmp_path)
    found = _load_validator().scan_skill_files(tmp_path)
    assert "Archived" not in found, (
        "archived skills are intentionally retired and must not be reported as unregistered"
    )


def test_scan_excludes_bundle_support_files(tmp_path: Path) -> None:
    """DISCRIMINATING: red if every nested .md is promoted to a skill.

    This is the case the first implementation got wrong: the real tree has 12
    README/reference files inside bundles, and a naive recursive scan reported
    all of them as unregistered skills.
    """
    _make_tree(tmp_path)
    found = _load_validator().scan_skill_files(tmp_path)
    assert "README" not in found, "a bundle README is documentation, not a skill"
    assert "some-reference" not in found, "bundle reference material is not a skill"


def test_scan_exact_set(tmp_path: Path) -> None:
    """Pins the whole contract, so no direction can drift silently."""
    _make_tree(tmp_path)
    assert _load_validator().scan_skill_files(tmp_path) == {"TopLevel", "Bundle"}


def test_scan_missing_directory_returns_empty(tmp_path: Path) -> None:
    """Fail-soft: an absent skills dir yields an empty set, not an exception."""
    assert _load_validator().scan_skill_files(tmp_path / "nope") == set()


# --- findings from adversarial review (glm-5.3-flash, kimi-k3), 2026-08-27 ---
# Both were latent at the time -- zero occurrences in the real tree -- but each
# is a SILENT drop, which is the failure mode this whole change exists to remove.


def test_bundle_shadowed_by_flat_file_is_reported_not_silently_dropped(
    tmp_path: Path, caplog
) -> None:
    """DISCRIMINATING: red while the collision is swallowed by ``setdefault``.

    ``NAME.md`` and ``NAME/SKILL.md`` both defining skill NAME is a genuine
    conflict. Keeping the flat file is a defensible precedence; keeping it
    *without telling anyone* means the bundle vanishes from the registry with
    no diagnostic anywhere.
    """
    (tmp_path / "testing.md").write_text("# flat", encoding="utf-8")
    (tmp_path / "testing").mkdir()
    (tmp_path / "testing" / "SKILL.md").write_text("# bundle", encoding="utf-8")

    from cohezion.registry import skill_discovery

    with caplog.at_level("WARNING", logger=skill_discovery.__name__):
        found = skill_discovery.discover_skills(tmp_path)

    assert found["testing"].name == "testing.md", "flat file keeps precedence"
    assert any("testing" in rec.message for rec in caplog.records), (
        "a shadowed bundle must produce a warning; silently dropping it is the "
        "exact class of bug this scan was rewritten to eliminate"
    )


def test_lowercase_bundle_marker_is_found(tmp_path: Path) -> None:
    """DISCRIMINATING: red under case-sensitive ``rglob("SKILL.md")``.

    Linux filesystems are case-sensitive, so a bundle whose marker is written
    ``skill.md`` was invisible -- indistinguishable from having no skill at all.
    """
    (tmp_path / "lower").mkdir()
    (tmp_path / "lower" / "skill.md").write_text("# bundle", encoding="utf-8")
    assert "lower" in _load_validator().scan_skill_files(tmp_path)
