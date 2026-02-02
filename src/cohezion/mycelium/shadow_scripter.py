
import asyncio
import logging
import json
from pathlib import Path
from typing import Optional, Dict, Any
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class ShadowScripter:
    """
    Mycelium Agent: Autonomously grows tests around existing code.
    Powered by local qwen2.5-coder.
    """
    
    def __init__(self, model: str = "qwen2.5-coder:7b"):
        self.model = model
        self.output_dir = Path("tests/shadow").resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def generate_test(self, file_path: Path) -> Optional[Path]:
        """
        Reads a source file and generates a pytest suite for it.
        """
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return None
            
        logger.info(f"🍄 Growing test for: {file_path.name}")
        content = file_path.read_text(errors='ignore')
        
        prompt = f"""
        ROLE: Expert Python QA Engineer (Pytest)
        TASK: Write a comprehensive pytest suite for the following code.
        
        REQUIREMENTS:
        1. Use `pytest` fixtures where appropriate.
        2. Mock external dependencies (requests, database, etc.) using `unittest.mock`.
        3. Cover happy paths and edge cases.
        4. Return ONLY the python code for the test file. No markdown, no explanations.
        
        SOURCE CODE ({file_path.name}):
        ```python
        {content[:4000]}
        ```
        (Truncated if too long)
        """
        
        try:
            # Call Local LLM
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=120
            )
            
            if response.status_code == 200:
                raw_text = response.json()['response']
                test_code = self._clean_code(raw_text)
                
                # Save File
                test_filename = f"test_{file_path.stem}_generated.py"
                output_path = self.output_dir / test_filename
                output_path.write_text(test_code)
                
                logger.info(f"✨ Test synthesized: {output_path}")
                return output_path
            else:
                logger.error(f"Model error {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return None

    def _clean_code(self, text: str) -> str:
        """Extract code from markdown blocks if present."""
        if "```python" in text:
            text = text.split("```python")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        return text.strip()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="Source file to generate test for")
    args = parser.parse_args()
    
    agent = ShadowScripter()
    asyncio.run(agent.generate_test(Path(args.file)))
