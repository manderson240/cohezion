"""
HypothesisAgent - Automated Hypothesis Testing (Gateway 20).

Uses the TrajectoryPredictor to imagine alternative future states, then
designs and executes empirical experiments in the sandbox to verify them.
"""

import logging
import subprocess
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch

from cohezion.agents.base import BaseAgent
from cohezion.flume.predictor import TrajectoryPredictor
from cohezion.swarm.swarm_types import SwarmConfig

logger = logging.getLogger(__name__)


class HypothesisAgent(BaseAgent):
    def __init__(self, config: SwarmConfig | None = None):
        config = config or SwarmConfig()
        super().__init__(
            model_name="qwen3-coder:30b",  # SOTA for Code Gen
            config=config,
        )
        self.predictor = TrajectoryPredictor(z_dim=768)  # Matches nomic-embed-text

    async def imagine_and_verify(self, context_query: str) -> str:
        """
        Imagine future branches of thought and verify their feasibility
        using empirical sandbox experiments.
        """
        logger.info(
            f"🧪 HypothesisAgent starting imagination cycle for: {context_query[:50]}..."
        )

        if self._encoder is None:
            from cohezion.flume.autoencoder import FlumeConfig, FlumeEncoder

            self._encoder = FlumeEncoder(config=FlumeConfig())

        z_start = self._encoder.get_semantic_vector(context_query)
        if hasattr(z_start, "numpy"):
            z_start = z_start.numpy()

        # 2. Imagine 3 branches
        branches = self.predictor.imagine_branches(
            torch.from_numpy(z_start).float(), perturbations=2, steps=3
        )

        report = ["## Automated Hypothesis Testing Report"]
        report.append(f"Context: {context_query}\n")

        for i, branch in enumerate(branches):
            branch_label = "Equilibrium Path" if i == 0 else f"Alternative Branch {i}"
            report.append(f"### Exploring: {branch_label}")

            # 3. Translate branch trajectory back to text (simplified: use LLM to interpret z_end)
            branch[-1].detach().cpu().numpy()
            # Since we can't 'decode' perfectly back to text yet (G5 is basic),
            # we ask the model to generate a hypothesis based on starting context + "imagination direction"

            prompt = f"""Based on the following context, imagine a technical hypothesis to test.
Assume we are exploring a {"conservative" if i == 0 else "highly creative"} direction.

CONTEXT:
{context_query}

Design a Python script to VERIFY this hypothesis.
Requirements:
1. Print 'VERIFICATION: SUCCESS' only if verified.
2. Use standard imports: `import numpy as np`, `import torch`.
3. Use `from cohezion.flume.autoencoder import FlumeEncoder`.
4. `FlumeEncoder().get_semantic_vector(text)` returns a 768-dim tensor.

TEMPLATE:
```python
import numpy as np
import torch
from cohezion.flume.autoencoder import FlumeEncoder

def main():
    encoder = FlumeEncoder()
    # Your logic here
    # result = ...
    print("VERIFICATION: SUCCESS" if result else "VERIFICATION: FAILURE")

if __name__ == "__main__":
    main()
```

HYPOTHESIS DESCRIPTION:
(1-line)

VERIFICATION SCRIPT (CODE BLOCK):
"""
            response = await self._call_ollama(prompt, temperature=0.5)

            # Extract hypothesis and script
            hypothesis_desc = "Unknown"
            code_block = ""

            if "HYPOTHESIS DESCRIPTION:" in response:
                hypothesis_desc = (
                    response.split("HYPOTHESIS DESCRIPTION:")[1].split("\n")[0].strip()
                )

            import re

            code_match = re.search(r"```python\n(.*?)```", response, re.DOTALL)
            if code_match:
                code_block = code_match.group(1)

            report.append(f"- **Hypothesis**: {hypothesis_desc}")

            if not code_block:
                report.append(
                    "- **Outcome**: ❌ Failed to generate verification script."
                )
                continue

            # 4. Sandbox Verification with possible self-correction
            success, error_msg = await self._run_sandbox_experiment(code_block)

            if not success and error_msg:
                # Attempt ONE self-correction cycle
                logger.info(f"🛠️ Attempting self-correction for: {error_msg[:50]}...")
                fix_prompt = f"Fix this Python script. Error: {error_msg}\n\nSCRIPT:\n```python\n{code_block}\n```"
                fix_response = await self._call_ollama(fix_prompt, temperature=0.3)
                fix_match = re.search(r"```python\n(.*?)```", fix_response, re.DOTALL)
                if fix_match:
                    code_block = fix_match.group(1)
                    success, error_msg = await self._run_sandbox_experiment(code_block)

            report.append(
                f"- **Outcome**: {'✅ VERIFIED' if success else '❌ REJECTED'} in Sandbox."
            )
            if error_msg:
                report.append(f"- **Error**: {error_msg}")

        return "\n".join(report)

    async def _run_sandbox_experiment(self, code: str) -> tuple[bool, str]:
        """Execute a hypothesis verification script and return (Success, ErrorMsg)."""
        sandbox_dir = Path(".sandbox")
        sandbox_dir.mkdir(exist_ok=True)
        sandbox_file = (
            sandbox_dir / f"hypothesis_{int(time.time())}_{np.random.randint(1000)}.py"
        )

        sandbox_file.write_text(code)

        try:
            import os

            env = os.environ.copy()
            src_path = str(Path.cwd() / "src")
            env["PYTHONPATH"] = f"{src_path}:{env.get('PYTHONPATH', '')}"

            result = subprocess.run(
                ["python3", str(sandbox_file)],
                capture_output=True,
                text=True,
                timeout=15,
                env=env,
            )

            logger.info(f"Sandbox stdout: {result.stdout}")
            if result.stderr:
                logger.warning(f"Sandbox stderr: {result.stderr}")

            is_success = "VERIFICATION: SUCCESS" in result.stdout
            error = result.stderr.strip() if not is_success and result.stderr else ""

            return is_success, error
        except Exception as e:
            logger.error(f"Sandbox experiment failed: {e}")
            return False, str(e)
        finally:
            if sandbox_file.exists():
                sandbox_file.unlink()

    async def process(self, context: str, **kwargs: Any) -> str:
        """Entry point for hypothesis testing."""
        return await self.imagine_and_verify(context)
