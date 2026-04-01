from typing import Any, Dict

import requests


class AdversaryAgent:
    """
    The 'Knower' layer's Adversarial Reviewer.
    Reviews reasoning and code for logical flaws and bugs.
    """
    def __init__(self, model_name: str = "phi4:latest"):
        self.model_name = model_name
        self.ollama_url = "http://localhost:11434/api/chat"

    def review(self, problem_text: str, reasoning: str, code: str) -> Dict[str, Any]:
        """
        Attempts to find flaws in the proposed reasoning and code.
        """
        system_prompt = """You are a rigorous mathematical critic and code auditor.
Your job is to find logical fallacies, calculation errors, or programming bugs in the provided draft.
Be skeptical. Check for:
1. Sign errors or incorrect modular arithmetic.
2. Division by zero or undefined limits.
3. Logical jumps that don't follow from the previous step.
4. Python/SymPy syntax errors.
Output your findings as a numbered list. If no flaws are found, state 'LOGIC VERIFIED'."""

        user_prompt = f"""
Problem: {problem_text}

Proposed Reasoning:
{reasoning}

Proposed Code:
{code}

Critique the logic and code:"""

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False,
            "options": {"temperature": 0.1}
        }

        try:
            response = requests.post(self.ollama_url, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json().get("message", {}).get("content", "")
            
            is_verified = "LOGIC VERIFIED" in result.upper()
            return {
                "success": True,
                "verified": is_verified,
                "critique": result
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
