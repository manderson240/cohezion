# Implementation Plan: Overnight Geometric Research & Skill Synthesis

## Background & Motivation
The Cohezion platform is fully synchronous, asynchronous, and guarded. To achieve true self-improving AGI, we must activate an overnight autonomous research pipeline. By integrating **AgentSkills** (standardized tool execution), **autoresearch** (autonomous literature and hypothesis generation), and the geometric insights from **Awesome-Latent-Space** (topology, manifold mapping), we can enable the platform to autonomously discover, test, and encode new knowledge into its 12D physical and 256D latent manifolds.

## Scope & Impact
1.  **AgentSkills Integration**: Import the `AgentSkills` framework, mapping its tools into our `data_mesh_registry.json` to vastly expand the Swarm's capabilities overnight.
2.  **Autonomous Research Pipeline**: Implement an `autoresearch_daemon.py` that utilizes `cohezion-research` to pull SOTA papers (specifically targeting Latent Space Geometry).
3.  **Geometric Correspondence (Awesome-Latent-Space)**: Map the newly researched concepts into the FLUME VAE 256D latent space. Use advanced geometric techniques (persistent homology, manifold interpolation) to find structural overlaps with our existing 12D `physics_state` trajectories.
4.  **Skill Synthesis**: Orchestrate the synthesis of new executable skills and deterministic policies from these geometric correspondences.

## Specialist Team Execution Strategy (Strict V-Model Enforcement)

### Phase 1: Tool Integration & Mesh Sourcing (System Architects & Hardware Specialists)
**Objective**: Expand the agentic toolset via AgentSkills.
**Tasks**:
- Create an `AgentSkillsBridge` that dynamically imports and wraps the `AgentSkills` framework into our FastMCP `skills_server_mcp.py` or a dedicated `agentskills_mcp.py` server.
- Run `make mcp-guard` to auto-parse these new tools and add them to the `data_mesh_registry.json`.
- Ensure all new tools require strict `AutonomyTier` validation via the `AutonomyEngine`.

### Phase 2: Autonomous Literature Review (Physics Engineers & Research Orchestrators)
**Objective**: Establish the `autoresearch` overnight polling loop.
**Tasks**:
- Create `src/cohezion/research/scripts/autoresearch_daemon.py`.
- Configure the daemon to query arXiv and HuggingFace for terms related to "Latent Space Geometry", "Manifold Topology", and "Representation Learning" (from the `Awesome-Latent-Space` repository).
- The daemon will spawn a `ResearchOrchestrator` swarm to summarize and hypothesize based on the literature.
- Output: A set of high-confidence hypotheses and theoretical models saved to `data/universe/research_*.json`.

### Phase 3: Geometric Mapping & Validation (Quantum Algorithm & Biologist Specialists)
**Objective**: Establish the "geometric correspondence" between the new literature and our 12D manifold.
**Tasks**:
- Create a `GeometricCorrespondencer` within the `LatentLinker` (`kg_guard.py` or new `geometry_guard.py`).
- Convert the new hypotheses into 256D `FlumeVAE` thought vectors.
- Perform a topological mapping (e.g., measuring curvature, geodesic distance) between these new hypothesis vectors and the existing vectors of our successful `Journey` trajectories.
- If a geometric overlap (correspondence) is found, validate the hypothesis by writing a deterministic test harness using the `AgentSkills` tools.

### Phase 4: Policy Distillation (System Architects)
**Objective**: Solidify the validated geometric correspondences into permanent code.
**Tasks**:
- The `OMEGA Distiller` (`omega_distiller.py`) reads the successful geometric validations.
- It translates these proven structural overlaps into new `[POLICY]` definitions in `src/cohezion/policies/` and markdown guides in `SKILL_PRIME.md`.

## Verification & Testing
- **Phase 1**: Run `make mcp-guard` and verify the `data_mesh_registry.json` expands with AgentSkills tools.
- **Phase 2**: Trigger the `autoresearch_daemon.py` manually and verify a `research_*.json` artifact is produced.
- **Phase 3**: Verify the `GeometricCorrespondencer` successfully calculates a topological overlap score for the new research artifact.
- **Phase 4**: Verify `make omega-distiller` produces a new Python policy script from the research.