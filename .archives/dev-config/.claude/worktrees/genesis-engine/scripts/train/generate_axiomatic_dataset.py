#!/usr/bin/env python3
"""
Generate SFT dataset from Cohezion knowledge graph and pulse data.
Harvests Learnings, Insights, and Mission Journals for fine-tuning.
"""

import json
from pathlib import Path


PROJECT_ROOT = Path("/home/mike-anderson/dev/cohezion")
LEARNINGS_FILE = PROJECT_ROOT / "src/cohezion/knowledge_graph/KEY_LEARNINGS.md"
INSIGHTS_FILE = PROJECT_ROOT / "src/cohezion/knowledge_graph/LIVE_INSIGHTS.md"
PULSE_DIR = PROJECT_ROOT / "apps/dashboard/src/assets/data"
OUTPUT_FILE = PROJECT_ROOT / "cohezion_kb.jsonl"


def main():
    print("🌾 Harvesting Cohezion Axioms...")
    dataset = []

    # 1. Harvest Learnings
    if LEARNINGS_FILE.exists():
        content = LEARNINGS_FILE.read_text()
        sections = content.split("### Learning")
        for section in sections[1:]:
            title_end = section.find("\n")
            title = section[:title_end].strip()
            body = section[title_end:].strip()

            dataset.append({"instruction": f"Explain Cohezion Learning: {title}", "output": body})

    # 2. Harvest Live Insights
    if INSIGHTS_FILE.exists():
        content = INSIGHTS_FILE.read_text()
        sections = content.split("## Insight @")
        for section in sections[1:]:
            body = section.strip()
            dataset.append({"instruction": "Provide a recent Cohezion autonomic insight.", "output": body})

    # 3. Harvest Pulse Trajectories
    pulses = sorted(PULSE_DIR.glob("pulse_*.json"))
    for pulse_file in pulses[-10:]:  # Last 10 pulses
        try:
            data = json.loads(pulse_file.read_text())
            dataset.append(
                {
                    "instruction": f"Summarize the 12D physics state for {data.get('journey_id', 'unknown')}.",
                    "output": json.dumps(data, indent=2),
                }
            )
        except:
            continue

    # Write to JSONL
    with open(OUTPUT_FILE, "w") as f:
        for entry in dataset:
            f.write(json.dumps(entry) + "\n")

    print(f"✅ Dataset generated: {OUTPUT_FILE} ({len(dataset)} entries)")


if __name__ == "__main__":
    main()
