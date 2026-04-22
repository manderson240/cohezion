"""Unit tests for scripts/migrate_skills_to_frontmatter.py.

Pure functions + apply-mode via tmp_path so tests don't touch the real skills dir.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


_SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import migrate_skills_to_frontmatter as m  # noqa: E402


def test_filename_to_spec_name_standard_prime() -> None:
    assert m.filename_to_spec_name("ADVERSARIAL_TESTING_PRIME") == "adversarial-testing-prime"


def test_filename_to_spec_name_lowercases_and_dashes_underscores() -> None:
    assert m.filename_to_spec_name("Already_mixed_CASE") == "already-mixed-case"


def test_filename_to_spec_name_strips_invalid_chars() -> None:
    assert m.filename_to_spec_name("name!with@bad#chars") == "namewithbadchars"


def test_filename_to_spec_name_collapses_repeated_dashes() -> None:
    assert m.filename_to_spec_name("a__b___c") == "a-b-c"


def test_filename_to_spec_name_bounds_to_64_chars() -> None:
    assert len(m.filename_to_spec_name("A" * 100)) == 64


def test_extract_description_picks_domain_expertise_paragraph() -> None:
    body = (
        "# SKILL: TEST_PRIME\n\n"
        "## DOMAIN EXPERTISE\n\n"
        "You are a specialist in **test design** and `pytest` conventions.\n\n"
        "## KEY TEXTS\n\n- pytest docs\n"
    )
    desc = m.extract_description(body)
    assert "specialist in test design" in desc
    assert "pytest conventions" in desc
    assert "**" not in desc
    assert "`" not in desc


def test_extract_description_truncates_at_sentence_boundary() -> None:
    body = "## DOMAIN EXPERTISE\n\nFirst sentence is short. " + (
        "Second sentence is very long " * 50
    )
    desc = m.extract_description(body, max_chars=80)
    assert desc.endswith(".")
    assert len(desc) <= 80


def test_extract_description_falls_back_to_first_section() -> None:
    body = "# SKILL: X\n\n## OVERVIEW\n\nOverview text here is the fallback.\n"
    assert "Overview text here" in m.extract_description(body)


def test_extract_description_handles_empty_body() -> None:
    desc = m.extract_description("")
    assert desc  # non-empty placeholder satisfies spec 1-char minimum


def test_has_frontmatter_detects_leading_triple_dash() -> None:
    assert m.has_frontmatter("---\nname: x\n---\n\n# body")
    assert m.has_frontmatter("\n\n---\nname: x\n---\nbody")


def test_has_frontmatter_rejects_non_frontmatter() -> None:
    assert not m.has_frontmatter("# SKILL: X\n\n## DOMAIN EXPERTISE\n")
    assert not m.has_frontmatter("")
    assert not m.has_frontmatter("body only, no frontmatter")


def test_yaml_scalar_escapes_quotes_and_backslashes() -> None:
    assert m.yaml_scalar('he said "hi"') == '"he said \\"hi\\""'
    assert m.yaml_scalar("path\\to\\file") == '"path\\\\to\\\\file"'


def test_yaml_list_empty_produces_flow_array() -> None:
    assert m.yaml_list([]) == "[]"


def test_yaml_list_quotes_each_element() -> None:
    assert m.yaml_list(["a", "b", "c"]) == '["a", "b", "c"]'


def test_build_frontmatter_includes_all_registry_fields() -> None:
    fm = m.build_frontmatter(
        "test-skill",
        "A test skill.",
        {
            "version": "v1.0",
            "concepts": ["Concept A", "Concept B"],
            "see_also": ["OTHER_PRIME"],
            "source": "src/cohezion/skills/TEST_PRIME.md",
        },
    )
    assert fm.startswith("---\n")
    assert "name: test-skill" in fm
    assert 'description: "A test skill."' in fm
    assert 'version: "v1.0"' in fm
    assert '"Concept A"' in fm
    assert '"OTHER_PRIME"' in fm


def test_build_frontmatter_omits_empty_registry_fields() -> None:
    fm = m.build_frontmatter(
        "test-skill", "A test.", {"version": "v1.0", "concepts": [], "see_also": []}
    )
    assert "concepts:" not in fm
    assert "see_also:" not in fm


def test_build_frontmatter_without_registry_entry() -> None:
    fm = m.build_frontmatter("test-skill", "Desc.", None)
    assert "metadata:" not in fm
    assert "name: test-skill" in fm


def _write_skill(tmp_path: Path, stem: str, body: str) -> Path:
    path = tmp_path / f"{stem}.md"
    path.write_text(body, encoding="utf-8")
    return path


def test_migrate_file_dry_run_does_not_write(tmp_path) -> None:
    path = _write_skill(
        tmp_path, "TEST_PRIME", "# SKILL\n\n## DOMAIN EXPERTISE\n\nA test.\n"
    )
    original = path.read_text()
    status, _ = m.migrate_file(path, {"TEST_PRIME": {"version": "v1"}}, apply=False)
    assert status == "migrated"
    assert path.read_text() == original


def test_migrate_file_apply_writes_frontmatter(tmp_path) -> None:
    path = _write_skill(
        tmp_path, "TEST_PRIME", "# SKILL\n\n## DOMAIN EXPERTISE\n\nA test specialist.\n"
    )
    status, _ = m.migrate_file(path, {"TEST_PRIME": {"version": "v1"}}, apply=True)
    assert status == "migrated"
    content = path.read_text()
    assert content.startswith("---\n")
    assert "name: test-prime" in content
    assert "# SKILL" in content  # original body preserved


def test_migrate_file_is_idempotent(tmp_path) -> None:
    path = _write_skill(
        tmp_path,
        "TEST_PRIME",
        '---\nname: test-prime\ndescription: "existing"\n---\n\n# SKILL\n',
    )
    status, _ = m.migrate_file(path, {}, apply=True)
    assert status == "already-has-frontmatter"


def test_migrate_file_skips_non_prime(tmp_path) -> None:
    path = _write_skill(tmp_path, "README", "# Readme\n")
    status, _ = m.migrate_file(path, {}, apply=True)
    assert status == "skipped-not-prime"


def test_main_dry_run_exits_0_no_writes(tmp_path, capsys) -> None:
    _write_skill(
        tmp_path, "TEST_PRIME", "# SKILL\n\n## DOMAIN EXPERTISE\n\nA test.\n"
    )
    (tmp_path / "skill_registry.json").write_text(
        json.dumps({"TEST_PRIME": {"version": "v1"}})
    )
    rc = m.main(["--skills-dir", str(tmp_path)])
    assert rc == 0
    assert not (tmp_path / "TEST_PRIME.md").read_text().startswith("---")


def test_main_apply_writes_and_backs_up(tmp_path, capsys) -> None:
    _write_skill(
        tmp_path, "TEST_PRIME", "# SKILL\n\n## DOMAIN EXPERTISE\n\nA test.\n"
    )
    (tmp_path / "skill_registry.json").write_text(
        json.dumps({"TEST_PRIME": {"version": "v1", "concepts": ["C1"]}})
    )
    backup_root = tmp_path / "backup"
    rc = m.main(
        [
            "--apply",
            "--skills-dir",
            str(tmp_path),
            "--backup-root",
            str(backup_root),
        ]
    )
    assert rc == 0
    assert (tmp_path / "TEST_PRIME.md").read_text().startswith("---\n")
    backups = list(backup_root.glob("skills-pre-migration-*/TEST_PRIME.md"))
    assert len(backups) == 1
    assert not backups[0].read_text().startswith("---")


def test_main_returns_2_when_skills_dir_missing(tmp_path, capsys) -> None:
    rc = m.main(["--skills-dir", str(tmp_path / "nonexistent")])
    assert rc == 2
