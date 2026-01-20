"""
Skill Audit Agent for Cohezion.

Scans the skills registry, clusters them by functional similarity, 
and identifies overlaps for distillation.
"""

import os
import logging
from typing import Dict, List, Any
from pathlib import Path

from cohezion.swarm.agents.base import BaseAgent

logger = logging.getLogger(__name__)

class SkillAuditAgent(BaseAgent):
    """
    An agent capable of auditing the skill registry for distinction and complementarity.
    """
    
    def __init__(self, model_name: str = "phi3:mini", **kwargs):
        super().__init__(model_name=model_name, **kwargs)
        self.skills_dir = Path("src/cohezion/skills")
        
    async def scan_skills(self) -> List[Dict[str, str]]:
        """
        Reads all skill files and extracts their core summary.
        """
        skills = []
        for file_path in self.skills_dir.glob("*.md"):
            content = file_path.read_text()
            # Extract name and a snippet of the instruction/expertise
            name = file_path.stem
            summary = self._extract_summary(content)
            skills.append({"name": name, "summary": summary, "path": str(file_path)})
        return skills

    def _extract_summary(self, content: str) -> str:
        """
        Extracts the expertise or instruction section from a skill file.
        """
        if "## DOMAIN EXPERTISE" in content:
            parts = content.split("## DOMAIN EXPERTISE")
            return parts[1].split("##")[0].strip()
        return content[:500] # Fallback

    async def audit_cluster(self, cluster_name: str, skills: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Audits a specific cluster of skills for functional overlap.
        """
        skill_list_str = "\n".join([f"- {s['name']}: {s['summary']}" for s in skills])
        
        prompt = f"""
        Audit the following cluster of skills for functional overlap and complementarity.
        
        CLUSTER: {cluster_name}
        
        SKILLS:
        {skill_list_str}
        
        Determine which skills are redundant, which are distinct but complementary, 
        and which should be merged.
        
        Format your response as:
        [KEEP]: [Skill Names]
        [MERGE]: [Skill A, Skill B] -> [New Skill Name]
        [REFACTOR]: [Skill Names] (Reasoning)
        """
        
        response = await self._call_ollama(prompt)
        return {"cluster": cluster_name, "audit": response}

    async def process(self, input_data: str) -> str:
        """
        Main entry point for auditing the whole registry.
        """
        skills = await self.scan_skills()
        # For a full audit, we'd cluster first. 
        # For now, we return the count and a snippet.
        return f"Audited {len(skills)} skills. Ready for clustering."

    async def batch_audit(self):
        """
        Audits the entire registry by functional clusters.
        """
        all_skills = await self.scan_skills()
        
        # Define functional clusters
        clusters = {
            "Visualization": ["VISUALIZATION", "PLOT", "RENDERING", "UI", "ANIMATION"],
            "Methodology": ["FLUME", "ABSTRACTION", "COMPARISON", "PHILOSOPHY"],
            "Economics": ["CREDIT", "YIELD", "RESOURCE", "DEPIN", "FUNDING"],
            "Intelligence": ["SIMULATION", "PREDICTION", "INFERENCE", "WORLD_MODEL"],
            "Management": ["PROJECT", "PRODUCT", "REPO", "AUDIT"],
            "Connectivity": ["MCP", "API", "CLOUD", "BRIDGE"],
        }
        
        results = []
        for c_name, keywords in clusters.items():
            cluster_skills = [s for s in all_skills if any(kw in s['name'] for kw in keywords)]
            if cluster_skills:
                print(f"Auditing {c_name} Cluster ({len(cluster_skills)} skills)...")
                res = await self.audit_cluster(c_name, cluster_skills)
                results.append(res)
                
        return results

async def main():
    agent = SkillAuditAgent()
    try:
        results = await agent.batch_audit()
        
        # Save results to a markdown file
        report_path = Path("/home/mike-anderson/.gemini/antigravity/brain/4f5d1f06-5ebf-4df8-ac39-15c8a876e05c/skill_audit_results.md")
        content = "# Full Skill Audit Results\n\n"
        for res in results:
            content += f"## {res['cluster']}\n{res['audit']}\n\n"
        report_path.write_text(content)
        print(f"Report saved to {report_path}")
    finally:
        await agent.close()

if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
