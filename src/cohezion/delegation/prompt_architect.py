
import asyncio
import logging
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class PromptArchitect:
    """
    The Meta-Prompt Architect.
    Deconstructs high-level intent, matches it to the right agent,
    and generates an optimized persona-based prompt.
    """
    
    def __init__(self, model: str = "qwen2.5-coder:7b"):
        self.model = model
        self.repo_map = Path("REPO_MAP.md")
        self.capability_map = Path(".agent/CAPABILITY_MAP.md")

    async def architect_task(self, intent: str) -> Dict[str, Any]:
        """
        Main entry point. Transforms intent into a delegated task payload.
        """
        logger.info(f"🏗️  Architecting Task for: {intent}")
        
        context = self._get_context()
        
        prompt = f"""
        ROLE: Expert Prompt Engineer & System Architect.
        
        TASK: Analyze the USER INTENT and create a Delegation Plan.
        
        USER INTENT: "{intent}"
        
        AVAILABLE AGENTS:
        - CodingAgent (qwen2.5-coder): Writes code.
        - ResearchAgent (deepseek-r1): Analyzes data/web.
        - ShadowScripter (Mycelium): Writes tests.
        - Nexus (Governance): Makes decisions.
        
        CONTEXT (Repository Structure):
        {context[:2000]}... (Truncated)
        
        INSTRUCTION:
        1. Select the SINGLE best agent for this task.
        2. Write a highly specific, optimized prompt for that agent.
        3. Include file paths from the Context if relevant.
        
        OUTPUT FORMAT (JSON ONLY):
        {{
            "selected_agent": "<Agent Name>",
            "reasoning": "<Why this agent?>",
            "optimized_prompt": "<The actual prompt to send to the agent>",
            "target_files": ["<List of relevant file paths>"]
        }}
        """
        
        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                },
                timeout=60
            )
            
            if response.status_code == 200:
                raw_response = response.json()['response']
                cleaned = self._clean_json(raw_response)
                plan = json.loads(cleaned)
                logger.info(f"📋 Plan Created: {plan['selected_agent']} -> {plan['reasoning']}")
                return plan
            else:
                logger.error(f"Architecture Error: {response.status_code}")
                return {"error": "Model Failure"}
                
        except Exception as e:
            logger.error(f"Architecture Failed: {e}")
            logger.error(f"Raw Response: {response.json().get('response', 'N/A')}")
            return {"error": str(e)}

    def _clean_json(self, text: str) -> str:
        """Removes markdown ticks and think blocks."""
        # Remove think blocks (DeepSeek specific)
        if "<think>" in text:
            text = text.split("</think>")[-1]
            
        # Remove markdown
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
            
        return text.strip()

    def _get_context(self) -> str:
        """Reads REPO_MAP for context."""
        if self.repo_map.exists():
            return self.repo_map.read_text()
        return "No Repository Map found."

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("intent", help="The high-level user request")
    args = parser.parse_args()
    
    architect = PromptArchitect()
    asyncio.run(architect.architect_task(args.intent))
