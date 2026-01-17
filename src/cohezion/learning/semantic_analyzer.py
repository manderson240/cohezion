"""
Semantic Analysis Engine - Analyze knowledge base for patterns and insights.

Features:
- Cluster similar content
- Extract key themes
- Identify capability gaps
- Generate skill recommendations
"""

import json
import logging
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict, field
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SemanticCluster:
    """A cluster of semantically related items."""
    cluster_id: str
    theme: str
    items: list[str]
    keywords: list[str]
    strength: float  # 0-1


@dataclass
class CapabilityGap:
    """An identified gap in capabilities."""
    gap_id: str
    area: str
    description: str
    severity: str  # low, medium, high, critical
    recommended_fix: str


@dataclass
class SemanticAnalysis:
    """Complete semantic analysis result."""
    timestamp: str
    nodes_analyzed: int
    clusters: list[SemanticCluster]
    top_themes: list[tuple[str, int]]
    capability_gaps: list[CapabilityGap]
    skill_recommendations: list[str]
    
    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "nodes_analyzed": self.nodes_analyzed,
            "clusters": [asdict(c) for c in self.clusters],
            "top_themes": self.top_themes,
            "capability_gaps": [asdict(g) for g in self.capability_gaps],
            "skill_recommendations": self.skill_recommendations,
        }


class SemanticAnalyzer:
    """
    Analyzes universe nodes for semantic patterns.
    
    Uses keyword extraction and co-occurrence analysis
    for lightweight clustering (no ML dependencies).
    """
    
    # Known capability domains
    CAPABILITY_DOMAINS = [
        "visualization", "analysis", "synthesis", "security", "performance",
        "learning", "memory", "routing", "simulation", "debate", "audio",
        "database", "api", "testing", "deployment", "monitoring",
    ]
    
    # Keywords by domain
    DOMAIN_KEYWORDS = {
        "visualization": ["plot", "chart", "render", "3d", "animate", "display"],
        "analysis": ["analyze", "evaluate", "assess", "measure", "compare"],
        "synthesis": ["synthesize", "integrate", "combine", "merge", "unify"],
        "security": ["secure", "auth", "encrypt", "protect", "validate"],
        "performance": ["optimize", "fast", "efficient", "cache", "speed"],
        "learning": ["learn", "adapt", "improve", "train", "model"],
        "memory": ["remember", "store", "retrieve", "persist", "history"],
        "routing": ["route", "dispatch", "select", "match", "classify"],
        "simulation": ["simulate", "generate", "physics", "journey", "trajectory"],
        "debate": ["debate", "vote", "consensus", "agree", "perspective"],
        "audio": ["voice", "tts", "speech", "audio", "podcast"],
        "database": ["query", "store", "surreal", "vector", "embed"],
        "api": ["endpoint", "rest", "http", "request", "response"],
        "testing": ["test", "assert", "verify", "validate", "coverage"],
        "deployment": ["deploy", "cloud", "docker", "container", "run"],
        "monitoring": ["monitor", "health", "audit", "log", "metric"],
    }
    
    def __init__(self, base_path: Path | None = None):
        self.base_path = base_path or Path("src/cohezion")
        self.nodes: list[dict] = []
    
    def load_nodes(self):
        """Load all universe nodes for analysis."""
        kg_path = self.base_path / "knowledge_graph" / "universe_nodes"
        
        # Load JSON files
        for json_file in kg_path.rglob("*.json"):
            try:
                with open(json_file) as f:
                    data = json.load(f)
                    self.nodes.append({
                        "path": str(json_file),
                        "type": json_file.parent.name,
                        "data": data,
                    })
            except Exception as e:
                logger.warning(f"Could not load {json_file}: {e}")
        
        # Load skill files
        skills_path = self.base_path / "skills"
        for md_file in skills_path.glob("*.md"):
            self.nodes.append({
                "path": str(md_file),
                "type": "skill",
                "data": {"content": md_file.read_text()[:2000]},
            })
        
        logger.info(f"Loaded {len(self.nodes)} nodes for analysis")
    
    def extract_keywords(self, text: str) -> list[str]:
        """Extract keywords from text."""
        # Simple keyword extraction
        words = re.findall(r'\b[a-z]+\b', text.lower())
        # Filter stopwords
        stopwords = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                     "being", "have", "has", "had", "do", "does", "did", "will",
                     "would", "could", "should", "may", "might", "can", "to",
                     "of", "in", "for", "on", "with", "at", "by", "from", "or",
                     "and", "as", "if", "but", "not", "this", "that", "these",
                     "those", "it", "its", "we", "our", "they", "their"}
        keywords = [w for w in words if w not in stopwords and len(w) > 3]
        return keywords
    
    def _extract_strings_recursive(self, obj: Any, depth: int = 0) -> list[str]:
        """Recursively extract strings from a dictionary or list."""
        if depth > 3:
            return []
        
        match obj:
            case str():
                return [obj]
            case dict():
                return [s for v in obj.values() for s in self._extract_strings_recursive(v, depth + 1)]
            case list():
                return [s for item in obj[:10] for s in self._extract_strings_recursive(item, depth + 1)]
            case _:
                return []

    def get_node_text(self, node: dict) -> str:
        """Extract text content from a node."""
        data = node.get("data", {})
        
        if isinstance(data, str):
            return data
            
        # Prioritize key fields
        priority_keys = ["content", "synthesis", "summary", "query", "reasoning"]
        texts = [str(data[k]) for k in priority_keys if k in data]
        
        # Add all other strings found recursively
        texts.extend(self._extract_strings_recursive(data))
        
        return " ".join(texts)[:5000]
    
    def cluster_by_domain(self) -> list[SemanticCluster]:
        """Cluster nodes by capability domain."""
        domain_nodes: dict[str, list[str]] = defaultdict(list)
        domain_keywords: dict[str, Counter] = defaultdict(Counter)
        
        for node in self.nodes:
            text = self.get_node_text(node)
            keywords = self.extract_keywords(text)
            
            # Match to domains
            for domain, domain_kws in self.DOMAIN_KEYWORDS.items():
                if any(kw in keywords for kw in domain_kws):
                    domain_nodes[domain].append(node["path"])
                    domain_keywords[domain].update(keywords)
        
        clusters = []
        for domain, paths in domain_nodes.items():
            top_kws = [kw for kw, _ in domain_keywords[domain].most_common(10)]
            clusters.append(SemanticCluster(
                cluster_id=f"cluster_{domain}",
                theme=domain,
                items=paths[:20],  # Limit for output
                keywords=top_kws,
                strength=min(1.0, len(paths) / 10),
            ))
        
        return sorted(clusters, key=lambda c: len(c.items), reverse=True)
    
    def identify_gaps(self, clusters: list[SemanticCluster]) -> list[CapabilityGap]:
        """Identify capability gaps based on coverage."""
        covered = {c.theme for c in clusters if len(c.items) >= 2}
        gaps = []
        
        for domain in self.CAPABILITY_DOMAINS:
            if domain not in covered:
                severity = "high" if domain in ["security", "testing", "monitoring"] else "medium"
                gaps.append(CapabilityGap(
                    gap_id=f"gap_{domain}",
                    area=domain,
                    description=f"Limited or no coverage for {domain} capabilities",
                    severity=severity,
                    recommended_fix=f"Create {domain.upper()}_PRIME skill and MCP server",
                ))
        
        return gaps
    
    def generate_skill_recommendations(
        self,
        clusters: list[SemanticCluster],
        gaps: list[CapabilityGap],
    ) -> list[str]:
        """Generate recommendations for new skills."""
        recommendations = []
        
        # From gaps
        for gap in gaps:
            recommendations.append(
                f"Create {gap.area.upper()}_PRIME skill to address {gap.area} gap"
            )
        
        # From strong clusters
        for cluster in clusters[:5]:
            if cluster.strength > 0.5:
                recommendations.append(
                    f"Strengthen {cluster.theme} with advanced patterns from keywords: {', '.join(cluster.keywords[:5])}"
                )
        
        return recommendations[:10]
    
    def analyze(self) -> SemanticAnalysis:
        """Run full semantic analysis."""
        self.load_nodes()
        
        # Extract all keywords
        all_keywords = []
        for node in self.nodes:
            text = self.get_node_text(node)
            all_keywords.extend(self.extract_keywords(text))
        
        # Get top themes
        keyword_counts = Counter(all_keywords)
        top_themes = keyword_counts.most_common(20)
        
        # Cluster
        clusters = self.cluster_by_domain()
        
        # Find gaps
        gaps = self.identify_gaps(clusters)
        
        # Recommendations
        recommendations = self.generate_skill_recommendations(clusters, gaps)
        
        return SemanticAnalysis(
            timestamp=datetime.now(UTC).isoformat(),
            nodes_analyzed=len(self.nodes),
            clusters=clusters,
            top_themes=top_themes,
            capability_gaps=gaps,
            skill_recommendations=recommendations,
        )
    
    def save_analysis(self, analysis: SemanticAnalysis, output_path: Path | None = None):
        """Save analysis results."""
        output = output_path or (self.base_path / "knowledge_graph" / "audits" / f"semantic_analysis_{int(datetime.now().timestamp())}.json")
        output.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output, "w") as f:
            json.dump(analysis.to_dict(), f, indent=2)
        
        logger.info(f"Semantic analysis saved to {output}")
        return output


def run_semantic_analysis() -> SemanticAnalysis:
    """Run semantic analysis on the knowledge base."""
    analyzer = SemanticAnalyzer()
    analysis = analyzer.analyze()
    analyzer.save_analysis(analysis)
    return analysis


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    analysis = run_semantic_analysis()
    
    print(f"\n=== Semantic Analysis ===")
    print(f"Nodes analyzed: {analysis.nodes_analyzed}")
    print(f"Clusters: {len(analysis.clusters)}")
    print(f"\nTop themes: {analysis.top_themes[:10]}")
    print(f"\nCapability gaps: {[g.area for g in analysis.capability_gaps]}")
    print(f"\nRecommendations: {analysis.skill_recommendations[:5]}")
