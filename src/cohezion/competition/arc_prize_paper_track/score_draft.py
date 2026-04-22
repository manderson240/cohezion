"""Score paper draft quality against paper-track criteria."""

from __future__ import annotations

from pathlib import Path
from typing import Any

SECTIONS = [
    ("abstract", 15),
    ("introduction", 10),
    ("architecture", 20),
    ("results", 15),
    ("novelty", 15),
    ("artifacts", 10),
    ("references", 5),
    ("prior_work", 10),
]


def score_draft(path: str) -> dict[str, Any]:
    text = Path(path).read_text()
    scores = {}

    # Abstract: check keywords, novelty claim, length
    abs_match = text.lower().find("abstract") >= 0
    if abs_match:
        abs_score = 8
        if "alignment gate" in text.lower()[:800]: abs_score += 2
        if "skill refinement" in text.lower()[:800]: abs_score += 2
        if len(text) > 3000: abs_score += 3
        scores["abstract"] = min(15, abs_score)
    else:
        scores["abstract"] = 0

    # Introduction
    intro_score = 5 if "## 1. Introduction" in text else 0
    if "chollet" in text.lower(): intro_score += 2
    if "arc-agi-2" in text.lower(): intro_score += 2
    if "novel" in text.lower() or "new" in text.lower(): intro_score += 1
    scores["introduction"] = min(10, intro_score)

    # Architecture: formal definitions, subsections, diagrams mentioned
    arch_score = 5 if "## 2." in text else 0
    if "alignment gate" in text.lower(): arch_score += 3
    if "journey tracker" in text.lower(): arch_score += 2
    if "skill refinement" in text.lower(): arch_score += 2
    if "### 2." in text and text.count("### 2.") >= 2: arch_score += 3
    if "formal" in text.lower() or "theorem" in text.lower() or "definition" in text.lower(): arch_score += 3
    if "diagram" in text.lower() or "figure" in text.lower(): arch_score += 2
    scores["architecture"] = min(20, arch_score)

    # Results: actual data, tables, numbers
    results_score = 2 if "## 3." in text else 0
    if "%" in text: results_score += 3
    if "solve rate" in text.lower(): results_score += 3
    if "table" in text.lower(): results_score += 3
    if "ablation" in text.lower(): results_score += 4
    scores["results"] = min(15, results_score)

    # Novelty: explicit differentiation from prior work
    nov_score = 3 if "## 4." in text else 0
    if "unlike" in text.lower() or "compared" in text.lower(): nov_score += 3
    if "arc prize" in text.lower(): nov_score += 3
    if "metacognitive" in text.lower(): nov_score += 3
    if "open-ended" in text.lower(): nov_score += 3
    scores["novelty"] = min(15, nov_score)

    # Artifacts
    art_score = 3 if "## 5." in text else 0
    if "github" in text.lower() or "open source" in text.lower(): art_score += 3
    if "license" in text.lower(): art_score += 2
    if "mit" in text.lower() or "apache" in text.lower(): art_score += 2
    scores["artifacts"] = min(10, art_score)

    # References: count citation entries
    ref_count = text.count("(") + text.count("[") - text.count("(") // 2
    # More precise: count lines that look like references
    ref_lines = [l for l in text.split("\n") if l.strip().startswith("- ") and ("chollet" in l.lower() or "arcprize" in l.lower() or "20" in l)]
    ref_count = len([l for l in text.split("## References")[-1].split("\n") if l.strip() and not l.strip().startswith("-") and len(l.strip()) > 10]) if "## References" in text else 0
    ref_count = max(len([l for l in text.split("## References")[-1].split("\n") if l.strip() and l.strip()[0].isalpha() and "20" in l]), 0) if "## References" in text else 0
    if ref_count == 0:
        # crude fallback: count lines that look like citations after "References"
        after_ref = text.split("## References")[-1] if "## References" in text else ""
        ref_count = len([l for l in after_ref.split("\n") if len(l.strip()) > 20 and any(c.isdigit() for c in l)])
    scores["references"] = min(5, ref_count)

    # Prior Work
    pw_score = 0
    if "## 2. Prior Work" in text or "## 2. Related Work" in text or "## Prior Work" in text:
        pw_score = 5
        if "arChitects" in text.lower() or "dreamcoder" in text.lower(): pw_score += 3
        if len([l for l in text.split("## 2. Prior Work")[-1].split("\n") if l.strip() and l.strip()[0].isalpha()]) > 5: pw_score += 2
    scores["prior_work"] = min(10, pw_score)

    total = sum(scores[s] for s, _ in SECTIONS)
    max_total = sum(m for _, m in SECTIONS)
    return {
        "sections": scores,
        "total": total,
        "max": max_total,
        "percent": round(total / max_total * 100, 1),
    }


if __name__ == "__main__":
    result = score_draft(Path(__file__).with_name("DRAFT.md"))
    for s, v in result["sections"].items():
        print(f"  {s:20s}: {v:2d}/{[m for n, m in SECTIONS if n == s][0]}")
    print(f"\n  Total: {result['total']}/{result['max']} = {result['percent']}%")
