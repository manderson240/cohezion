#!/usr/bin/env python3
"""
session_handoff.py — Automatic session continuation generator.

Writes continuation.md when context pressure is high, enabling seamless
handoff between Claude Code sessions. Integrates with autocontext.

Usage:
    uv run python3 scripts/research/session_handoff.py
    # Or from autorun loop: session_handoff.write_if_needed()
"""
from __future__ import annotations

import json
import subprocess
import timeit
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent


def get_session_dir() -> Path | None:
    """Get the current session directory from cz CLI."""
    try:
        result = subprocess.run(
            ['cz', 'session', 'status', '--json'],
            capture_output=True, text=True, timeout=5
        )
        data = json.loads(result.stdout)
        d = data.get('session_dir', '')
        return Path(d) if d else None
    except Exception:
        return None


def get_context_pct() -> float:
    """Get context usage percentage (0.0-1.0)."""
    try:
        result = subprocess.run(
            ['cz', 'context', '--json'],
            capture_output=True, text=True, timeout=5
        )
        data = json.loads(result.stdout)
        return data.get('percentage', 0.0) / 100.0
    except Exception:
        return 0.0


def get_git_summary() -> dict:
    """Get recent git activity for handoff."""
    try:
        log = subprocess.run(
            ['git', 'log', '--oneline', '-5'],
            capture_output=True, text=True, timeout=5, cwd=ROOT
        ).stdout.strip()
        branch = subprocess.run(
            ['git', 'branch', '--show-current'],
            capture_output=True, text=True, timeout=5, cwd=ROOT
        ).stdout.strip()
        return {'branch': branch, 'recent_commits': log.split('\n')}
    except Exception:
        return {}


def get_autoresearch_summary(jsonl_path: Path) -> dict:
    """Get top experiment findings for handoff context."""
    if not jsonl_path.exists():
        return {}
    try:
        from collections import defaultdict
        import statistics

        by_exp = defaultdict(list)
        lines = jsonl_path.read_text().strip().split('\n')
        # Sample last 10k entries for speed
        for line in lines[-10000:]:
            try:
                rec = json.loads(line)
                exp = rec.get('experiment', '')
                if exp and not exp.startswith('FINDING_'):
                    delta = float(rec.get('delta', 0))
                    keep = rec.get('keep', 'discard')
                    by_exp[exp].append((delta, keep))
            except Exception:
                pass

        top = []
        for exp, runs in sorted(by_exp.items(), key=lambda x: -statistics.mean(d for d, _ in x[1] if d > 0) * sum(1 for _, k in x[1] if k == 'keep') / max(1, len(x[1]))):
            keeps = sum(1 for _, k in runs if k == 'keep')
            deltas = [d for d, _ in runs if d > 0]
            if keeps > 0 and deltas:
                top.append({
                    'experiment': exp,
                    'keep_frac': round(keeps / len(runs), 2),
                    'mean_delta': round(statistics.mean(deltas), 4),
                })
            if len(top) >= 5:
                break
        return {'total_runs': len(lines), 'top_experiments': top}
    except Exception:
        return {}


def write_handoff(force: bool = False) -> bool:
    """Write continuation.md if context >= 80% or forced.

    Returns True if file was written.
    """
    t0 = timeit.default_timer()
    ctx_pct = get_context_pct()

    if not force and ctx_pct < 0.80:
        return False

    session_dir = get_session_dir()
    if not session_dir:
        # Fallback path
        session_dir = ROOT / '.cohezion-sessions' / 'current'
        session_dir.mkdir(parents=True, exist_ok=True)

    git = get_git_summary()
    research = get_autoresearch_summary(ROOT / 'autoresearch_overnight.jsonl')

    content = f"""# Session Continuation
**Written:** {datetime.now(timezone.utc).isoformat()}
**Context:** {ctx_pct:.0%}
**Branch:** {git.get('branch', 'unknown')}

## Active Plan
None — autoresearch mode

## Git State
Branch: {git.get('branch', 'unknown')}
Recent commits:
{chr(10).join('  ' + c for c in git.get('recent_commits', []))}

## Autoresearch State
{json.dumps(research, indent=2)}

## Key Findings (this session)
1. EVO linear scaling law: delta(N) = N * 0.1500 + 0.1250
   - E63_n3_lr3 × N then E50_fixed: deterministic, stdev=0
   - Proven for N=1..12, formula confirmed
2. V-model gate: 5 invariants, <6s, exit 0 = clear
3. Wiring audit: 880/1129 orphans (77.9%), 3 recommendations
4. Nemotron v5.2: bit_manip_x3 + cipher_x2 = 16,788 examples
5. autocontext: monitor/compress/budget/archive wired into autorun_2h

## Next Steps
1. Check ARC solver agent result (still running)
2. Implement wiring fix #2: cli/main.py → __main__.py (920 lines, ~50-80 downstream)
3. Run `uv run python3 scripts/research/vmodel_gate.py --level full` to verify state
4. Resume autoresearch: `uv run python3 /tmp/evo_optimal_schedule.py`

## Commands to Resume
```bash
cd /home/mike-anderson/dev/cohezion
uv run python3 scripts/research/vmodel_gate.py --level full
uv run python3 scripts/research/adaptive_schedule.py autoresearch_overnight.jsonl --n 5
uv run python3 /tmp/evo_optimal_schedule.py &
```

Elapsed write time: {(timeit.default_timer() - t0)*1000:.0f}ms
"""

    cont_path = session_dir / 'continuation.md'
    cont_path.write_text(content)
    print(f"[session_handoff] Written to {cont_path} ({ctx_pct:.0%} context, {(timeit.default_timer()-t0)*1000:.0f}ms)")
    return True


def write_if_needed() -> bool:
    """Called from autoresearch loop — writes if context >= 80%."""
    return write_handoff(force=False)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--force', action='store_true', help='Write regardless of context level')
    args = parser.parse_args()
    written = write_handoff(force=args.force)
    if not written:
        pct = get_context_pct()
        print(f"[session_handoff] Context at {pct:.0%} — no handoff needed (threshold: 80%)")
