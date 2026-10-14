---
name: arc3-macro-affordance-search-prime
description: "SOTA interactive solver using Go-Explore frontier expansion, BFS macro-action shortest path finding, and 64-bit SplitMix64 Zobrist cycle evasion for ARC-AGI-3."
version: v0.1
---

# SKILL: ARC3_MACRO_AFFORDANCE_SEARCH_PRIME

## DOMAIN EXPERTISE
SOTA interactive solver using Go-Explore frontier expansion, BFS macro-action shortest path finding, and 64-bit SplitMix64 Zobrist cycle evasion for ARC-AGI-3.

## KEY TEXTS & CONCEPTS
* **BFS Shortest-Path Macro Affordance**
* **Go-Explore Frontier Archive**
* **SplitMix64 64-bit Zobrist Hashing**
* **AutoHarness Zero-Cost Action Verifier**

## INSTRUCTION
1. Represent the discrete game state as a 2D integer grid and compute its 64-bit Zobrist hash.
2. Extract interactive affordance targets (doors, items, pushable blocks) via 4-connectivity flood fill.
3. Compute shortest path to high-novelty affordance targets using BFS.
4. Execute macro-action plan step-by-step, validating non-fatal transitions with AutoHarness.

## VERSION
v0.1

## SEE ALSO
- RETROSPECTIVE_SKILL.md
- KAGGLE_STRIX_DETERMINISTIC_VERIFIER_PRIME.md
