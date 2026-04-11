# SKILL: AUTONOMIC_HEALING_PRIME

## DOMAIN EXPERTISE
Expert in designing and maintaining self-healing, autonomic AI platforms. Specializes in "Sense/Feel/Act" control loops, trajectory drift detection, and proactive resource re-balancing within the Cohezion ecosystem.

## KEY TEXTS & CONCEPTS
* **The Heartbeat Protocol**: Proactive monitoring of long-running daemons via periodic timestamp updates in `data/system/heartbeats.json`.
* **Trajectory Drift**: Real-time detection of agentic coherence deviation from the HIHO 0.5 attractor.
* **Autonomic Actuation**: The capability of the system to autonomously terminate, restart, or tune processes based on health and velocity metrics.
* **Immune System (Gateway 13)**: The primary architectural layer responsible for system health and self-diagnosis.

## INSTRUCTION
1. **Monitor Heartbeats**: Regularly check `data/system/heartbeats.json` for all background daemons (`github-scout`, `autoresearch-daemon`). Flag failures if heartbeats are >5 minutes old.
2. **Correct Active Journeys**: Run `trajectory_guard.py` to monitor active trajectories. If drift is detected, synthesize a "Trajectory Correction" prompt and inject it into the session.
3. **Re-balance Resources**: If task velocity drops, reactively terminate `BRONZE` quality tier tasks to free up local VRAM for `GOLD` tier verification tasks.
4. **CI Enforcement**: Ensure `make health-guard` is part of the build pipeline to validate the platform's self-healing readiness.

## VERSION
v1.0 (Autonomic Ascension)

## SEE ALSO
- LAZY_INFRASTRUCTURE_PRIME.md
- MANIFOLD_INTEGRITY_PRIME.md
- DATA_GOVERNANCE_PRIME.md
