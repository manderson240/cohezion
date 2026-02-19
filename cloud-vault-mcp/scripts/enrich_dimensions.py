#!/usr/bin/env python3
"""
12D Graph Phase 3-4: Enrich papers with complexity and impact dimensions.

Phase 3 dimensions:
  - algorithm_complexity (0.0-1.0): Technical complexity of methods described
  - implementation_difficulty (0.0-1.0): How hard to implement in practice

Phase 4 dimensions:
  - impact_score (0.0-1.0): Based on vault connectivity (incoming links as proxy)
  - interdisciplinary_transfer (0.0-1.0): Potential for cross-domain application

Uses Ollama phi4-mini-reasoning for classification, with heuristic fallback.
Updates both YAML frontmatter and SurrealDB records.
"""

import asyncio
import json
import re
import sys
from pathlib import Path

import httpx
import yaml

VAULT_PATH = Path("/home/mike-anderson/vaults/cohezion-vault")
PAPERS_DIR = VAULT_PATH / "papers"
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "phi3:mini"
SURREALDB_URL = "http://localhost:8000"
SURREALDB_HEADERS = {
    "Accept": "application/json",
    "surreal-ns": "cohezion",
    "surreal-db": "vault",
}
SURREALDB_AUTH = ("root", "root")


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown content."""
    if not content.startswith("---"):
        return {}, content
    end = content.find("---", 3)
    if end == -1:
        return {}, content
    fm_text = content[3:end].strip()
    try:
        fm = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError:
        return {}, content
    body = content[end + 3:].strip()
    return fm, body


def write_frontmatter(fm: dict, body: str) -> str:
    """Serialize frontmatter + body back to markdown."""
    fm_text = yaml.dump(fm, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return f"---\n{fm_text}---\n{body}\n"


async def classify_with_ollama(
    client: httpx.AsyncClient, title: str, summary: str
) -> dict[str, float]:
    """Use Ollama to classify complexity and transfer potential."""
    prompt = f"""Rate this research paper on two dimensions. Return ONLY a JSON object.

PAPER: "{title}"
SUMMARY: {summary[:400]}

Rate each 0.0-1.0:
- algorithm_complexity: How technically complex are the methods? (0=simple overview, 1=novel algorithms/proofs)
- implementation_difficulty: How hard to implement practically? (0=conceptual only, 1=requires specialized expertise)
- interdisciplinary_transfer: Can findings transfer to other domains? (0=domain-specific, 1=broadly applicable)

Respond with ONLY valid JSON, no other text:
{{"algorithm_complexity": 0.0, "implementation_difficulty": 0.0, "interdisciplinary_transfer": 0.0}}"""

    try:
        resp = await client.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 300},
            },
            timeout=60.0,
        )
        if resp.status_code != 200:
            return {}
        data = resp.json()
        text = data.get("response", "")
        # Strip thinking tags if present
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        # Extract JSON from response
        match = re.search(r"\{[^{}]+\}", text)
        if not match:
            return {}
        result = json.loads(match.group())
        return {
            "algorithm_complexity": max(0, min(1, float(result.get("algorithm_complexity", 0.5)))),
            "implementation_difficulty": max(0, min(1, float(result.get("implementation_difficulty", 0.5)))),
            "interdisciplinary_transfer": max(0, min(1, float(result.get("interdisciplinary_transfer", 0.5)))),
        }
    except Exception as e:
        print(f"  Ollama error: {type(e).__name__}: {e}")
        return {}


def compute_impact_score(fm: dict, body: str) -> float:
    """Compute impact score based on connectivity and link count."""
    connectivity = float(fm.get("connectivity", 0))
    # Count incoming wiki-links as proxy for citations
    link_count = len(re.findall(r"\[\[", body))
    # Normalize: connectivity (0-1) weight 0.6, link density weight 0.4
    link_score = min(1.0, link_count / 10)
    return round(connectivity * 0.6 + link_score * 0.4, 3)


def heuristic_complexity(title: str, tags: list, body: str) -> dict[str, float]:
    """Fallback heuristic when Ollama is unavailable."""
    title_lower = title.lower()
    body_lower = body[:500].lower()

    # Algorithm complexity heuristics
    complexity_keywords = [
        "algorithm", "proof", "theorem", "optimization", "neural", "transformer",
        "matrix", "decomposition", "quantum", "topology", "differential",
    ]
    complexity_count = sum(1 for k in complexity_keywords if k in body_lower or k in title_lower)
    algorithm_complexity = min(1.0, complexity_count / 4)

    # Implementation difficulty heuristics
    impl_keywords = [
        "implementation", "architecture", "framework", "pipeline", "deploy",
        "infrastructure", "system design", "engineering",
    ]
    impl_count = sum(1 for k in impl_keywords if k in body_lower or k in title_lower)
    implementation_difficulty = min(1.0, impl_count / 3)

    # Interdisciplinary transfer
    tag_set = set(tags) if tags else set()
    diverse_domains = len(tag_set)
    interdisciplinary_transfer = min(1.0, diverse_domains / 4)

    return {
        "algorithm_complexity": round(algorithm_complexity, 3),
        "implementation_difficulty": round(implementation_difficulty, 3),
        "interdisciplinary_transfer": round(interdisciplinary_transfer, 3),
    }


async def update_surrealdb(client: httpx.AsyncClient, paper_id: str, dims: dict):
    """Update SurrealDB record with new dimensions."""
    # Build SET clause
    sets = ", ".join([f"dimensions.{k} = {v}" for k, v in dims.items()])
    query = f"UPDATE vault_memory SET {sets} WHERE path CONTAINS '{paper_id}' AND type = 'paper'"
    try:
        resp = await client.post(
            f"{SURREALDB_URL}/sql",
            content=query,
            headers=SURREALDB_HEADERS,
            auth=SURREALDB_AUTH,
            timeout=10.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data and data[0].get("status") == "OK":
                updated = data[0].get("result", [])
                return len(updated) > 0
    except Exception as e:
        print(f"  SurrealDB error for {paper_id}: {e}")
    return False


async def main():
    papers = sorted(PAPERS_DIR.glob("*.md"))
    print(f"Found {len(papers)} papers to enrich")

    # Check which papers already have new dimensions
    already_done = 0
    to_process = []
    for paper_path in papers:
        content = paper_path.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(content)
        dims = fm.get("dimensions", {})
        if "algorithm_complexity" in dims and "impact_score" in dims:
            already_done += 1
        else:
            to_process.append(paper_path)

    print(f"Already enriched: {already_done}, remaining: {len(to_process)}")

    if not to_process:
        print("All papers already enriched!")
        return

    updated_count = 0
    surreal_count = 0

    async with httpx.AsyncClient() as client:
        for i, paper_path in enumerate(to_process):
            paper_id = paper_path.stem
            content = paper_path.read_text(encoding="utf-8")
            fm, body = parse_frontmatter(content)

            if not fm:
                print(f"  [{i+1}/{len(to_process)}] Skip {paper_id} (no frontmatter)")
                continue

            title = fm.get("title", paper_id)
            tags = fm.get("tags", [])

            # Get Ollama classification
            ollama_dims = await classify_with_ollama(client, str(title), body[:500])

            if not ollama_dims:
                # Fallback to heuristics
                ollama_dims = heuristic_complexity(str(title), tags, body)
                source = "heuristic"
            else:
                source = "ollama"

            # Compute impact score
            impact = compute_impact_score(fm, body)

            # Merge all new dimensions
            new_dims = {
                "algorithm_complexity": ollama_dims["algorithm_complexity"],
                "implementation_difficulty": ollama_dims["implementation_difficulty"],
                "interdisciplinary_transfer": ollama_dims["interdisciplinary_transfer"],
                "impact_score": impact,
            }

            # Update frontmatter
            if "dimensions" not in fm:
                fm["dimensions"] = {}
            fm["dimensions"].update(new_dims)

            # Write back
            new_content = write_frontmatter(fm, body)
            paper_path.write_text(new_content, encoding="utf-8")
            updated_count += 1

            # Update SurrealDB
            if await update_surrealdb(client, paper_id, new_dims):
                surreal_count += 1

            status = "✓" if source == "ollama" else "~"
            print(f"  [{i+1}/{len(to_process)}] {status} {paper_id} ({source}) "
                  f"complexity={new_dims['algorithm_complexity']:.2f} "
                  f"difficulty={new_dims['implementation_difficulty']:.2f} "
                  f"transfer={new_dims['interdisciplinary_transfer']:.2f} "
                  f"impact={new_dims['impact_score']:.2f}")

    print(f"\nDone: {updated_count} papers enriched, {surreal_count} SurrealDB records updated")
    print(f"Dimensions added: algorithm_complexity, implementation_difficulty, interdisciplinary_transfer, impact_score")


if __name__ == "__main__":
    asyncio.run(main())
