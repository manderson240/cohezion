#!/usr/bin/env python3
"""
Autoresearch Experiment: Skill Context Density Optimization
Each run applies a set of skillOverrides, measures token savings, logs result.
"""

import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

import autoresearch_store as store  # canonical storage: SurrealDB + vault + datamesh graph


SETTINGS_PATH = Path.home() / ".claude" / "settings.json"
SKILLS_DIR = Path.home() / ".claude" / "skills"

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


def log_result(
    experiment_id: str,
    config: dict,
    metrics: dict,
    winner: bool,
    notes: str,
    derived_from: str | None = None,
) -> None:
    """Delegate persistence to the canonical store (SurrealDB + vault + datamesh graph).

    The `derived_from` arg names the prior run; the loop lineage is stored via the `references`
    graph edge (param name intentionally differs from the edge table).
    """
    store.log_result(experiment_id, config, metrics, winner, notes, derived_from=derived_from)


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
    # ── Round 8: SkillReducer Stage-2 (arXiv 2603.29919) — progressive disclosure ──
    "exp_H_skillreducer_rules_audit": {
        "description": (
            "SkillReducer Stage-2 audit: classify rules-file body as actionable "
            "(directives/commands/code) vs non-actionable (prose/rationale/examples), "
            "estimate progressive-disclosure savings. Non-destructive — measures the "
            "opportunity, does not rewrite critical files (e.g. harness.md invariants)."
        ),
        "overrides": {},
        "_skillreducer_audit": True,
    },
}


# Actionable = a line a model must ACT on (rule/command/code/path). Non-actionable = prose
# rationale/examples that SkillReducer moves to on-demand (progressive disclosure).
# Word-boundary the command keywords so they match whole commands, not prose substrings
# ("python" in "pythonic", "git" in "digital", etc.) — without \b the audit under-reports
# the non-actionable (compressible) fraction.
_ACTIONABLE_RE = re.compile(
    r"(MUST|NEVER|ALWAYS|DO NOT|DON'T|Rule:|Verification|`|^\s*[-*|]\s|"
    r"\buv run\b|\bgit\b|\bcurl\b|\bpython\b|\bexport\b|\bchmod\b|\bsudo\b|"
    r"->|::|\$\(|\bgrep\b|\bsed\b)",
    re.IGNORECASE,
)


def analyze_actionable_ratio(text: str) -> dict:
    """Estimate actionable vs non-actionable body for a rules/skill file (SkillReducer Stage-2).

    Lines inside ``` fences count as actionable (code). Of the remaining prose lines, the
    non-actionable fraction is the progressive-disclosure compression candidate.
    """
    lines = text.splitlines()
    in_fence = False
    actionable_chars = nonaction_chars = 0
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            actionable_chars += len(line)
            continue
        if in_fence or not stripped:
            actionable_chars += len(line)
            continue
        if _ACTIONABLE_RE.search(stripped):
            actionable_chars += len(line)
        else:
            nonaction_chars += len(line)
    total = actionable_chars + nonaction_chars or 1
    return {
        "actionable_tokens": actionable_chars // 4,
        "nonaction_tokens": nonaction_chars // 4,
        "nonaction_pct": round(nonaction_chars / total * 100, 1),
    }


def run_all(dry_run: bool = False):
    skill_tokens = measure_skill_tokens()
    settings = json.loads(SETTINGS_PATH.read_text())
    existing = get_existing_overrides(settings)

    total_new_overrides = {}
    cumulative_savings = 0
    prev_exp_id = None  # for the datamesh `derived_from` lineage chain

    if not dry_run:
        synced = store.sync_buffer()  # flush any offline-buffered rows first
        if synced:
            print(f"Synced {synced} buffered result(s) into SurrealDB")

    print(f"\n{'=' * 60}")
    print(f"SKILL DENSITY AUTORESEARCH — {datetime.now(UTC).date()}")
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
                derived_from=prev_exp_id,
            )
            prev_exp_id = exp_id
            print("  → INFO (audit only, no overrides applied)")
            continue

        # SkillReducer Stage-2 audit: measure actionable vs non-actionable rules body.
        if exp.get("_skillreducer_audit"):
            rules_dir = Path.home() / ".claude" / "rules"
            per_file = {}
            if rules_dir.exists():
                for f in sorted(os.listdir(rules_dir)):
                    if f.endswith(".md"):
                        per_file[f] = analyze_actionable_ratio((rules_dir / f).read_text())
            compressible = sum(v["nonaction_tokens"] for v in per_file.values())
            total_rules = sum(
                v["actionable_tokens"] + v["nonaction_tokens"] for v in per_file.values()
            )
            # Candidates: high prose-ratio files (safe to progressively disclose). Exclude
            # harness.md from auto-action — its body is dense invariants, human-gated only.
            candidates = sorted(
                (
                    (f, v["nonaction_tokens"], v["nonaction_pct"])
                    for f, v in per_file.items()
                    if v["nonaction_pct"] >= 50 and f != "harness.md"
                ),
                key=lambda x: -x[1],
            )[:6]
            print(f"\n  Experiment: {exp_id}")
            print(f"  Desc: {exp['description']}")
            print(
                f"  Rules body: {total_rules:,}t total | "
                f"~{compressible:,}t non-actionable ({round(compressible / (total_rules or 1) * 100, 1)}%)"
            )
            print("  Top progressive-disclosure candidates (prose ≥50%, excl. harness.md):")
            for f, nt, pct in candidates:
                print(f"    {nt:5,}t  {pct:4.0f}% prose  {f}")
            metrics = {
                "rules_total_tokens": total_rules,
                "nonaction_tokens": compressible,
                "nonaction_pct": round(compressible / (total_rules or 1) * 100, 1),
                "candidates": [c[0] for c in candidates],
                "tokens_saved_new": 0,  # audit: opportunity sizing, no settings change
                "routing_coverage": 1.0,
                "compound_skills_preserved": True,
            }
            log_result(
                exp_id,
                {"skillreducer_audit": True, "dry_run": dry_run},
                metrics,
                winner=False,
                notes=exp["description"],
                derived_from=prev_exp_id,
            )
            prev_exp_id = exp_id
            print("  → INFO (SkillReducer Stage-2 audit; human-gated, no edits applied)")
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
            derived_from=prev_exp_id,
        )
        prev_exp_id = exp_id

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
