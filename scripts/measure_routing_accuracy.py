#!/usr/bin/env python3
"""
Routing Accuracy Measurement Tool (ID-2)

Parses historical human user prompts from ~/.claude/projects/ jsonl logs,
runs them through the cohezion task classifier, and analyzes routing
accuracy, distributions, and potential misclassification anomalies.
"""

import json
import sys
import re
from pathlib import Path
from typing import List, Tuple, Dict, Any

# Ensure we can import from src/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

try:
    from cohezion.inference.task_classifier import classify, RouteDecision
except ImportError as e:
    print(f"Failed to import task_classifier: {e}", file=sys.stderr)
    sys.exit(1)

PROJECTS_DIR = Path("/home/mike-anderson/.claude/projects")


def find_jsonl_files(base_path: Path) -> List[Path]:
    """Find all jsonl files recursively in base_path."""
    if not base_path.exists():
        print(f"Projects directory {base_path} does not exist.", file=sys.stderr)
        return []
    return list(base_path.glob("**/*.jsonl"))


def extract_prompts(jsonl_files: List[Path]) -> List[Dict[str, Any]]:
    """Extract user prompts from jsonl files."""
    extracted = []
    user_msg_count = 0
    total_files_parsed = 0

    for path in jsonl_files:
        total_files_parsed += 1
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        # We match type="user" and message role="user"
                        if data.get("type") == "user":
                            msg = data.get("message", {})
                            if isinstance(msg, dict) and msg.get("role") == "user":
                                user_msg_count += 1
                                content = msg.get("content")
                                if isinstance(content, str):
                                    content_stripped = content.strip()
                                    # Filter: prompts > 50 characters to focus on substantial requests
                                    # Also filter out system-injected or automation templates if any
                                    if len(content_stripped) > 50:
                                        extracted.append(
                                            {
                                                "prompt": content_stripped,
                                                "file": path.relative_to(PROJECTS_DIR.parent),
                                                "line": line_num,
                                                "branch": data.get("gitBranch", "unknown"),
                                                "timestamp": data.get("timestamp", ""),
                                            }
                                        )
                    except (json.JSONDecodeError, TypeError, KeyError):
                        continue
        except Exception:
            # Silently handle read errors for specific files (e.g. locks or permission issues)
            pass

    print(
        f"Scanned {total_files_parsed} files. Found {user_msg_count} user messages, of which {len(extracted)} are > 50 characters."
    )
    return extracted


def is_potential_misclassification(prompt: str, decision: RouteDecision) -> Tuple[bool, str]:
    """
    Detect heuristic indicators of routing anomalies:
    - Code blocks/keywords routed to NPU (False Negative for GPU)
    - Short categorical/binary requests routed to GPU (False Positive for GPU)
    """
    prompt_lower = prompt.lower()

    # 1. False Negatives (Should be GPU, but routed to NPU)
    if decision.node == "npu":
        # Check for code blocks
        if "```" in prompt:
            return True, "FN: Contains markdown code block (```) but routed to NPU"

        # Check for explicit programming language block patterns or indent style code
        if re.search(
            r"(?:^|[\n\t])[ \t]*(def |class |import |from \w+ import |#include|func |fn )", prompt
        ):
            return True, "FN: Technical code keywords/structure at line start but routed to NPU"

        # Check for strong code-gen/refactoring action keywords + code nouns
        code_verbs = r"\b(write|implement|create|generate|build|refactor|rewrite|debug|optimize)\b"
        code_nouns = r"\b(function|class|method|module|code|script|test|tests|endpoint|api|schema|pipeline)\b"
        if re.search(code_verbs, prompt_lower) and re.search(code_nouns, prompt_lower):
            return True, "FN: Strong code verbs and nouns but routed to NPU"

        # Check for test writing requests
        if re.search(
            r"\b(unit|integration|e2e|smoke|regression|pytest|jest)\s+test\b", prompt_lower
        ):
            return True, "FN: Request to write/generate tests but routed to NPU"

    # 2. False Positives (Should be NPU, but routed to GPU)
    elif decision.node == "gpu":
        # Check for categorical requests that should have overridden to NPU
        if re.search(
            r"\b(yes/no|yes or no|true or false|one word|one letter|multiple choice)\b",
            prompt_lower,
        ):
            return True, "FP: Prompt requests simple/categorical answer but routed to GPU"

        # Very short prompts that got routed to GPU without strong patterns (should be NPU)
        if len(prompt) < 100 and "defaulting to GPU" in decision.reason:
            return True, "FP: Short prompt (<100 chars) default-routed to GPU"

    return False, ""


def run_analysis(prompts_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Run classifier and perform statistical analysis."""
    stats = {
        "total": len(prompts_data),
        "npu_count": 0,
        "gpu_count": 0,
        "types": {},
        "reasons": {},
        "anomalies": [],
    }

    for item in prompts_data:
        prompt = item["prompt"]
        decision = classify(prompt)

        # Count node assignments
        if decision.node == "npu":
            stats["npu_count"] += 1
        else:
            stats["gpu_count"] += 1

        # Count output types
        stats["types"][decision.output_type] = stats["types"].get(decision.output_type, 0) + 1

        # Count reason patterns
        stats["reasons"][decision.reason] = stats["reasons"].get(decision.reason, 0) + 1

        # Check for anomalies
        is_anomaly, anomaly_reason = is_potential_misclassification(prompt, decision)
        if is_anomaly:
            stats["anomalies"].append(
                {
                    "prompt": prompt,
                    "decision": str(decision),
                    "reason": decision.reason,
                    "anomaly_reason": anomaly_reason,
                    "file": item["file"],
                    "line": item["line"],
                }
            )

    return stats


def print_report(stats: Dict[str, Any]):
    """Print markdown-formatted summary report."""
    total = stats["total"]
    if total == 0:
        print("No prompts to analyze.")
        return

    npu_pct = (stats["npu_count"] / total) * 100
    gpu_pct = (stats["gpu_count"] / total) * 100

    print("# Task Classifier Routing Accuracy Report\n")
    print(f"**Total Valid Prompts (>50 chars):** {total}")
    print(f"**NPU Routed (Economy):** {stats['npu_count']} ({npu_pct:.2f}%)")
    print(f"**GPU Routed (Premium):** {stats['gpu_count']} ({gpu_pct:.2f}%)\n")

    print("## Output Type Distribution")
    print("| Output Type | Count | Percentage |")
    print("|---|---|---|")
    for otype, count in sorted(stats["types"].items(), key=lambda x: x[1], reverse=True):
        pct = (count / total) * 100
        print(f"| {otype} | {count} | {pct:.2f}% |")
    print()

    print("## Top Matching Rules")
    print("| Rule Reason / Matcher | Count | Percentage |")
    print("|---|---|---|")
    # Top 10 rules
    sorted_reasons = sorted(stats["reasons"].items(), key=lambda x: x[1], reverse=True)[:10]
    for reason, count in sorted_reasons:
        pct = (count / total) * 100
        print(f"| {reason} | {count} | {pct:.2f}% |")
    print()

    anomalies = stats["anomalies"]
    print(f"## Potential Misclassifications / Anomalies ({len(anomalies)})")
    if not anomalies:
        print("No anomalies detected!")
    else:
        print("| File:Line | Decision | Anomaly Cause | Prompt Snippet |")
        print("|---|---|---|---|")
        for a in anomalies[:25]:  # Show top 25 anomalies
            snippet = a["prompt"][:80].replace("\n", " ") + ("..." if len(a["prompt"]) > 80 else "")
            # escape | in markdown table
            snippet = snippet.replace("|", "\\|")
            file_line = f"{a['file']}:{a['line']}"
            print(f"| {file_line} | `{a['decision']}` | *{a['anomaly_reason']}* | `{snippet}` |")
        if len(anomalies) > 25:
            print(
                f"\n*(Showing top 25 of {len(anomalies)} anomalies. See full outputs for detail)*"
            )


def main():
    print("Finding project logs in ~/.claude/projects/...")
    files = find_jsonl_files(PROJECTS_DIR)
    if not files:
        sys.exit(1)

    print(f"Extracting user prompts from {len(files)} log files...")
    prompts_data = extract_prompts(files)
    if not prompts_data:
        print("No user prompts matching filter criteria were found.")
        sys.exit(0)

    print("Running classification analysis...")
    stats = run_analysis(prompts_data)

    print("\n" + "=" * 80 + "\n")
    print_report(stats)
    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    main()
