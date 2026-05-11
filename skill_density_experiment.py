#!/usr/bin/env python3
"""
Autoresearch Experiment: Skill Context Density Optimization
Each run applies a set of skillOverrides, measures token savings, logs result.
"""

import json, os, sys
from datetime import datetime, timezone
from pathlib import Path

SETTINGS_PATH = Path.home() / ".claude" / "settings.json"
SKILLS_DIR = Path.home() / ".claude" / "skills"
JSONL_PATH = Path(__file__).parent / "autoresearch.jsonl"

# Skills that must NEVER be overridden — core compound engineering
PROTECTED = {"autoresearch", "autoresearch-team", "cohezion-dynamic-modularity"}

# Skills that define routing coverage — model needs these at full context to suggest them
CORE_ROUTING = {
    "autoresearch",
    "autoresearch-team",
    "cohezion-dynamic-modularity",
    "find-skills",
    "claude-code-agent-teams",
    "multi-agent-isolated-worktree-pattern",
    "autoharness-skill",
    "autoharness-init",
    "autoharness-update",
    "spec",
    "learn",
    "sync",  # global commands loaded elsewhere
}


# Skills already overridden (don't touch, additive-only rule)
def get_existing_overrides(settings: dict) -> dict:
    return dict(settings.get("skillOverrides", {}))


def measure_skill_tokens() -> dict[str, int]:
    """Measure token cost of each skill in ~/.claude/skills/"""
    result = {}
    for entry in SKILLS_DIR.iterdir():
        skill_md = entry / "SKILL.md"
        if skill_md.exists():
            content = skill_md.read_text()
            result[entry.name] = len(content) // 4
    return result


def compute_savings(skill_tokens: dict, existing: dict, new_overrides: dict) -> dict:
    """Compute token savings from applying new_overrides on top of existing."""
    total_tokens = sum(skill_tokens.values())

    # Tokens saved by existing overrides (user-invocable-only = 100%, name-only = 95%)
    existing_saved = sum(
        skill_tokens.get(name, 0) * (1.0 if mode == "user-invocable-only" else 0.95)
        for name, mode in existing.items()
    )

    # Tokens saved by new overrides
    new_saved = sum(
        skill_tokens.get(name, 0) * (1.0 if mode == "user-invocable-only" else 0.95)
        for name, mode in new_overrides.items()
        if name not in existing
    )

    unoptimized_before = total_tokens - int(existing_saved)
    unoptimized_after = total_tokens - int(existing_saved) - int(new_saved)

    return {
        "total_skill_tokens": total_tokens,
        "tokens_saved_existing": int(existing_saved),
        "tokens_saved_new": int(new_saved),
        "tokens_still_loading_before": unoptimized_before,
        "tokens_still_loading_after": unoptimized_after,
        "savings_pct": round(new_saved / unoptimized_before * 100, 1)
        if unoptimized_before > 0
        else 0,
    }


def routing_coverage(skill_tokens: dict, existing: dict, new_overrides: dict) -> float:
    """
    Fraction of CORE_ROUTING skills still fully visible (not overridden at all).
    1.0 = all core routing skills remain at full context.
    This is the metric that matters — we don't care about AMD kernel skills disappearing.
    """
    all_overrides = {**existing, **new_overrides}
    core_present = {k for k in CORE_ROUTING if k in skill_tokens}
    if not core_present:
        return 1.0
    visible_core = sum(1 for k in core_present if k not in all_overrides)
    return round(visible_core / len(core_present), 3)


def apply_overrides(settings: dict, new_overrides: dict) -> None:
    """Apply new_overrides to settings (additive, never removes)."""
    if "skillOverrides" not in settings:
        settings["skillOverrides"] = {}
    for k, v in new_overrides.items():
        if k not in settings["skillOverrides"]:
            settings["skillOverrides"][k] = v


def log_result(experiment_id: str, config: dict, metrics: dict, winner: bool, notes: str) -> None:
    if config.get("dry_run"):
        return  # never log dry-run results
    # Deduplicate: skip if same experiment_id already logged as winner
    if JSONL_PATH.exists():
        existing = [json.loads(l) for l in JSONL_PATH.read_text().splitlines() if l.strip()]
        if any(e["experiment_id"] == experiment_id and e["winner"] for e in existing):
            return
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "experiment_id": experiment_id,
        "config": config,
        "metrics": metrics,
        "winner": winner,
        "notes": notes,
    }
    with open(JSONL_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
    print(
        f"  Logged: {experiment_id} | winner={winner} | saved={metrics.get('tokens_saved_new', 0):,}t"
    )


# ─── Experiment Definitions ───────────────────────────────────────────────────

EXPERIMENTS = {
    "exp_A_situational_name_only": {
        "description": "Apply name-only to clearly situational skills (fix-specific, rarely proactive)",
        "overrides": {
            # Fix-specific: user reaches for these when something breaks, not proactively
            "linux-electron-oauth-deeplink-fix": "name-only",
            "electron-appimage-erofs-fix": "name-only",
            "uv-sync-extra-vs-group": "name-only",
            "worktree-sparse-checkout-workflow-edit": "name-only",
            "git-pr-branch-from-origin-main": "name-only",
            "xfail-strict-bug-bridge-pattern": "name-only",
            "close-deferral": "name-only",
            # Campaign skills: only triggered by user intent
            "ci-green-ruff-fractal-campaign": "name-only",
            "stacked-branch-cherry-pick-cascade": "name-only",
            # Context-specific: only useful for specific hardware/infra sessions
            "check-git-log-before-low-level-unlock": "name-only",
            "surrealdb-http-direct-ingest": "name-only",
            "service-port-registry": "name-only",
            # Session-specific: agent campaigns only
            "agent-claim-verification": "name-only",
        },
    },
    "exp_B_reference_user_invocable": {
        "description": "Hide pure reference skills entirely (users type them directly, model never suggests)",
        "overrides": {
            "mcp-cli-reference": "user-invocable-only",
            "vexor-search-reference": "user-invocable-only",
            "memory-reference": "user-invocable-only",
            "team-vault-reference": "user-invocable-only",
            "gh-cli-reference": "user-invocable-only",
            "large-commit-protocol-reference": "user-invocable-only",
            "web-search-reference": "user-invocable-only",
            "grep-mcp-reference": "user-invocable-only",
            "playwright-cli-reference": "user-invocable-only",
        },
    },
    "exp_C_kaggle_when_inactive": {
        "description": "Set kaggle to name-only during non-competition work (Kaggle deadline May-Nov)",
        "overrides": {
            "kaggle": "name-only",
        },
    },
    "exp_D_heavy_utility_name_only": {
        "description": "Heavy utility skills (polish-campaign, dynamic-template) to name-only — rarely proactive",
        "overrides": {
            "polish-campaign-orchestrator": "name-only",
            "dynamic-template-generator": "name-only",
        },
    },
    # ── Round 2: borderline utility skills ──────────────────────────────────
    "exp_E_meta_reference_name_only": {
        "description": "Token optimization reference skill → name-only (meta/reference, user reaches for it by name)",
        "overrides": {
            "claude-code-token-optimization": "name-only",
        },
    },
    "exp_F_pattern_guide_name_only": {
        "description": "multi-agent-isolated-worktree-pattern → name-only (pattern reference, not proactively suggested mid-session)",
        "overrides": {
            "multi-agent-isolated-worktree-pattern": "name-only",
        },
    },
    # ── Round 3: CLAUDE.md + rules token audit (new dimension) ──────────────
    "exp_G_rules_token_audit": {
        "description": "Audit ~/.claude/rules/*.md token cost — informational only, no settings change",
        "overrides": {},  # no overrides; metrics will show opportunity size
        "_audit_only": True,
    },
}


def run_all(dry_run: bool = False):
    skill_tokens = measure_skill_tokens()
    settings = json.loads(SETTINGS_PATH.read_text())
    existing = get_existing_overrides(settings)

    total_new_overrides = {}
    cumulative_savings = 0

    print(f"\n{'=' * 60}")
    print(f"SKILL DENSITY AUTORESEARCH — {datetime.now(timezone.utc).date()}")
    print(f"{'=' * 60}")
    print(f"Total skills: {len(skill_tokens)}, baseline tokens: {sum(skill_tokens.values()):,}")
    print(f"Already overridden: {len(existing)}")
    print()

    for exp_id, exp in EXPERIMENTS.items():
        # Audit-only experiments: no overrides, just measure and log
        if exp.get("_audit_only"):
            rules_dir = Path.home() / ".claude" / "rules"
            rules_tokens = (
                {
                    f: len((rules_dir / f).read_text()) // 4
                    for f in sorted(os.listdir(rules_dir))
                    if f.endswith(".md")
                }
                if rules_dir.exists()
                else {}
            )
            total_rules = sum(rules_tokens.values())
            print(f"\n  Experiment: {exp_id}")
            print(f"  Desc: {exp['description']}")
            print(f"  Rules files: {len(rules_tokens)}, total tokens: ~{total_rules:,}t")
            for fname, t in sorted(rules_tokens.items(), key=lambda x: -x[1])[:8]:
                print(f"    {t:5,}t  {fname}")
            metrics = {
                "rules_total_tokens": total_rules,
                "rules_count": len(rules_tokens),
                "tokens_saved_new": 0,
                "routing_coverage": 1.0,
                "compound_skills_preserved": True,
            }
            log_result(
                exp_id,
                {"audit_only": True, "dry_run": dry_run},
                metrics,
                winner=False,
                notes=exp["description"],
            )
            print("  → INFO (audit only, no overrides applied)")
            continue

        overrides = {k: v for k, v in exp["overrides"].items() if k not in PROTECTED}
        new = {k: v for k, v in overrides.items() if k not in existing}

        if not new:
            print(f"  {exp_id}: SKIP (all already applied)")
            continue

        metrics = compute_savings(skill_tokens, existing, new)
        metrics["routing_coverage"] = routing_coverage(skill_tokens, existing, new)
        metrics["compound_skills_preserved"] = all(p not in new for p in PROTECTED)

        is_winner = (
            metrics["tokens_saved_new"] > 0
            and metrics["routing_coverage"] >= 0.85
            and metrics["compound_skills_preserved"]
        )

        print(f"\n  Experiment: {exp_id}")
        print(f"  Desc: {exp['description']}")
        print(f"  New overrides: {list(new.keys())}")
        print(
            f"  Tokens saved: {metrics['tokens_saved_new']:,}t ({metrics['savings_pct']}% of remaining)"
        )
        print(f"  Routing coverage: {metrics['routing_coverage']:.1%}")
        print(f"  Compound skills preserved: {metrics['compound_skills_preserved']}")
        print(f"  → {'WINNER ✓' if is_winner else 'SKIP ✗'}")

        log_result(
            exp_id,
            {"overrides": new, "dry_run": dry_run},
            metrics,
            winner=is_winner,
            notes=exp["description"],
        )

        if is_winner and not dry_run:
            apply_overrides(settings, new)
            total_new_overrides.update(new)
            cumulative_savings += metrics["tokens_saved_new"]
            print("  Applied to settings ✓")

    if not dry_run and total_new_overrides:
        # Validate JSON before writing
        json.dumps(settings)  # raises if invalid
        SETTINGS_PATH.write_text(json.dumps(settings, indent=2))
        print(f"\n{'=' * 60}")
        print(f"SETTINGS UPDATED: {len(total_new_overrides)} new overrides applied")
        print(f"Total additional tokens saved: ~{cumulative_savings:,}t/turn")
        print(f"{'=' * 60}")
    elif dry_run:
        print("\n[DRY RUN — no settings written]")
    else:
        print("\nNo winners found — settings unchanged")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    run_all(dry_run=dry_run)
