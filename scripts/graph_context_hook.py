#!/usr/bin/env python3
"""
Graph Context Hook — inject graph awareness into agent prompts.

Runs as a UserPromptSubmit hook. Extracts keywords from the user's prompt,
queries the SurrealDB graph, and prints compact context to stdout.
Silent (zero output) when no neurons match or SurrealDB is unavailable.

Environment: $CLAUDE_USER_PROMPT contains the user's prompt text.
"""

import base64
import json
import os
import re
import sys
import urllib.request

SURREAL_URL = "http://localhost:8001/sql"
SURREAL_NS = "cohezion"
SURREAL_DB = "vault"
SURREAL_USER = "root"
SURREAL_PASS = "root"

SKIP_PATTERNS = re.compile(
    r"^(yes|no|y|n|continue|proceed|commit|push|commit and push|"
    r"/\w+.*|ok|done|stop|cancel|help|thanks|thank you|"
    r"compound it|do it|go|go ahead|lgtm|ship it|d|c|"
    r"\d+)$",
    re.IGNORECASE,
)

STOPWORDS = frozenset(
    "a an the is are was were be been being have has had do does did "
    "will would shall should may might can could of in to for on with "
    "at by from as into through during before after above below between "
    "and or but not no nor so yet both either neither each every all "
    "any few more most other some such than too very just about also "
    "back how its let me my our out own same she that their them then "
    "there these they this those up us we what when where which while "
    "who whom why you your i he him his her it we make run add fix "
    "use get set put new old can tell show look find read write edit "
    "create update delete check test pick path".split()
)


def surreal_query(sql: str) -> list | None:
    """Execute SurrealQL, return results or None on failure."""
    try:
        creds = base64.b64encode(f"{SURREAL_USER}:{SURREAL_PASS}".encode()).decode()
        req = urllib.request.Request(
            SURREAL_URL,
            data=sql.encode("utf-8"),
            headers={
                "Accept": "application/json",
                "Content-Type": "text/plain",
                "Authorization": f"Basic {creds}",
                "surreal-ns": SURREAL_NS,
                "surreal-db": SURREAL_DB,
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read())
        if isinstance(data, dict) and "code" in data:
            return None
        return data
    except Exception:
        return None


def extract_keywords(prompt: str) -> list[str]:
    """Extract candidate keywords from a user prompt."""
    clean = re.sub(r"[^\w\s-]", " ", prompt.lower())
    words = [w for w in clean.split() if w not in STOPWORDS and len(w) > 2]

    if not words:
        return []

    candidates = []

    # 3-word windows (best for multi-word note titles)
    for i in range(len(words) - 2):
        candidates.append(" ".join(words[i : i + 3]))

    # 2-word windows
    for i in range(len(words) - 1):
        candidates.append(" ".join(words[i : i + 2]))

    # Single substantial words
    for w in words:
        if len(w) > 3:
            candidates.append(w)

    return candidates[:12]


def _esc(s: str) -> str:
    return s.replace("'", "\\'")


def find_best_match(candidates: list[str]) -> dict | None:
    """Try candidates against the graph, return first match."""
    for candidate in candidates:
        sql = (
            f"SELECT id, title, activation, stage, cluster_id, aspect, "
            f"tags, synapse_out, synapse_in, path "
            f"FROM neuron "
            f"WHERE string::contains(string::lowercase(title), '{_esc(candidate)}') "
            f"ORDER BY activation DESC LIMIT 1;"
        )
        results = surreal_query(sql)
        if results and results[0].get("result"):
            return results[0]["result"][0]
    return None


def get_connections(neuron_id: str) -> tuple[list, list]:
    """Get outbound and inbound connections for a neuron."""
    sql = (
        f"SELECT out.title AS title, out.activation AS activation, "
        f"out.stage AS stage, out.cluster_id AS cluster, out.path AS path "
        f"FROM synapse WHERE in = {neuron_id} "
        f"ORDER BY out.activation DESC LIMIT 5;\n"
        f"SELECT in.title AS title, in.activation AS activation, "
        f"in.stage AS stage, in.cluster_id AS cluster, in.path AS path "
        f"FROM synapse WHERE out = {neuron_id} "
        f"ORDER BY in.activation DESC LIMIT 5;"
    )
    results = surreal_query(sql)
    if not results or len(results) < 2:
        return [], []
    return results[0].get("result", []), results[1].get("result", [])


def _act_bar(activation: float) -> str:
    filled = round(activation * 5)
    return "[" + "\u2588" * filled + "\u2591" * (5 - filled) + "]"


def format_output(neuron: dict, outbound: list, inbound: list) -> str:
    """Format compact context output."""
    act = neuron.get("activation", 0)
    title = neuron.get("title", "?")
    stage = neuron.get("stage", "?")
    cluster = neuron.get("cluster_id", "?")
    s_out = neuron.get("synapse_out", 0)
    s_in = neuron.get("synapse_in", 0)
    path = neuron.get("path", "?")
    tags = neuron.get("tags", [])

    lines = [f'--- Graph Context: "{title}" ---']
    lines.append(f"{_act_bar(act)} {act:.2f} {title} ({stage}, {cluster}, out:{s_out} in:{s_in})")
    lines.append(f"  Path: {path}")
    if tags:
        lines.append(f"  Tags: {', '.join(str(t) for t in tags[:6])}")

    for link in outbound[:5]:
        la = link.get("activation", 0)
        lines.append(f"  -> {_act_bar(la)} {la:.2f} {link.get('title', '?')} ({link.get('cluster', '?')})")

    for link in inbound[:5]:
        la = link.get("activation", 0)
        lines.append(f"  <- {_act_bar(la)} {la:.2f} {link.get('title', '?')} ({link.get('cluster', '?')})")

    # Read list: matched neuron path + top 2 connected paths by activation
    read_paths = []
    if path and path != "?":
        read_paths.append(path)
    connected = sorted(
        [l for l in (outbound + inbound) if l.get("path")],
        key=lambda l: l.get("activation", 0),
        reverse=True,
    )
    for link in connected:
        p = link.get("path", "")
        if p and p not in read_paths:
            read_paths.append(p)
        if len(read_paths) >= 3:
            break
    if read_paths:
        lines.append(f"  Read: {' | '.join(read_paths)}")

    lines.append("\u2500" * 40)
    return "\n".join(lines)


def main():
    prompt = os.environ.get("CLAUDE_USER_PROMPT", "").strip()
    if not prompt:
        return

    if SKIP_PATTERNS.match(prompt):
        return

    if len(prompt) < 8:
        return

    keywords = extract_keywords(prompt)
    if not keywords:
        return

    neuron = find_best_match(keywords)
    if not neuron:
        return

    neuron_id = str(neuron["id"])
    outbound, inbound = get_connections(neuron_id)
    print(format_output(neuron, outbound, inbound))


if __name__ == "__main__":
    main()
