# ruff: noqa: S104  # binds 0.0.0.0 in dev/internal services
"""Git Context MCP Server - Code-aware compound sessions.

Port: 8368
Features:
- Git status and diff analysis
- Branch/commit tracking
- Code change context
- Staged change inspection
- Repository metadata

Enables code-aware BMAD workflows.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess
import sys
from typing import Any

from aiohttp import web


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

MCP_PORT = int(os.getenv("MCP_PORT", "8368"))

# Resolve git executable at module load to avoid S607 partial-path warnings.
_GIT = shutil.which("git") or "/usr/bin/git"


class GitContext:
    """Git repository context analyzer."""

    def __init__(self, repo_path: str = "."):
        from pathlib import Path

        from cohezion.mcp.servers.safe_input import sanitize_path

        self.repo_path = sanitize_path(repo_path, base_dir=Path.cwd())

    def _run_git(self, args: list[str]) -> tuple[str, bool]:
        """Run git command and return output."""
        try:
            result = subprocess.run(  # noqa: S603 - repo_path sanitized via sanitize_path; args from internal callers only
                [_GIT, "-C", str(self.repo_path), *args],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                return result.stdout.strip(), True
            else:
                return result.stderr.strip(), False
        except Exception as e:
            return str(e), False

    def is_git_repo(self) -> bool:
        """Check if path is a git repository."""
        _, success = self._run_git(["rev-parse", "--git-dir"])
        return success

    def get_status(self) -> dict[str, Any]:
        """Get repository status."""
        if not self.is_git_repo():
            return {"error": "Not a git repository"}

        # Get branch
        branch, _ = self._run_git(["branch", "--show-current"])

        # Get status
        status_output, _ = self._run_git(["status", "--porcelain", "-b"])

        # Parse status
        staged = []
        unstaged = []
        untracked = []

        for line in status_output.split("\n"):
            if not line or line.startswith("##"):
                continue

            status = line[:2]
            file = line[3:].strip()

            if status[0] in "MADRC":  # Staged
                staged.append({"file": file, "status": status[0]})
            if status[1] in "MD":  # Unstaged
                unstaged.append({"file": file, "status": status[1]})
            if status == "??":  # Untracked
                untracked.append(file)

        return {
            "branch": branch,
            "stagedCount": len(staged),
            "unstagedCount": len(unstaged),
            "untrackedCount": len(untracked),
            "staged": staged,
            "unstaged": unstaged,
            "untracked": untracked,
            "hasChanges": len(staged) + len(unstaged) > 0,
        }

    def get_diff(self, staged: bool = False) -> str:
        """Get diff output."""
        args = ["diff", "--cached", "--stat"] if staged else ["diff", "--stat"]
        output, success = self._run_git(args)
        return output if success else ""

    def get_log(self, limit: int = 10) -> list[dict]:
        """Get commit log."""
        format_str = "%H|%s|%an|%ad"
        output, success = self._run_git(
            ["log", f"--pretty=format:{format_str}", f"--max-count={limit}", "--date=short"]
        )

        if not success:
            return []

        commits = []
        for line in output.split("\n"):
            if "|" in line:
                parts = line.split("|", 3)
                if len(parts) == 4:
                    commits.append(
                        {
                            "hash": parts[0][:8],
                            "message": parts[1],
                            "author": parts[2],
                            "date": parts[3],
                        }
                    )

        return commits

    def get_branches(self) -> list[str]:
        """Get list of branches."""
        output, success = self._run_git(["branch", "-a", "--format=%(refname:short)"])
        if success:
            return [b.strip() for b in output.split("\n") if b.strip()]
        return []

    def get_repo_info(self) -> dict[str, Any]:
        """Get repository metadata."""
        if not self.is_git_repo():
            return {"error": "Not a git repository"}

        # Remote URL
        remote, _ = self._run_git(["remote", "get-url", "origin"])

        # Total commits
        commits_output, _ = self._run_git(["rev-list", "--count", "HEAD"])
        total_commits = int(commits_output) if commits_output.isdigit() else 0

        # Last commit
        last_commit, _ = self._run_git(["log", "-1", "--pretty=format:%s|%an|%ad", "--date=short"])

        return {
            "path": str(self.repo_path),
            "remote": remote,
            "totalCommits": total_commits,
            "lastCommit": last_commit,
        }


routes = web.RouteTableDef()


@routes.get("/health")
async def health(request: web.Request) -> web.Response:
    """Health check."""
    return web.json_response(
        {
            "status": "healthy",
            "server": "git-context",
            "port": MCP_PORT,
        }
    )


@routes.get("/")
async def index(request: web.Request) -> web.Response:
    """Server info."""
    return web.json_response(
        {
            "name": "Git Context MCP Server",
            "version": "1.0.0",
            "port": MCP_PORT,
            "tools": [
                "git_status",
                "git_diff",
                "git_log",
                "git_branches",
                "git_info",
            ],
        }
    )


@routes.post("/tools/git_status")
async def tool_git_status(request: web.Request) -> web.Response:
    """Get repository status."""
    try:
        data = await request.json()
        repo_path = data.get("repoPath", ".")

        git = GitContext(repo_path)

        if not git.is_git_repo():
            return web.json_response({"error": f"Not a git repository: {repo_path}"}, status=400)

        status = git.get_status()

        return web.json_response(
            {
                "tool": "git_status",
                "repoPath": str(git.repo_path),
                "status": status,
            }
        )
    except Exception as e:
        logger.exception("Git status failed")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/git_diff")
async def tool_git_diff(request: web.Request) -> web.Response:
    """Get diff output."""
    try:
        data = await request.json()
        repo_path = data.get("repoPath", ".")
        staged = data.get("staged", False)

        git = GitContext(repo_path)
        diff = git.get_diff(staged)

        return web.json_response(
            {
                "tool": "git_diff",
                "repoPath": str(git.repo_path),
                "staged": staged,
                "diff": diff[:5000] if len(diff) > 5000 else diff,
                "truncated": len(diff) > 5000,
            }
        )
    except Exception as e:
        logger.exception("Git diff failed")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/git_log")
async def tool_git_log(request: web.Request) -> web.Response:
    """Get commit log."""
    try:
        data = await request.json()
        repo_path = data.get("repoPath", ".")
        limit = data.get("limit", 10)

        git = GitContext(repo_path)
        commits = git.get_log(limit)

        return web.json_response(
            {
                "tool": "git_log",
                "repoPath": str(git.repo_path),
                "count": len(commits),
                "commits": commits,
            }
        )
    except Exception as e:
        logger.exception("Git log failed")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/git_branches")
async def tool_git_branches(request: web.Request) -> web.Response:
    """Get branches."""
    try:
        data = await request.json()
        repo_path = data.get("repoPath", ".")

        git = GitContext(repo_path)
        branches = git.get_branches()

        return web.json_response(
            {
                "tool": "git_branches",
                "repoPath": str(git.repo_path),
                "count": len(branches),
                "branches": branches[:50],  # Limit output
            }
        )
    except Exception as e:
        logger.exception("Git branches failed")
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/tools/git_info")
async def tool_git_info(request: web.Request) -> web.Response:
    """Get repository info."""
    try:
        data = await request.json()
        repo_path = data.get("repoPath", ".")

        git = GitContext(repo_path)
        info = git.get_repo_info()

        return web.json_response(
            {
                "tool": "git_info",
                "info": info,
            }
        )
    except Exception as e:
        logger.exception("Git info failed")
        return web.json_response({"error": str(e)}, status=500)


def create_app() -> web.Application:
    """Create the web application."""
    from cohezion.mcp.shared.auth import api_key_middleware

    app = web.Application(middlewares=[api_key_middleware])
    app.add_routes(routes)
    return app


# Global app instance for import
app = create_app()


async def main():
    """Run the Git Context MCP Server."""
    logger.info(f"Starting Git Context MCP Server on port {MCP_PORT}")
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", MCP_PORT)
    await site.start()

    logger.info(f"✅ Git Context Server running on http://localhost:{MCP_PORT}")

    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Git Context Server stopped")
