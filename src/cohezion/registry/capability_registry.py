"""
Unified Capability Registry.
Aggregates Skills, Agents, and MCP Servers into a single natural-language search index.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


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
    """A skill, agent, or MCP server with usage tracking and compound hooks."""

    name: str
    type: str  # "skill", "agent", "mcp"
    description: str
    path: str
    tags: list[str] = field(default_factory=list)
    score: float = 0.0
    usage_count: int = 0  # Track invocations for optimization
    last_used: str = ""  # ISO timestamp for recency analysis
    future_proofing_hooks: list[str] = field(default_factory=list)  # Reusable "compound" hooks
    compound_impact_score: float = 0.0  # Measure of how much this feature helped others


class CapabilityRegistry:
    """Unified registry with usage tracking for compound engineering."""

    USAGE_FILE = "capability_usage.json"

    def __init__(self, root_dir: Path | None = None):
        self.root_dir = root_dir or Path(__file__).parent.parent.parent.parent
        self.capabilities: list[Capability] = []
        self.vectorizer = None
        self.vectors = None
        self._usage_cache: dict[str, dict] = {}  # name -> {count, last_used}

        # Load immediately
        self._load_usage()
        self.refresh()

    def refresh(self):
        """Scan codebase and rebuild index."""
        self.capabilities = []

        self._scan_skills()
        self._scan_mcp()
        self._scan_agents()
        self._apply_usage_to_capabilities()

        if SKLEARN_AVAILABLE and self.capabilities:
            self._build_index()
        else:
            logger.warning("Scikit-learn not available or no capabilities. Search will be limited.")

    def _scan_skills(self):
        """Load skills from skill_registry.json, falling back to filesystem scan."""
        registry_json = Path(__file__).parent / "skill_registry.json"

        if registry_json.exists():
            try:
                data = json.loads(registry_json.read_text())
                for name, meta in data.items():
                    tags = ["skill", "instruction"]
                    tags.append(name.replace("_", " ").lower())
                    keywords = meta.get("keywords", [])
                    if keywords:
                        tags.extend(keywords)

                    self.capabilities.append(
                        Capability(
                            name=name,
                            type="skill",
                            description=meta.get("description", f"Skill: {name}"),
                            path=meta.get("path", ""),
                            tags=tags,
                        )
                    )
                return
            except Exception as e:
                logger.error(f"Failed to load skill_registry.json: {e}")

        # Fallback: scan markdown files directly
        skills_dir = self.root_dir / "src/cohezion/skills"
        if not skills_dir.exists():
            return

        for md_file in skills_dir.glob("*.md"):
            try:
                self.capabilities.append(
                    Capability(
                        name=md_file.stem,
                        type="skill",
                        description=f"Skill defined in {md_file.name}",
                        path=str(md_file.relative_to(self.root_dir)),
                        tags=[
                            "skill",
                            "instruction",
                            md_file.stem.replace("_", " ").lower(),
                        ],
                    )
                )
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
                self.capabilities.append(
                    Capability(
                        name=server.get("name"),
                        type="mcp",
                        description=server.get("description", ""),
                        path=server.get("path", ""),
                        tags=["tool", "server", "int", *server.get("tools", [])],
                    )
                )
            # External
            for server in data.get("external", []):
                self.capabilities.append(
                    Capability(
                        name=server.get("name"),
                        type="mcp",
                        description=server.get("description", ""),
                        path=server.get("url", ""),
                        tags=["tool", "server", "ext"],
                    )
                )
        except Exception as e:
            logger.error(f"Failed to scan MCP registry: {e}")

    def _scan_agents(self):
        """Scan all agent directories for python classes with docstring extraction."""
        agent_dirs = [
            self.root_dir / "src/cohezion/agents",
            self.root_dir / "src/cohezion/swarm/agents",
        ]
        seen_names: set[str] = set()

        for agents_dir in agent_dirs:
            if not agents_dir.exists():
                continue

            for py_file in agents_dir.glob("*.py"):
                if py_file.name.startswith("__") or py_file.name == "base.py":
                    continue
                if py_file.name.endswith("_test.py"):
                    continue

                try:
                    content = py_file.read_text(errors="ignore")
                    if "class " not in content:
                        continue

                    # Extract actual class name from source
                    class_name = None
                    for line in content.split("\n"):
                        stripped = line.strip()
                        if stripped.startswith("class ") and "Agent" in stripped:
                            class_name = stripped.split("(")[0].replace("class ", "").strip()
                            break

                    if not class_name:
                        class_name = "".join(word.capitalize() for word in py_file.stem.split("_"))
                        if not class_name.endswith("Agent"):
                            class_name += "Agent"

                    if class_name in seen_names:
                        continue
                    seen_names.add(class_name)

                    # Extract class docstring for description
                    desc = f"Agent defined in {py_file.name}"
                    lines = content.split("\n")
                    in_class = False
                    in_docstring = False
                    docstring_lines: list[str] = []
                    for line in lines:
                        if f"class {class_name}" in line:
                            in_class = True
                            continue
                        if in_class and not in_docstring:
                            stripped = line.strip()
                            if stripped.startswith('"""'):
                                # Check for single-line docstring: """text"""
                                if stripped.count('"""') >= 2:
                                    desc = (
                                        stripped.removeprefix('"""')
                                        .removesuffix('"""')
                                        .strip()[:200]
                                    )
                                    break
                                # Multi-line docstring starts
                                in_docstring = True
                                first = stripped.removeprefix('"""').strip()
                                if first:
                                    docstring_lines.append(first)
                                continue
                            if stripped and not stripped.startswith("#"):
                                break  # No docstring found
                        elif in_docstring:
                            if '"""' in line:
                                # Closing triple-quote
                                last = line.split('"""')[0].strip()
                                if last:
                                    docstring_lines.append(last)
                                break
                            stripped = line.strip()
                            if stripped:
                                docstring_lines.append(stripped)
                    if docstring_lines:
                        desc = " ".join(docstring_lines)[:200]

                    # Semantic tag extraction
                    tags = ["agent", "autonomous"]
                    tag_keywords = {
                        "maintenance": ["git_health", "pruning", "cleanup", "simplif"],
                        "analysis": ["analy", "audit", "benchmark", "metric"],
                        "security": ["security", "guard", "alignment", "ethics"],
                        "creative": ["narrative", "cosmic", "universe", "world_model"],
                        "research": ["research", "scout", "explor", "hypothesis"],
                        "coding": ["code", "architect", "engineer", "skill_distill"],
                        "knowledge": ["memory", "librarian", "chronicle", "knowledge"],
                        "healing": ["heal", "immune", "diagnos", "repair"],
                    }
                    content_lower = content.lower()
                    for tag, keywords in tag_keywords.items():
                        if any(kw in content_lower for kw in keywords):
                            tags.append(tag)

                    self.capabilities.append(
                        Capability(
                            name=class_name,
                            type="agent",
                            description=desc,
                            path=str(py_file.relative_to(self.root_dir)),
                            tags=tags,
                        )
                    )
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

        self.vectorizer = TfidfVectorizer(stop_words="english")
        self.vectors = self.vectorizer.fit_transform(corpus)

    def find(self, query: str, top_k: int = 5) -> list[Capability]:
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

    def get_capabilities(self, name: str) -> list[str]:
        """Get tags/capabilities for a specific component name."""
        for cap in self.capabilities:
            if cap.name == name:
                return cap.tags
        return []

    def increment_usage(self, name: str) -> None:
        """Record that a capability was used. 🎯 Compound Engineering!"""
        now = datetime.now().isoformat()
        if name in self._usage_cache:
            self._usage_cache[name]["count"] += 1
            self._usage_cache[name]["last_used"] = now
        else:
            self._usage_cache[name] = {"count": 1, "last_used": now}

        # Update in-memory capability
        for cap in self.capabilities:
            if cap.name == name:
                cap.usage_count = self._usage_cache[name]["count"]
                cap.last_used = now
                break

        self._persist_usage()
        logger.debug(f"📊 Usage tracked: {name} (count: {self._usage_cache[name]['count']})")

    def get_top_used(self, top_k: int = 10) -> list[Capability]:
        """Get most frequently used capabilities for optimization."""
        sorted_caps = sorted(self.capabilities, key=lambda c: c.usage_count, reverse=True)
        return sorted_caps[:top_k]

    def _load_usage(self) -> None:
        """Load usage stats from persistent cache."""
        usage_file = Path(__file__).parent / self.USAGE_FILE
        if usage_file.exists():
            try:
                self._usage_cache = json.loads(usage_file.read_text())
                logger.info(f"📈 Loaded usage stats for {len(self._usage_cache)} capabilities")
            except Exception as e:
                logger.warning(f"Failed to load usage cache: {e}")
                self._usage_cache = {}

    def _persist_usage(self) -> None:
        """Save usage stats to persistent cache."""
        usage_file = Path(__file__).parent / self.USAGE_FILE
        try:
            usage_file.write_text(json.dumps(self._usage_cache, indent=2))
        except Exception as e:
            logger.error(f"Failed to persist usage: {e}")

    def _apply_usage_to_capabilities(self) -> None:
        """Apply cached usage stats to scanned capabilities."""
        for cap in self.capabilities:
            if cap.name in self._usage_cache:
                cap.usage_count = self._usage_cache[cap.name].get("count", 0)
                cap.last_used = self._usage_cache[cap.name].get("last_used", "")

    def persist_capability_snapshot(self, reason: str = "periodic") -> dict:
        """Persist current capability state to vault + SurrealDB.

        Writes a summary of all capabilities, their scores, usage counts, and
        compound impact to the knowledge persistence pipeline.

        Args:
            reason: Why this snapshot is being taken (e.g., "periodic", "capability-change")

        Returns:
            Dict with persistence results from knowledge_bridge.
        """
        try:
            from cohezion.governance.knowledge_bridge import Learning, persist_learning

            top_caps = sorted(self.capabilities, key=lambda c: c.usage_count, reverse=True)[:10]
            cap_summary = "\n".join(
                f"- {c.name} ({c.type}): score={c.score:.2f}, usage={c.usage_count}"
                for c in top_caps
            )

            learning = Learning(
                number=0,
                title=f"Capability snapshot ({reason})",
                content=(
                    f"Registry contains {len(self.capabilities)} capabilities. "
                    f"Top 10 by usage:\n{cap_summary}"
                ),
                date=datetime.now().strftime("%Y-%m-%d"),
                tags=["capability", "snapshot", reason],
                propagate_to="Capability registry evolution",
            )

            return persist_learning(learning)

        except Exception as e:
            logger.debug("Capability snapshot persistence failed: %s", e)
            return {"error": str(e)}


if __name__ == "__main__":
    # Test Run
    logging.basicConfig(level=logging.INFO)
    reg = CapabilityRegistry()
    print(f"Loaded {len(reg.capabilities)} capabilities.")

    test_queries = [
        "physics simulation",
        "critique code",
        "manage project constraints",
        "deploy to cloud",
    ]

    for q in test_queries:
        print(f"\nQUERY: '{q}'")
        for res in reg.find(q, top_k=3):
            print(
                f"  - [{res.type.upper()}] {res.name}: {res.description[:50]}... ({res.score:.2f})"
            )
