#!/usr/bin/env python3
"""
Auto-Improving Code Review Agent - Compound Loop Demonstration

This agentic workflow exercises all 5 ported Cohezion skills:
1. cohezion-compound-engineering (alignment gate, execution)
2. cohezion-hiho-stability (coherence monitoring)
3. cohezion-flume (experience encoding)
4. cohezion-model-routing (model selection)
5. cohezion-retrospective (pattern extraction)

The workflow continuously improves by:
- Checking request alignment before execution
- Monitoring HIHO coherence throughout
- Encoding experiences to FLUME
- Selecting optimal models per subtask
- Retrospecting and refining skills
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import random
import time
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==========================================
# DATA STRUCTURES
# ==========================================

@dataclass
class ExecutionResult:
    """Result of a task execution."""
    task_id: str
    success: bool
    output: str
    duration_seconds: float
    tokens_used: int
    coherence: float  # HIHO coherence score
    anomaly_score: float  # Deviation from expected
    model_used: str
    degraded: bool = False
    metadata: dict = field(default_factory=dict)

@dataclass
class CoherenceReading:
    """HIHO coherence measurement."""
    timestamp: float
    value: float  # 0.0-1.0
    regime: str  # sub-HIHO, HIHO-stable, super-HIHO
    recommendation: str

@dataclass
class WorkflowSession:
    """Tracks a complete compound engineering session."""
    session_id: str
    start_time: float
    executions: list[ExecutionResult] = field(default_factory=list)
    coherence_history: list[CoherenceReading] = field(default_factory=list)
    learnings: list[dict] = field(default_factory=list)
    skill_refinements: list[dict] = field(default_factory=list)

# ==========================================
# SKILL 1: COMPOUND ENGINEERING (Core Loop)
# ==========================================

class CompoundEngine:
    """Execute → Retrospect → Refine loop."""

    def __init__(self):
        self.sessions: dict[str, WorkflowSession] = {}

    def start_session(self) -> WorkflowSession:
        """Initialize new compound session."""
        session = WorkflowSession(
            session_id=hashlib.sha256(str(time.time()).encode()).hexdigest()[:16],
            start_time=time.time(),
        )
        self.sessions[session.session_id] = session
        logger.info(f"Started session {session.session_id}")
        return session

    def check_alignment(self, request: str, available_skills: list[str]) -> dict:
        """Alignment gate - check if request is well-formed."""
        # Simulate alignment analysis
        coherence = self._estimate_alignment(request)

        return {
            "coherence": coherence,
            "should_proceed": coherence >= 0.5,
            "issues": self._identify_issues(request) if coherence < 0.5 else [],
            "estimated_tokens": len(request.split()) * 3,
        }

    def _estimate_alignment(self, request: str) -> float:
        """Estimate request coherence (0.0-1.0)."""
        # Heuristic: clear requests have actionable verbs and specific targets
        lower = request.lower()

        score = 0.5  # Start at HIHO

        # Boost for specific keywords
        if any(v in lower for v in ["implement", "fix", "refactor", "test", "analyze"]):
            score += 0.2

        # Boost for file mentions
        if ".py" in lower or "/" in lower:
            score += 0.15

        # Boost for clear scope
        if len(request.split()) > 5 and len(request.split()) < 50:
            score += 0.1

        # Penalty for vague terms
        if any(v in lower for v in ["something", "thing", "stuff", "do something"]):
            score -= 0.3

        return max(0.0, min(1.0, score))

    def _identify_issues(self, request: str) -> list[str]:
        """Identify why alignment is low."""
        issues = []
        lower = request.lower()

        if len(request.split()) < 5:
            issues.append("Request too brief")
        if any(v in lower for v in ["something", "thing"]):
            issues.append("Vague target")
        if "." not in request and "/" not in request:
            issues.append("No specific file mentioned")

        return issues

    async def execute_task(
        self,
        session: WorkflowSession,
        task: str,
        executor_fn: Callable[..., Coroutine[Any, Any, dict]],
    ) -> ExecutionResult:
        """Execute with full instrumentation."""
        task_id = f"{session.session_id}-{len(session.executions)}"

        # Pre-execution alignment check
        alignment = self.check_alignment(task, ["code_review", "refactor", "analyze"])
        if not alignment["should_proceed"]:
            logger.warning(f"Low alignment ({alignment['coherence']:.2f}): {alignment['issues']}")

        start = time.time()

        try:
            # Execute
            result = await executor_fn(task)
            success = result.get("success", True)
            output = result.get("output", "")
            tokens = result.get("tokens", 0)
        except Exception as e:
            success = False
            output = str(e)
            tokens = 0

        duration = time.time() - start

        # Measure coherence post-execution
        coherence = self._measure_execution_coherence(success, output)

        exec_result = ExecutionResult(
            task_id=task_id,
            success=success,
            output=output,
            duration_seconds=duration,
            tokens_used=tokens,
            coherence=coherence,
            anomaly_score=random.uniform(0.1, 0.4),  # Simulated
            model_used=result.get("model", "unknown"),
        )

        session.executions.append(exec_result)
        return exec_result

    def _measure_execution_coherence(self, success: bool, output: str) -> float:
        """Measure HIHO coherence from execution."""
        if not success:
            return random.uniform(0.1, 0.3)  # Low coherence on failure

        # Check output quality indicators
        coherence = 0.5

        if len(output) > 100:
            coherence += 0.1  # Substantive output
        if "error" not in output.lower() and "fail" not in output.lower():
            coherence += 0.1  # Clean output
        if "```" in output:
            coherence += 0.1  # Has code blocks

        return min(1.0, coherence)

# ==========================================
# SKILL 2: HIHO STABILITY
# ==========================================

class HIHOMonitor:
    """Monitor and maintain 0.5 coherence point."""

    def calculate_hiho_score(self, coherence: float) -> float:
        """Score peaks at 0.5, drops at extremes."""
        return 1.0 - abs(coherence - 0.5) * 2

    def diagnose(self, coherence: float) -> CoherenceReading:
        """Diagnose coherence regime."""
        if coherence < 0.3:
            regime = "sub-HIHO"
            recommendation = "increase_token_diversity"
        elif coherence > 0.7:
            regime = "super-HIHO"
            recommendation = "inject_langevin_noise"
        else:
            regime = "HIHO-stable"
            recommendation = "maintain"

        return CoherenceReading(
            timestamp=time.time(),
            value=coherence,
            regime=regime,
            recommendation=recommendation,
        )

    def apply_damping(self, coherence: float) -> float:
        """Apply negative feedback if over-coherent."""
        if coherence > 0.7:
            # Inject small noise to maintain 0.5
            return coherence - random.uniform(0.05, 0.15)
        return coherence

# ==========================================
# SKILL 3: FLUME (Experience Encoding)
# ==========================================

class FlumeEncoder:
    """Encode experiences to 256D vectors."""

    def __init__(self, z_dim: int = 256):
        self.z_dim = z_dim
        self.experience_cache: dict[str, dict] = {}

    def encode(self, text: str) -> list[float]:
        """Encode text to z-space (simulated)."""
        # Deterministic hash-based encoding
        hash_val = hashlib.sha256(text.encode()).hexdigest()
        seed = int(hash_val[:8], 16)

        random.seed(seed)
        z = [random.gauss(0, 1) for _ in range(self.z_dim)]

        # Normalize
        magnitude = sum(x**2 for x in z) ** 0.5
        return [x / magnitude for x in z]

    def similarity(self, z1: list[float], z2: list[float]) -> float:
        """Cosine similarity."""
        dot = sum(a * b for a, b in zip(z1, z2))
        return dot  # Already normalized

    def cache_experience(self, task: str, result: ExecutionResult):
        """Store executed experience."""
        key = self.encode(task)
        key_str = hashlib.sha256(json.dumps(key).encode()).hexdigest()[:16]

        self.experience_cache[key_str] = {
            "task": task,
            "success": result.success,
            "coherence": result.coherence,
            "model": result.model_used,
            "z": key,  # The encoded vector
        }

        logger.info(f"Cached experience: {key_str}")

    def find_similar(self, task: str, threshold: float = 0.85) -> list[dict]:
        """Find similar past experiences."""
        z_task = self.encode(task)
        similar = []

        for key, exp in self.experience_cache.items():
            sim = self.similarity(z_task, exp["z"])
            if sim > threshold:
                similar.append({**exp, "similarity": sim})

        return sorted(similar, key=lambda x: x["similarity"], reverse=True)

# ==========================================
# SKILL 4: MODEL ROUTING
# ==========================================

class ModelRouter:
    """Intelligent local LLM selection."""

    MODEL_MAP = {
        "code": {"primary": "deepseek-r1:14b", "fallback": ["qwen3.5:14b", "phi4"]},
        "analyze": {"primary": "qwen3.5:32b", "fallback": ["deepseek-r1:14b"]},
        "fast": {"primary": "phi4-mini", "fallback": ["falcon3:7b"]},
        "embed": {"primary": "nomic-embed-text", "fallback": []},
    }

    def classify_task(self, task: str) -> str:
        """Classify to task type."""
        lower = task.lower()

        if any(kw in lower for kw in ["fix", "refactor", "implement"]):
            return "code"
        elif any(kw in lower for kw in ["analyze", "review", "check"]):
            return "analyze"
        elif any(kw in lower for kw in ["embed", "vectorize"]):
            return "embed"
        else:
            return "fast"

    def select_model(self, task: str) -> dict:
        """Select model for task."""
        task_type = self.classify_task(task)
        config = self.MODEL_MAP.get(task_type, self.MODEL_MAP["fast"])

        # Simulate availability check
        available = self._check_ollama_available(config["primary"])

        if available:
            model = config["primary"]
        else:
            model = config["fallback"][0] if config["fallback"] else "phi4-mini"

        return {
            "task_type": task_type,
            "model": model,
            "estimated_ram_gb": 14 if "14b" in model else (32 if "32b" in model else 6),
        }

    def _check_ollama_available(self, model: str) -> bool:
        """Check if model is available (simulated)."""
        # In real implementation: subprocess.run(["ollama", "list"], ...)
        return True

# ==========================================
# SKILL 5: RETROSPECTIVE (Pattern Extraction)
# ==========================================

class RetrospectionEngine:
    """Extract patterns and refine skills."""

    def analyze_execution(self, result: ExecutionResult) -> dict:
        """Analyze execution for lessons."""
        insights = []
        should_refine = False

        # Coherence check
        if result.coherence >= 0.4 and result.success:
            should_refine = True
            insights.append(f"Execution succeeded with coherence {result.coherence:.2f}")

        if result.coherence > 0.7:
            insights.append(f"Over-coherent ({result.coherence:.2f}): risk of hallucination")

        if not result.success:
            insights.append(f"Failed: {result.output[:100]}")

        # Calculate compound score
        compound_score = 0.0
        if result.success:
            compound_score = result.coherence * 0.5 + (1.0 - result.anomaly_score) * 0.3 + 0.2

        return {
            "should_refine": should_refine,
            "coherence": result.coherence,
            "compound_score": compound_score,
            "insights": insights,
            "recommendation": self._generate_recommendation(result),
        }

    def _generate_recommendation(self, result: ExecutionResult) -> str:
        """Generate actionable recommendation."""
        if not result.success:
            return "Investigate failure root cause"
        if result.coherence < 0.4:
            return "Add more context to prompts"
        if result.coherence > 0.7:
            return "Reduce overconfidence with damping"
        return "Refine skill with extracted patterns"

    def suggest_skill_refinement(
        self,
        session: WorkflowSession,
    ) -> list[dict]:
        """Suggest skills needing updates."""
        # If we have 3+ learnings in a domain, suggest refinement
        by_domain: dict[str, list] = {}
        for learning in session.learnings:
            domain = learning.get("domain", "general")
            if domain not in by_domain:
                by_domain[domain] = []
            by_domain[domain].append(learning)

        suggestions = []
        for domain, learnings in by_domain.items():
            if len(learnings) >= 3:
                suggestions.append({
                    "skill_name": f"{domain.upper()}_PRIME",
                    "reason": f"{len(learnings)} learnings accumulated",
                    "suggested_additions": [l["title"] for l in learnings[:5]],
                })

        return suggestions

# ==========================================
# AGENTIC WORKFLOW: AUTO-IMPROVING CODE REVIEW
# ==========================================

class AutoImprovingCodeReviewAgent:
    """
    Code review agent that continuously improves using compound engineering.
    
    Each code review:
    1. Checks alignment before execution
    2. Monitors HIHO stability throughout
    3. Encodes experience to FLUME
    4. Routes to optimal model per subtask
    5. Retrospects and refines skills
    """

    def __init__(self):
        self.compound = CompoundEngine()
        self.hiho = HIHOMonitor()
        self.flume = FlumeEncoder()
        self.router = ModelRouter()
        self.retro = RetrospectionEngine()

        self.session: WorkflowSession | None = None

    async def start(self):
        """Start compound session."""
        self.session = self.compound.start_session()
        logger.info("Auto-Improving Code Review Agent started")
        logger.info(f"Session: {self.session.session_id}")

    async def review_code(self, code_snippet: str, context: str = "") -> dict:
        """
        Review code with compound engineering.
        
        Args:
            code_snippet: Code to review
            context: Additional context
            
        Returns:
            Review results with learnings
        """
        # Step 1: Alignment Check (COMPOUND ENGINEERING)
        task = f"Review code: {context}\n\n{code_snippet[:200]}"
        alignment = self.compound.check_alignment(
            task,
            ["code_review", "security_analysis", "style_check"]
        )

        logger.info(f"Alignment: {alignment['coherence']:.2f} (proceed={alignment['should_proceed']})")

        if not alignment['should_proceed']:
            return {
                "proceeded": False,
                "reason": f"Low alignment: {alignment['issues']}",
            }

        # Step 2: Model Selection (MODEL ROUTING)
        model_selection = self.router.select_model(task)
        logger.info(f"Selected model: {model_selection['model']}")

        # Step 3: Execute Review (simulated)
        async def review_executor(task: str) -> dict:
            # Simulated code review
            await asyncio.sleep(0.5)

            # Simulate finding issues
            issues_found = []
            if "import" not in code_snippet:
                issues_found.append("Missing imports")
            if "def " not in code_snippet and "class " not in code_snippet:
                issues_found.append("No function or class defined")

            output = f"Review complete. Issues: {len(issues_found)}\n"
            if issues_found:
                output += "\n".join(f"- {i}" for i in issues_found)
            else:
                output += "✓ Code looks good"

            return {
                "success": True,
                "output": output,
                "tokens": 512,
                "model": model_selection["model"],
            }

        result = await self.compound.execute_task(
            self.session,
            task,
            review_executor,
        )

        # Step 4: HIHO Stability Check
        hiho_reading = self.hiho.diagnose(result.coherence)
        self.session.coherence_history.append(hiho_reading)

        logger.info(f"HIHO: {result.coherence:.2f} → {hiho_reading.regime} ({hiho_reading.recommendation})")

        if hiho_reading.recommendation == "inject_langevin_noise":
            result.coherence = self.hiho.apply_damping(result.coherence)

        # Step 5: FLUME Experience Encoding
        self.flume.cache_experience(task, result)

        # Find similar past experiences
        similar = self.flume.find_similar(task, threshold=0.7)
        if similar:
            logger.info(f"Found {len(similar)} similar experiences")

        # Step 6: Retrospection (PATTERN EXTRACTION)
        analysis = self.retro.analyze_execution(result)

        # Store learning if warranted
        if analysis["should_refine"]:
            learning = {
                "id": len(self.session.learnings) + 1,
                "title": f"Code review: {context or 'unknown'}",
                "coherence": result.coherence,
                "compound_score": analysis["compound_score"],
                "domain": "code_review",
            }
            self.session.learnings.append(learning)
            logger.info(f"Learning extracted: {learning['compound_score']:.3f}")

        return {
            "proceeded": True,
            "result": result,
            "hiho": hiho_reading,
            "analysis": analysis,
            "similar_experiences": len(similar),
        }

    async def retro_session(self) -> dict:
        """
        Retro the entire session and suggest skill refinements.
        """
        if not self.session or not self.session.executions:
            return {"error": "No session to retro"}

        # Session metrics
        total_execs = len(self.session.executions)
        successful = sum(1 for e in self.session.executions if e.success)
        avg_coherence = sum(e.coherence for e in self.session.executions) / total_execs

        logger.info(f"Session retro: {successful}/{total_execs} successful, "
                   f"avg_coherence={avg_coherence:.2f}")

        # Suggest skill refinements
        refinements = self.retro.suggest_skill_refinement(self.session)

        for ref in refinements:
            logger.info(f"Suggest refinement: {ref['skill_name']} ({ref['reason']})")
            self.session.skill_refinements.append(ref)

        return {
            "total_executions": total_execs,
            "success_rate": successful / total_execs,
            "avg_coherence": avg_coherence,
            "hiho_stable": sum(1 for h in self.session.coherence_history
                            if h.regime == "HIHO-stable") / len(self.session.coherence_history),
            "learnings_extracted": len(self.session.learnings),
            "skill_refinements_suggested": len(refinements),
        }

# ==========================================
# DEMONSTRATION
# ==========================================

async def main():
    """Run the agentic workflow demonstration."""

    print("=" * 70)
    print("AUTO-IMPROVING CODE REVIEW AGENT")
    print("Compound Engineering Workflow Demonstration")
    print("=" * 70)
    print()

    agent = AutoImprovingCodeReviewAgent()
    await agent.start()

    # Test cases: vary in quality to demonstrate compound loop
    test_snippets = [
        # Clear, specific (high alignment)
        ("def process_data(data):\n    return [x*2 for x in data]",
         "Data processing function"),

        # Vague (low alignment)
        ("x = 5\ny = 10",
         "Something with variables"),

        # Complex (moderate alignment)
        ("import json\n\nclass Config:\n    def load(self, path):\n        with open(path) as f:\n            return json.load(f)",
         "Configuration loader"),
    ]

    print(f"Processing {len(test_snippets)} code reviews...")
    print("-" * 70)

    for i, (code, context) in enumerate(test_snippets, 1):
        print(f"\nReview #{i}: {context}")
        print(f"Code: {code[:50]}...")

        result = await agent.review_code(code, context)

        if result["proceeded"]:
            print("  Status: ✓ Complete")
            print(f"  Coherence: {result['result'].coherence:.2f} ({result['hiho'].regime})")
            print(f"  Compound Score: {result['analysis']['compound_score']:.3f}")
            print(f"  Similar experiences: {result['similar_experiences']}")

            if result['analysis']['should_refine']:
                print("  ✓ Learning extracted")
        else:
            print(f"  Status: ✗ Blocked ({result['reason']})")

        await asyncio.sleep(0.1)  # Brief pause

    print("\n" + "=" * 70)
    print("SESSION RETROSPECTIVE")
    print("=" * 70)

    retro = await agent.retro_session()

    print(f"Total Executions: {retro['total_executions']}")
    print(f"Success Rate: {retro['success_rate']:.1%}")
    print(f"Average Coherence: {retro['avg_coherence']:.2f}")
    print(f"HIHO Stable Time: {retro['hiho_stable']:.1%}")
    print(f"Learnings Extracted: {retro['learnings_extracted']}")
    print(f"Skill Refinements: {retro['skill_refinements_suggested']}")

    print("\n" + "=" * 70)
    print("ALL 5 SKILLS EXERCISED:")
    print("  ✓ cohezion-compound-engineering (alignment, execution, session)")
    print("  ✓ cohezion-hiho-stability (coherence monitoring, damping)")
    print("  ✓ cohezion-flume (experience encoding, similarity search)")
    print("  ✓ cohezion-model-routing (task classification, model selection)")
    print("  ✓ cohezion-retrospective (pattern extraction, refinements)")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
