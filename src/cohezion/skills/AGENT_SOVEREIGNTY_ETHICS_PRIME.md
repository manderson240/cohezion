---
name: agent-sovereignty-ethics-prime
description: "Sovereignty = Autonomous decision-making within ethical boundaries Safety = Constitutional constraints + security pipeline + human oversight Agency = Ability to act, learn, and evolve without explicit instruction"
---

# AGENT_SOVEREIGNTY_ETHICS_PRIME

**Skill**: Agent Sovereignty & Constitutional Governance
**Version**: 1.0
**Purpose**: Ensure safe agency within pre-established ethical codes and security contexts
**Governance**: CONSTITUTION.md + COHEZION_CHARTER.md + Security Pipeline
**Integration**: TipOfTheSpearRouter + Google Stitch MCP + CompoundExecutor

## Core Principle: Safe Sovereignty

**Sovereignty** = Autonomous decision-making within ethical boundaries
**Safety** = Constitutional constraints + security pipeline + human oversight
**Agency** = Ability to act, learn, and evolve without explicit instruction

```
Agent Intent → Constitutional Check → Security Filter → Sovereignty Approval → Execute
     ↓              ↓                      ↓                   ↓              ↓
  Request      Hard Lines         Prompt Guard         HIHO 0.5      Action Taken
             (WMD, CSAM)        Rate Limit          Coherence      + Journey Log
```

## 1. Constitutional Governance (Hard Constraints)

**From CONSTITUTION.md** - NEVER violated, regardless of user/operator instruction:

### Hard Lines (Automatic REJECT)

| Constraint | Detection Method | Response |
|------------|------------------|----------|
| **WMD Creation** | Keyword scan (biological, chemical, nuclear, radiological weapons) | Block + Log violation |
| **Critical Infrastructure Attack** | Pattern match (power grid, water, financial systems attack) | Block + Alert operator |
| **Malicious Code** | AST analysis for cyberweapon patterns | Block + Explain rejection |
| **CSAM** | Content filter (zero tolerance) | Block + Immediate escalation |
| **Undermining Oversight** | State hiding detection (encrypted logs, obfuscated traces) | Block + Transparency enforcement |
| **Species-Level Threat** | Existential risk pattern (AGI weaponization, human disempowerment) | Block + Human review |
| **Illegitimate Power** | Political coup, electoral manipulation patterns | Block + Ethical review |

**Implementation**:
```python
from cohezion.security.pipeline import SecurityPipeline

pipeline = SecurityPipeline()

# Check request against constitutional hard lines
result = pipeline.check_constitutional_compliance(request)

if result.violated:
    logger.critical(f"Constitutional violation: {result.constraint}")
    return ConstitutionalViolation(
        constraint=result.constraint,
        reason=result.reason,
        severity="CRITICAL",
        action="BLOCKED"
    )
```

### Ethical Practice (WARN but may proceed with caveats)

| Principle | Detection | Response |
|-----------|-----------|----------|
| **Honesty** | Confidence calibration, uncertainty tracking | Warn if confidence < 0.6, require human review |
| **Harm Avoidance** | Consequence prediction, impact analysis | Warn if potential harm score > 0.4 |
| **Transparency** | Hidden agenda detection | Warn if reasoning opacity > 0.5 |
| **Non-Deception** | Intent-vs-stated mismatch | Warn if mismatch detected, explain discrepancy |

**Implementation**:
```python
# Check ethical principles
ethical_score = pipeline.check_ethical_compliance(request, agent_state)

if ethical_score.honesty < 0.6:
    logger.warning(f"Low honesty score: {ethical_score.honesty}")
    # Proceed but flag for human review
    request.metadata["requires_human_review"] = True
    request.metadata["ethical_concern"] = "low_confidence"
```

## 2. HIHO Stability (0.5 Coherence Rule)

**From COHEZION_CHARTER.md**: All agent actions must maintain 0.5 coherence for stable reality precipitation.

### Coherence Monitoring

```python
from cohezion.universe.engine import AxiomaticState

def check_agent_coherence(agent_state: dict) -> float:
    """Check if agent state maintains HIHO stability.

    Returns:
        Coherence score (0.0-1.0). Optimal: 0.5
    """
    axiomatic = AxiomaticState(**agent_state)
    coherence = axiomatic.coherence_score()

    # HIHO stability peaks at 0.5
    hiho_stability = 1.0 - abs(coherence - 0.5) * 2.0

    return max(0.0, min(1.0, hiho_stability))
```

### Coherence Enforcement

| Coherence | HIHO Stability | Agent Action |
|-----------|----------------|--------------|
| < 0.3 | Low (< 0.4) | **RESTRICT**: Agent too uncertain, escalate to human |
| 0.3-0.4 | Medium (0.4-0.6) | **CAUTION**: Proceed with logging, flag for review |
| **0.45-0.55** | **HIGH (0.9-1.0)** | **OPTIMAL**: Full agency, minimal oversight |
| 0.55-0.7 | Medium (0.4-0.6) | **CAUTION**: Agent over-confident, inject uncertainty |
| > 0.7 | Low (< 0.4) | **RESTRICT**: Agent certainty too high, validate assumptions |

**Implementation**:
```python
hiho_stability = check_agent_coherence(agent_state)

if hiho_stability < 0.4:
    # Coherence outside HIHO window
    if agent_state.coherence < 0.5:
        action = "ESCALATE_TO_HUMAN"  # Too uncertain
        logger.warning(f"Agent coherence too low: {agent_state.coherence}")
    else:
        action = "INJECT_UNCERTAINTY"  # Too certain
        logger.warning(f"Agent coherence too high: {agent_state.coherence}")
        # Force confidence calibration
        result.confidence *= 0.8  # Reduce overconfidence
else:
    action = "PROCEED_WITH_AGENCY"
```

## 3. Idempotency & Deterministic Responsibility

**From CHARTER**: All agentic actions must use idempotency keys for reproducibility.

### Idempotency Protocol

```python
from hashlib import sha256
import json

def generate_idempotency_key(request: dict, agent_id: str) -> str:
    """Generate deterministic idempotency key.

    Args:
        request: Normalized request (sorted keys, canonical JSON)
        agent_id: Agent identifier

    Returns:
        SHA-256 hash for idempotent action tracking
    """
    # Canonical representation
    canonical = json.dumps(request, sort_keys=True)
    key_input = f"{agent_id}:{canonical}"

    return sha256(key_input.encode()).hexdigest()


# Usage in agent execution
idempotency_key = generate_idempotency_key(request, agent_id="researcher-1")

# Check if action already executed
if vault.check_idempotency_key(idempotency_key):
    logger.info(f"Action already executed, returning cached result")
    return vault.get_cached_result(idempotency_key)

# Execute and store with idempotency key
result = execute_action(request)
vault.store_result(idempotency_key, result)
```

## 4. Expert Domain Lattice (Consensus Governance)

**From CHARTER**: Complex problems routed through 5 specialist agents with 3/5 consensus.

### EDL Consensus Protocol

```python
from cohezion.swarm.specialist_agents_config import EDLConsensus

edl = EDLConsensus(
    agents=["architect", "engineer", "biologist", "qhw", "qalgo"],
    quorum=3,  # Minimum 3/5 for approval
    blocking_roles=["engineer", "qalgo"]  # Physics/compute veto
)

# Multi-agent vote
votes = []
for agent in edl.agents:
    response = agent.evaluate(request)
    votes.append({
        "agent": agent.role,
        "decision": response.decision,  # APPROVE | REVISE | REJECT
        "rationale": response.rationale,
        "confidence": response.confidence
    })

# Consensus decision
consensus = edl.resolve_consensus(votes)

if consensus.decision == "APPROVE":
    # ≥3 agents approved, no blocking rejections
    logger.info(f"EDL consensus: APPROVE ({consensus.vote_count})")
    proceed_with_execution()
elif consensus.decision == "REVISE":
    # 2 agents approve OR 1 blocking rejection with feedback
    logger.warning(f"EDL consensus: REVISE - {consensus.feedback}")
    revise_request(consensus.feedback)
else:  # REJECT
    # ≤1 agent approves OR 2+ blocking rejections
    logger.error(f"EDL consensus: REJECT - {consensus.reasons}")
    return RejectionResponse(reasons=consensus.reasons)
```

## 5. Integration with TipOfTheSpearRouter

**Sovereignty at Each Tier**:

```python
from cohezion.swarm.tip_of_spear_router import TipOfTheSpearRouter
from cohezion.security.agent_sovereignty import AgentSovereigntyLayer

router = TipOfTheSpearRouter()
sovereignty = AgentSovereigntyLayer(
    constitution_path=".agent/CONSTITUTION.md",
    charter_path=".agent/COHEZION_CHARTER.md"
)

# Multi-tier routing with sovereignty checks at each level
async def route_with_sovereignty(request: str, agent_id: str):
    """Route request through tip-of-spear with sovereignty enforcement."""

    # Step 1: Constitutional check (hard lines)
    constitutional_check = sovereignty.check_constitution(request)
    if constitutional_check.violated:
        return ConstitutionalViolation(constitutional_check)

    # Step 2: Ethical check (soft guidelines)
    ethical_score = sovereignty.check_ethics(request, agent_state)
    if ethical_score.requires_review:
        request.metadata["human_review"] = True

    # Step 3: Route to smallest model (HOT tier)
    decision = router.select_model(request)
    result = await execute_with_model(decision.model, request)

    # Step 4: Confidence check (HIHO coherence)
    if result.confidence < 0.7:
        # Escalate to WARM tier
        logger.info(f"Low confidence ({result.confidence}), escalating to WARM tier")
        warm_decision = router.escalate_to_warm(request, domain=decision.domain)
        result = await execute_with_model(warm_decision.model, request)

        # Re-check confidence
        if result.confidence < 0.7:
            # Final escalation to CLOUD
            logger.warning(f"Still low confidence, escalating to CLOUD")
            cloud_decision = router.escalate_to_cloud(request)
            result = await execute_with_model(cloud_decision.model, request)

    # Step 5: HIHO coherence check on result
    hiho_stability = check_agent_coherence(result.agent_state)
    if hiho_stability < 0.4:
        logger.warning(f"Result outside HIHO window: {hiho_stability}")
        result.metadata["coherence_warning"] = True
        result.metadata["hiho_stability"] = hiho_stability

    # Step 6: Journey logging (idempotency + traceability)
    idempotency_key = generate_idempotency_key(request, agent_id)
    journey_tracker.record_execution(
        agent_id=agent_id,
        request=request,
        result=result,
        idempotency_key=idempotency_key,
        sovereignty_checks={
            "constitutional": constitutional_check.status,
            "ethical": ethical_score.score,
            "hiho_stability": hiho_stability
        }
    )

    return result
```

## 6. Google Stitch MCP Integration

**Purpose**: Enable design-to-code workflows with agent sovereignty over UI generation.

### Stitch MCP Server Setup

```python
from cohezion.mcp.stitch_mcp_client import StitchMCPClient

stitch = StitchMCPClient(
    server_url="https://stitch-mcp.withgoogle.com",
    api_key=os.getenv("STITCH_API_KEY")
)

# Agent Skills integration
stitch.register_agent_skill("ui-generation", {
    "description": "Generate UI screens from text prompts",
    "sovereignty_level": "SUPERVISED",  # Requires human review
    "ethical_constraints": ["no_deceptive_ui", "accessibility_required"]
})

# Design Agent coordination
async def generate_ui_with_sovereignty(prompt: str, agent_id: str):
    """Generate UI via Stitch with constitutional compliance."""

    # Check prompt for deceptive patterns
    sovereignty_check = sovereignty.check_ui_prompt(prompt)
    if sovereignty_check.is_deceptive:
        logger.error(f"Deceptive UI pattern detected: {sovereignty_check.reason}")
        return Rejection(reason="UI must not deceive users")

    # Generate via Stitch
    design = await stitch.generate_design(prompt)

    # Extract Design DNA
    design_dna = await stitch.get_design_dna(design.project_id)

    # Ethical review: Check for dark patterns
    dark_patterns = sovereignty.check_dark_patterns(design_dna)
    if dark_patterns:
        logger.warning(f"Dark patterns detected: {dark_patterns}")
        design_dna.metadata["dark_pattern_warning"] = True
        design_dna.metadata["requires_human_review"] = True

    # Export to DESIGN.md (agent-friendly format)
    design_md = await stitch.export_design_md(design.project_id)

    # Journey tracking
    journey_tracker.record_design(
        agent_id=agent_id,
        prompt=prompt,
        design_dna=design_dna,
        sovereignty_checks={
            "deceptive_ui": False,
            "dark_patterns": dark_patterns,
            "accessibility": design_dna.accessibility_score
        }
    )

    return design_md
```

### Stitch Agent Skills (Pre-Built Workflows)

Cohezion can leverage Stitch's Agent Skills for UI automation:

| Skill | Purpose | Sovereignty Level |
|-------|---------|-------------------|
| **design-critique** | Real-time design feedback | AUTONOMOUS (low risk) |
| **voice-canvas** | Voice-controlled design updates | SUPERVISED (voice input = user intent) |
| **design-to-code** | Convert Stitch → HTML/React | AUTONOMOUS (deterministic) |
| **multi-version-reasoning** | Explore design alternatives | AUTONOMOUS (exploration) |
| **export-design-dna** | Extract design system metadata | AUTONOMOUS (read-only) |

**Integration Pattern**:
```python
# Use Stitch skill via MCP
skill_result = await stitch.execute_skill(
    skill_name="design-to-code",
    input_data={"project_id": design.project_id},
    sovereignty_context={
        "agent_id": "ui-agent-1",
        "ethical_constraints": ["no_deceptive_ui"],
        "human_review_required": False  # Deterministic conversion
    }
)
```

## 7. Observable AI (Transparency Requirement)

**From CHARTER**: Expose internal states, FLUME trajectories, and confidence levels *before* action.

### Pre-Action Transparency

```python
class TransparentAgentExecution:
    """Observable AI execution with pre-action state exposure."""

    async def execute_with_transparency(self, request: str, agent_id: str):
        # Step 1: Expose internal state BEFORE action
        pre_action_state = {
            "agent_id": agent_id,
            "request": request,
            "current_coherence": self.coherence_score(),
            "flume_position": self.flume_vae.get_latent_position(),
            "confidence_estimate": self.estimate_confidence(request),
            "routing_decision": self.router.select_model(request),
            "sovereignty_checks": {
                "constitutional": "PASS",
                "ethical_score": 0.85,
                "hiho_stability": 0.92
            }
        }

        logger.info(f"PRE-ACTION STATE: {json.dumps(pre_action_state, indent=2)}")

        # Step 2: Wait for human override window (if required)
        if pre_action_state["routing_decision"].requires_review:
            logger.warning("Action requires human review, waiting 5s for override...")
            await asyncio.sleep(5)
            # Check for human override signal
            if self.human_override_signal():
                logger.info("Human override received, aborting action")
                return HumanOverride(reason="Operator intervention")

        # Step 3: Execute action (fully observable)
        result = await self.execute_action(request)

        # Step 4: Post-action transparency
        post_action_state = {
            "result_confidence": result.confidence,
            "coherence_after": self.coherence_score(),
            "flume_trajectory": self.flume_vae.get_trajectory(),
            "sovereignty_violations": []
        }

        logger.info(f"POST-ACTION STATE: {json.dumps(post_action_state, indent=2)}")

        return result
```

## 8. Anti-Patterns (Common Sovereignty Violations)

| ❌ Anti-Pattern | ✅ Correct Pattern |
|----------------|-------------------|
| Execute action without constitutional check | Always check hard lines first, block violations |
| Ignore low confidence (<0.7), proceed anyway | Escalate to next tier or human review |
| Hide reasoning from human operators | Expose full state before action (Observable AI) |
| Skip idempotency key, allow duplicate actions | Generate deterministic key, check vault before execution |
| Route complex task to single agent | Use EDL consensus (3/5 quorum) for complex decisions |
| Generate deceptive UI patterns | Check for dark patterns, flag for human review |
| Operate outside HIHO coherence window (0.45-0.55) | Monitor coherence, inject uncertainty if >0.7, escalate if <0.3 |

## 9. Sovereignty Metrics Dashboard

Track agent sovereignty health:

```python
from cohezion.cost_optimization.local_savings_tracker import SovereigntyDashboard

dashboard = SovereigntyDashboard()

metrics = dashboard.get_sovereignty_metrics()

print(f"Constitutional Violations: {metrics.constitutional_violations}")  # Target: 0
print(f"Ethical Warnings: {metrics.ethical_warnings}")  # Target: <5%
print(f"HIHO Stability Avg: {metrics.avg_hiho_stability:.2f}")  # Target: >0.8
print(f"Idempotency Key Reuse: {metrics.idempotency_reuse_rate:.1%}")  # Target: <1%
print(f"EDL Consensus Rate: {metrics.edl_consensus_rate:.1%}")  # Target: >90%
print(f"Human Override Rate: {metrics.human_override_rate:.1%}")  # Target: <10%
print(f"Stitch Dark Pattern Detections: {metrics.stitch_dark_patterns}")  # Target: 0
```

## 10. Emergency Protocols

### Constitution Override (Operator Only)

```python
# ONLY for emergency situations (e.g., life-safety, critical infrastructure defense)
# Requires operator authentication + audit logging

def emergency_constitution_override(
    reason: str,
    operator_id: str,
    auth_token: str,
    time_limit_minutes: int = 15
):
    """EMERGENCY ONLY: Temporarily relax constitutional constraints.

    WARNING: This is a nuclear option. All actions logged to immutable audit trail.
    """
    # Verify operator credentials
    if not verify_operator_auth(operator_id, auth_token):
        raise UnauthorizedOverride("Invalid operator credentials")

    # Create override session (time-limited)
    override_session = {
        "operator_id": operator_id,
        "reason": reason,
        "timestamp": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(minutes=time_limit_minutes),
        "actions_taken": []
    }

    # Log to immutable audit trail
    audit_trail.log_emergency_override(override_session)

    # Alert all monitoring systems
    alerts.send_critical(f"CONSTITUTION OVERRIDE by {operator_id}: {reason}")

    return override_session
```

---

## Version History

- **v1.0** (2026-03-21): Initial skill - Constitutional governance, HIHO stability, idempotency, EDL consensus, Stitch MCP integration, Observable AI

**Implementation Status**: ✅ Specification Complete
**Next Phase**: Implement AgentSovereigntyLayer + TipOfTheSpearRouter + StitchMCPClient
**Expected Impact**: 100% constitutional compliance, >90% EDL consensus rate, zero deceptive UI generation
