"""Session salvage — recover WORK from Claude Code transcripts before they are pruned.

Companion to ``claude_usage`` (which counts tokens from the same files). This module
recovers content: what was written, what was run, what was asked.

WHY THIS EXISTS (2026-07-18, /doctor): ``cleanupPeriodDays`` was 7 — 262 logged startups
had left only 221 transcripts spanning 8 days, and Entire.io held 0 checkpoints as a
fallback. Everything older was already deleted. Retention is now raised, but transcripts
still roll off eventually, and the reasoning in them is never committed to git.

HONEST SCOPE (metacognitive-calibration): most transcript content is REDUNDANT — committed
Write/Edit payloads are already in git and the vault holds 22k+ notes. The unique value is
narrow: work that never landed. ``unique_writes`` isolates exactly that by comparing the
transcript payload against the file on disk today. A salvage run that returns nothing is a
REAL and good outcome (it means nothing was lost), not a failure to explain away.

Design mirrors ``claude_usage``: ``extract_session_artifacts`` is pure (records in, dataclass
out, unit-tested); ``load_session`` is the I/O edge.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path


# Tools whose invocation produces file content we could recover.
_WRITE_TOOLS = {"Write", "Edit", "NotebookEdit"}
_COMMAND_RE = re.compile(r"<command-name>/?([\w:-]+)</command-name>")

TRANSCRIPT_ROOT = Path.home() / ".claude" / "projects"


@dataclass(frozen=True)
class FileWrite:
    """One recovered file-writing tool call."""

    path: str
    tool: str
    content: str

    @property
    def n_bytes(self) -> int:
        return len(self.content)

    @property
    def sha(self) -> str:
        return hashlib.sha256(self.content.encode("utf-8", "replace")).hexdigest()[:12]


@dataclass
class SessionArtifacts:
    """Everything recoverable from one session, before any judgment is applied."""

    session_id: str = ""
    cwd: str = ""
    first_ts: str = ""
    last_ts: str = ""
    user_prompts: list[str] = field(default_factory=list)
    file_writes: list[FileWrite] = field(default_factory=list)
    bash_commands: list[str] = field(default_factory=list)
    commands_invoked: list[str] = field(default_factory=list)

    @property
    def files_touched(self) -> list[str]:
        seen: dict[str, None] = {}
        for w in self.file_writes:
            seen[w.path] = None
        return list(seen)


def _text_of(content: object) -> str:
    """Flatten a message.content into plain text, ignoring structured blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"
        )
    return ""


def _is_tool_result(content: object) -> bool:
    """Tool results arrive with type=user; they are machine output, not a human ask."""
    return isinstance(content, list) and any(
        isinstance(b, dict) and b.get("type") == "tool_result" for b in content
    )


def _write_from(name: str, inp: dict) -> FileWrite | None:
    path = inp.get("file_path") or inp.get("notebook_path")
    if not isinstance(path, str):
        return None
    if name == "Edit":
        content = inp.get("new_string")
    elif name == "NotebookEdit":
        content = inp.get("new_source")
    else:
        content = inp.get("content")
    if not isinstance(content, str):
        return None
    return FileWrite(path=path, tool=name, content=content)


def extract_session_artifacts(records: Iterable[dict]) -> SessionArtifacts:
    """Pure: transcript records -> recovered artifacts. Never raises on malformed input."""
    art = SessionArtifacts()
    for rec in records:
        if not isinstance(rec, dict):
            continue
        if not art.session_id and isinstance(rec.get("sessionId"), str):
            art.session_id = rec["sessionId"]
        if not art.cwd and isinstance(rec.get("cwd"), str):
            art.cwd = rec["cwd"]
        ts = rec.get("timestamp")
        if isinstance(ts, str):
            art.first_ts = art.first_ts or ts
            art.last_ts = ts

        msg = rec.get("message")
        content = msg.get("content") if isinstance(msg, dict) else None

        if rec.get("type") == "user":
            if _is_tool_result(content):
                continue
            text = _text_of(content)
            art.commands_invoked.extend(_COMMAND_RE.findall(text))
            stripped = _COMMAND_RE.sub("", text).strip()
            if stripped:
                art.user_prompts.append(stripped)
            continue

        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            name, inp = block.get("name"), block.get("input")
            if not isinstance(name, str) or not isinstance(inp, dict):
                continue
            if name == "Bash":
                cmd = inp.get("command")
                if isinstance(cmd, str):
                    art.bash_commands.append(cmd)
            elif name in _WRITE_TOOLS:
                w = _write_from(name, inp)
                if w is not None:
                    art.file_writes.append(w)
    return art


def unique_writes(art: SessionArtifacts) -> list[FileWrite]:
    """The narrow slice of real salvage value: writes whose content is NOT what is on
    disk today — i.e. work that was later overwritten, reverted, or never landed.

    Only the LAST write per path is considered: a session that iterates on a file three
    times produced one final state, not three candidates.
    """
    latest: dict[str, FileWrite] = {}
    for w in art.file_writes:
        latest[w.path] = w

    out: list[FileWrite] = []
    for path, w in latest.items():
        try:
            current = Path(path).read_text(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            out.append(w)  # vanished or unreadable -> transcript is the only copy
            continue
        if current != w.content:
            out.append(w)
    return out


def iter_records(path: Path) -> Iterator[dict]:
    """I/O edge: stream one transcript, skipping unparseable lines."""
    try:
        with path.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(rec, dict):
                    yield rec
    except OSError:
        return


def load_session(path: Path) -> SessionArtifacts:
    """I/O edge: one transcript file -> artifacts."""
    return extract_session_artifacts(iter_records(path))


def is_subagent_transcript(path: Path) -> bool:
    """Subagent transcripts live at <project>/<session-id>/subagents/agent-*.jsonl.

    They are the MAJORITY of the corpus (165 of 221 when this was written) because
    delegated agents do bulk work. A ``*/*.jsonl`` glob silently misses all of them.
    """
    return path.parent.name == "subagents"


def iter_transcripts(root: Path | None = None, *, subagents: bool = True) -> Iterator[Path]:
    """All transcript files, newest first — main sessions AND subagent runs."""
    root = root or TRANSCRIPT_ROOT
    if not root.is_dir():
        return iter(())
    files = [p for p in root.rglob("*.jsonl") if subagents or not is_subagent_transcript(p)]
    return iter(sorted(files, key=lambda p: p.stat().st_mtime, reverse=True))


# Paths that are ephemeral by construction — losing them is not data loss.
_EPHEMERAL = ("/tmp/", "/scratchpad/", "/.cache/", "/node_modules/")


def is_ephemeral(path: str) -> bool:
    """True for scratch/temp paths whose disappearance is expected, not a loss."""
    return any(seg in path for seg in _EPHEMERAL)
