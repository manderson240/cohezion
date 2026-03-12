#!/usr/bin/env python3
"""
Hourly Job: Autonomic Quality Audit
Showcases SKILL: AUTONOMIC_QUALITY_GUARD_PRIME
Delegate: qwen3-coder-next:latest (Deep Reasoning)
"""

import asyncio
import logging
import re
import sys
from datetime import datetime
from pathlib import Path


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import trackio

from cohezion.swarm.compound_client import get_compound_client


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("QualityGuard")


async def main():
    logger.info("🛡️ Starting Hourly Quality Audit (The Audit-of-Audits)...")

    # Initialize Trackio (Local only)
    trackio.init(project="cohezion-core")

    # 1. Sensing: Collect recent job outputs
    pulse_dir = Path("apps/dashboard/src/assets/data")
    memory_file = Path("memory/session_snapshot.md")
    patch_dir = Path("src/cohezion/skills/patches")

    recent_outputs = []

    # Check for recent pulse
    pulses = sorted(pulse_dir.glob("pulse_*.json"))
    if pulses:
        recent_outputs.append(f"Pulse: {pulses[-1].read_text()[:500]}...")

    # Check memory snapshot
    if memory_file.exists():
        recent_outputs.append(f"Memory: {memory_file.read_text()[-500:]}")

    # Check for recent patch
    patches = sorted(patch_dir.glob("refinement_*.md"))
    if patches:
        recent_outputs.append(f"Skill Patch: {patches[-1].read_text()[:500]}...")

    if not recent_outputs:
        logger.info("⚠️ No recent outputs found to audit. Skipping.")
        trackio.alert(
            title="Audit Skipped",
            text="No recent outputs found to audit.",
            level=trackio.AlertLevel.WARN,
        )
        trackio.finish()
        return

    # 2. Analysis: Delegate to High-Tier model for semantic drift detection
    client = get_compound_client()
    prompt = f"""
    You are an AUTONOMIC_QUALITY_GUARD_PRIME specialist.
    Perform a 'Deep Audit' on the following recent automation outputs.
    
    Outputs:
    {chr(10).join(recent_outputs)}
    
    Instruction:
    - Check for 'Semantic Drift': Do these outputs align with our core Cohezion principles (Compound Engineering, HIHO Stability)?
    - Identify any 'Hallucinations' or logical inconsistencies.
    - Rate overall System Coherence (0.0 to 1.0). Return only the number on the first line.
    - If Coherence < 0.8, propose a 'Counter-Prompt' to fix the drift in the originating job.
    """

    # Force use of a high-tier model by requesting 'debate' or 'analysis' task type
    response = await client.generate(prompt, task_type="analysis")

    # Parse coherence score
    coherence_score = 0.0
    try:
        match = re.search(r"(\d+\.\d+)", response.split("\n")[0])
        if match:
            coherence_score = float(match.group(1))
    except (ValueError, IndexError):
        logger.warning("Could not parse coherence score from response.")

    # Log to Trackio
    trackio.log({"system_coherence": coherence_score})

    if coherence_score < 0.5:
        trackio.alert(
            title="CRITICAL DRIFT",
            text=f"System Coherence dropped to {coherence_score:.2f}",
            level=trackio.AlertLevel.ERROR,
        )
    elif coherence_score < 0.8:
        trackio.alert(
            title="Warning: Semantic Drift",
            text=f"System Coherence is {coherence_score:.2f}. Counter-prompt proposed.",
            level=trackio.AlertLevel.WARN,
        )

    # 3. Manifestation: Save the audit report
    audit_dir = Path("reports/audits")
    audit_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H")
    audit_file = audit_dir / f"meta_audit_{timestamp}.md"

    with open(audit_file, "w") as f:
        f.write(f"# Meta-Audit Report {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(response)

    logger.info(f"✅ Meta-Audit complete. Report: {audit_file}")
    trackio.finish()


if __name__ == "__main__":
    asyncio.run(main())
