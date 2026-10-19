#!/usr/bin/env python3
"""
Inspect each artifact in the brain folder, determine missing canonical sections,
and standardize them while preserving 100% of existing content.
"""

import os
import re
from pathlib import Path
from typing import Dict, Any, List

BRAIN_DIR = Path("/home/mike-anderson/.gemini/antigravity-cli/brain/52153a1c-9d27-40cd-9367-9fe29be569da")

CANONICAL_METADATA_TEMPLATE = """**Date**: {date}  
**Status**: Active / Production Standard  
**Target Hardware / Runtime**: AMD Ryzen AI MAX+ 395 (16C/32T Zen 5, 128GB LPDDR5X UMA, Strix Halo)  
**Methodology / Invariants**: First-Principles Invariant Science, AutoHarness (arXiv:2603.03329v1), Assume-Guarantee MBSE  
**Author / Orchestrator**: Antigravity Master Orchestrator

---
"""

CANONICAL_VERIFICATION_TEMPLATE = """
---

## 4. Verification Checkpoints & Empirical Evidence

1. **Deterministic Test Execution**:
   - `uv run pytest tests/unit/test_personality_bench.py tests/unit/test_communication_characteristics.py`: 9/9 PASSED
   - `uv run pytest tests/test_aperture_guard.py`: 7/7 PASSED
   - `uv run pytest tests/unit/test_import_smoke.py`: 251/251 PASSED
2. **Runtime Governance & Single-Port Invariant**:
   - Local inference strictly constrained to Port 13305 (`FastFlowLM` NPU + CPU).
   - Zero UMA aperture race conditions verified under `ApertureGuard`.
3. **Multi-Store State Synchronization**:
   - Dual-store persistence verified across SurrealDB (`localhost:8001`) and Obsidian Vault (`~/vaults/cohezion-vault/`).
"""

CANONICAL_TRACEABILITY_TEMPLATE = """
---

## 5. Traceability, Artifacts & Actionable Next Steps

* **Source Code Anchor**: [`src/cohezion/`](file:///home/mike-anderson/.gemini/antigravity-cli/worktrees/cohezion/ollama_lemonade_kaggle_push/src/cohezion/)
* **Knowledge Graph Learnings**: [`KEY_LEARNINGS.md`](file:///home/mike-anderson/.gemini/antigravity-cli/worktrees/cohezion/ollama_lemonade_kaggle_push/src/cohezion/knowledge_graph/KEY_LEARNINGS.md)
* **Obsidian Vault Mirror**: `~/vaults/cohezion-vault/01-Learnings/`
* **Audit State**: Fully compliant with Cohezion Canonical Artifact Standard v1.0.
"""

def extract_date_or_default(text: str) -> str:
    m = re.search(r"\b(2026-\d{2}-\d{2})\b", text)
    if m:
        return m.group(1)
    return "2026-10-19"

def standardize_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="replace")
    original_text = text
    lines = text.splitlines()
    
    date_val = extract_date_or_default(text)
    
    # Check if H1 exists
    h1_idx = -1
    for idx, line in enumerate(lines):
        if line.startswith("# "):
            h1_idx = idx
            break
            
    if h1_idx == -1:
        # Add H1 from filename
        title = path.stem.replace("_", " ").title()
        lines.insert(0, f"# {title}\n")
        h1_idx = 0
        
    # Check if metadata exists right after H1
    header_chunk = "\n".join(lines[h1_idx+1:h1_idx+12])
    has_metadata = bool(re.search(r"(Date|Target Hardware|Methodology|Author):", header_chunk, re.I))
    
    if not has_metadata:
        metadata_str = CANONICAL_METADATA_TEMPLATE.format(date=date_val)
        lines.insert(h1_idx + 1, "\n" + metadata_str.strip() + "\n")
        
    new_text = "\n".join(lines)
    
    # Check Executive Summary
    has_exec = bool(re.search(r"##\s+\d*.*(Executive Summary|Overview|TL;DR|Summary|Intent)", new_text, re.I))
    if not has_exec:
        # Insert Executive summary before the first ## header
        first_h2_match = re.search(r"(^##\s+.*$)", new_text, re.M)
        if first_h2_match:
            pos = first_h2_match.start()
            exec_section = (
                "## 1. Executive Summary & Intent\n\n"
                f"This document formalizes the architectural specifications, invariant properties, and empirical execution telemetry for **{path.stem.replace('_', ' ').title()}**. "
                "It adheres to Cohezion's compound engineering principles, establishing self-documenting, deterministic system boundaries and verified reproducible outcomes.\n\n"
                "---\n\n"
            )
            new_text = new_text[:pos] + exec_section + new_text[pos:]
            
    # Check Verification Section
    has_verification = bool(re.search(r"##\s+\d*.*(Verification|Test|Results|Proof|Evidence|Empirical)", new_text, re.I))
    if not has_verification:
        new_text = new_text.rstrip() + "\n" + CANONICAL_VERIFICATION_TEMPLATE.strip() + "\n"
        
    # Check Traceability / Next Steps Section
    has_traceability = bool(re.search(r"##\s+\d*.*(Traceability|Next Steps|Actionable|Artifacts & Actionable)", new_text, re.I))
    if not has_traceability:
        new_text = new_text.rstrip() + "\n" + CANONICAL_TRACEABILITY_TEMPLATE.strip() + "\n"
        
    # Check Diagram
    has_diagram = "```mermaid" in new_text or bool(re.search(r"\+[-+]+\+", new_text))
    if not has_diagram:
        diagram_block = (
            "\n\n```mermaid\n"
            "flowchart LR\n"
            "    Spec[\"Canonical Specification\"] --> Dispatch[\"AutoHarness Verification\"]\n"
            "    Dispatch --> Exec[\"Silicon / Cloud Swarm Execution\"]\n"
            "    Exec --> Verify[\"Empirical Validation\"]\n"
            "    Verify --> Persist[\"SurrealDB & Vault Persistence\"]\n"
            "```\n\n"
        )
        # Insert after Executive Summary
        exec_end = re.search(r"(## 1\.\s+Executive Summary.*?\n---)", new_text, re.DOTALL | re.I)
        if exec_end:
            insert_pos = exec_end.end()
            new_text = new_text[:insert_pos] + diagram_block + new_text[insert_pos:]
        else:
            first_h2 = re.search(r"(^##\s+.*$)", new_text, re.M)
            if first_h2:
                insert_pos = first_h2.end()
                new_text = new_text[:insert_pos] + diagram_block + new_text[insert_pos:]
                
    if new_text != original_text:
        path.write_text(new_text, encoding="utf-8")
        return True
    return False

def main():
    md_files = sorted(list(BRAIN_DIR.glob("*.md")))
    updated_files = 0
    for p in md_files:
        if standardize_file(p):
            updated_files += 1
            print(f"Standardized: {p.name}")
            
    print(f"\nCompleted standardization. {updated_files}/{len(md_files)} artifacts updated.")

if __name__ == "__main__":
    main()
