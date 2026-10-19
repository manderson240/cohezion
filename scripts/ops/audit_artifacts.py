#!/usr/bin/env python3
"""
Audit all conversation artifacts for Readability, Efficacy, and Structural Consistency.
"""

import os
import re
from pathlib import Path
from typing import Dict, Any, List

BRAIN_DIR = Path("/home/mike-anderson/.gemini/antigravity-cli/brain/52153a1c-9d27-40cd-9367-9fe29be569da")

def analyze_artifact(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    word_count = len(text.split())
    line_count = len(lines)
    
    # 1. Structural Checks
    has_h1 = any(l.startswith("# ") for l in lines)
    
    # Matches Date:, **Date**:, **Target Hardware / Runtime**:, etc.
    has_metadata_header = bool(re.search(r"\b(Date|Target Hardware|Methodology|Author|Version)\b\s*\**\s*:", text, re.I))
    
    has_exec_summary = bool(re.search(r"##\s+\d*\.?\s*(Executive Summary|Overview|TL;DR|Summary|Intent)", text, re.I))
    has_diagram = "```mermaid" in text or bool(re.search(r"\+[-+]+\+", text))
    
    # Matches technical body sections
    has_specs = bool(re.search(r"##\s+\d*\.?\s*.*(Specification|Architecture|Design|Implementation|Methodology|Mechanism|Root Cause|Pillars|Diagnostic|Standards|Doctrine|Blueprint|Strategy|Foundations|Systemic|Hardware|Optimization)", text, re.I))
    if not has_specs:
        # Fallback: file has at least 3 distinct H2 headers providing technical content
        h2_headers = [l for l in lines if l.startswith("## ")]
        has_specs = len(h2_headers) >= 3
        
    has_verification = bool(re.search(r"##\s+\d*\.?\s*.*(Verification|Test|Results|Proof|Evidence|Empirical)", text, re.I))
    has_alerts = bool(re.search(r">\s*\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]", text))
    has_links = bool(re.search(r"\[.*?\]\((file://|http|#).*?\)", text))
    has_tables = bool(re.search(r"\|.*?\|.*?\|", text))
    
    # Readability heuristics
    sentences = re.split(r"[.!?]+", text)
    valid_sentences = [s.strip() for s in sentences if len(s.strip().split()) > 2]
    avg_sentence_len = (word_count / len(valid_sentences)) if valid_sentences else 0.0
    
    # Structural compliance score (0 to 100)
    score = 0
    checks = {
        "h1_title": (has_h1, 10),
        "metadata_header": (has_metadata_header, 15),
        "exec_summary": (has_exec_summary, 20),
        "diagram_or_schematic": (has_diagram, 15),
        "technical_specs": (has_specs, 15),
        "verification_evidence": (has_verification, 15),
        "links_or_tables": ((has_links or has_tables), 10),
    }
    
    for key, (passed, pts) in checks.items():
        if passed:
            score += pts
            
    # Readability grade
    if avg_sentence_len <= 18:
        readability = "High (Clean, punchy)"
    elif avg_sentence_len <= 26:
        readability = "Moderate (Standard technical)"
    else:
        readability = "Dense (Complex periodic sentences)"
        
    # Efficacy grade
    if score >= 85:
        efficacy = "High (Production Grade)"
    elif score >= 65:
        efficacy = "Moderate (Meets Base Spec)"
    else:
        efficacy = "Needs Standardization"
        
    return {
        "file": path.name,
        "line_count": line_count,
        "word_count": word_count,
        "score": score,
        "readability": readability,
        "avg_sentence_len": round(avg_sentence_len, 1),
        "efficacy": efficacy,
        "has_h1": has_h1,
        "has_metadata_header": has_metadata_header,
        "has_exec_summary": has_exec_summary,
        "has_diagram": has_diagram,
        "has_specs": has_specs,
        "has_verification": has_verification,
        "has_alerts": has_alerts,
        "has_tables": has_tables,
        "has_links": has_links,
    }

def main():
    md_files = sorted(list(BRAIN_DIR.glob("*.md")))
    results = [analyze_artifact(p) for p in md_files]
    
    print(f"Total Markdown Artifacts Audited: {len(results)}")
    print(f"{'Artifact File':<50} | {'Score':<5} | {'Efficacy':<24} | {'Readability':<20} | {'Words'}")
    print("-" * 115)
    
    perfect_count = sum(1 for r in results if r["score"] == 100)
    high_count = sum(1 for r in results if r["score"] >= 85)
    mod_count = sum(1 for r in results if 65 <= r["score"] < 85)
    low_count = sum(1 for r in results if r["score"] < 65)
    
    for r in results:
        print(f"{r['file']:<50} | {r['score']:<5} | {r['efficacy']:<24} | {r['readability']:<20} | {r['word_count']}")
        
    print("-" * 115)
    print(f"Summary: Perfect (100): {perfect_count} | High (>=85): {high_count} | Moderate (65-84): {mod_count} | Low (<65): {low_count}")

if __name__ == "__main__":
    main()
