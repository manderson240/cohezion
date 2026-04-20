---
title: Vault Completion Retrospective
date: 2026-02-23
tags: [pattern, retrospective, vault, quality-assurance]
status: active
aspect: thinker
neural:
  activation: 0.72
  stage: growing
  synapse_in: 8
  synapse_out: 7
---

# Vault Completion Retrospective

A structured pattern for conducting vault-level retrospectives after major project phases or milestones. Assesses knowledge coverage, link health, graph connectivity, and identifies gaps or stale content requiring attention in the next cycle.

## Problem

After a multi-session compound engineering sprint, the vault accumulates new notes, links, and structural changes. Without a systematic review, problems accumulate silently: orphan notes with no inbound links, broken wiki-links to renamed or deleted notes, stale status values on completed decisions, and entire topic areas with thin coverage. These issues compound over time, degrading the vault's value as a knowledge base.

## Solution

Run a structured retrospective at the end of each major project phase. The retrospective produces actionable findings organized into four categories:

### 1. Coverage Audit

- Count notes per directory (`concepts/`, `papers/`, `decisions/`, etc.)
- Identify thin notes (under 800 characters of body content) that need expansion
- Flag directories with fewer notes than expected given project scope

### 2. Link Health Check

- Scan for broken wiki-links (targets that do not exist as files)
- Identify orphan notes (zero inbound links from other notes)
- Measure average links per note and compare against previous retrospective

### 3. Graph Connectivity Analysis

- Calculate the number of connected components in the wiki-link graph
- Identify bridge notes (whose removal would disconnect graph components)
- Measure graph density (actual edges / possible edges) as a health metric

### 4. Freshness Review

- Flag notes with `status: stub` that are older than 7 days
- Identify decisions with `status: proposed` that have been open longer than 14 days
- Check that completed experiments have results documented

## When to Use

- After completing a major project phase (e.g., Phase 4 Universe Simulation)
- After a knowledge graph densification sprint
- Before starting a new project phase that depends on existing vault content
- Monthly, as part of vault maintenance hygiene

## Related

- [[lesson-effective-retrospectives]] — general retrospective practices that inform this vault-specific pattern
- [[2026-02-14-phases-1-3-retrospective-key-learnings]] — Phase 1-3 retrospective using this structured format
- [[2026-02-14-phase-4-retrospective-and-phase-5-overnight-plan]] — Phase 4 retrospective demonstrating the pattern at a compound engineering milestone
- [[2026-02-14-compound-engineering-team-execution-retrospective]] — team execution retrospective feeding forward into Phase 5-7 planning
- [[knowledge-graph-densification]] — the retrospective identifies densification targets for the next cycle
- [[bidirectional-linking]] — link health checks verify that bidirectional links are consistently maintained
- [[compound-engineering]] — the retrospective is a quality gate in the compound engineering lifecycle

## Relevance to Cohezion

The vault completion retrospective is how Cohezion maintains knowledge quality over time. By systematically auditing coverage, links, connectivity, and freshness after each phase, the pattern prevents the silent accumulation of debt in the knowledge graph and ensures each compounding cycle starts from a clean, well-connected foundation.
