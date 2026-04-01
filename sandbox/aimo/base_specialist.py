import json
import re
from typing import Dict, Optional

import requests
from adversary_agent import AdversaryAgent
from symbolic_executor import SymbolicExecutor


class BaseSpecialist:
    """
    Base class for Specialist Swarm Agents using local, cloud, and hybrid models.
    Integrates Adversarial TDD for high-fidelity reasoning.
    """

    def __init__(self, name: str, model_name: Optional[str] = None, timeout: int = 300):
        self.name = name
        self.default_models = {
            "Algebraist": "qwen2-math:1.5b",
            "NumberTheorist": "qwen2-math:1.5b",
            "Geometer": "phi3:mini",
            "Combinatorist": "qwen2-math:1.5b",
            "Coordinator": "phi3:mini",
        }
        self.model_name = model_name or self.default_models.get(name, "qwen2-math:1.5b")
        self.ollama_url = "http://localhost:11434/api/chat"
        self.prompts = self._load_prompts()
        self.knowledge_vault = self._load_vault()
        self.executor = SymbolicExecutor()
        self.adversary = AdversaryAgent()
        self.timeout = timeout  # 5 minutes for reasoning models (default 300)

    def _load_prompts(self) -> Dict[str, str]:
        with open("specialist_prompts.json", "r") as f:
            return json.load(f)

    def _load_vault(self) -> str:
        with open("math_knowledge_vault.json", "r") as f:
            vault = json.load(f)
            vault_str = "\n".join(
                [
                    f"{k.upper()}:\n" + "\n".join([f"- {name}: {desc}" for name, desc in v.items()])
                    for k, v in vault.items()
                ]
            )
            return vault_str

    def solve(self, problem_text: str, keep_alive: str = "1m") -> str:
        system_prompt = self.prompts.get(self.name, "You are a helpful mathematical assistant.")
        system_prompt += f"\n\nLocal Knowledge Base (Reference as needed):\n{self.knowledge_vault}"

        # 1. Cloud Provider Call via Ollama (gemini-*, claude-*, qwen3.5:cloud, etc.)
        if (
            self.model_name.endswith(":cloud")
            or self.model_name.startswith("gemini-")
            or self.model_name.startswith("claude-")
        ):
            print(f"[{self.name}] Calling Cloud Model: {self.model_name}")
            messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Problem: {problem_text}\n\nProvide step-by-step reasoning and final answer in \\boxed{{}} format.",
                },
            ]

            payload = {
                "model": self.model_name,
                "messages": messages,
                "stream": False,
                "options": {"temperature": 0.2, "num_ctx": 16384},
            }

            try:
                response = requests.post(self.ollama_url, json=payload, timeout=self.timeout)
                response.raise_for_status()
                result = response.json()
                return result.get("message", {}).get("content", "\\boxed{0}")
            except Exception as e:
                return f"Error calling cloud model: {str(e)}"

        # 2. Standard Ollama Flow (local models)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Problem: {problem_text}\n\nReasoning and Final Answer:"},
        ]

        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "keep_alive": keep_alive,
            "options": {"temperature": 0.2, "num_ctx": 8192, "num_thread": 16},
        }

        try:
            response = requests.post(self.ollama_url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            result = response.json()
            initial_text = result.get("message", {}).get("content", "")

            # Adversarial Review Loop (Max 2 refinement cycles)
            for attempt in range(2):
                code_match = re.search(r"```python(.*?)```", initial_text, re.DOTALL)
                if code_match:
                    code_to_run = code_match.group(1).strip()

                    # A. ADVERSARIAL REVIEW
                    print(f"[{self.name}] Initiating Adversarial Review (Cycle {attempt + 1})...")
                    review_result = self.adversary.review(problem_text, initial_text, code_to_run)

                    if review_result.get("verified"):
                        print(f"[{self.name}] Logic Verified by Adversary.")
                    else:
                        print(
                            f"[{self.name}] Adversary found flaws: {review_result.get('critique')}"
                        )
                        messages.append({"role": "assistant", "content": initial_text})
                        messages.append(
                            {
                                "role": "user",
                                "content": f"An adversarial reviewer found potential flaws in your logic or code:\n{review_result.get('critique')}\n\nPlease fix these issues and provide a corrected Python code block.",
                            }
                        )
                        payload["messages"] = messages
                        retry_response = requests.post(
                            self.ollama_url, json=payload, timeout=self.timeout
                        )
                        retry_response.raise_for_status()
                        initial_text = retry_response.json().get("message", {}).get("content", "")
                        continue

                    # B. SYMBOLIC EXECUTION
                    exec_result = self.executor.execute(code_to_run)
                    if exec_result.get("success"):
                        messages.append({"role": "assistant", "content": initial_text})
                        messages.append(
                            {
                                "role": "user",
                                "content": f"Execution Result:\n{exec_result['results']}\n\nNow provide the final non-negative integer answer as \\boxed{{X}}.",
                            }
                        )
                        payload["messages"] = messages
                        response2 = requests.post(
                            self.ollama_url, json=payload, timeout=self.timeout
                        )
                        response2.raise_for_status()
                        return response2.json().get("message", {}).get("content", "")
                    else:
                        messages.append({"role": "assistant", "content": initial_text})
                        messages.append(
                            {
                                "role": "user",
                                "content": f"The symbolic code you wrote failed with the following error:\n{exec_result.get('error')}\nPlease identify the mistake and provide a corrected Python code block.",
                            }
                        )
                        payload["messages"] = messages
                        retry_response = requests.post(
                            self.ollama_url, json=payload, timeout=self.timeout
                        )
                        retry_response.raise_for_status()
                        initial_text = retry_response.json().get("message", {}).get("content", "")
                else:
                    return initial_text

            return initial_text

        except Exception as e:
            return f"Error calling Ollama: {str(e)}"

    def extract_answer(self, response_text: str) -> Optional[int]:
        # CRITICAL: Check for error BEFORE regex extraction (Story 1.2)
        if response_text.startswith("Error"):
            return 0
        match = re.search(r"\\boxed\{(\d+)\}", response_text)
        if match:
            return int(match.group(1)) % 100000
        numbers = re.findall(r"\d+", response_text)
        if numbers:
            return int(numbers[-1]) % 100000
        return 0
