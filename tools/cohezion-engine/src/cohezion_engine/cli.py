"""Cohezion Engine CLI - spec-driven development workflow tool."""
import json

import click

from cohezion_engine import __version__
from cohezion_engine.config import get_config_dir
from cohezion_engine.context import estimate_context
from cohezion_engine import session as session_mod
from cohezion_engine import worktree as worktree_mod
from cohezion_engine import plan as plan_mod


@click.group()
@click.version_option(version=__version__, prog_name="cz")
def cli():
    """cz - Cohezion Engine workflow CLI.

    Provides session management, context tracking, worktree isolation,
    and plan lifecycle for spec-driven development.
    """


@cli.command()
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def status(as_json: bool):
    """Show cohezion-engine status and configuration."""
    config_dir = get_config_dir()
    data = {
        "version": __version__,
        "config_dir": str(config_dir),
    }
    if as_json:
        click.echo(json.dumps(data))
    else:
        click.echo(f"cohezion-engine v{data['version']}")
        click.echo(f"Config: {data['config_dir']}")


@cli.command("context")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option("--limit", default=200_000, help="Context token limit", show_default=True)
def context_cmd(as_json: bool, limit: int):
    """Estimate current Claude Code context usage."""
    data = estimate_context(context_limit=limit)
    if as_json:
        click.echo(json.dumps(data))
    else:
        pct = data["percentage"]
        status_str = data["status"]
        color = "green" if status_str == "OK" else "yellow" if status_str == "WARNING" else "red"
        click.echo(f"Context: {click.style(f'{pct:.1f}%', fg=color)} ({status_str})")
        if "error" in data:
            click.echo(f"  Note: {data['error']}", err=True)


@cli.group()
def session():
    """Session lifecycle management."""


@session.command("status")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def session_status(as_json: bool):
    """Show current session ID and directory."""
    sid = session_mod.get_session_id()
    sess_dir = session_mod.get_session_dir()
    data = {"session_id": sid, "session_dir": str(sess_dir)}
    if as_json:
        click.echo(json.dumps(data))
    else:
        click.echo(f"Session: {sid}")
        click.echo(f"Dir:     {sess_dir}")


@session.command("send-clear")
@click.argument("plan_path", required=False)
@click.option("--general", "is_general", is_flag=True, help="General continuation (no plan)")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def session_send_clear(plan_path: str | None, is_general: bool, as_json: bool):
    """Trigger session continuation / clear."""
    if is_general:
        plan_path = None
    result = session_mod.send_clear(plan_path)
    if as_json:
        click.echo(json.dumps(result))
    else:
        icon = "✓" if result["success"] else "⚠"
        click.echo(f"{icon} {result['message']} (method: {result['method']})")


@cli.group()
def worktree():
    """Git worktree isolation management."""


@worktree.command("status")
@click.option("--json", "as_json", is_flag=True)
def worktree_status(as_json: bool):
    """Show active worktree info."""
    data = worktree_mod.get_worktree_status()
    if as_json:
        click.echo(json.dumps(data))
    else:
        if data["active"]:
            click.echo(f"Active worktree: {data['branch']} ({data['path']})")
        else:
            click.echo("No active worktree")


@worktree.command("detect")
@click.argument("slug")
@click.option("--json", "as_json", is_flag=True)
def worktree_detect(slug: str, as_json: bool):
    """Check if a worktree exists for SLUG."""
    data = worktree_mod.detect_worktree(slug)
    if as_json:
        click.echo(json.dumps(data))
    else:
        if data["found"]:
            click.echo(f"Found: {data['path']} (branch: {data['branch']})")
        else:
            click.echo(f"No worktree found for slug '{slug}'")


@worktree.command("create")
@click.argument("slug")
@click.option("--json", "as_json", is_flag=True)
def worktree_create(slug: str, as_json: bool):
    """Create a new worktree for SLUG."""
    data = worktree_mod.create_worktree(slug)
    if as_json:
        click.echo(json.dumps(data))
    else:
        if data.get("success"):
            click.echo(f"Created: {data['path']} (branch: {data['branch']})")
        else:
            click.echo(f"Error: {data.get('error')} — {data.get('detail', '')}", err=True)


@worktree.command("diff")
@click.argument("slug")
@click.option("--json", "as_json", is_flag=True)
def worktree_diff(slug: str, as_json: bool):
    """List files changed in worktree SLUG vs base branch."""
    data = worktree_mod.diff_worktree(slug)
    if as_json:
        click.echo(json.dumps(data))
    else:
        if data.get("success"):
            for f in data.get("files_changed", []):
                click.echo(f)
        else:
            click.echo(f"Error: {data.get('error')}", err=True)


@worktree.command("sync")
@click.argument("slug")
@click.option("--json", "as_json", is_flag=True)
def worktree_sync(slug: str, as_json: bool):
    """Squash merge worktree SLUG back to base branch."""
    data = worktree_mod.sync_worktree(slug)
    if as_json:
        click.echo(json.dumps(data))
    else:
        if data.get("success"):
            click.echo(f"Synced (commit: {data['commit_hash']}, files: {data['files_changed']})")
        else:
            click.echo(f"Error: {data.get('error')}", err=True)


@worktree.command("cleanup")
@click.argument("slug")
@click.option("--json", "as_json", is_flag=True)
def worktree_cleanup(slug: str, as_json: bool):
    """Remove worktree and branch for SLUG."""
    data = worktree_mod.cleanup_worktree(slug)
    if as_json:
        click.echo(json.dumps(data))
    else:
        if data.get("success"):
            click.echo(f"Removed: {data['removed_path']}")
        else:
            click.echo(f"Error: {data.get('error')}", err=True)


@cli.group()
def plan():
    """Plan file lifecycle management."""


@plan.command("register")
@click.argument("plan_path")
@click.argument("status")
def plan_register(plan_path: str, status: str):
    """Register PLAN_PATH with current session at STATUS."""
    plan_mod.register_plan(plan_path, status)
    click.echo(f"Registered: {plan_path} ({status})")


@plan.command("status")
@click.option("--json", "as_json", is_flag=True)
def plan_status(as_json: bool):
    """Show current plan and its status."""
    info = plan_mod.get_plan_status()
    if info is None:
        if as_json:
            click.echo(json.dumps({"plan": None}))
        else:
            click.echo("No plan registered for this session")
        return
    if as_json:
        click.echo(json.dumps(info))
    else:
        click.echo(f"Plan: {info['path']}")
        click.echo(f"Status: {info['registered_status']}")
        if info.get("frontmatter"):
            fm = info["frontmatter"]
            click.echo(f"  Status (file): {fm.get('Status', '?')}")
            click.echo(f"  Approved: {fm.get('Approved', '?')}")


if __name__ == "__main__":
    cli()
