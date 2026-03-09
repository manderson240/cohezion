#!/usr/bin/env python3
"""
Overnight Job: The Elegance Engine
Runs continuously to identify complex code and propose elegantly simple refactors.
"""

import asyncio
import logging
import sys
import time
from pathlib import Path
from datetime import datetime
import subprocess

PROJECT_ROOT = Path("/home/mike-anderson/dev/cohezion")
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from cohezion.swarm.compound_client import get_compound_client
import trackio

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("EleganceEngine")

def get_complex_files():
    """Use ruff to find files with high cyclomatic complexity."""
    try:
        # Run ruff check for complexity (C901)
        result = subprocess.run(
            "ruff check src/cohezion --select C901 --format text", 
            shell=True, capture_output=True, text=True, cwd=PROJECT_ROOT
        )
        files = set()
        for line in result.stdout.split('\n'):
            if "C901" in line and ":" in line:
                filepath = line.split(":")[0]
                if (PROJECT_ROOT / filepath).exists():
                    files.add(PROJECT_ROOT / filepath)
        return list(files)
    except Exception as e:
        logger.error(f"Error checking complexity: {e}")
        return []

async def run_elegance_loop():
    logger.info("✨ Starting the Elegance Engine (Overnight Continuous Refactoring)...")
    trackio.init(project="cohezion-core", space_id="manderson240/cohezion-trackio", run_name="elegance-engine")
    
    client = get_compound_client()
    proposals_dir = PROJECT_ROOT / "reports/elegance_proposals"
    proposals_dir.mkdir(parents=True, exist_ok=True)
    
    end_time = time.time() + (8 * 3600)  # Run for 8 hours
    
    while time.time() < end_time:
        complex_files = get_complex_files()
        
        if not complex_files:
            logger.info("No highly complex files found by Ruff. System is elegant.")
            trackio.log({"complex_files_count": 0})
            await asyncio.sleep(3600) # Sleep an hour
            continue
            
        trackio.log({"complex_files_count": len(complex_files)})
        
        # Pick one file to refactor per cycle to keep it breathable
        target_file = complex_files[0]
        logger.info(f"Targeting {target_file.name} for elegant simplification.")
        
        code_content = target_file.read_text()
        
        # Skip if too large for simple context window handling right now
        if len(code_content) > 15000:
            logger.info("File too large for zero-waste context. Skipping.")
            await asyncio.sleep(600)
            continue
            
        prompt = f"""
        You are an ELEGANT_SIMPLICITY_PRIME specialist.
        Review the following Python file: {target_file.name}
        
        ```python
        {code_content}
        ```
        
        Instruction:
        - Refactor this code to drastically reduce cyclomatic complexity and line count.
        - Apply the principles of "Elegant Simplicity". Remove redundant loops, consolidate state, and rely on functional patterns.
        - Do not change the core public API.
        - Output the proposed refactored code wrapped in ```python ... ``` tags, preceded by a brief summary of the complexity removed.
        """
        
        try:
            response = await client.generate(prompt, task_type="coding")
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            proposal_file = proposals_dir / f"simplify_{target_file.stem}_{timestamp}.md"
            
            with open(proposal_file, "w") as f:
                f.write(f"# Elegance Proposal for {target_file.name}\n\n")
                f.write(response)
                
            logger.info(f"✅ Elegance proposal generated: {proposal_file.name}")
            trackio.log({"proposals_generated": 1})
            
        except Exception as e:
            logger.error(f"Failed to generate elegance proposal: {e}")
            
        # Sleep for 45 minutes between refactor attempts to avoid API/Compute saturation
        logger.info("Sleeping before next elegance cycle...")
        await asyncio.sleep(2700) 

    logger.info("🌅 8-Hour Elegance Engine cycle complete.")
    trackio.finish()

if __name__ == "__main__":
    asyncio.run(run_elegance_loop())
