"""Subprocess sandbox utilities for multi-framework tier execution.

Prevents credential exfiltration, prompt injection execution, and
unauthorized file system access when running AI framework subprocesses.

Sandbox layers:
1. Environment sanitization — strip sensitive env vars (API keys, tokens)
2. Working directory isolation — run in tmpdir, not project root
3. Resource limits — cap subprocess CPU + memory via resource module
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path


logger = logging.getLogger(__name__)

# Environment variables that must NEVER be passed to subprocess.
# AI frameworks spawned as subprocesses should not have credential access.
_SENSITIVE_ENV_KEYS = frozenset(
    {
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "OPENAI_API_KEY",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
        "GOOGLE_API_KEY",
        "HUGGINGFACE_API_KEY",
        "GITHUB_TOKEN",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "SURREAL_PASSWORD",
        "DATABASE_URL",
        "SECRET_KEY",
        "SUDO_PASSWORD",
    }
)

# Env vars ALLOWED for subprocess (whitelist approach for Claude Code tier)
_CLAUDE_CODE_ALLOWED_ENV_KEYS = frozenset(
    {
        "HOME",
        "PATH",
        "TERM",
        "LANG",
        "LC_ALL",
        "USER",
        "LOGNAME",
        "SHELL",
        "VIRTUAL_ENV",
        "UV_PYTHON",
        "PYTHONPATH",
        "ANTHROPIC_API_KEY",  # Claude Code needs this to call Anthropic API
    }
)


def sanitized_env(*, allow_anthropic: bool = False, allow_gemini: bool = False) -> dict[str, str]:
    """Return a sanitized environment dict with sensitive keys removed.

    Parameters
    ----------
    allow_anthropic : bool
        If True, ANTHROPIC_API_KEY is preserved (needed for Claude Code tier).
    allow_gemini : bool
        If True, GEMINI_API_KEY is preserved (needed for Gemini CLI tier).

    Returns
    -------
    dict[str, str]
        Sanitized os.environ copy safe for subprocess use.
    """
    env = dict(os.environ)
    allowed_exceptions = set()
    if allow_anthropic and "ANTHROPIC_API_KEY" in env:
        allowed_exceptions.add("ANTHROPIC_API_KEY")
    if allow_gemini and "GEMINI_API_KEY" in env:
        allowed_exceptions.add("GEMINI_API_KEY")

    for key in list(env.keys()):
        if key in _SENSITIVE_ENV_KEYS and key not in allowed_exceptions:
            del env[key]

    return env


def sandbox_tempdir() -> Path:
    """Create a temporary working directory for sandboxed subprocess execution.

    The directory is isolated from the project root — subprocesses run here
    cannot access source code, credentials, or vault data by accident.

    Returns a Path to the tmpdir (caller is responsible for cleanup).
    """
    tmpdir = Path(tempfile.mkdtemp(prefix="cohezion_sandbox_"))
    logger.debug("Sandbox tmpdir created: %s", tmpdir)
    return tmpdir


def apply_resource_limits() -> None:
    """Apply soft resource limits to the current process.

    Called via subprocess preexec_fn to cap memory and CPU for sandboxed tiers.
    No-ops on platforms that don't support resource module.
    """
    try:
        import resource

        # Cap virtual memory at 4GB (prevents runaway allocations)
        resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3, resource.RLIM_INFINITY))
        # Cap CPU time at 120 seconds
        resource.setrlimit(resource.RLIMIT_CPU, (120, resource.RLIM_INFINITY))
    except (OSError, ImportError, ValueError) as exc:
        logger.debug("Resource limits not applied: %s", exc)


class SandboxedSubprocess:
    """Context for running a subprocess with full sandboxing applied.

    Usage:
        with SandboxedSubprocess(allow_anthropic=True) as sb:
            result = subprocess.run(cmd, env=sb.env, cwd=sb.cwd, ...)
        # tmpdir auto-cleaned after with block
    """

    def __init__(self, *, allow_anthropic: bool = False, allow_gemini: bool = False) -> None:
        self._allow_anthropic = allow_anthropic
        self._allow_gemini = allow_gemini
        self._tmpdir: Path | None = None
        self.env: dict[str, str] = {}
        self.cwd: str = "/tmp"

    def __enter__(self) -> SandboxedSubprocess:
        self._tmpdir = sandbox_tempdir()
        self.cwd = str(self._tmpdir)
        self.env = sanitized_env(
            allow_anthropic=self._allow_anthropic,
            allow_gemini=self._allow_gemini,
        )
        return self

    def __exit__(self, *_: object) -> None:
        if self._tmpdir and self._tmpdir.exists():
            import shutil

            try:
                shutil.rmtree(self._tmpdir)
                logger.debug("Sandbox tmpdir cleaned: %s", self._tmpdir)
            except Exception as exc:
                logger.debug("Sandbox tmpdir cleanup failed: %s", exc)
