#!/usr/bin/env python3
"""
Bash Tool Catcher - PreToolUse hook for Claude Code.

Detects Bash commands that should have used a dedicated Claude Code tool
(Read, Grep, Glob, Edit, Write), logs them, and suggests the exact
replacement tool call.

Receives JSON on stdin, outputs warnings on stdout, always exits 0 (non-blocking).
"""

import json
import re
import shlex
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path


# ── Extractors ──────────────────────────────────────────────────────────────
# Each extractor parses a matched command and returns a suggested tool call
# string. Returns None if it can't extract cleanly.


def _extract_cat(cmd: str) -> str | None:
    m = re.search(r"cat\s+([^\s|><&;]+)", cmd)
    if m:
        return f'Read(file_path="{m.group(1)}")'
    return None


def _extract_head(cmd: str) -> str | None:
    n_m = re.search(r"-n\s*(\d+)", cmd)
    f_m = re.search(r"head(?:\s+-n\s*\d+)?\s+([^\s|><&;]+)", cmd)
    if f_m:
        path = f_m.group(1)
        limit = n_m.group(1) if n_m else "50"
        return f'Read(file_path="{path}", limit={limit})'
    return None


def _extract_tail(cmd: str) -> str | None:
    n_m = re.search(r"-n\s*(\d+)", cmd)
    f_m = re.search(r"tail(?:\s+-n\s*\d+)?\s+([^\s|><&;]+)", cmd)
    if f_m:
        path = f_m.group(1)
        note = f" # use offset=(total_lines - {n_m.group(1)})" if n_m else ""
        return f'Read(file_path="{path}", offset=<N>, limit={n_m.group(1) if n_m else 20}){note}'
    return None


def _extract_grep(cmd: str) -> str | None:
    try:
        parts = shlex.split(cmd)
    except ValueError:
        parts = cmd.split()

    # Find the grep/rg invocation
    try:
        idx = next(i for i, p in enumerate(parts) if p in ("grep", "rg", "ripgrep"))
    except StopIteration:
        return None

    args = parts[idx + 1 :]
    flags: list[str] = []
    positionals: list[str] = []
    skip_next = False
    for a in args:
        if skip_next:
            skip_next = False
            continue
        if a.startswith("-"):
            if a in ("-e", "-m", "--include", "--exclude", "-A", "-B", "-C"):
                skip_next = True
            flags.append(a)
        else:
            positionals.append(a)

    pattern = positionals[0] if positionals else "<pattern>"
    path = positionals[1] if len(positionals) > 1 else "."
    case_flag = ", -i=True" if any(f in ("-i", "--ignore-case") for f in flags) else ""
    return f'Grep(pattern="{pattern}", path="{path}"{case_flag})'


def _extract_find(cmd: str) -> str | None:
    name_m = re.search(r"-name\s+['\"]?([^\s'\"]+)['\"]?", cmd)
    path_m = re.search(r"find\s+([^\s-][^\s]*)", cmd)
    if name_m:
        raw = name_m.group(1)
        # Convert shell glob to double-star glob
        glob = "**/" + raw if not raw.startswith("/") else raw
        root = path_m.group(1) if path_m else "."
        if root == ".":
            return f'Glob(pattern="{glob}")'
        return f'Glob(pattern="{glob}", path="{root}")'
    return None


def _extract_ls(cmd: str) -> str | None:
    m = re.search(r"ls(?:\s+-[^\s]*)?\s+([^\s|><&;]+)", cmd)
    if m:
        path = m.group(1).rstrip("/")
        return f'Glob(pattern="{path}/*")'
    return 'Glob(pattern="./*")'


def _extract_sed(cmd: str) -> str | None:
    # sed -i 's/old/new/' file
    m = re.search(r"s([/|#])(.+?)\1(.+?)\1", cmd)
    f_m = re.search(r"sed\s+(?:-i\s+)?'[^']+'\s+([^\s|><&;]+)", cmd)
    if m and f_m:
        old, new, path = m.group(2), m.group(3), f_m.group(1)
        return f'Edit(file_path="{path}", old_string="{old}", new_string="{new}")'
    return None


def _extract_echo_redirect(cmd: str) -> str | None:
    m = re.search(r"echo\s+(.+?)\s*>+\s*([^\s|><&;]+)", cmd)
    if m:
        content, path = m.group(1).strip("'\""), m.group(2)
        short = content[:40] + "..." if len(content) > 40 else content
        return f'Write(file_path="{path}", content="{short}")'
    return None


def _extract_awk(_cmd: str) -> str | None:
    return "Read(...) or Edit(...) depending on whether you're reading or transforming"


def _extract_printf_redirect(cmd: str) -> str | None:
    m = re.search(r"printf\s+(.+?)\s*>+\s*([^\s|><&;]+)", cmd)
    if m:
        path = m.group(2)
        return f'Write(file_path="{path}", content=<content>)'
    return None


# ── Detection rules ─────────────────────────────────────────────────────────
# Each rule: (pattern, preferred_tool, suggestion, extractor_fn)
Rule = tuple[re.Pattern, str, str, Callable[[str], str | None]]

RULES: list[Rule] = [
    (
        re.compile(r"^\s*cat\s+(?!<<)", re.MULTILINE),
        "Read",
        "Use the Read tool to read file contents",
        _extract_cat,
    ),
    (
        re.compile(r"^\s*head\s+", re.MULTILINE),
        "Read",
        "Use Read with a `limit` param instead of head",
        _extract_head,
    ),
    (
        re.compile(r"^\s*tail\s+(?!-f)", re.MULTILINE),
        "Read",
        "Use Read with `offset` + `limit` params instead of tail",
        _extract_tail,
    ),
    (
        re.compile(r"^\s*(grep|rg|ripgrep)\s+", re.MULTILINE),
        "Grep",
        "Use the Grep tool for content search",
        _extract_grep,
    ),
    (
        re.compile(r"^\s*find\s+.*-name\s+", re.MULTILINE),
        "Glob",
        "Use the Glob tool for file pattern matching",
        _extract_find,
    ),
    (
        re.compile(r"^\s*ls\s+", re.MULTILINE),
        "Glob",
        "Use Glob to list files by pattern",
        _extract_ls,
    ),
    (
        re.compile(r"^\s*sed\s+-i", re.MULTILINE),
        "Edit",
        "Use the Edit tool for in-place file edits",
        _extract_sed,
    ),
    (
        re.compile(r"echo\s+.*>+\s+\S+", re.MULTILINE),
        "Write",
        "Use the Write tool to write file contents",
        _extract_echo_redirect,
    ),
    (
        re.compile(r"^\s*awk\s+", re.MULTILINE),
        "Edit/Read",
        "Use Edit or Read instead of awk for file manipulation",
        _extract_awk,
    ),
    (
        re.compile(r"^\s*printf\s+.*>+\s+\S+", re.MULTILINE),
        "Write",
        "Use the Write tool to write file contents",
        _extract_printf_redirect,
    ),
]

# ── Exemptions ───────────────────────────────────────────────────────────────
EXEMPTIONS: list[re.Pattern] = [
    re.compile(r"tail\s+-f"),  # live log following
    re.compile(r"cat\s+<<"),  # heredoc
    re.compile(r"grep.*\|"),  # grep in a pipeline is fine
    re.compile(r"\|\s*(grep|rg)"),  # piped into grep
    re.compile(r"ls\s+-la?\s*/proc"),  # /proc filesystem inspection
    re.compile(r"find\s+/proc"),  # /proc filesystem inspection
]


def is_exempt(command: str) -> bool:
    return any(p.search(command) for p in EXEMPTIONS)


def check_violations(command: str) -> list[dict]:
    if is_exempt(command):
        return []
    violations = []
    for pattern, tool, suggestion, extractor in RULES:
        if pattern.search(command):
            match = pattern.search(command)
            snippet = command[max(0, match.start() - 5) : match.end() + 30].strip()
            snippet = snippet.replace("\n", " ")[:60]
            suggested_call = extractor(command)
            violations.append(
                {
                    "tool": tool,
                    "suggestion": suggestion,
                    "snippet": snippet,
                    "suggested_call": suggested_call,
                }
            )
    return violations


def log_violation(session_id: str, command: str, violations: list[dict]) -> None:
    log_path = Path.home() / ".local" / "share" / "claude-code" / "bash-catcher.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(UTC).isoformat(),
        "session_id": session_id,
        "command_preview": command[:200],
        "violations": violations,
    }
    with log_path.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def main() -> None:
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    tool_name = hook_input.get("tool_name", "")
    if tool_name != "Bash":
        sys.exit(0)

    tool_input = hook_input.get("tool_input", {})
    command = tool_input.get("command", "")
    session_id = hook_input.get("session_id", "unknown")

    violations = check_violations(command)
    if not violations:
        sys.exit(0)

    log_violation(session_id, command, violations)

    lines = ["[bash-catcher] Bash used where a dedicated tool would be better:"]
    for v in violations:
        lines.append(f"  • `{v['snippet']}` → use {v['tool']} tool")
        if v.get("suggested_call"):
            lines.append(f"    Suggested: {v['suggested_call']}")
    lines.append("Log: ~/.local/share/claude-code/bash-catcher.jsonl")

    print("\n".join(lines))
    sys.exit(0)


if __name__ == "__main__":
    main()
