"""
Meta-Skill Agent Implementation.

This agent is responsible for "harvesting" skills from successful tasks
and registering them in the system. It implements Gateway 6 capabilities.

Author: Cohezion Agentic Team
Date: 2026-01-18
"""

import json
import logging
import asyncio
import torch
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

from cohezion.flume.autoencoder import FlumeEncoder

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ProposedSkill:
    name: str
    description: str
    content: str
    tags: List[str]

class MetaSkillAgent:
    def __init__(self, registry_path: str, skills_dir: str):
        self.registry_path = Path(registry_path)
        self.skills_dir = Path(skills_dir)
        self.encoder = FlumeEncoder(z_dim=256)
        
        # Ensure directories exist
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        
    def _load_registry(self) -> Dict:
        if not self.registry_path.exists():
            return {}
        with open(self.registry_path, 'r') as f:
            return json.load(f)

    def _save_registry(self, registry: Dict):
        with open(self.registry_path, 'w') as f:
            json.dump(registry, f, indent=2)

    async def validate_novelty(self, proposed: ProposedSkill) -> bool:
        """
        Check if skill is semantically novel compared to existing skills.
        Returns True if novel (safe to add), False if duplicate.
        """
        logger.info(f"Validating novelty for: {proposed.name}")
        
        registry = self._load_registry()
        if not registry:
            return True # First skill is always unique
            
        # Use robust semantic vector from Ollama/Nomic
        z_proposed = self.encoder.get_semantic_vector(proposed.description)
        
        for name, data in registry.items():
            existing_desc = data.get('description', '')
            z_existing = self.encoder.get_semantic_vector(existing_desc)
            
            # Compute cosine similarity
            # Ensure tensors are float and same device
            z_p = z_proposed.float()
            z_e = z_existing.float()
            
            sim = torch.nn.functional.cosine_similarity(z_p.unsqueeze(0), z_e.unsqueeze(0)).item()
            logger.info(f"Similarity with {name}: {sim:.3f}")
            
            if sim > 0.82: # Lowered to 0.82 for Nomic (strict deduplication)
                logger.warning(f"Skill {proposed.name} is too similar to {name} (sim={sim:.3f}). Rejected.")
                return False
                
        return True

    async def harvest_skill(self, proposed: ProposedSkill) -> bool:
        """
        Main entry point: Validate and save a new skill.
        """
        # 1. Check novelty
        is_novel = await self.validate_novelty(proposed)
        if not is_novel:
            return False
            
        # 2. Write file
        filename = f"{proposed.name}_PRIME.md"
        file_path = self.skills_dir / filename
        
        try:
            with open(file_path, 'w') as f:
                f.write(proposed.content)
            logger.info(f"Skill file written to {file_path}")
        except Exception as e:
            logger.error(f"Failed to write skill file: {e}")
            return False
            
        # 3. Update Registry
        registry = self._load_registry()
        registry[proposed.name] = {
            "path": str(file_path),
            "description": proposed.description,
            "tags": proposed.tags,
            "auto_generated": True
        }
        self._save_registry(registry)
        logger.info(f"Skill {proposed.name} registered successfully.")
        
        return True

# --- Simulation / Test ---
async def run_demo():
    agent = MetaSkillAgent(
        registry_path="src/cohezion/registry/skill_registry.json",
        skills_dir="src/cohezion/skills"
    )
    
    # Mock a new skill proposal
    
    # 1. Duplicate Test
    duplicate_skill = ProposedSkill(
        name="ETERNAL_WORLD_PRIME",
        description="A skill for making universes persist across server restarts using databases.",
        content="# SKILL: ETERNAL_WORLD_PRIME...",
        tags=["persistence", "database"]
    )
    
    print("\n--- Testing Duplicate Rejection ---")
    success = await agent.harvest_skill(duplicate_skill)
    print(f"Duplicate Accepted? {success}")
    
    # 2. Novel Test
    novel_skill = ProposedSkill(
        name="ITALIAN_COOKING_PRIME",
        description="Recipes and techniques for making authentic Italian pasta dishes.",
        content="# SKILL: ITALIAN_COOKING_PRIME\n\n## INSTRUCTION\n1. Boil water...",
        tags=["cooking", "culture"]
    )
    
    print("\n--- Testing Novel Acceptance ---")
    success_novel = await agent.harvest_skill(novel_skill)
    print(f"Novel Accepted? {success_novel}")

if __name__ == "__main__":
    asyncio.run(run_demo())
