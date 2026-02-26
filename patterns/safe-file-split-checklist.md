---
title: "{{title}}"
date: "2026-02-17"
tags: [pattern]
---

## Problem

## Solution

## Code Example

## When to Use

## Related Decisions

- [[2026-02-17-singleton-consolidation-mandatory-during-file-splits|Decision: Singleton Consolidation Mandatory During File Splits]] — the key invariant this checklist enforces: when splitting a file, singletons must be consolidated to avoid duplicate state
- [[2026-02-23-enforce-no-orphan-modules-policy|Decision: Enforce No Orphan Modules Policy]] — file splits create orphan risk if not wired into the module tree
- [[2026-02-24-anti-pattern-disconnected-modules-without-consumers|Anti-pattern: Disconnected Modules Without Consumers]] — what happens when a file split is done without this checklist

## Decisions That Applied This Pattern

- [[2026-02-09-session-46-git-unification-complete]] — the git unification session that resolved 30+ file conflicts, a scenario where this checklist's caller-tracking prevents breaking changes

## Related Patterns

- [[private-to-public-rename-drift]] — renames during file splits are a common missed-caller scenario
- [[service-class-singleton-pattern]] — singleton management is the critical step in any file split

## Related Concepts

- [[dna-origami-2d-semiconductor-patterning]]
- [[entire-io-to-vault-mapping]]
- [[automated-concept-extraction]]
- [[sheetsbr idge-mcp-testing]]
- [[phase1-production-validation-runbook]]
- [[typescript-error-diagnostic]]
- [[surrealdb-query-driven-analysis]]
- [[agent-logs-vault-schema]]
