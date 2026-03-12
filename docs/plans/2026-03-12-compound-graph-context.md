# Compound Graph Context Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the SurrealDB graph active — auto-inject graph context at session start (briefing) and per-prompt (hook) for ~50% token savings with better quality.

**Architecture:** Two layers that compound. Layer 1: a `briefing` command generates `metabolism/graph-briefing.md` on cron. Layer 2: a `UserPromptSubmit` hook extracts keywords and injects graph context before the agent responds. Both use existing `graph_context.py` infrastructure (query helper, formatters).

**Tech Stack:** Python 3.10+ stdlib only (urllib, json, re, sys, os, datetime). SurrealDB 3.0 on port 8001. Claude Code hooks system.

---

## Task 1: Add `cmd_briefing` to graph_context.py

**Files:**
- Modify: `scripts/graph_context.py:188-236` (add function before COMMANDS dict, register in dict)

**Step 1: Write `cmd_briefing` function**

Add this function before the `COMMANDS` dict (before line 222):

```python
def cmd_briefing(args: list[str]):
    """Generate a compact graph briefing for agent context injection."""
    from datetime import datetime, timezone

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"# Graph Briefing — {ts}\n")

    # Vitals
    stats_sql = "SELECT count() AS n FROM neuron GROUP ALL; SELECT count() AS n FROM synapse GROUP ALL;"
    stats = query(stats_sql)
    n_neurons = stats[0]["result"][0]["n"] if stats[0]["result"] else 0
    n_synapses = stats[1]["result"][0]["n"] if stats[1]["result"] else 0

    stage_sql = "SELECT stage, count() AS n FROM neuron GROUP BY stage;"
    stages = query(stage_sql)[0]["result"]
    stage_str = ", ".join(f"{s['n']} {s['stage']}" for s in stages)

    print(f"## Vitals")
    print(f"Neurons: {n_neurons} | Synapses: {n_synapses}")
    print(f"Stages: {stage_str}\n")

    # Hot neurons (top 15)
    hot_sql = "SELECT id, title, activation, stage, cluster_id, synapse_out, synapse_in FROM neuron ORDER BY activation DESC LIMIT 15;"
    hot = query(hot_sql)[0]["result"]
    print(f"## Hot Neurons (top 15)")
    for n in hot:
        print(_format_neuron_line(n))
    print()

    # Cross-domain bridges (neurons with synapses into 2+ clusters)
    bridge_sql = """
        SELECT id, title, activation, stage, cluster_id, synapse_out, synapse_in
        FROM neuron
        WHERE synapse_out > 3 AND synapse_in > 1
        ORDER BY (synapse_out + synapse_in) DESC LIMIT 10;
    """
    bridges = query(bridge_sql)[0]["result"]
    if bridges:
        print(f"## Cross-Domain Bridges (top 10 by connectivity)")
        for n in bridges:
            print(_format_neuron_line(n))
        print()

    # Attention needed
    embryo_sql = "SELECT id, title, activation FROM neuron WHERE stage = 'embryo' ORDER BY activation DESC LIMIT 5;"
    embryos = query(embryo_sql)[0]["result"]
    orphan_sql = "SELECT id, title FROM neuron WHERE synapse_out = 0 AND synapse_in = 0 LIMIT 5;"
    orphans = query(orphan_sql)[0]["result"]

    print(f"## Attention Needed")
    n_embryos = next((s["n"] for s in stages if s["stage"] == "embryo"), 0)
    print(f"- {n_embryos} embryo notes" + (f" (top: {', '.join(e['title'] for e in embryos[:3])})" if embryos else ""))
    if orphans:
        print(f"- {len(orphans)} disconnected neurons: {', '.join(o['title'] for o in orphans[:3])}")
    print()

    # Recent activity (modified in last 24h — use activation as proxy since we don't track modified_at precisely)
    recent_sql = "SELECT id, title, activation, stage, cluster_id, synapse_out, synapse_in FROM neuron WHERE activation >= 0.9 ORDER BY activation DESC LIMIT 10;"
    recent = query(recent_sql)[0]["result"]
    if recent:
        print(f"## Highest Energy")
        for n in recent:
            print(_format_neuron_line(n))
        print()
```

**Step 2: Register the command in COMMANDS dict**

Add to the COMMANDS dict (after `"r": cmd_resolve,`):

```python
    "briefing": cmd_briefing,
```

**Step 3: Update the module docstring**

Add this line to the docstring usage section:

```
    graph_context.py briefing                  # Full vault briefing for agent context
```

**Step 4: Run and verify output**

Run: `python3 scripts/graph_context.py briefing`

Expected: Markdown output with sections: Vitals, Hot Neurons (15 lines), Cross-Domain Bridges, Attention Needed, Highest Energy. Total ~40-60 lines, readable as compact markdown.

**Step 5: Generate the briefing file**

Run: `python3 scripts/graph_context.py briefing > metabolism/graph-briefing.md`

Verify: `wc -l metabolism/graph-briefing.md` → should be 40-80 lines.

**Step 6: Commit**

```bash
git add scripts/graph_context.py metabolism/graph-briefing.md
git commit -m "feat: add briefing command — pre-computed graph context for session start"
```

---

## Task 2: Create the context hook script

**Files:**
- Create: `scripts/graph_context_hook.py`

**Step 1: Write the hook script**

Create `scripts/graph_context_hook.py`:

```python
#!/usr/bin/env python3
"""
Graph Context Hook — inject graph awareness into agent prompts.

Runs as a UserPromptSubmit hook. Extracts keywords from the user's prompt,
queries the SurrealDB graph, and prints compact context to stdout.
Silent (zero output) when no neurons match or SurrealDB is unavailable.

Environment: $CLAUDE_USER_PROMPT contains the user's prompt text.
"""

import json
import os
import re
import sys
import urllib.request
import base64

SURREAL_URL = "http://localhost:8001/sql"
SURREAL_NS = "cohezion"
SURREAL_DB = "vault"
SURREAL_USER = "root"
SURREAL_PASS = "root"

# Prompts that are pure commands — never query the graph for these
SKIP_PATTERNS = re.compile(
    r"^(yes|no|y|n|continue|proceed|commit|push|commit and push|"
    r"/\w+|ok|done|stop|cancel|help|thanks|thank you|"
    r"compound it|do it|go|go ahead|lgtm|ship it)$",
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
    "who whom why you your i he him his her it we us".split()
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
    # Clean the prompt
    clean = re.sub(r"[^\w\s-]", " ", prompt.lower())
    words = [w for w in clean.split() if w not in STOPWORDS and len(w) > 2]

    if not words:
        return []

    candidates = []

    # Try 3-word windows first (best for multi-word note titles)
    for i in range(len(words) - 2):
        candidates.append(" ".join(words[i : i + 3]))

    # Then 2-word windows
    for i in range(len(words) - 1):
        candidates.append(" ".join(words[i : i + 2]))

    # Then single words (only substantial ones)
    for w in words:
        if len(w) > 3:
            candidates.append(w)

    return candidates[:12]  # Cap to avoid excessive queries


def find_best_match(candidates: list[str]) -> dict | None:
    """Try candidates against the graph, return first match."""
    for candidate in candidates:
        esc = candidate.replace("'", "\\'")
        sql = (
            f"SELECT id, title, activation, stage, cluster_id, aspect, "
            f"tags, synapse_out, synapse_in, path "
            f"FROM neuron "
            f"WHERE string::contains(string::lowercase(title), '{esc}') "
            f"ORDER BY activation DESC LIMIT 1;"
        )
        results = surreal_query(sql)
        if results and results[0].get("result"):
            return results[0]["result"][0]
    return None


def get_connections(neuron_id: str) -> tuple[list, list]:
    """Get outbound and inbound connections for a neuron."""
    out_sql = (
        f"SELECT out.title AS title, out.activation AS activation, "
        f"out.stage AS stage, out.cluster_id AS cluster "
        f"FROM synapse WHERE in = {neuron_id} "
        f"ORDER BY out.activation DESC LIMIT 5;"
    )
    in_sql = (
        f"SELECT in.title AS title, in.activation AS activation, "
        f"in.stage AS stage, in.cluster_id AS cluster "
        f"FROM synapse WHERE out = {neuron_id} "
        f"ORDER BY in.activation DESC LIMIT 5;"
    )
    # Single combined query
    combined = f"{out_sql}\n{in_sql}"
    results = surreal_query(combined)
    if not results or len(results) < 2:
        return [], []
    return results[0].get("result", []), results[1].get("result", [])


def act_bar(activation: float) -> str:
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

    lines = []
    lines.append(f"--- Graph Context: \"{title}\" ---")
    lines.append(f"{act_bar(act)} {act:.2f} {title} ({stage}, {cluster}, out:{s_out} in:{s_in})")
    lines.append(f"  Path: {path}")
    if tags:
        lines.append(f"  Tags: {', '.join(str(t) for t in tags[:6])}")

    for link in outbound[:5]:
        la = link.get("activation", 0)
        lines.append(f"  -> {act_bar(la)} {la:.2f} {link.get('title', '?')} ({link.get('cluster', '?')})")

    for link in inbound[:5]:
        la = link.get("activation", 0)
        lines.append(f"  <- {act_bar(la)} {la:.2f} {link.get('title', '?')} ({link.get('cluster', '?')})")

    lines.append(f"{'─' * 40}")
    return "\n".join(lines)


def main():
    prompt = os.environ.get("CLAUDE_USER_PROMPT", "").strip()
    if not prompt:
        return

    # Skip pure commands
    if SKIP_PATTERNS.match(prompt):
        return

    # Skip very short prompts
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

    output = format_output(neuron, outbound, inbound)
    print(output)


if __name__ == "__main__":
    main()
```

**Step 2: Make executable and test with a mock prompt**

Run:
```bash
chmod +x scripts/graph_context_hook.py
CLAUDE_USER_PROMPT="flesh out the exotic vacuum note" python3 scripts/graph_context_hook.py
```

Expected: Compact graph context output with neuron metadata and connections (or empty if "exotic vacuum" doesn't match exactly — adjust test prompt to a known neuron title).

**Step 3: Test skip behavior on command prompts**

Run:
```bash
CLAUDE_USER_PROMPT="yes" python3 scripts/graph_context_hook.py
CLAUDE_USER_PROMPT="commit and push" python3 scripts/graph_context_hook.py
CLAUDE_USER_PROMPT="continue" python3 scripts/graph_context_hook.py
```

Expected: Zero output for all three (no graph injection on pure commands).

**Step 4: Test graceful degradation (SurrealDB down)**

Run:
```bash
SURREAL_URL_BAK="$SURREAL_URL"
CLAUDE_USER_PROMPT="quantum entanglement research" python3 -c "
import scripts.graph_context_hook as h
h.SURREAL_URL = 'http://localhost:9999/sql'
h.main()
" 2>/dev/null
echo "Exit code: $?"
```

Expected: Zero output, exit code 0 (silent failure).

**Step 5: Commit**

```bash
git add scripts/graph_context_hook.py
git commit -m "feat: graph context hook — auto-inject graph awareness per prompt"
```

---

## Task 3: Register the hook in settings.json

**Files:**
- Modify: `.claude/settings.json:3-16` (add hook to UserPromptSubmit array)

**Step 1: Add the hook entry**

Add to the existing `UserPromptSubmit` hooks array (after the permission-audit hook, inside the `"hooks"` array at line 6):

```json
          {
            "type": "command",
            "command": "python3 /home/mike-anderson/vaults/cohezion-vault/scripts/graph_context_hook.py"
          }
```

**Step 2: Verify JSON is valid**

Run: `python3 -c "import json; json.load(open('.claude/settings.json'))"`

Expected: No error.

**Step 3: Commit**

```bash
git add .claude/settings.json
git commit -m "feat: register graph context hook in UserPromptSubmit"
```

---

## Task 4: Add briefing to dreaming cron

**Files:**
- Modify: `scripts/dreaming-cron.sh:53-62` (add briefing generation after dreaming engine run)

**Step 1: Add briefing generation step**

Add after the dreaming engine run block (after line 62, before the exit code check):

```bash
# ── Generate Graph Briefing ──────────────────────────────────────────────────
log "BRIEFING: Generating graph-briefing.md"
python3 "${VAULT_DIR}/scripts/graph_context.py" briefing > "${VAULT_DIR}/metabolism/graph-briefing.md" 2>> "$LOG_FILE" || log "WARN: briefing generation failed"
```

**Step 2: Verify the cron script still works**

Run: `bash -n scripts/dreaming-cron.sh` (syntax check)

Expected: No output (valid bash).

**Step 3: Commit**

```bash
git add scripts/dreaming-cron.sh
git commit -m "feat: add graph briefing generation to dreaming cron"
```

---

## Task 5: Add CLAUDE.md directive

**Files:**
- Modify: `CLAUDE.md:5-9` (Agent Orientation section)

**Step 1: Add briefing directive**

Add after the VAULT_MANIFEST.md line in Agent Orientation:

```markdown
**Graph awareness?** Read `metabolism/graph-briefing.md` for vault shape, hot neurons, bridges, and attention items (~1000 tokens, updated by cron).
```

**Step 2: Verify the file reads naturally**

Read: `head -12 CLAUDE.md`

Expected: Agent Orientation now mentions both VAULT_MANIFEST.md and graph-briefing.md.

**Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "feat: add graph briefing directive to CLAUDE.md Agent Orientation"
```

---

## Task 6: End-to-end verification

**Step 1: Generate fresh briefing**

Run: `python3 scripts/graph_context.py briefing > metabolism/graph-briefing.md`

Verify: `wc -l metabolism/graph-briefing.md` → 40-80 lines.

**Step 2: Test hook with real vault neuron**

Run:
```bash
CLAUDE_USER_PROMPT="tell me about sarfatti post-quantum mechanics" python3 scripts/graph_context_hook.py
```

Expected: Graph context output showing the Sarfatti neuron with connections.

**Step 3: Test hook silence on commands**

Run:
```bash
for prompt in "yes" "commit and push" "/learn" "continue" "D"; do
    output=$(CLAUDE_USER_PROMPT="$prompt" python3 scripts/graph_context_hook.py 2>/dev/null)
    if [ -n "$output" ]; then
        echo "FAIL: '$prompt' produced output"
    else
        echo "PASS: '$prompt' silent"
    fi
done
```

Expected: All PASS.

**Step 4: Measure token cost**

Run:
```bash
echo "=== Briefing tokens ==="
wc -c metabolism/graph-briefing.md | awk '{printf "%.0f tokens (approx)\n", $1/4}'

echo "=== Hook output tokens ==="
CLAUDE_USER_PROMPT="sarfatti post-quantum" python3 scripts/graph_context_hook.py 2>/dev/null | wc -c | awk '{printf "%.0f tokens (approx)\n", $1/4}'
```

Expected: Briefing ~800-1200 tokens, hook output ~300-500 tokens.

**Step 5: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix: end-to-end verification adjustments" # only if changes made
```
