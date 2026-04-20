from dataclasses import dataclass

from math_parser import MathParser, MathProblemState


@dataclass
class SwarmTask:
    problem_id: str
    problem_text: str
    state: MathProblemState
    assigned_specialists: list[str]
    max_steps: int = 10
    dual_run: bool = True
    reasoning_complexity: float = 0.5


class SwarmCoordinator:
    def __init__(self, open_weight_only: bool = True):
        self.parser = MathParser()
        self.open_weight_only = open_weight_only
        self.specialists = {
            "Algebraist": "algebra",
            "NumberTheorist": "number_theory",
            "Geometer": "geometry",
            "Combinatorist": "combinatorics",
        }

    def plan_journey(self, problem_id: str, problem_text: str) -> SwarmTask:
        state = self.parser.parse(problem_text)
        domain_scores = {
            "Algebraist": state.algebra,
            "NumberTheorist": state.number_theory,
            "Geometer": state.geometry,
            "Combinatorist": state.combinatorics,
        }
        sorted_specialists = sorted(domain_scores.items(), key=lambda x: x[1], reverse=True)
        assigned = [name for name, score in sorted_specialists if score > 0.2]
        if not assigned:
            assigned = ["Algebraist", "NumberTheorist"]

        if len(assigned) < 2:
            assigned.append("Algebraist" if assigned[0] != "Algebraist" else "NumberTheorist")

        # Compute reasoning complexity from structural depth and token density
        reasoning_complexity = state.structural_depth * 0.3 + state.token_density * 0.7

        return SwarmTask(
            problem_id=problem_id,
            problem_text=problem_text,
            state=state,
            assigned_specialists=assigned,
            reasoning_complexity=reasoning_complexity,
        )
