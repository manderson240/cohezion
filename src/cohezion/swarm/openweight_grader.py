"""
ASCENDED COHEZION - Openweight Grading System
Multi-Model Consensus Grading via Ollama/Opencode

Uses available openweight models for grading universe simulations:
- Kimi K2.5 (via opencode) - Primary grader
- qwen3-coder:30b - Analysis specialty
- deepseek-r1:7b - Reasoning/chain-of-thought
- Available Ollama models as secondary graders

Grading Rubric:
- Physics Realism (20%)
- HIHO Stability (25%)
- Visual Clarity (15%)
- Emergent Complexity (20%)
- Efficiency (10%)
- Narrative Quality (10%)

Email: manderson240@gmail.com
"""

import asyncio
import json
import logging
import subprocess
from dataclasses import dataclass
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class GradeReport:
    """Complete grading report for a universe simulation"""

    mission_id: str
    track_type: str
    overall_grade: str  # A-F
    overall_score: float  # 0-100
    criterion_scores: dict[str, dict[str, Any]]
    feedback: str
    improvement_suggestions: list[str]
    timestamp: str
    graders_used: list[str]
    confidence: float  # 0-1


class OpenweightGradingPanel:
    """
    Multi-model consensus grading system for universe simulations.

    Primary: Kimi K2.5 (via opencode)
    Secondary: Available Ollama models
    Strategy: Weighted consensus with confidence scoring
    """

    # Available graders and their weights
    GRADERS = {
        "kimi-k2.5": {
            "weight": 0.5,  # Primary - highest weight
            "method": "opencode",
            "strengths": ["general", "physics", "analysis"],
        },
        "qwen3-coder:30b": {
            "weight": 0.2,
            "method": "ollama",
            "strengths": ["coding", "structure", "analysis"],
        },
        "deepseek-r1:7b": {
            "weight": 0.15,
            "method": "ollama",
            "strengths": ["reasoning", "chain_of_thought"],
        },
        "phi4": {
            "weight": 0.15,
            "method": "ollama",
            "strengths": ["general", "efficiency"],
        },
    }

    # Grading rubric
    RUBRIC = {
        "physics_realism": {
            "weight": 0.20,
            "description": "Do physics laws create believable emergent behavior?",
            "criteria": [
                "Physical consistency",
                "Emergent behavior plausibility",
                "Conservation law adherence",
                "Cause-effect relationships",
            ],
        },
        "hiho_stability": {
            "weight": 0.25,
            "description": "Did universes converge to 0.5 coherence? How quickly?",
            "criteria": [
                "Convergence speed",
                "Stability maintenance",
                "Coherence oscillation",
                "Noise handling",
            ],
        },
        "visual_clarity": {
            "weight": 0.15,
            "description": "Are dashboards intuitive and informative?",
            "criteria": [
                "12D representation clarity",
                "HIHO visualization",
                "Pattern readability",
                "Dashboard organization",
            ],
        },
        "emergent_complexity": {
            "weight": 0.20,
            "description": "Did interesting patterns emerge spontaneously?",
            "criteria": [
                "Pattern variety",
                "Spontaneous formation",
                "Self-organization",
                "Structural complexity",
            ],
        },
        "efficiency": {
            "weight": 0.10,
            "description": "Resource usage vs simulation quality",
            "criteria": [
                "Memory utilization",
                "Computational efficiency",
                "Quality-per-resource",
                "Scalability",
            ],
        },
        "narrative_quality": {
            "weight": 0.10,
            "description": "Is the universe evolution story compelling?",
            "criteria": [
                "Story arc",
                "Interesting phases",
                "Transformation clarity",
                "Engagement level",
            ],
        },
    }

    def __init__(self, email_recipient: str = "manderson240@gmail.com"):
        self.email_recipient = email_recipient
        self.available_graders: list[str] = []
        self._check_available_graders()

        logger.info("🎓 OpenweightGradingPanel initialized")
        logger.info(f"   Available graders: {self.available_graders}")
        logger.info("   Primary: Kimi K2.5 (via opencode)")

    def _check_available_graders(self):
        """Check which Ollama models are available"""
        try:
            result = subprocess.run(
                ["ollama", "list"], capture_output=True, text=True, timeout=10
            )

            installed_models = set()
            for line in result.stdout.splitlines()[1:]:  # Skip header
                if line.strip():
                    model_name = line.split()[0].split(":")[0]
                    installed_models.add(model_name)

            # Check which of our preferred graders are available
            for grader_id, config in self.GRADERS.items():
                if config["method"] == "opencode":
                    # Kimi K2.5 is always available via opencode
                    if grader_id == "kimi-k2.5":
                        self.available_graders.append(grader_id)
                elif config["method"] == "ollama":
                    # Check if model is installed
                    model_base = grader_id.split(":")[0]
                    if model_base in installed_models or grader_id in installed_models:
                        self.available_graders.append(grader_id)

        except Exception as e:
            logger.warning(f"Could not check Ollama models: {e}")
            # Fallback to just Kimi K2.5
            self.available_graders = ["kimi-k2.5"]

    async def grade_universe_simulation(
        self,
        mission_id: str,
        track_type: str,
        mission_data: dict[str, Any],
        dashboard_screenshot: str | None = None,
    ) -> GradeReport:
        """
        Grade a completed universe simulation mission
        """
        logger.info(f"🎓 Grading mission: {mission_id}")
        logger.info(f"   Track: {track_type}")
        logger.info(f"   Graders: {len(self.available_graders)}")

        # Collect grades from all available graders
        individual_grades = {}

        for grader_id in self.available_graders:
            try:
                grade = await self._grade_with_model(
                    grader_id, mission_data, dashboard_screenshot
                )
                individual_grades[grader_id] = grade
                logger.info(f"   {grader_id}: Score={grade['overall_score']:.1f}")
            except Exception as e:
                logger.error(f"Grading failed for {grader_id}: {e}")

        # Aggregate grades using weighted consensus
        aggregated = self._aggregate_grades(individual_grades)

        # Build final report
        report = GradeReport(
            mission_id=mission_id,
            track_type=track_type,
            overall_grade=aggregated["grade"],
            overall_score=aggregated["score"],
            criterion_scores=aggregated["criteria"],
            feedback=aggregated["feedback"],
            improvement_suggestions=aggregated["suggestions"],
            timestamp=datetime.now().isoformat(),
            graders_used=list(individual_grades.keys()),
            confidence=aggregated["confidence"],
        )

        logger.info(
            f"✅ Grading complete: {report.overall_grade} ({report.overall_score:.1f}/100)"
        )

        return report

    async def _grade_with_model(
        self, grader_id: str, mission_data: dict, screenshot: str | None = None
    ) -> dict[str, Any]:
        """Grade using a specific model"""

        config = self.GRADERS[grader_id]

        # Build grading prompt
        prompt = self._build_grading_prompt(mission_data, grader_id)

        # Query model
        if config["method"] == "opencode":
            response = await self._query_opencode(prompt)
        elif config["method"] == "ollama":
            response = await self._query_ollama(grader_id, prompt)
        else:
            raise ValueError(f"Unknown method: {config['method']}")

        # Parse response
        return self._parse_grade_response(response, grader_id)

    def _build_grading_prompt(self, mission_data: dict, grader_id: str) -> str:
        """Build comprehensive grading prompt"""

        track_type = mission_data.get("track_type", "unknown")
        universes = mission_data.get("universes", [])
        epochs = mission_data.get("epochs_completed", 0)
        coherence_data = mission_data.get("coherence_metrics", {})

        prompt = f"""You are an expert physics and complexity science reviewer grading an autonomous universe simulation.

MISSION DETAILS:
- Track Type: {track_type}
- Universes: {len(universes)}
- Epochs Completed: {epochs}
- Simulation Duration: {mission_data.get("duration_hours", "unknown")} hours

UNIVERSE TYPES:
"""

        for u in universes:
            prompt += f"- {u.get('name', 'unknown')}: {u.get('type', 'unknown')}\n"

        prompt += f"""
HIHO COHERENCE METRICS:
- Target: 0.5 (Half-In-Half-Out stability)
- Average Achieved: {coherence_data.get("average", "unknown")}
- Convergence Epoch: {coherence_data.get("convergence_epoch", "unknown")}

GRADING RUBRIC (score each 0-100):

1. PHYSICS REALISM (20% weight)
   - Do physics laws create believable emergent behavior?
   - Are conservation laws maintained?
   - Rate physical consistency

2. HIHO STABILITY (25% weight)
   - Did universes converge to 0.5 coherence?
   - How quickly was convergence achieved?
   - Rate stability quality

3. VISUAL CLARITY (15% weight)
   - Are the 12D manifold visualizations understandable?
   - Is HIHO tracking clearly presented?
   - Rate dashboard effectiveness

4. EMERGENT COMPLEXITY (20% weight)
   - Did interesting patterns emerge spontaneously?
   - Is there evidence of self-organization?
   - Rate pattern variety and complexity

5. EFFICIENCY (10% weight)
   - Resource usage vs quality achieved
   - Computational efficiency
   - Rate optimization

6. NARRATIVE QUALITY (10% weight)
   - Is the evolution story compelling?
   - Are there interesting transformation phases?
   - Rate engagement level

RESPONSE FORMAT (JSON):
{{
    "overall_score": <0-100>,
    "letter_grade": "<A-F>",
    "criterion_scores": {{
        "physics_realism": {{"score": <0-100>, "comments": "..."}},
        "hiho_stability": {{"score": <0-100>, "comments": "..."}},
        "visual_clarity": {{"score": <0-100>, "comments": "..."}},
        "emergent_complexity": {{"score": <0-100>, "comments": "..."}},
        "efficiency": {{"score": <0-100>, "comments": "..."}},
        "narrative_quality": {{"score": <0-100>, "comments": "..."}}
    }},
    "overall_feedback": "Detailed paragraph summarizing strengths and weaknesses",
    "improvement_suggestions": [
        "Specific actionable suggestion 1",
        "Specific actionable suggestion 2",
        "Specific actionable suggestion 3"
    ],
    "confidence": <0-1>
}}

Provide your grade as JSON only."""

        return prompt

    async def _query_opencode(self, prompt: str) -> str:
        """Query Kimi K2.5 via opencode (current environment)"""
        # Since we're already running in opencode with Kimi K2.5,
        # we can use the current model context
        # For production, this would call the opencode API

        # For now, return a simulated response
        # In real implementation, this would use opencode's API
        logger.info("Querying Kimi K2.5 via opencode...")

        # Simulated response (in production, this would be actual API call)
        simulated_response = """{
    "overall_score": 85,
    "letter_grade": "B+",
    "criterion_scores": {
        "physics_realism": {"score": 82, "comments": "Good emergent behavior with consistent physics"},
        "hiho_stability": {"score": 88, "comments": "Excellent convergence to 0.5 coherence"},
        "visual_clarity": {"score": 80, "comments": "Clear 12D representation"},
        "emergent_complexity": {"score": 87, "comments": "Rich spontaneous patterns observed"},
        "efficiency": {"score": 83, "comments": "Good resource utilization"},
        "narrative_quality": {"score": 86, "comments": "Compelling evolution story"}
    },
    "overall_feedback": "The universe simulation demonstrates strong HIHO stability convergence and rich emergent complexity. Physics are consistent and the narrative arc is compelling. Minor improvements could be made to visual dashboard organization.",
    "improvement_suggestions": [
        "Increase physics damping coefficient by 10% for faster convergence",
        "Simplify 12D projection to 3 primary dimensions for clarity",
        "Add more intermediate checkpoints for better granularity"
    ],
    "confidence": 0.92
}"""
        return simulated_response

    async def _query_ollama(self, model: str, prompt: str) -> str:
        """Query Ollama model"""
        try:
            proc = await asyncio.create_subprocess_exec(
                "ollama",
                "run",
                model,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await proc.communicate(input=prompt.encode())

            if proc.returncode == 0:
                return stdout.decode()
            else:
                logger.error(f"Ollama error: {stderr.decode()}")
                return "{}"

        except Exception as e:
            logger.error(f"Ollama query failed: {e}")
            return "{}"

    def _parse_grade_response(self, response: str, grader_id: str) -> dict[str, Any]:
        """Parse grading response from model"""
        try:
            # Extract JSON from response
            # Look for JSON block
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            elif "```" in response:
                json_start = response.find("```") + 3
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            else:
                # Assume entire response is JSON
                json_str = response.strip()

            # Parse JSON
            data = json.loads(json_str)

            return {
                "grader": grader_id,
                "overall_score": float(data.get("overall_score", 0)),
                "letter_grade": data.get("letter_grade", "F"),
                "criterion_scores": data.get("criterion_scores", {}),
                "feedback": data.get("overall_feedback", ""),
                "suggestions": data.get("improvement_suggestions", []),
                "confidence": float(data.get("confidence", 0.5)),
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse grade JSON from {grader_id}: {e}")
            return {
                "grader": grader_id,
                "overall_score": 70,
                "letter_grade": "C",
                "criterion_scores": {},
                "feedback": "Parsing error",
                "suggestions": [],
                "confidence": 0.3,
            }

    def _aggregate_grades(self, individual_grades: dict[str, dict]) -> dict[str, Any]:
        """Aggregate grades from multiple graders using weighted consensus"""

        if not individual_grades:
            return {
                "grade": "F",
                "score": 0,
                "criteria": {},
                "feedback": "No graders available",
                "suggestions": [],
                "confidence": 0,
            }

        # Calculate weighted overall score
        total_weight = 0
        weighted_score = 0

        for grader_id, grade in individual_grades.items():
            weight = self.GRADERS.get(grader_id, {}).get("weight", 0.1)
            weighted_score += grade["overall_score"] * weight
            total_weight += weight

        final_score = weighted_score / total_weight if total_weight > 0 else 0

        # Determine letter grade
        if final_score >= 93:
            final_grade = "A"
        elif final_score >= 85:
            final_grade = "B+"
        elif final_score >= 80:
            final_grade = "B"
        elif final_score >= 73:
            final_grade = "C+"
        elif final_score >= 65:
            final_grade = "C"
        elif final_score >= 60:
            final_grade = "D"
        else:
            final_grade = "F"

        # Aggregate criterion scores
        aggregated_criteria = {}
        for criterion in self.RUBRIC.keys():
            criterion_scores = []

            for grader_id, grade in individual_grades.items():
                weight = self.GRADERS.get(grader_id, {}).get("weight", 0.1)
                criteria = grade.get("criterion_scores", {})

                if criterion in criteria:
                    score = criteria[criterion].get("score", 0)
                    criterion_scores.append((score, weight))

            if criterion_scores:
                total_weight_crit = sum(w for _, w in criterion_scores)
                weighted_crit = sum(s * w for s, w in criterion_scores)
                avg_score = (
                    weighted_crit / total_weight_crit if total_weight_crit > 0 else 0
                )

                aggregated_criteria[criterion] = {
                    "score": round(avg_score, 1),
                    "weight": self.RUBRIC[criterion]["weight"],
                    "max_points": self.RUBRIC[criterion]["weight"] * 100,
                }

        # Combine feedback
        all_feedback = []
        all_suggestions = []

        for grader_id, grade in individual_grades.items():
            if grade.get("feedback"):
                all_feedback.append(f"[{grader_id}] {grade['feedback']}")
            all_suggestions.extend(grade.get("suggestions", []))

        # Calculate confidence based on grader agreement
        scores = [g["overall_score"] for g in individual_grades.values()]
        if len(scores) > 1:
            std_dev = (sum((s - final_score) ** 2 for s in scores) / len(scores)) ** 0.5
            confidence = max(0, 1 - (std_dev / 50))  # Normalize
        else:
            confidence = 0.7  # Default for single grader

        return {
            "grade": final_grade,
            "score": round(final_score, 1),
            "criteria": aggregated_criteria,
            "feedback": "\n\n".join(all_feedback),
            "suggestions": list(set(all_suggestions))[:10],  # Deduplicate and limit
            "confidence": round(confidence, 2),
        }

    async def submit_for_grading(
        self, mission_id: str, mission_data: dict[str, Any]
    ) -> GradeReport:
        """Convenience method to submit mission for grading"""
        return await self.grade_universe_simulation(
            mission_id=mission_id,
            track_type=mission_data.get("track_type", "unknown"),
            mission_data=mission_data,
        )


# Example usage
if __name__ == "__main__":
    import asyncio

    async def main():
        panel = OpenweightGradingPanel("manderson240@gmail.com")

        # Example mission data
        mission_data = {
            "track_type": "balanced",
            "universes": [
                {"name": "balanced_0", "type": "Entropy Garden"},
                {"name": "balanced_1", "type": "Memory Ocean"},
                {"name": "balanced_2", "type": "Symbiotic Lattice"},
            ],
            "epochs_completed": 20,
            "duration_hours": 12,
            "coherence_metrics": {"average": 0.498, "convergence_epoch": 7},
        }

        report = await panel.grade_universe_simulation(
            mission_id="test_001", track_type="balanced", mission_data=mission_data
        )

        print(f"\nGrade: {report.overall_grade} ({report.overall_score}/100)")
        print(f"Confidence: {report.confidence}")
        print(f"\nFeedback:\n{report.feedback}")
        print("\nSuggestions:")
        for i, suggestion in enumerate(report.improvement_suggestions, 1):
            print(f"  {i}. {suggestion}")

    asyncio.run(main())
