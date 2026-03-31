"""
Hookify Obsidian Vault Integration
Write decisions, violations, and learning artifacts to the vault graph
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


logger = logging.getLogger(__name__)


class HookifyVaultWriter:
    """
    Write Hookify artifacts to Obsidian vault with graph semantics

    Leverages vault architecture:
    - cortex/: Rule definitions and theory
    - prefrontal/: Decision records
    - hippocampus/: Session logs and violations
    - cerebellum/: Pattern templates and skills
    """

    def __init__(self, vault_path: Path):
        self.vault_path = vault_path

    def write_rule_violation(
        self,
        rule_id: str,
        session_id: str,
        context: dict[str, Any],
        violation: dict[str, Any],
        timestamp: str | None = None,
    ) -> Path:
        """
        Write violation to hippocampus (session memory)

        Returns path to created note
        """
        if timestamp is None:
            timestamp = datetime.now().isoformat()

        # Create violation note
        filename = f"violation_{rule_id}_{session_id}_{timestamp[:10]}.md"
        filepath = self.vault_path / "hippocampus" / "hookify-violations" / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # Frontmatter
        frontmatter = {
            "title": f"Hookify Violation: {rule_id}",
            "date": timestamp,
            "tags": ["hookify", "violation", rule_id, f"session-{session_id}"],
            "aspect": "knower",
            "neural": {
                "activation": context.get("coherence", 0.0),
                "stage": "violation",
                "synapse_in": 1,
                "synapse_out": 0,
            },
        }

        # Content
        content = f"""---
{yaml.dump(frontmatter, default_flow_style=False)}---

# Violation: {rule_id}

**Session**: {session_id}  
**Timestamp**: {timestamp}  
**Coherence**: {context.get("coherence", "N/A")}

## Violation Details

{violation.get("message", "No message")}

**Severity**: {violation.get("severity", "warning")}

## Context

```json
{json.dumps(context, indent=2)}
```

## Resolution

- [ ] Address root cause
- [ ] Adjust lever if needed
- [ ] Update rule if pattern persists

## Related

- [[prefrontal/hookify-decisions/{rule_id}_lever-adjustments.md|Lever Adjustments]]
- [[cerebellum/skills/hookify-troubleshooting.md|Troubleshooting Guide]]
"""

        filepath.write_text(content)
        logger.info(f"Wrote violation to {filepath}")

        return filepath

    def write_lever_decision(
        self,
        rule_id: str,
        lever_name: str,
        previous_value: Any,
        new_value: Any,
        rationale: str,
        timestamp: str | None = None,
    ) -> Path:
        """
        Write lever change decision to prefrontal (decision records)

        Returns path to created note
        """
        if timestamp is None:
            timestamp = datetime.now().isoformat()

        filename = f"{rule_id}_{lever_name}_{timestamp[:10]}.md"
        filepath = self.vault_path / "prefrontal" / "hookify-decisions" / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)

        frontmatter = {
            "title": f"Lever Change: {rule_id}.{lever_name}",
            "date": timestamp,
            "tags": ["hookify", "decision", "lever-change", rule_id],
            "aspect": "prefrontal",
            "decision": {
                "type": "lever_adjustment",
                "rule": rule_id,
                "lever": lever_name,
                "previous": previous_value,
                "new": new_value,
            },
        }

        content = f"""---
{yaml.dump(frontmatter, default_flow_style=False)}---

# Decision: Adjust {rule_id}.{lever_name}

**Date**: {timestamp}  
**Type**: Lever Adjustment  
**Status**: Committed

## Change Summary

| Property | Before | After |
|----------|--------|-------|
| {lever_name} | `{previous_value}` | `{new_value}` |

## Rationale

{rationale}

## Impact Analysis

### Coherence
- Expected impact on HIHO stability
- Affected triggers: {rule_id}

### Risk
- [ ] Low (cosmetic)
- [ ] Medium (behavioral)
- [ ] High (architectural)

## Rollback Plan

If this change causes issues:
1. Revert lever to `{previous_value}`
2. Re-run affected sessions
3. Clear violation cache

## References

- [[cortex/FLUME-Architecture.md|FLUME Architecture]]
- [[cerebellum/skills/HOOKIFY_PRIME.md|Hookify Skill]]
"""

        filepath.write_text(content)
        logger.info(f"Wrote decision to {filepath}")

        return filepath

    def write_rule_learning_summary(
        self, rule_id: str, period: str, statistics: dict[str, Any], recommendations: list[str]
    ) -> Path:
        """
        Write recursive learning summary to cerebellum (patterns)

        Returns path to created note
        """
        timestamp = datetime.now().isoformat()
        filename = f"{rule_id}_learning_{period}.md"
        filepath = self.vault_path / "cerebellum" / "hookify-patterns" / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)

        frontmatter = {
            "title": f"Learning Summary: {rule_id} ({period})",
            "date": timestamp,
            "tags": ["hookify", "learning", "pattern", rule_id],
            "aspect": "cerebellum",
            "stats": statistics,
        }

        recs = "\n".join(f"- {r}" for r in recommendations)

        content = f"""---
{yaml.dump(frontmatter, default_flow_style=False)}---

# Learning Summary: {rule_id}

**Period**: {period}  
**Generated**: {timestamp}

## Statistics

```json
{json.dumps(statistics, indent=2)}
```

## Patterns Identified

### High-Violation Triggers
- Which triggers cause most violations
- Time-of-day patterns
- Context patterns

### Coherence Distribution
- Mean: {statistics.get("mean_coherence", "N/A")}
- Median: {statistics.get("median_coherence", "N/A")}
- Std Dev: {statistics.get("std_coherence", "N/A")}

## Recommendations

{recs}

## Rule Evolution

This learning should inform:
1. Default lever adjustments
2. Condition refinements
3. Adversarial test additions
4. Documentation updates

## Next Review

- [ ] Schedule follow-up in 1 week
- [ ] Track recommendation effectiveness
- [ ] Update HOOKIFY_RULES.md if patterns solidify
"""

        filepath.write_text(content)
        logger.info(f"Wrote learning summary to {filepath}")

        return filepath

    def write_cosmological_changelog(
        self,
        session_id: str,
        iterations: list[dict[str, Any]],
        final_coherence: float,
        accuracy: float,
    ) -> Path:
        """
        Write Ralph Loop cosmological changelog to hippocampus

        Mirrors Anthropic's CHANGELOG.md pattern
        Returns path to created note
        """
        timestamp = datetime.now().isoformat()
        filename = f"changelog_{session_id}_{timestamp[:10]}.md"
        filepath = self.vault_path / "hippocampus" / "cosmological-logs" / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # Build iteration table
        iter_rows = []
        for i, it in enumerate(iterations):
            status = "✓" if it.get("coherence", 0) >= 0.5 else "✗"
            iter_rows.append(
                f"| {i + 1} | {it.get('coherence', 'N/A'):.4f} | {it.get('accuracy', 'N/A'):.4f} | "
                f"{it.get('error', 'N/A'):.6f} | {status} |"
            )

        iter_table = "\n".join(iter_rows)

        frontmatter = {
            "title": f"Cosmological Changelog: {session_id}",
            "date": timestamp,
            "tags": ["cosmology", "ralph-loop", "changelog", session_id],
            "aspect": "hippocampus",
            "cosmology": {
                "final_coherence": final_coherence,
                "final_accuracy": accuracy,
                "iterations": len(iterations),
                "converged": final_coherence >= 0.5,
            },
        }

        content = f"""---
{yaml.dump(frontmatter, default_flow_style=False)}---

# Cosmological Changelog: {session_id}

**Session**: {session_id}  
**Date**: {timestamp}  
**Status**: {"✓ Converged" if final_coherence >= 0.5 else "✗ Not Converged"}

## Summary

Final coherence: **{final_coherence:.4f}** (target: 0.5000)  
Final accuracy: **{accuracy:.4f}%** (target: 0.1000%)

## Iteration Log

| # | Coherence | Accuracy | Error | HIHO |
|---|-----------|----------|-------|------|
{iter_table}

## Failed Approaches

*Document what didn't work and why*

- [ ] Approach 1: Description
- [ ] Approach 2: Description

## Breakthrough Moments

*When coherence crossed HIHO threshold*

- Iteration {next((i + 1 for i, it in enumerate(iterations) if it.get("coherence", 0) >= 0.5), "N/A")}: 
  Coherence reached HIHO (0.5)

## Test Results

### Cosmological Test Suite
- [ ] 1% accuracy achieved
- [ ] 0.5% accuracy achieved
- [ ] 0.2% accuracy achieved
- [ ] 0.1% accuracy achieved ✓

### Multi-Cosmology Validation
- [ ] Cosmology 1: Lambda CDM
- [ ] Cosmology 2: wCDM
- [ ] Cosmology 3: Neutrino mass

## Git Commits

*Auto-generated from Ralph Loop auto_commit lever*

```bash
# git log --oneline for this session
```

## Witness Plate

This changelog serves as the **permanent witness** of this cosmological computation.

- [[cortex/theory-of-everything-synthesis.md|TOE Framework]]
- [[cerebellum/skills/HOOKIFY_PRIME.md|Hookify Skill]]
- [[cerebellum/runbook-benchmarking-validation.md|Validation Runbook]]
"""

        filepath.write_text(content)
        logger.info(f"Wrote cosmological changelog to {filepath}")

        return filepath

    def write_session_learning(
        self,
        session_id: str,
        learning_title: str,
        learning_content: str,
        tags: list[str] | None = None,
        learning_number: int = 0,
    ) -> dict[str, Any]:
        """Orchestrate full learning persistence: vault + SurrealDB + KEY_LEARNINGS.

        This is the single entry point for all knowledge capture. It calls
        knowledge_bridge.persist_learning() for the 3-layer write, then writes
        a Hookify learning summary to cerebellum/hookify-patterns/.

        Returns dict with paths/status for each persistence layer.
        """
        from cohezion.governance.knowledge_bridge import Learning, persist_learning

        learning = Learning(
            number=learning_number,
            title=learning_title,
            content=learning_content,
            date=datetime.now().strftime("%Y-%m-%d"),
            tags=tags or ["session", "learning"],
            propagate_to="Compound engineering patterns",
        )

        # 3-layer persistence via knowledge_bridge
        bridge_result = persist_learning(learning)

        # Also write Hookify-formatted summary to cerebellum/hookify-patterns/
        try:
            self.write_rule_learning_summary(
                rule_id="knowledge_persist",
                period=f"session-{session_id}",
                statistics={
                    "vault_written": bool(bridge_result.get("vault")),
                    "surrealdb_written": bridge_result.get("surrealdb", False),
                    "learning_number": learning_number,
                },
                recommendations=[f"Learning: {learning_title}"],
            )
        except Exception as e:
            logger.warning("Hookify summary write failed (non-blocking): %s", e)

        return bridge_result

    def create_rule_neuron_in_graph(self, rule_id: str, surrealdb_client: Any):
        """
        Create a neuron in SurrealDB graph for this rule

        This establishes the graph structure for synapse connections
        """
        try:
            neuron_id = f"neuron:prefrontal_{rule_id}"

            sql = f"""
                CREATE {neuron_id} CONTENT {{
                    title: "{rule_id}",
                    aspect: "prefrontal",
                    tags: ["hookify", "rule"],
                    created: time::now()
                }};
            """

            surrealdb_client.query(sql)
            logger.info(f"Created rule neuron: {neuron_id}")

        except Exception as e:
            logger.warning(f"Could not create rule neuron: {e}")
