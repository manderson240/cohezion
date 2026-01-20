"""
Unified Capability Registry.
Aggregates Skills, Agents, and MCP Servers into a single natural-language search index.
"""

import os
import json
import glob
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any

# Scikit-Learn for TF-IDF (Lightweight Search)
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class Capability:
    name: str
    type: str  # "skill", "agent", "mcp"
    description: str
    path: str
    tags: List[str] = field(default_factory=list)
    score: float = 0.0

class CapabilityRegistry:
    def __init__(self, root_dir: Path = None):
        self.root_dir = root_dir or Path(__file__).parent.parent.parent.parent
        self.capabilities: List[Capability] = []
        self.vectorizer = None
        self.vectors = None
        
        # Load immediately
        self.refresh()

    def refresh(self):
        """Scan codebase and rebuild index."""
        self.capabilities = []
        
        self._scan_skills()
        self._scan_mcp()
        self._scan_agents()
        
        if SKLEARN_AVAILABLE and self.capabilities:
            self._build_index()
        else:
            logger.warning("Scikit-learn not available or no capabilities. Search will be limited.")

    def _scan_skills(self):
        """Scan .md files in skills directory."""
        skills_dir = self.root_dir / "src/cohezion/skills"
        if not skills_dir.exists():
            return
            
        for md_file in skills_dir.glob("*_PRIME.md"):
            try:
                content = md_file.read_text(errors='ignore')
                # Improved extraction: read up to 20 lines, looking for description field or first paragraph
                desc = ""
                lines = content.split('\n')
                for line in lines[:20]:
                    if "description:" in line:
                         desc = line.split("description:")[1].strip().strip('"')
                         break
                
                # Fallback: Look for the first line after title
                if not desc or desc == "No description":
                    for i, line in enumerate(lines):
                        if line.startswith("# ") and i+2 < len(lines):
                            potential_desc = lines[i+2].strip()
                            if potential_desc and not potential_desc.startswith("#"):
                                desc = potential_desc
                                break
                
                if not desc:
                    desc = f"Skill defined in {md_file.name}"

                self.capabilities.append(Capability(
                    name=md_file.stem,
                    type="skill",
                    description=desc,
                    path=str(md_file.relative_to(self.root_dir)),
                    tags=["markdown", "instruction", md_file.stem.replace('_', ' ').lower()]
                ))
            except Exception as e:
                logger.error(f"Failed to scan skill {md_file}: {e}")

    def _scan_mcp(self):
        """Load MCP registry json."""
        mcp_file = self.root_dir / "src/cohezion/mcp/mcp_registry.json"
        if not mcp_file.exists():
            return

        try:
            data = json.loads(mcp_file.read_text())
            # Internal
            for server in data.get("internal", []):
                self.capabilities.append(Capability(
                    name=server.get("name"),
                    type="mcp",
                    description=server.get("description", ""),
                    path=server.get("path", ""),
                    tags=["tool", "server", "int"] + server.get("tools", [])
                ))
            # External
            for server in data.get("external", []):
                self.capabilities.append(Capability(
                     name=server.get("name"),
                     type="mcp",
                     description=server.get("description", ""),
                     path=server.get("url", ""),
                     tags=["tool", "server", "ext"]
                ))
        except Exception as e:
            logger.error(f"Failed to scan MCP registry: {e}")

    def _scan_agents(self):
        """Scan agents directory for python classes."""
        agents_dir = self.root_dir / "src/cohezion/swarm/agents"
        if not agents_dir.exists():
            return
            
        for py_file in agents_dir.glob("*.py"):
            if py_file.name == "__init__.py" or py_file.name == "base.py":
                continue
                
            # Basic static analysis to avoid importing everything
            try:
                content = py_file.read_text()
                # Heuristic: looks for class definition
                if "class " in content and "Agent" in content:
                    class_name = py_file.stem.capitalize() + "Agent"
                    desc = f"Agent defined in {py_file.name}"
                    
                    self.capabilities.append(Capability(
                        name=class_name,
                        type="agent",
                        description=desc,
                        path=str(py_file.relative_to(self.root_dir)),
                        tags=["agent", "swarm", "autonomous"]
                    ))
            except Exception as e:
                 logger.error(f"Failed to scan agent {py_file}: {e}")

    def _build_index(self):
        """Build TF-IDF tokens."""
        # Use description AND tags AND name AND full path for better matching
        # For skills, we might want to index more content if desc is weak
        corpus = []
        for c in self.capabilities:
            text = f"{c.name} {c.description} {' '.join(c.tags)} {c.path}"
            corpus.append(text)
            
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.vectors = self.vectorizer.fit_transform(corpus)

    def find(self, query: str, top_k: int = 5) -> List[Capability]:
        """Natural language search."""
        if not SKLEARN_AVAILABLE or self.vectorizer is None:
            # Fallback: simple text match
            results = []
            for c in self.capabilities:
                if query.lower() in c.name.lower() or query.lower() in c.description.lower():
                    c.score = 1.0
                    results.append(c)
            return results[:top_k]
            
        # TF-IDF Search
        query_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self.vectors).flatten()
        
        # Sort indices
        ranked_indices = scores.argsort()[::-1]
        
        results = []
        for idx in ranked_indices[:top_k]:
            if scores[idx] > 0.0:
                cap = self.capabilities[idx]
                cap.score = float(scores[idx])
                results.append(cap)
                
        return results

if __name__ == "__main__":
    # Test Run
    logging.basicConfig(level=logging.INFO)
    reg = CapabilityRegistry()
    print(f"Loaded {len(reg.capabilities)} capabilities.")
    
    test_queries = [
        "physics simulation",
        "critique code",
        "manage project constraints",
        "deploy to cloud"
    ]
    
    for q in test_queries:
        print(f"\nQUERY: '{q}'")
        for res in reg.find(q, top_k=3):
            print(f"  - [{res.type.upper()}] {res.name}: {res.description[:50]}... ({res.score:.2f})")
