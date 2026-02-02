
import asyncio
import logging
import json
from pathlib import Path
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class ExpansionLoop:
    """
    The Growth Engine.
    Monitors STRATEGIC_DIRECTIVE.md and executes the Research->Code->Test loop.
    """
    
    def __init__(self):
        self.directive_path = Path("STRATEGIC_DIRECTIVE.md")
        self.workspace = Path("research/expansion")
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.active_directive = None

    async def run_forever(self):
        """Main Daemon Loop."""
        logger.info("🌱 Expansion Loop Active. Waiting for Directives...")
        
        while True:
            await self.check_directive()
            await asyncio.sleep(10) # check every 10s

    async def check_directive(self):
        """Check if a new directive exists and is active."""
        if not self.directive_path.exists():
            return

        content = self.directive_path.read_text()
        if "**STATUS**: ACTIVE" in content and content != self.active_directive:
            self.active_directive = content
            command = self._extract_command(content)
            logger.info(f"🚀 Detected New Directive: {command}")
            await self.execute_expansion(command)

    def _extract_command(self, content: str) -> str:
        for line in content.splitlines():
            if line.startswith("**COMMAND**"):
                return line.split(":", 1)[1].strip()
        return "Unknown"

    async def execute_expansion(self, command: str):
        """
        Simplified V1 Execution:
        1. Acknowledge (Log)
        2. Create a specific plan (Mock for now)
        3. Mark Directive as IN_PROGRESS
        """
        logger.info(f"⚙️  Executing Expansion for: {command}")
        
        # 1. Update Status
        new_content = self.active_directive.replace("**STATUS**: ACTIVE", "**STATUS**: IN_PROGRESS")
        self.directive_path.write_text(new_content)
        
        # 2. Simulate Work (Placeholder for ResearchAgent/CodingAgent)
        logger.info("   - Step 1: Researching... [DONE]")
        await asyncio.sleep(1)
        logger.info("   - Step 2: Coding... [DONE]")
        await asyncio.sleep(1)
        logger.info("   - Step 3: Mycelium Testing... [DONE]")
        
        # 3. Complete
        final_content = new_content.replace("**STATUS**: IN_PROGRESS", "**STATUS**: COMPLETED")
        self.directive_path.write_text(final_content)
        logger.info("✅ Expansion Complete.")

if __name__ == "__main__":
    loop = ExpansionLoop()
    asyncio.run(loop.run_forever())
