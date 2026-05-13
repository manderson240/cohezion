from pathlib import Path


def test_core_files_exist():
    """Verify that essential project files are intact."""
    core_files = [
        "pyproject.toml",
        "src/cohezion/__init__.py",
        "conductor/product.md",
        "src/cohezion/knowledge_graph/MISSION_JOURNAL.md",
        "src/cohezion/knowledge_graph/KEY_LEARNINGS.md",
    ]
    for file_path in core_files:
        assert Path(file_path).exists(), f"{file_path} is missing!"


def test_gitignore_patterns():
    """Verify that new ignore patterns are present."""
    with open(".gitignore") as f:
        content = f.read()

    assert "*.tar.gz" in content
    assert "*.bundle" in content
    assert "/archive/worktrees/" in content
    assert "node_modules/" in content


def test_no_massive_backup_in_head():
    """Verify that the 9.7GB backup is not in the current checkout."""
    massive_backup = "luma_speedrun_BACKUP_20260402_162540.tar.gz"
    assert not Path(massive_backup).exists()


def test_mined_knowledge_preserved():
    """Verify that mined knowledge is in the mission journal."""
    journal_path = "src/cohezion/knowledge_graph/MISSION_JOURNAL.md"
    with open(journal_path) as f:
        content = f.read()

    assert "SESSION 89: REPOSITORY SIZE OPTIMIZATION & REPAIR" in content
    assert "Luma Breakthrough Sprint" in content
    assert "3320518" in content  # AGI PID
