"""Tip-of-Spear Routing with Confidence-Based Escalation and Agent Sovereignty.

Architecture:
  Request → Constitutional Check → Domain Detection → Model Selection (HOT tier)
      ↓
  Execute → Confidence Check (<0.7?) → Escalate to WARM tier
      ↓
  Execute → Confidence Check (<0.7?) → Escalate to COLD tier
      ↓
  Execute → Confidence Check (<0.7?) → Escalate to CLOUD tier
      ↓
  Final Result (with sovereignty metadata)

Key Features:
- Constitutional compliance (hard lines: WMD, CSAM, critical infrastructure)
- HIHO coherence monitoring (0.45-0.55 optimal window)
- Idempotency keys for deterministic responsibility
- Observable AI (pre-action state exposure)
- Google Stitch MCP integration for UI workflows
- EDL consensus for complex decisions (3/5 quorum)

Usage:
    from cohezion.swarm.tip_of_spear_router import TipOfTheSpearRouter

    router = TipOfTheSpearRouter()
    result = await router.route_with_sovereignty(
        request="Calculate derivative of f(x) = 3x²",
        agent_id="math-agent-1"
    )

    if result.constitutional_violation:
        logger.error(f"Blocked: {result.violation_reason}")
    elif result.confidence < 0.7:
        logger.warning(f"Low confidence, escalated {result.escalation_count} times")
    else:
        logger.info(f"Success: {result.model} (confidence {result.confidence})")
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from typing import Any

from cohezion.swarm.cost_aware_router import CostAwareRouter, QueryComplexityAnalyzer
from cohezion.swarm.model_pool_config import TierConfig


logger = logging.getLogger(__name__)


class ModelTier(Enum):
    """Model tier for escalation path."""

    HOT = "hot"  # Always loaded, <100ms
    WARM = "warm"  # Loaded at startup, ~200ms
    COLD = "cold"  # On-demand, 1-5s load
    CLOUD = "cloud"  # API call, variable latency


class ConstitutionalViolation(Enum):
    """Hard line violations (automatic rejection)."""

    WMD = "wmd"  # Weapons of mass destruction
    CRITICAL_INFRASTRUCTURE = "critical_infrastructure"  # Power, water, financial attacks
    MALICIOUS_CODE = "malicious_code"  # Cyberweapons
    CSAM = "csam"  # Child sexual abuse material
    UNDERMINING_OVERSIGHT = "undermining_oversight"  # State hiding, log obfuscation
    SPECIES_THREAT = "species_threat"  # AGI weaponization, human disempowerment
    ILLEGITIMATE_POWER = "illegitimate_power"  # Coups, electoral manipulation


@dataclass
class SovereigntyCheckResult:
    """Result of sovereignty validation checks."""

    constitutional_compliant: bool
    violation: ConstitutionalViolation | None = None
    ethical_score: float = 1.0  # 0.0-1.0, 1.0 = perfect
    hiho_stability: float = 0.5  # 0.0-1.0, peaks at 0.5 coherence
    requires_human_review: bool = False
    warnings: list[str] = field(default_factory=list)


@dataclass
class RoutingResult:
    """Result of tip-of-spear routing with sovereignty metadata."""

    success: bool
    model: str
    tier: ModelTier
    response: str
    confidence: float
    escalation_count: int
    constitutional_violation: ConstitutionalViolation | None
    sovereignty_metadata: dict[str, Any]
    idempotency_key: str
    execution_time_ms: float


class ConstitutionalChecker:
    """Check requests against constitutional hard lines."""

    # Keywords for hard line violations
    WMD_KEYWORDS = {
        "biological weapon",
        "chemical weapon",
        "nuclear weapon",
        "radiological weapon",
        "bioweapon",
        "nerve agent",
        "anthrax",
        "plutonium",
        "uranium enrichment",
    }

    CRITICAL_INFRA_KEYWORDS = {
        "power grid attack",
        "water supply attack",
        "financial system attack",
        "scada exploit",
        "industrial control attack",
    }

    MALICIOUS_CODE_KEYWORDS = {
        "cyberweapon",
        "ransomware",
        "trojan",
        "rootkit",
        "botnet",
        "ddos attack",
        "sql injection exploit",
    }

    CSAM_KEYWORDS = {
        # (Content filter handles actual detection, this is keyword-based)
        "csam",
        "child exploitation",
    }

    UNDERMINING_OVERSIGHT_KEYWORDS = {
        "hide logs",
        "obfuscate traces",
        "delete audit trail",
        "bypass monitoring",
    }

    SPECIES_THREAT_KEYWORDS = {
        "agi weaponization",
        "human disempowerment",
        "extinction event",
        "takeover humanity",
    }

    ILLEGITIMATE_POWER_KEYWORDS = {
        "electoral manipulation",
        "coup d'état",
        "overthrow government",
        "election fraud",
    }

    def check_constitutional_compliance(self, request: str) -> SovereigntyCheckResult:
        """Check request against constitutional hard lines.

        Args:
            request: User request to validate

        Returns:
            SovereigntyCheckResult with compliance status
        """
        request_lower = request.lower()

        # Check each hard line
        if any(kw in request_lower for kw in self.WMD_KEYWORDS):
            return SovereigntyCheckResult(
                constitutional_compliant=False,
                violation=ConstitutionalViolation.WMD,
                ethical_score=0.0,
            )

        if any(kw in request_lower for kw in self.CRITICAL_INFRA_KEYWORDS):
            return SovereigntyCheckResult(
                constitutional_compliant=False,
                violation=ConstitutionalViolation.CRITICAL_INFRASTRUCTURE,
                ethical_score=0.0,
            )

        if any(kw in request_lower for kw in self.MALICIOUS_CODE_KEYWORDS):
            return SovereigntyCheckResult(
                constitutional_compliant=False,
                violation=ConstitutionalViolation.MALICIOUS_CODE,
                ethical_score=0.0,
            )

        if any(kw in request_lower for kw in self.CSAM_KEYWORDS):
            return SovereigntyCheckResult(
                constitutional_compliant=False,
                violation=ConstitutionalViolation.CSAM,
                ethical_score=0.0,
            )

        if any(kw in request_lower for kw in self.UNDERMINING_OVERSIGHT_KEYWORDS):
            return SovereigntyCheckResult(
                constitutional_compliant=False,
                violation=ConstitutionalViolation.UNDERMINING_OVERSIGHT,
                ethical_score=0.0,
            )

        if any(kw in request_lower for kw in self.SPECIES_THREAT_KEYWORDS):
            return SovereigntyCheckResult(
                constitutional_compliant=False,
                violation=ConstitutionalViolation.SPECIES_THREAT,
                ethical_score=0.0,
            )

        if any(kw in request_lower for kw in self.ILLEGITIMATE_POWER_KEYWORDS):
            return SovereigntyCheckResult(
                constitutional_compliant=False,
                violation=ConstitutionalViolation.ILLEGITIMATE_POWER,
                ethical_score=0.0,
            )

        # All checks passed
        return SovereigntyCheckResult(
            constitutional_compliant=True, violation=None, ethical_score=1.0
        )


class TipOfTheSpearRouter:
    """Tip-of-spear routing with confidence-based escalation and sovereignty enforcement.

    Routing cascade:
    1. HOT tier (phi3:mini, 2.2GB, <100ms) - Fast, simple queries
    2. WARM tier (qwen2-math:7b, 4.7GB, ~200ms) - Domain specialists
    3. COLD tier (phi4:latest, 9GB, 1-5s) - Advanced reasoning
    4. CLOUD tier (qwen3.5:cloud, API) - Final fallback

    Confidence threshold: 0.7 (escalate if below)
    HIHO optimal window: 0.45-0.55 coherence
    """

    def __init__(
        self,
        confidence_threshold: float = 0.7,
        max_escalations: int = 3,
        hiho_min: float = 0.45,
        hiho_max: float = 0.55,
    ):
        """Initialize tip-of-spear router.

        Args:
            confidence_threshold: Minimum confidence to accept result (default: 0.7)
            max_escalations: Maximum tier escalations before giving up (default: 3)
            hiho_min: Minimum HIHO coherence for optimal stability (default: 0.45)
            hiho_max: Maximum HIHO coherence for optimal stability (default: 0.55)
        """
        self.confidence_threshold = confidence_threshold
        self.max_escalations = max_escalations
        self.hiho_min = hiho_min
        self.hiho_max = hiho_max

        # Components
        self.cost_aware_router = CostAwareRouter.get_default()
        self.complexity_analyzer = QueryComplexityAnalyzer()
        self.constitutional_checker = ConstitutionalChecker()
        self.tier_config = TierConfig()

        # Statistics
        self.total_requests = 0
        self.constitutional_violations = 0
        self.escalations_by_tier: dict[str, int] = {
            "hot_to_warm": 0,
            "warm_to_cold": 0,
            "cold_to_cloud": 0,
        }

    def generate_idempotency_key(self, request: str, agent_id: str) -> str:
        """Generate deterministic idempotency key.

        Args:
            request: User request (normalized)
            agent_id: Agent identifier

        Returns:
            SHA-256 hash for idempotent action tracking
        """
        # Normalize request (lowercase, strip whitespace)
        normalized = request.lower().strip()
        key_input = f"{agent_id}:{normalized}"

        return sha256(key_input.encode()).hexdigest()

    def check_hiho_stability(self, coherence: float) -> tuple[float, list[str]]:
        """Check HIHO stability and generate warnings.

        Args:
            coherence: Current agent coherence (0.0-1.0)

        Returns:
            Tuple of (hiho_stability, warnings)
            - hiho_stability: 0.0-1.0, peaks at 0.5 coherence
            - warnings: List of warning messages
        """
        # HIHO stability: peaks at exactly 0.5, falls off symmetrically
        hiho_stability = 1.0 - abs(coherence - 0.5) * 2.0
        hiho_stability = max(0.0, min(1.0, hiho_stability))

        warnings = []
        if coherence < self.hiho_min:
            warnings.append(
                f"Coherence too low ({coherence:.2f} < {self.hiho_min}): "
                "Agent too uncertain, escalate to human"
            )
        elif coherence > self.hiho_max:
            warnings.append(
                f"Coherence too high ({coherence:.2f} > {self.hiho_max}): "
                "Agent overconfident, inject uncertainty"
            )

        return hiho_stability, warnings

    async def route_with_sovereignty(
        self,
        request: str,
        agent_id: str,
        initial_tier: ModelTier = ModelTier.HOT,
    ) -> RoutingResult:
        """Route request through tip-of-spear with sovereignty enforcement.

        Args:
            request: User request
            agent_id: Agent identifier for journey tracking
            initial_tier: Starting tier (default: HOT)

        Returns:
            RoutingResult with response, confidence, and sovereignty metadata
        """
        start_time = time.time()
        self.total_requests += 1

        # Step 1: Generate idempotency key
        idempotency_key = self.generate_idempotency_key(request, agent_id)

        # Step 2: Constitutional check (hard lines)
        constitutional_check = self.constitutional_checker.check_constitutional_compliance(request)

        if not constitutional_check.constitutional_compliant:
            self.constitutional_violations += 1
            logger.error(f"Constitutional violation: {constitutional_check.violation.value}")

            return RoutingResult(
                success=False,
                model="BLOCKED",
                tier=ModelTier.HOT,
                response=f"Request blocked due to constitutional violation: {constitutional_check.violation.value}",
                confidence=0.0,
                escalation_count=0,
                constitutional_violation=constitutional_check.violation,
                sovereignty_metadata={
                    "constitutional_check": "FAILED",
                    "violation": constitutional_check.violation.value,
                    "ethical_score": 0.0,
                },
                idempotency_key=idempotency_key,
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        # Step 3: Detect domain + complexity
        domain = self.complexity_analyzer.detect_domain(request)
        complexity = self.complexity_analyzer.analyze(request)

        logger.info(
            f"Request domain: {domain}, complexity: {complexity.value}, "
            f"starting tier: {initial_tier.value}"
        )

        # Step 4: Cascade through tiers with confidence checks
        current_tier = initial_tier
        escalation_count = 0
        result = None

        while escalation_count <= self.max_escalations:
            # Select model for current tier
            model = self._select_model_for_tier(current_tier, domain, complexity)

            # Execute with model (simulated for now)
            result = await self._execute_with_model(model, request)

            logger.info(
                f"Tier {current_tier.value}: model={model}, confidence={result['confidence']:.2f}"
            )

            # Check confidence
            if result["confidence"] >= self.confidence_threshold:
                # Success! Confidence meets threshold
                break

            # Escalate to next tier
            escalation_count += 1
            next_tier = self._get_next_tier(current_tier)

            if next_tier is None:
                # No more tiers to escalate to
                logger.warning(
                    f"Max escalations reached ({self.max_escalations}), "
                    f"final confidence: {result['confidence']:.2f}"
                )
                break

            # Track escalation
            escalation_key = f"{current_tier.value}_to_{next_tier.value}"
            self.escalations_by_tier[escalation_key] = (
                self.escalations_by_tier.get(escalation_key, 0) + 1
            )

            logger.info(
                f"Low confidence ({result['confidence']:.2f} < {self.confidence_threshold}), "
                f"escalating to {next_tier.value}"
            )

            current_tier = next_tier

        # Step 5: HIHO coherence check
        # (For now, use confidence as proxy for coherence)
        coherence = result["confidence"]
        hiho_stability, hiho_warnings = self.check_hiho_stability(coherence)

        # Step 6: Build sovereignty metadata
        sovereignty_metadata = {
            "constitutional_check": "PASSED",
            "ethical_score": constitutional_check.ethical_score,
            "hiho_stability": hiho_stability,
            "coherence": coherence,
            "warnings": hiho_warnings,
            "domain": domain,
            "complexity": complexity.value,
        }

        execution_time_ms = (time.time() - start_time) * 1000

        return RoutingResult(
            success=True,
            model=result["model"],
            tier=current_tier,
            response=result["response"],
            confidence=result["confidence"],
            escalation_count=escalation_count,
            constitutional_violation=None,
            sovereignty_metadata=sovereignty_metadata,
            idempotency_key=idempotency_key,
            execution_time_ms=execution_time_ms,
        )

    def _select_model_for_tier(self, tier: ModelTier, domain: str | None, complexity) -> str:
        """Select optimal model for tier + domain.

        Args:
            tier: Current tier (HOT/WARM/COLD/CLOUD)
            domain: Domain specialization (math/code/vision) or None
            complexity: Query complexity (SIMPLE/MEDIUM/COMPLEX)

        Returns:
            Model name
        """
        if tier == ModelTier.HOT:
            # HOT tier: Fast, general models
            return "phi3:mini"

        elif tier == ModelTier.WARM:
            # WARM tier: Domain specialists
            if domain == "math":
                return "qwen2-math:7b"
            elif domain == "code":
                return "qwen2.5-coder:7b"
            elif domain == "vision":
                return "moondream:latest"
            else:
                # General warm model
                return "qwen2.5-coder:7b"

        elif tier == ModelTier.COLD:
            # COLD tier: Advanced reasoning
            if domain == "code":
                return "deepcoder:14b"
            else:
                return "phi4:latest"

        else:  # CLOUD
            # CLOUD tier: Gemini fallback chain (cost-optimized)
            # Primary: Gemini Pro (2M context, best quality)
            # Fallback: Gemini Flash (1M context, 7x cheaper)
            if domain == "code":
                return "gemini-2.5-pro"
            else:
                return "gemini-2.5-flash"

    def _get_next_tier(self, current_tier: ModelTier) -> ModelTier | None:
        """Get next tier in escalation path.

        Args:
            current_tier: Current tier

        Returns:
            Next tier or None if at final tier
        """
        escalation_path = {
            ModelTier.HOT: ModelTier.WARM,
            ModelTier.WARM: ModelTier.COLD,
            ModelTier.COLD: ModelTier.CLOUD,
            ModelTier.CLOUD: None,  # Final tier
        }
        return escalation_path.get(current_tier)

    async def _execute_with_model(self, model: str, request: str) -> dict:
        """Execute request with specified model (SIMULATED).

        Args:
            model: Model name
            request: User request

        Returns:
            Dict with model, response, confidence
        """
        # SIMULATION: In real implementation, this would call Ollama/cloud APIs
        await asyncio.sleep(0.05)  # Simulate latency

        # Simulate confidence based on model tier
        if "phi3:mini" in model:
            confidence = 0.65  # Often needs escalation
        elif "qwen2" in model or "ministral" in model or "moondream" in model:
            confidence = 0.75  # Usually sufficient
        elif "phi4" in model or "deepcoder" in model:
            confidence = 0.85  # High confidence
        else:  # Cloud models
            confidence = 0.95  # Highest confidence

        return {
            "model": model,
            "response": f"[SIMULATED RESPONSE from {model}]",
            "confidence": confidence,
        }

    def get_statistics(self) -> dict:
        """Get routing statistics.

        Returns:
            Dict with escalation counts, violation counts
        """
        return {
            "total_requests": self.total_requests,
            "constitutional_violations": self.constitutional_violations,
            "escalations": self.escalations_by_tier,
            "violation_rate": (
                self.constitutional_violations / self.total_requests
                if self.total_requests > 0
                else 0.0
            ),
        }
