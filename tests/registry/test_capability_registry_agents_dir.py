"""Tests for CapabilityRegistry agent-card discovery in sparse worktrees.

Regression (diamond backlog, 2026-07-09): linked worktrees created with a
sparse-checkout cone that excludes .claude/ have no agent cards on disk, so
A2A discovery (GET /agents) silently found zero markdown specialists there
while passing in the main checkout ("env-dependent" failure).
"""

from pathlib import Path

from cohezion.registry.capability_registry import CapabilityRegistry


def _write_card(agents_dir: Path, name: str) -> None:
    agents_dir.mkdir(parents=True, exist_ok=True)
    (agents_dir / f"{name}.md").write_text(
        f"---\nname: {name}\ndescription: test specialist\n---\nbody\n"
    )


def test_local_cards_preferred(tmp_path: Path) -> None:
    """A checkout with its own cards uses them — no git indirection."""
    _write_card(tmp_path / ".claude" / "agents", "vault-keeper")
    reg = CapabilityRegistry(root_dir=tmp_path)
    assert reg._resolve_agents_dir() == tmp_path / ".claude" / "agents"
    names = {c.name for c in reg.capabilities if c.type == "agent"}
    assert "vault-keeper" in names


def test_sparse_worktree_falls_back_to_common_root(tmp_path: Path) -> None:
    """A worktree without materialized cards resolves the main checkout's."""
    main = tmp_path / "main"
    _write_card(main / ".claude" / "agents", "vault-keeper")
    gitdir = main / ".git" / "worktrees" / "wt1"
    gitdir.mkdir(parents=True)
    (gitdir / "commondir").write_text("../..\n")

    wt = tmp_path / "wt1"
    wt.mkdir()
    (wt / ".git").write_text(f"gitdir: {gitdir}\n")
    # sparse cone left only an empty agents dir (or none at all)
    (wt / ".claude" / "agents").mkdir(parents=True)

    reg = CapabilityRegistry(root_dir=wt)
    assert reg._resolve_agents_dir() == main / ".claude" / "agents"
    names = {c.name for c in reg.capabilities if c.type == "agent"}
    assert "vault-keeper" in names


def test_absolute_commondir_also_resolves(tmp_path: Path) -> None:
    """git may write commondir as an absolute path; pathlib's join handles it
    (an absolute right-hand operand replaces the left)."""
    main = tmp_path / "main"
    _write_card(main / ".claude" / "agents", "surreal-dba")
    gitdir = main / ".git" / "worktrees" / "wt2"
    gitdir.mkdir(parents=True)
    (gitdir / "commondir").write_text(f"{main / '.git'}\n")

    wt = tmp_path / "wt2"
    wt.mkdir()
    (wt / ".git").write_text(f"gitdir: {gitdir}\n")

    reg = CapabilityRegistry(root_dir=wt)
    assert reg._resolve_agents_dir() == main / ".claude" / "agents"


def test_no_cards_anywhere_is_quiet(tmp_path: Path) -> None:
    """No cards locally and no git indirection: no crash, no agent caps."""
    reg = CapabilityRegistry(root_dir=tmp_path)
    assert reg._resolve_agents_dir() == tmp_path / ".claude" / "agents"
    assert [c for c in reg.capabilities if c.type == "agent"] == []
