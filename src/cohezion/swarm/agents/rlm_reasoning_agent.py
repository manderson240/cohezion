
import logging
import asyncio
from typing import Any, Dict, List, Optional
from cohezion.swarm.agents.base import BaseAgent, AgentResponse
from cohezion.swarm.swarm_types import SwarmConfig
from cohezion.swarm.rlm.rlm_executor import get_rlm_executor
from cohezion.swarm.rlm.scalar_context_manager import ScalarContextManager

logger = logging.getLogger(__name__)

class RLMReasoningAgent(BaseAgent):
    """
    Recursive Language Model Reasoning Agent.
    Specialized in deep-dive research using recursive loops to manage "infinite" context.
    """

    SYSTEM_PROMPT = """You are the Recursive Reasoning Specialist.
Your goal is to digest massive technical inputs by programmatically decomposing them.
You have access to a Python REPL via the RLMExecutor.
Write code to:
1. Examine specific portions of the context.
2. Formulate sub-hypotheses.
3. Recursively call for more detail.

Focus on maintaining coherence across deep recursion layers.
"""

    def __init__(self, config: SwarmConfig | None = None):
        super().__init__(
            model_name="deepseek-r1:70b", # High-reasoning model for complex RLM tasks
            config=config or SwarmConfig(),
        )
        self.executor = get_rlm_executor()
        self.context_manager = ScalarContextManager(config=self.config)

    async def process(self, input_data: str, stability: float = 0.0) -> AgentResponse:
        """
        Deep-dive reasoning loop with scalar context optimization.
        """
        logger.info("🧠 RLMReasoningAgent initiating deep-dive loop.")

        # 1. Initial Decomposition
        raw_segments = input_data.split('\n\n')

        # 2. Prioritize Context using Scalar Heuristics
        # This will SUMMARIZE low-importance segments and DIVE high-importance ones.
        optimized_segments = await self.context_manager.prioritize_context(
            raw_segments,
            query="Extract transformative FLUME implications",
            stability=stability
        )

        # 3. Formulate RLM Context
        context = {
            "source_segments": optimized_segments,
            "observations": [],
            "hypotheses": [],
            "iteration": 0,
            "stability_frame": stability
        }

        # 4. LLM Decision Move
        prompt = f"""RLM DEEP-DIVE INITIATED.
Stability Frame: {stability:.4f}
Optimized Segments: {len(optimized_segments)}

Context has been pre-filtered using Scalar Importance.
Segments marked 'SUMMARIZE' have been compressed to preserve context window.
Segments marked 'DIVE' are available in full.

Current Context:
{json.dumps([{ 'action': s['action'], 'scalar': s['importance_scalar'], 'content': f"{s['content'][:100]}..." } for s in optimized_segments], indent=2)}

Propose a Python snippet to analyze the 'DIVE' segments and store insights in 'ctx['observations']'.
"""

        # Call LLM to get code
        res = await self._call_ollama(prompt, system_prompt=self.SYSTEM_PROMPT, temperature=0.2)

        # Extract code from response
        code = self._extract_code(res)

        if not code:
            # Fallback to direct synthesis if code extraction fails
            code = "ctx['observations'].append('Automated synthesis scan complete.')"

        # Execute in RLM Sandbox
        exec_result = self.executor.execute_recursive_step(code, context)

        if not exec_result["success"]:
            logger.error(f"RLM Error: {exec_result['stderr']}")
            # synthesize with available context anyway
            updated_context = context
        else:
            updated_context = exec_result['updated_context']

        # 5. Final Synthesis
        final_prompt = f"""SYNTHESIS OF RECURSIVE ANALYSIS:
Observations: {json.dumps(updated_context.get('observations', []), indent=2)}
Stability: {stability}

Generate a unified, 12D-aware research hypothesis based on this analysis.
"""
        synthesis = await self._call_ollama(final_prompt, system_prompt=self.SYSTEM_PROMPT)

        return AgentResponse(synthesis)

    async def close(self):
        await super().close()
        await self.context_manager.close()

    def _extract_code(self, text: str) -> Optional[str]:
        if "```python" in text:
            return text.split("```python")[1].split("```")[0].strip()
        if "```" in text:
            return text.split("```")[1].split("```")[0].strip()
        return text.strip() if "=" in text else None

if __name__ == "__main__":
    async def test():
        agent = RLMReasoningAgent()
        # Test with a multi-page abstract simulation
        long_input = "Sample SOTA Paper on Manifold Encoding... " * 100
        res = await agent.process(long_input)
        print(res)
        await agent.close()
    asyncio.run(test())
