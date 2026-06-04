"""AutoHarness: Automatic synthesis of code harnesses and policies for LLM agents.

Implements the DeepMind AutoHarness pattern (arXiv:2603.03329v1):
1. **Code-as-action-verifier**: Automatically synthesizes and refines deterministic validation logic (rules/constraints checking) to prevent illegal actions. Formulates this search over program space as a tree search guided by Thompson sampling.
2. **Harness-as-policy**: Distills the agent's decision logic into a deterministic program (python policy) based on execution traces, bypassing LLM calls at inference time.
"""

from __future__ import annotations

import hashlib
import json
import logging
import random
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import httpx


logger = logging.getLogger(__name__)


@dataclass
class AutoHarnessHypothesis:
    """A node in the code hypothesis tree search space."""

    code_id: str
    code: str
    description: str
    successes: float = 1.0  # prior successes
    failures: float = 1.0  # prior failures
    parent_id: str | None = None
    children_ids: list[str] = field(default_factory=list)
    trials: int = 0
    feedback_history: list[str] = field(default_factory=list)

    def update(self, success: bool):
        """Update successes and failures for Thompson Sampling."""
        self.trials += 1
        if success:
            self.successes += 1.0
        else:
            self.failures += 1.0

    def sample(self) -> float:
        """Sample from the Beta distribution for this hypothesis."""
        return random.betavariate(self.successes, self.failures)


class ThompsonSamplingSearch:
    """Manages the tree search space over synthesized code hypotheses using Thompson Sampling."""

    def __init__(self):
        self.hypotheses: dict[str, AutoHarnessHypothesis] = {}
        self.root_id: str | None = None

    def add_hypothesis(self, code: str, description: str, parent_id: str | None = None) -> str:
        """Add a new code candidate to the search tree."""
        code_id = hashlib.sha256(code.encode()).hexdigest()[:12]
        if code_id not in self.hypotheses:
            hyp = AutoHarnessHypothesis(
                code_id=code_id,
                code=code,
                description=description,
                parent_id=parent_id,
            )
            self.hypotheses[code_id] = hyp
            if parent_id and parent_id in self.hypotheses:
                self.hypotheses[parent_id].children_ids.append(code_id)
            if self.root_id is None:
                self.root_id = code_id
        return code_id

    def select_best(self) -> AutoHarnessHypothesis:
        """Select a hypothesis using Thompson Sampling (balancing exploration and exploitation)."""
        if not self.hypotheses:
            raise ValueError("No hypotheses in search tree.")

        # Sample all and return the one with the highest sample score
        best_hyp = None
        best_score = -1.0
        for hyp in self.hypotheses.values():
            score = hyp.sample()
            if score > best_score:
                best_score = score
                best_hyp = hyp
        return best_hyp or next(iter(self.hypotheses.values()))


class CodeAsActionVerifier:
    """Synthesizes, tests, and refines a python action-validation harness."""

    def __init__(self, environment_name: str, ollama_url: str = "http://localhost:11434"):
        self.environment_name = environment_name
        self.ollama_url = ollama_url
        self.search = ThompsonSamplingSearch()
        self.active_code_id: str | None = None

    async def initialize(self, rules_spec: str, baseline_code_stub: str | None = None) -> str:
        """Generates the initial code harness from environment rules."""
        if baseline_code_stub:
            code = baseline_code_stub
            desc = "Manual baseline harness"
        else:
            prompt = (
                f"You are AutoHarness, a DeepMind system. Synthesize a python validation function "
                f"`is_legal_action(action: str) -> tuple[bool, str]` for the environment "
                f"'{self.environment_name}' based on these rules:\n\n{rules_spec}\n\n"
                f"The function should check if the action follows the rules. It should return "
                f"(True, '') if valid, or (False, 'detailed error message') if invalid.\n"
                f"Return ONLY valid python code block enclosed in ```python ... ```, containing the function."
            )
            code = await self._call_local_llm(prompt)
            desc = "Initial synthesized harness"

        code_id = self.search.add_hypothesis(code, desc)
        self.active_code_id = code_id
        return code_id

    def verify(self, action: str) -> tuple[bool, str]:
        """Validate an action using the current active code hypothesis."""
        if not self.active_code_id:
            return True, ""

        hyp = self.search.hypotheses[self.active_code_id]

        # Execute the python code dynamically in a sandboxed namespace
        try:
            namespace = {}
            exec(hyp.code, namespace)
            if "is_legal_action" in namespace:
                is_legal_fn = namespace["is_legal_action"]
                result = is_legal_fn(action)
                if isinstance(result, tuple) and len(result) == 2:
                    return result
                return bool(result), ""
            else:
                return False, "Synthesized code missing 'is_legal_action' function definition."
        except Exception as e:
            return False, f"Harness execution error: {type(e).__name__}: {e}"

    async def record_feedback(self, action: str, env_error: str) -> str:
        """Record environment execution feedback (an illegal action was caught). Refines harness."""
        if not self.active_code_id:
            raise ValueError("Harness not initialized.")

        active_hyp = self.search.hypotheses[self.active_code_id]
        active_hyp.update(success=False)  # Mark this candidate as failed for this trial
        active_hyp.feedback_history.append(f"Action '{action}' failed with env error: {env_error}")

        # Choose the best hypothesis to mutate/refine
        selected_parent = self.search.select_best()

        # Call local model to mutate the selected parent's code to fix the failure case
        mutation_prompt = (
            f"You are AutoHarness. The following python verification harness was generated for "
            f"'{self.environment_name}':\n\n```python\n{selected_parent.code}\n```\n\n"
            f"However, it failed to correctly predict/handle this feedback:\n"
            f"- Action tried: '{action}'\n"
            f"- Environmental error/feedback: '{env_error}'\n\n"
            f"Please mutate the python code to correctly validate this action and incorporate the feedback. "
            f"Maintain the signature: `is_legal_action(action: str) -> tuple[bool, str]`.\n"
            f"Return ONLY valid python code block enclosed in ```python ... ```, containing the function."
        )

        mutated_code = await self._call_local_llm(mutation_prompt)
        new_code_id = self.search.add_hypothesis(
            code=mutated_code,
            description=f"Refinement of {selected_parent.code_id} fixing action '{action}'",
            parent_id=selected_parent.code_id,
        )
        self.active_code_id = new_code_id
        return new_code_id

    def record_success(self):
        """Record that the current active code hypothesis validated a successful environment step."""
        if self.active_code_id:
            self.search.hypotheses[self.active_code_id].update(success=True)

    async def _call_local_llm(self, prompt: str) -> str:
        """Interact with local phi4 or qwen3-coder models running on port 11434."""
        model_name = "phi4:latest"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={"model": model_name, "prompt": prompt, "stream": False},
                    timeout=30.0,
                )
                if resp.status_code == 200:
                    text = resp.json().get("response", "").strip()
                    # Extract python code block if present
                    if "```python" in text:
                        text = text.split("```python")[1].split("```")[0].strip()
                    elif "```" in text:
                        text = text.split("```")[1].split("```")[0].strip()
                    return text
        except Exception as e:
            logger.warning(
                "Local LLM call failed in AutoHarness, using simple fallback logic: %s", e
            )

        # Simple fallback stub in case local model is offline
        return (
            "def is_legal_action(action: str) -> tuple[bool, str]:\n"
            "    if not action or len(action.strip()) == 0:\n"
            "        return False, 'Action cannot be empty'\n"
            "    return True, ''"
        )


class HarnessAsPolicy:
    """Compiles the agent's decision logic into a deterministic python policy from traces."""

    def __init__(self, task_name: str, ollama_url: str = "http://localhost:11434"):
        self.task_name = task_name
        self.ollama_url = ollama_url
        self.traces: list[tuple[dict[str, Any], str]] = []
        self.compiled_code: str | None = None

    def add_trace(self, context: dict[str, Any], chosen_action: str):
        """Add an execution trace mapping input context to the verified correct action."""
        self.traces.append((context, chosen_action))

    async def compile_policy(self) -> bool:
        """Analyze traces and synthesize a deterministic python function `decide_action(context: dict) -> str`."""
        if not self.traces:
            return False

        trace_summary = []
        for idx, (ctx, act) in enumerate(self.traces[-10:]):
            trace_summary.append(f"Trace #{idx}:\nContext: {json.dumps(ctx)}\nAction: '{act}'")

        prompt = (
            "You are AutoHarness. Your goal is to synthesize a deterministic python function "
            "`decide_action(context: dict) -> str` that reproduces the mapping shown in these traces:\n\n"
            + "\n\n".join(trace_summary)
            + "\n\nOutput ONLY a python block containing `decide_action` that executes without "
            "calling any LLMs, based on the keys and values in the context dictionary."
        )

        compiled = await self._call_local_llm(prompt)
        # Test if it executes cleanly against all collected traces
        success = True
        try:
            namespace = {}
            exec(compiled, namespace)
            decide_fn = namespace.get("decide_action")
            if not decide_fn:
                return False

            for ctx, act in self.traces:
                pred = decide_fn(ctx)
                if pred != act:
                    success = False
                    logger.debug(
                        "Policy mismatch: context %s -> predicted '%s', expected '%s'",
                        ctx,
                        pred,
                        act,
                    )
                    break
        except Exception as e:
            logger.warning("Synthesized policy failed testing: %s", e)
            success = False

        if success:
            self.compiled_code = compiled
            logger.info("Successfully compiled Harness-as-Policy for task %s", self.task_name)
            return True
        return False

    def execute(self, context: dict[str, Any]) -> str | None:
        """Execute the compiled policy. Returns None if policy is not compiled/failed."""
        if not self.compiled_code:
            return None
        try:
            namespace = {}
            exec(self.compiled_code, namespace)
            decide_fn = namespace["decide_action"]
            return str(decide_fn(context))
        except Exception as e:
            logger.warning("Executing compiled policy failed: %s", e)
            return None

    async def _call_local_llm(self, prompt: str) -> str:
        """Call local phi4/qwen3-coder models to compile policy."""
        model_name = "phi4:latest"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={"model": model_name, "prompt": prompt, "stream": False},
                    timeout=30.0,
                )
                if resp.status_code == 200:
                    text = resp.json().get("response", "").strip()
                    if "```python" in text:
                        text = text.split("```python")[1].split("```")[0].strip()
                    elif "```" in text:
                        text = text.split("```")[1].split("```")[0].strip()
                    return text
        except Exception:
            pass
        return (
            "def decide_action(context: dict) -> str:\n"
            "    # Stub fallback policy\n"
            "    return 'fallback_action'"
        )


class AutoHarnessEngine:
    """Top-level controller orchestrating Action Verification and Harness-as-Policy compilation."""

    def __init__(self, task_name: str, ollama_url: str = "http://localhost:11434"):
        self.task_name = task_name
        self.verifier = CodeAsActionVerifier(task_name, ollama_url)
        self.policy = HarnessAsPolicy(task_name, ollama_url)
        self.use_policy_only = False

    async def initialize(self, rules_spec: str):
        """Initialize the verification harness."""
        await self.verifier.initialize(rules_spec)

    async def execute_step(
        self, context: dict[str, Any], agent_fallback_fn: Callable[[dict[str, Any]], Any]
    ) -> str:
        """Execute a decision step. Uses the compiled policy if available, otherwise queries agent with harness verifier."""
        if self.use_policy_only and self.policy.compiled_code:
            action = self.policy.execute(context)
            if action is not None:
                # Run verifier on compile action
                is_valid, _ = self.verifier.verify(action)
                if is_valid:
                    return action
                # If compiled policy produces invalid action, disable it
                logger.warning(
                    "Compiled policy produced invalid action: '%s'. Disabling policy-only mode.",
                    action,
                )
                self.use_policy_only = False

        # Query fallback agent/LLM
        attempts = 0
        while attempts < 3:
            action = str(agent_fallback_fn(context))
            is_valid, err_msg = self.verifier.verify(action)
            if is_valid:
                # Record trace and verify success
                self.verifier.record_success()
                self.policy.add_trace(context, action)
                return action
            else:
                logger.warning(
                    "Harness rejected illegal action: '%s' (Error: %s). Retrying.", action, err_msg
                )
                context["__harness_retry_error__"] = f"Action rejected: {err_msg}"
                attempts += 1

        # Return whatever action we got if we exhausted attempts
        return action
