"""
Assess Git Health with FLUME Swarm.

Entry point for repository health assessment. Orchestrates agents,
performs static analysis, and generates a health report with improvement
suggestions.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path

from cohezion.core.persistence.surreal_client import (
    PhysicsState,
    SurrealClient,
    UniverseNode,
)
from cohezion.flume.git_encoder import GitEncoder

# Relative imports
from cohezion.healing.deep_audit import DeepAuditor
from cohezion.swarm.agents.code_simplification_agent import CodeSimplificationAgent
from cohezion.swarm.agents.git_health_agent import GitHealthAgent
from cohezion.swarm.git_health import (
    attribute_complexity,
    collect_git_metadata,
    get_repo_bloat,
    get_unpushed_commits,
)
from cohezion.swarm.journey_tracker import AgentType, get_journey_tracker
from cohezion.swarm.swarm_types import SwarmConfig


# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("GitHealthAssessment")


async def run_assessment():
    logger.info("🚀 Starting Git Health Assessment...")

    # 1. Static Analysis
    logger.info("🔍 Running Deep Audit (Static Analysis)...")
    auditor = DeepAuditor()
    base_path = Path("src/cohezion")

    for root, _, files in os.walk(base_path):
        for file in files:
            if file.endswith(".py"):
                auditor.audit_file(Path(root) / file)

    # 2. Git Metadata
    logger.info("📜 Collecting Git Metadata & Bloat Analysis...")
    recent_commits = collect_git_metadata()
    unpushed = get_unpushed_commits()
    bloat = get_repo_bloat()
    traces = attribute_complexity(auditor.issues)

    # 3. FLUME Analysis
    logger.info("🌊 Encoding Git Trajectories (FLUME)...")
    git_encoder = GitEncoder()
    drift_score = git_encoder.evaluate_drift(recent_commits)

    # 4. Swarm Analysis
    logger.info("🐝 Deploying Swarm Agents & Tracking Journey...")
    config = SwarmConfig()
    health_agent = GitHealthAgent(config)
    simplifier_agent = CodeSimplificationAgent(config)

    tracker = get_journey_tracker()
    tracker.start_journey("Assess overall git health and suggest simplifications.")

    health_task = health_agent.process(
        "Assess the overall repository health based on recent history.",
        context=recent_commits,
    )

    simplification_task = simplifier_agent.process(
        "Propose refactors for the most complex files identified in recent history.",
        traces=traces,
    )

    health_thought, simplifier_thought = await asyncio.gather(health_task, simplification_task)

    # Record Journey Steps
    tracker.record_step(
        agent_type=AgentType.ANALYST,
        agent_name="GitHealthAgent",
        perspective="technical",
        input_text="Assess overall git health",
        output_text=health_thought.content,
        physics_state={"complexity": 0.5, "coherence": health_thought.confidence},
        duration_ms=2000,  # Approximation
    )

    tracker.record_step(
        agent_type=AgentType.ANALYST,
        agent_name="CodeSimplificationAgent",
        perspective="technical",
        input_text="Propose refactors",
        output_text=simplifier_thought.content,
        physics_state={"complexity": 0.8, "coherence": simplifier_thought.confidence},
        duration_ms=3000,  # Approximation
    )

    tracker.end_journey(health_thought.content, final_confidence=0.9)

    # 5. Generate Report
    logger.info("📝 Generating Executive Summary & Report...")

    # Generate HTML/Markdown Executive Summary for Email
    f"""
    <h2>🛡️ Git Health Executive Brief</h2>
    <ul>
        <li><b>Health Score:</b> {auditor._calculate_global_score()} / 100</li>
        <li><b>Stability Drift:</b> {drift_score:.2f}</li>
        <li><b>Critical Issues:</b> {len([i for i in auditor.issues if i.severity == "Critical"])}</li>
        <li><b>Bloat Status:</b> {bloat["total_pending"]} pending files</li>
    </ul>
    <h3>Top Recommendations</h3>
    <pre>{health_thought.content[:500]}...</pre>
    """

    # Full Markdown Report
    report = f"""# 🛡️ Git Health Report - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 🎯 Executive Summary
- **Health Score:** {auditor._calculate_global_score()} / 100
- **Semantic Stability:** {drift_score:.2f} (1.0 = Stable)
- **Repo Bloat:** {bloat["total_pending"]} pending changes ⚠️
- **Unpushed Work:** {len(unpushed)} commits
- **Complexity Hotspots:** {len(traces)} issues attributed to history

## 📦 Bloat Details
- **Untracked:** {bloat.get("untracked_count", 0)} files
- **Modified/Deleted:** {bloat.get("modified_count", 0)} files
- **Hotspots:** {", ".join([f"{k} ({v})" for k, v in bloat.get("hotspots", [])])}

## 蜂 Health Agent Analysis
{health_thought.content}

## ⚡ Simplification Recommendations
{simplifier_thought.content}

## 📊 Complexity Attribution (Top 5)
"""
    for trace in sorted(traces, key=lambda t: t.date, reverse=True)[:5]:
        report += f"- `{trace.file_path}:{trace.line}` (Authored by {trace.author} in {trace.commit_hash[:8]})\n"
        if trace.issue:
            report += f"  - ⚠️ {trace.issue.message}\n"

    report_path = Path("src/cohezion/knowledge_graph/audits/git_health_report.md")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report)

    # 6. SurrealDB Persistence
    logger.info("💾 Offloading results to SurrealDB...")
    try:
        db = SurrealClient()
        await db.connect()

        audit_node = UniverseNode(
            id=f"audit_git_{datetime.now().strftime('%Y%H%d_%H%M%S')}",
            content=report,
            node_type="audit",
            physics_state=PhysicsState(
                complexity=auditor._calculate_global_score() / 100.0,
                stability=drift_score,
                mass=float(bloat["total_pending"]) / 100.0 if bloat["total_pending"] < 100 else 1.0,
            ),
            metadata={
                "unpushed_count": len(unpushed),
                "bloat_total": bloat["total_pending"],
                "drift_score": drift_score,
            },
        )
        await db.store_node(audit_node)
        logger.info(f"✅ Audit results persisted to SurrealDB as {audit_node.id}")
        await db.close()
    except Exception as e:
        logger.warning(f"⚠️ Failed to persist to SurrealDB (falling back to filesystem only): {e}")

    logger.info(f"✅ Assessment complete. Report saved to {report_path}")
    print(report)


if __name__ == "__main__":
    import os

    asyncio.run(run_assessment())
