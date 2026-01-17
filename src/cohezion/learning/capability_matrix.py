"""
Capability Matrix Generator - Comprehensive capability analysis.

Creates a matrix showing:
- All platform capabilities
- Implementation status
- Coverage gaps
- MCP/tool requirements
"""

import json
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Capability:
    """A platform capability."""
    name: str
    domain: str
    status: str  # implemented, partial, planned, gap
    components: list[str]
    skills: list[str]
    mcp_servers: list[str]
    tools: list[str]
    coverage_score: float  # 0-1


@dataclass
class CapabilityMatrix:
    """Complete capability matrix."""
    timestamp: str
    total_capabilities: int
    implemented: int
    partial: int
    gaps: int
    capabilities: list[Capability]
    gap_analysis: dict[str, Any]
    recommendations: list[str]
    
    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "summary": {
                "total": self.total_capabilities,
                "implemented": self.implemented,
                "partial": self.partial,
                "gaps": self.gaps,
                "coverage_rate": self.implemented / max(self.total_capabilities, 1),
            },
            "capabilities": [asdict(c) for c in self.capabilities],
            "gap_analysis": self.gap_analysis,
            "recommendations": self.recommendations,
        }


class CapabilityAnalyzer:
    """
    Analyzes and generates capability matrix.
    """
    
    # Define expected capabilities
    EXPECTED_CAPABILITIES = {
        "core": [
            ("swarm_orchestration", "Multi-agent swarm coordination"),
            ("calm_prediction", "Continuous thought trajectory prediction"),
            ("physics_simulation", "12D physics state tracking"),
            ("journey_tracking", "Agent journey recording"),
        ],
        "infrastructure": [
            ("api_server", "REST API endpoints"),
            ("mcp_server", "Model Context Protocol servers"),
            ("database", "SurrealDB integration"),
            ("caching", "Redis caching layer"),
        ],
        "intelligence": [
            ("smart_routing", "Intelligent model routing"),
            ("semantic_analysis", "Knowledge base analysis"),
            ("skill_generation", "Automatic skill creation"),
            ("learning", "Continuous learning loop"),
        ],
        "visualization": [
            ("3d_rendering", "3D trajectory visualization"),
            ("12d_plots", "Multi-panel physics plots"),
            ("interactive_ui", "Web-based interface"),
            ("animations", "GIF/video generation"),
        ],
        "reliability": [
            ("circuit_breaker", "Fault tolerance"),
            ("health_checks", "System monitoring"),
            ("graceful_degradation", "Fallback handling"),
            ("auto_healing", "Self-repair mechanisms"),
        ],
        "security": [
            ("input_validation", "Request validation"),
            ("rate_limiting", "Request throttling"),
            ("audit_logging", "Security event logging"),
            ("auth", "Authentication/authorization"),
        ],
        "knowledge": [
            ("skill_registry", "Skill management"),
            ("knowledge_graph", "Entity relationships"),
            ("memory", "Persistent memory"),
            ("notebooks", "Multimodal notebooks"),
        ],
        "audio": [
            ("tts", "Text-to-speech synthesis"),
            ("voice_profiles", "Agent voice personas"),
            ("podcast_gen", "Podcast generation"),
        ],
    }
    
    def __init__(self, base_path: Path | None = None):
        self.base_path = base_path or Path("src/cohezion")
    
    def check_component_exists(self, name: str) -> bool:
        """Check if a component exists in the codebase."""
        patterns = {
            "swarm_orchestration": ["swarm/democratic_debate.py", "swarm/workflows"],
            "calm_prediction": ["calm/predictor.py"],
            "physics_simulation": ["physics", "swarm/journey_tracker.py"],
            "journey_tracking": ["swarm/journey_tracker.py"],
            "api_server": ["api/__init__.py"],
            "mcp_server": ["mcp/"],
            "database": ["db/"],
            "caching": ["reliability/pool.py"],
            "smart_routing": ["swarm/smart_router.py"],
            "semantic_analysis": ["learning/semantic_analyzer.py"],
            "skill_generation": ["learning/skill_generator.py"],
            "learning": ["learning/"],
            "3d_rendering": ["viz/"],
            "12d_plots": ["api/__init__.py"],  # Contains plot endpoints
            "interactive_ui": ["api/static/index.html"],
            "animations": ["viz/hypertools_renderer.py"],
            "circuit_breaker": ["reliability/__init__.py"],
            "health_checks": ["healing/platform_audit.py"],
            "graceful_degradation": ["reliability/pool.py"],
            "auto_healing": ["healing/"],
            "input_validation": ["security/"],
            "rate_limiting": ["security/middleware.py"],
            "audit_logging": ["security/"],
            "auth": ["security/"],
            "skill_registry": ["registry/"],
            "knowledge_graph": ["knowledge_graph/"],
            "memory": ["mcp/", "swarm/memory/"],
            "notebooks": ["learning/multimodal_notebook.py"],
            "tts": ["audio/tts_service.py"],
            "voice_profiles": ["audio/tts_service.py"],
            "podcast_gen": ["learning/multimodal_notebook.py"],
        }
        
        if name not in patterns:
            return False
        
        for pattern in patterns[name]:
            path = self.base_path / pattern
            if path.exists():
                return True
        return False
    
    def get_related_skills(self, name: str) -> list[str]:
        """Get skills related to a capability."""
        skills_path = self.base_path / "skills"
        related = []
        
        name_parts = name.split("_")
        for skill_file in skills_path.glob("*.md"):
            skill_name = skill_file.stem.lower()
            if any(part in skill_name for part in name_parts):
                related.append(skill_file.stem)
        
        return related[:5]
    
    def get_mcp_servers(self, name: str) -> list[str]:
        """Get MCP servers related to a capability."""
        registry_path = self.base_path / "mcp" / "mcp_registry.json"
        if not registry_path.exists():
            return []
        
        try:
            with open(registry_path) as f:
                registry = json.load(f)
            
            servers = []
            for server in registry.get("internal", []):
                server_name = server.get("name", "")
                if any(part in server_name.lower() for part in name.split("_")):
                    servers.append(server_name)
            
            return servers
        except Exception:
            return []
    
    def analyze_capability(self, name: str, description: str, domain: str) -> Capability:
        """Analyze a single capability."""
        exists = self.check_component_exists(name)
        skills = self.get_related_skills(name)
        mcp_servers = self.get_mcp_servers(name)
        
        # Determine status
        if exists and skills:
            status = "implemented"
            coverage = 1.0
        elif exists:
            status = "partial"
            coverage = 0.6
        elif skills:
            status = "partial"
            coverage = 0.3
        else:
            status = "gap"
            coverage = 0.0
        
        return Capability(
            name=name,
            domain=domain,
            status=status,
            components=[name] if exists else [],
            skills=skills,
            mcp_servers=mcp_servers,
            tools=[],  # Could be populated from tool registry
            coverage_score=coverage,
        )
    
    def generate_matrix(self) -> CapabilityMatrix:
        """Generate complete capability matrix."""
        capabilities = []
        
        for domain, caps in self.EXPECTED_CAPABILITIES.items():
            for name, description in caps:
                cap = self.analyze_capability(name, description, domain)
                capabilities.append(cap)
        
        # Count by status
        implemented = sum(1 for c in capabilities if c.status == "implemented")
        partial = sum(1 for c in capabilities if c.status == "partial")
        gaps = sum(1 for c in capabilities if c.status == "gap")
        
        # Gap analysis by domain
        gap_analysis = {}
        for domain in self.EXPECTED_CAPABILITIES:
            domain_caps = [c for c in capabilities if c.domain == domain]
            domain_gaps = [c for c in domain_caps if c.status == "gap"]
            gap_analysis[domain] = {
                "total": len(domain_caps),
                "gaps": len(domain_gaps),
                "coverage": 1 - len(domain_gaps) / max(len(domain_caps), 1),
                "missing": [c.name for c in domain_gaps],
            }
        
        # Generate recommendations
        recommendations = []
        for cap in capabilities:
            if cap.status == "gap":
                recommendations.append(f"CRITICAL: Implement {cap.name} in {cap.domain}")
            elif cap.status == "partial" and not cap.skills:
                recommendations.append(f"Create {cap.name.upper()}_PRIME skill")
        
        return CapabilityMatrix(
            timestamp=datetime.now(UTC).isoformat(),
            total_capabilities=len(capabilities),
            implemented=implemented,
            partial=partial,
            gaps=gaps,
            capabilities=capabilities,
            gap_analysis=gap_analysis,
            recommendations=recommendations[:15],
        )
    
    def save_matrix(self, matrix: CapabilityMatrix) -> Path:
        """Save capability matrix."""
        output_dir = self.base_path / "knowledge_graph" / "audits"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"capability_matrix_{int(datetime.now().timestamp())}.json"
        with open(output_file, "w") as f:
            json.dump(matrix.to_dict(), f, indent=2)
        
        logger.info(f"Capability matrix saved to {output_file}")
        return output_file


def generate_capability_matrix() -> CapabilityMatrix:
    """Generate and save capability matrix."""
    analyzer = CapabilityAnalyzer()
    matrix = analyzer.generate_matrix()
    analyzer.save_matrix(matrix)
    return matrix


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    matrix = generate_capability_matrix()
    
    print(f"\n=== Capability Matrix ===")
    print(f"Total: {matrix.total_capabilities}")
    print(f"Implemented: {matrix.implemented}")
    print(f"Partial: {matrix.partial}")
    print(f"Gaps: {matrix.gaps}")
    print(f"\nGap Analysis by Domain:")
    for domain, data in matrix.gap_analysis.items():
        print(f"  {domain}: {data['coverage']*100:.0f}% coverage, gaps: {data['missing']}")
    print(f"\nTop Recommendations:")
    for rec in matrix.recommendations[:5]:
        print(f"  - {rec}")
