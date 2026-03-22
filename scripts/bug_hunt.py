"""
Bug Hunting Swarm Orchestrator.
Orchestrates Scout, Fixer, and Auditor agents to find and fix bugs.
Includes a Deep Retrospective phase to update KEY_LEARNINGS.md.
"""

import argparse
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

from cohezion.healing.deep_audit import DeepAuditor
from cohezion.swarm.agents.bug_auditor_agent import BugAuditorAgent
from cohezion.swarm.agents.bug_fixer_agent import BugFixerAgent
from cohezion.swarm.agents.bug_scout_agent import BugScoutAgent
from cohezion.universe.engine import UniverseSimulationEngine


# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("BugHunt")


async def run_bug_hunt(target_dir: str, recursive: bool = True):
    """
    Runs the full bug hunt cycle.
    """
    logger.info(f"🚀 Starting Bug Hunt Swarm on: {target_dir}")

    # 1. Initialize Agents
    scout = BugScoutAgent()
    fixer = BugFixerAgent()
    auditor = BugAuditorAgent()
    UniverseSimulationEngine()

    # 2. Run DeepAuditor for initial hotspots
    auditor_engine = DeepAuditor()
    target_path = Path(target_dir)

    python_files = []
    if target_path.is_file():
        if target_path.suffix == ".py":
            python_files = [target_path]
    elif recursive:
        python_files = list(target_path.rglob("*.py"))
    else:
        python_files = list(target_path.glob("*.py"))

    for py_file in python_files:
        auditor_engine.audit_file(py_file)

    # Filter issues that are relevant for scout (Quality, Performance)
    relevant_issues = [i for i in auditor_engine.issues if i.category in ["Quality", "Performance"]]

    if not relevant_issues:
        logger.info("✅ No critical static analysis issues found.")
        return

    logger.info(
        f"🔍 Found {len(relevant_issues)} potential hotspots. Dispatched Bug Hunting Swarm..."
    )

    # 3. Main Swarm Loop
    results = []

    for issue in relevant_issues:
        try:
            file_path = Path(issue.file_path)
            content = file_path.read_text()

            # --- PHASE 1: SCOUT ---
            scout_result = await scout.process(issue, content)
            analysis_text = scout_result["outputs"]["analysis"]

            # Use a simple JSON parsing heuristic (BugScout outputs JSON)
            try:
                # Find JSON block in reasoning output if necessary
                import re

                json_match = re.search(r"\{.*\}", analysis_text, re.DOTALL)
                analysis = json.loads(json_match.group(0)) if json_match else {}
            except Exception:
                analysis = {"is_bug": "bug" in analysis_text.lower()}

            if not analysis.get("is_bug"):
                logger.info(
                    f"🍃 [SCOUT] False positive or non-bug in {issue.file_path}:{issue.line}"
                )
                continue

            logger.info(f"🚨 [SCOUT] Confirmed BUG in {issue.file_path}:{issue.line}")

            # --- PHASE 2: FIXER ---
            fix_result = await fixer.process(scout_result, content)
            fixed_code = fix_result["outputs"]["fixed_code"]

            # --- PHASE 3: AUDITOR ---
            audit_result = await auditor.process(fix_result, content)
            audit_data = audit_result["outputs"]["audit_result"]

            try:
                json_match = re.search(r"\{.*\}", audit_data, re.DOTALL)
                audit_json = json.loads(json_match.group(0)) if json_match else {}
            except Exception:
                audit_json = {}

            results.append(
                {
                    "issue": vars(issue),
                    "analysis": analysis,
                    "fix": fixed_code,
                    "audit": audit_json,
                }
            )

            # --- PHASE 4: RETROSPECTIVE ---
            if audit_json.get("extracted_pattern") or audit_json.get("extracted_anti_pattern"):
                await perform_retrospective(audit_json, issue.file_path)

        except Exception as e:
            logger.error(f"❌ Error processing issue in {issue.file_path}: {e}")

    # 5. Generate Report
    generate_report(results)


async def perform_retrospective(audit_json: dict, file_path: str):
    """
    Appends new learnings to KEY_LEARNINGS.md.
    """
    learnings_path = Path("src/cohezion/knowledge_graph/KEY_LEARNINGS.md")
    if not learnings_path.exists():
        return

    pattern = audit_json.get("extracted_pattern", "N/A")
    anti_pattern = audit_json.get("extracted_anti_pattern", "N/A")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    new_learning = f"""
## Learning: BUG_HUNT_DISCOVERY ({timestamp})
* **Context**: Swarm Bug Hunt in `{file_path}`.
* **Core Concept**: {pattern}
* **Anti-Pattern**: {anti_pattern}
* **Impact**: Improvement in technical debt and stability.
* **Encoding**: 12D [t={datetime.now().strftime("%Y%m%d")}, stability=0.9, novelty=0.85, brane=1]

---
"""
    with open(learnings_path, "a") as f:
        f.write(new_learning)

    logger.info(f"📖 [RETROSPECTIVE] Registered new learning from {file_path}")


def generate_report(results: list):
    """
    Generates a Markdown report of the bug hunt.
    """
    report_path = Path("src/cohezion/knowledge_graph/audits/bug_hunt_report.md")
    report_path.parent.mkdir(parents=True, exist_ok=True)

    report = f"# Bug Hunt Swarm Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    report += f"Total Issues Processed: {len(results)}\n\n"

    for res in results:
        issue = res["issue"]
        analysis = res["analysis"]
        audit = res["audit"]

        report += f"## 🐞 Bug in `{issue['file_path']}:{issue['line']}`\n"
        report += f"- **Original Issue**: {issue['message']}\n"
        report += f"- **Scout Confidence**: {analysis.get('confidence', 'N/A')}\n"
        report += f"- **Auditor Score**: {audit.get('phi_score', 'N/A')}\n"
        report += f"### Impact\n{analysis.get('impact_analysis', 'N/A')}\n"
        report += f"### Extracted Pattern\n{audit.get('extracted_pattern', 'N/A')}\n"
        report += f"### Suggested Fix\n```python\n{res['fix']}\n```\n\n"
        report += "---\n\n"

    report_path.write_text(report)
    logger.info(f"📊 Report generated at {report_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Bug Hunting Swarm.")
    parser.get_all_args = lambda: None  # placeholder for my brain
    parser.add_argument(
        "--dir",
        type=str,
        default="src/cohezion",
        help="Target directory to hunt bugs in.",
    )
    parser.add_argument("--no-recursive", action="store_true", help="Do not search recursively.")

    args = parser.parse_args()

    asyncio.run(run_bug_hunt(args.dir, recursive=not args.no_recursive))
