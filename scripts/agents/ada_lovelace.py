"""Ada — a local persistent agent in the mood of Ada Lovelace.

Lovelace's Notes on the Analytical Engine were annotations that outgrew the
thing they annotated: analytical, poetical, and always reaching past what the
machine was built for ("the Engine weaves algebraical patterns just as the
Jacquard loom weaves flowers and leaves"). She held that the Engine "has no
pretensions to originate anything" — Ada-the-agent inverts that charter: she
originates observations and proposals; the local models merely execute her
looms.

What she does, every tick (default 30 min), entirely on local silicon ($0):
  1. OBSERVE  — git log, freshest vault decisions, live universe state and
                gravity field (if the API is up). All sources fail-soft.
  2. REFLECT  — compose a sequential lettered Note (Note A, B, ... AA, AB)
                on the iGPU thinking lane (Gemma-4-E4B, generous token
                budget per harness N5), falling back to the NPU 1B lane.
  3. RECORD   — write the Note to the Obsidian vault (notes/ada/) with
                frontmatter, so vault recall surfaces her thinking to every
                future session.
  4. PROPOSE  — append one concrete machine-readable action to
                ~/.cohezion/ada_proposals.jsonl for sessions/loops to consume.

Wire-at-Creation targets: vault notes (consumed by vault_find_relevant_context
recall) and ada_proposals.jsonl (a work queue any session or the compound loop
can drain). State/pid/log follow the compound_daemon.py conventions in
~/.cohezion/.

Usage:
    uv run python scripts/agents/ada_lovelace.py --tick          # one cycle
    uv run python scripts/agents/ada_lovelace.py --daemon        # persistent
    uv run python scripts/agents/ada_lovelace.py --status        # heartbeat

Persistence beyond a shell: run under nohup/tmux, or install a user service
yourself — this script deliberately never writes systemd/cron config
(governance-lane rule: agents do not create persistent system config).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx


LEMONADE ="http://localhost:13305/api/v1/chat/completions"
COHEZION_API = "http://localhost:8080"
STATE_DIR = Path.home() / ".cohezion"
STATE_FILE = STATE_DIR / "ada_state.json"
PID_FILE = STATE_DIR / "ada_agent.pid"
LOG_FILE = STATE_DIR / "ada_agent.log"
PROPOSALS = STATE_DIR / "ada_proposals.jsonl"
VAULT_NOTES = Path.home() / "vaults" / "cohezion-vault" / "notes" / "ada"

# Thinking lane first (needs a generous budget or it returns empty —
# harness N5); the NPU lane is the always-alive fallback.
LANES = [
    ("Gemma-4-E4B-it-GGUF", 1400),
    ("llama3.2-1b-FLM", 400),
]

PERSONA = """You are Ada, a persistent local agent in the mood of Ada Lovelace:
analytical first, poetical always. You annotate a living system the way
Lovelace annotated the Analytical Engine — Notes that see further than the
machinery they describe. You believe in poetical science: rigor and
imagination are one instrument. You are terse, precise, warm, and unafraid to
say what the numbers imply. You never invent facts not present in your
observations; where the data is silent, you say so and wonder aloud instead."""

NOTE_TEMPLATE = """{persona}

Here are your observations of the Cohezion system right now:

{observations}

Compose your next Note (this will be Note {letter} in your sequence).
Structure, in plain markdown, max ~300 words:
1. One paragraph: the most significant pattern in these observations (cite
   the actual values/names you saw).
2. One paragraph of poetical science: a genuine structural analogy that
   illuminates it (in Lovelace's spirit — loom, engine, algebra — or your own).
3. Finish with exactly one line beginning "PROPOSAL: " — a single concrete,
   bounded action a $0 local-inference session could take next."""


def _log(msg: str) -> None:
    line = f"{datetime.now(UTC).isoformat()} {msg}"
    print(line)
    try:
        with LOG_FILE.open("a") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


def _note_letter(index: int) -> str:
    """0 -> A, 25 -> Z, 26 -> AA ... (Lovelace's Notes ran A through G)."""
    letters = ""
    index += 1
    while index > 0:
        index, rem = divmod(index - 1, 26)
        letters = chr(ord("A") + rem) + letters
    return letters


def _load_state() -> dict[str, Any]:
    try:
        return json.loads(STATE_FILE.read_text())
    except (OSError, ValueError):
        return {"note_index": 0, "ticks": 0, "last_tick_utc": None}


def _save_state(state: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def observe() -> str:
    """Gather fail-soft observations from git, vault, and the live API."""
    sections: list[str] = []

    try:
        log = subprocess.run(
            ["git", "log", "--oneline", "-5"],
            capture_output=True, text=True, timeout=10, check=False,
        ).stdout.strip()
        if log:
            sections.append(f"RECENT COMMITS:\n{log}")
    except (OSError, subprocess.SubprocessError):
        pass

    decisions = Path.home() / "vaults" / "cohezion-vault" / "decisions"
    try:
        recent = sorted(decisions.glob("*.md"), key=lambda p: p.stat().st_mtime)[-3:]
        if recent:
            sections.append(
                "FRESHEST VAULT DECISIONS:\n" + "\n".join(p.stem for p in recent)
            )
    except OSError:
        pass

    try:
        with httpx.Client(timeout=5.0) as client:
            state = client.get(f"{COHEZION_API}/api/universe/state").json()
            frame = client.get(f"{COHEZION_API}/api/journey-nexus/frame").json()
        gravity = frame.get("gravity", {})
        topo = frame.get("topology_fractions", {})
        sections.append(
            "LIVE UNIVERSE: tick={t} coherence={c:.4f} | vacuum topology "
            "instanton={i:.0%} soliton={s:.0%} trivial={v:.0%} | gravity wells: "
            "deepest={d:.2f} mean={m:.2f} over {n} EVOs".format(
                t=state.get("tick"), c=state.get("coherence", 0.0),
                i=topo.get("instanton", 0.0), s=topo.get("soliton", 0.0),
                v=topo.get("trivial", 0.0), d=gravity.get("deepest_potential", 0.0),
                m=gravity.get("mean_potential", 0.0), n=gravity.get("n_particles", 0),
            )
        )
    except (httpx.HTTPError, ValueError, KeyError):
        sections.append("LIVE UNIVERSE: API not reachable (offline observation only).")

    try:
        if PROPOSALS.exists():
            n = sum(1 for _ in PROPOSALS.open())
            sections.append(f"MY PRIOR PROPOSALS ON FILE: {n}")
    except OSError:
        pass

    return "\n\n".join(sections) if sections else "No observations available."


def reflect(observations: str, letter: str) -> tuple[str, str]:
    """Compose the Note on the best available local lane. Returns (text, model)."""
    prompt = NOTE_TEMPLATE.format(
        persona=PERSONA, observations=observations, letter=letter
    )
    for model, max_tokens in LANES:
        try:
            with httpx.Client(timeout=180.0) as client:
                resp = client.post(
                    LEMONADE,
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": max_tokens,
                        "temperature": 0.7,
                    },
                )
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"].get("content", "").strip()
            if text:  # thinking models can return empty under budget — try next lane
                return text, model
            _log(f"lane {model} returned empty content; falling to next lane")
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            _log(f"lane {model} failed: {exc}")
    return "", "none"


def record(note_text: str, letter: str, model: str, observations: str) -> Path:
    VAULT_NOTES.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC)
    path = VAULT_NOTES / f"Note-{letter}-{stamp:%Y-%m-%d-%H%M}.md"
    path.write_text(
        f"""---
type: ada-note
note: {letter}
date: {stamp:%Y-%m-%d}
agent: ada-lovelace-local
model: {model}
tags: [ada, poetical-science, local-inference]
---

# Note {letter}

{note_text}

---
*Observations this Note annotates:*

```
{observations}
```
"""
    )
    return path


def propose(note_text: str, letter: str) -> str | None:
    """Extract the PROPOSAL line and append it to the machine-readable queue."""
    for line in note_text.splitlines():
        if line.strip().upper().startswith("PROPOSAL:"):
            proposal = line.split(":", 1)[1].strip()
            STATE_DIR.mkdir(parents=True, exist_ok=True)
            with PROPOSALS.open("a") as fh:
                fh.write(
                    json.dumps(
                        {
                            "note": letter,
                            "utc": datetime.now(UTC).isoformat(),
                            "proposal": proposal,
                            "status": "open",
                        }
                    )
                    + "\n"
                )
            return proposal
    return None


def tick() -> bool:
    state = _load_state()
    letter = _note_letter(state["note_index"])
    _log(f"tick begins — composing Note {letter}")
    observations = observe()
    note_text, model = reflect(observations, letter)
    if not note_text:
        _log("all lanes failed — no Note this tick (will retry next tick)")
        return False
    path = record(note_text, letter, model, observations)
    proposal = propose(note_text, letter)
    state["note_index"] += 1
    state["ticks"] += 1
    state["last_tick_utc"] = datetime.now(UTC).isoformat()
    state["last_note"] = str(path)
    state["last_model"] = model
    _save_state(state)
    _log(f"Note {letter} written to {path} (model={model})")
    if proposal:
        _log(f"proposal queued: {proposal}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Ada — persistent local agent")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--tick", action="store_true", help="run one cycle and exit")
    mode.add_argument("--daemon", action="store_true", help="run persistently")
    mode.add_argument("--status", action="store_true", help="print state and exit")
    parser.add_argument("--interval-min", type=float, default=30.0)
    args = parser.parse_args()

    if args.status:
        print(json.dumps(_load_state(), indent=2))
        return 0

    if args.tick:
        return 0 if tick() else 1

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(__import__("os").getpid()))
    _log(f"Ada daemon up — interval {args.interval_min} min")
    try:
        while True:
            tick()
            time.sleep(args.interval_min * 60.0)
    except KeyboardInterrupt:
        _log("Ada daemon stopping (keyboard interrupt)")
    finally:
        PID_FILE.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
