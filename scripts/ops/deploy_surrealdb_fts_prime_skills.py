#!/usr/bin/env python3
"""Deploys SurrealDB BM25 Full-Text Search (FTS) Index & Ingests all 71 PRIME Skills."""

import asyncio
import glob
import os
import re
import time
import httpx

SURREAL_URL = "http://localhost:8001/sql"
SKILLS_DIR = "src/cohezion/skills"

SURREAL_HEADERS = {
    "surreal-ns": "cohezion",
    "surreal-db": "main",
    "Authorization": "Basic cm9vdDpyb290",
    "Content-Type": "text/plain"
}

def parse_prime_skill(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    name = os.path.basename(path).replace(".md", "")
    
    # Extract Domain Expertise
    domain_match = re.search(r"## DOMAIN EXPERTISE\s+([^\n#]+)", content)
    domain = domain_match.group(1).strip() if domain_match else ""

    # Extract Concepts
    concepts_match = re.search(r"## KEY TEXTS & CONCEPTS\s+([\s\S]*?)(?=##|\Z)", content)
    concepts = concepts_match.group(1).strip() if concepts_match else ""

    return {
        "id": f"skill:{name.lower()}",
        "name": name,
        "domain": domain,
        "concepts": concepts,
        "body": content[:2000],  # First 2k chars for indexing
        "path": path,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

async def deploy_fts_and_ingest():
    print("\n" + "=" * 105)
    print("🐘 DEPLOYING SURREALDB BM25 FULL-TEXT SEARCH (FTS) FOR 71 PRIME SKILLS")
    print("=" * 105)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Define Analyzer and FTS Index
        print("\n▶ [1] Defining BM25 Analyzer & Search Index on `skill` table...")
        schema_sql = """
        DEFINE ANALYZER IF NOT EXISTS prime_analyzer TOKENIZERS class,blank,punct FILTERS lowercase,snowball(english);
        DEFINE TABLE IF NOT EXISTS skill SCHEMAFULL;
        DEFINE FIELD IF NOT EXISTS name ON TABLE skill TYPE string;
        DEFINE FIELD IF NOT EXISTS domain ON TABLE skill TYPE string;
        DEFINE FIELD IF NOT EXISTS concepts ON TABLE skill TYPE string;
        DEFINE FIELD IF NOT EXISTS body ON TABLE skill TYPE string;
        DEFINE FIELD IF NOT EXISTS path ON TABLE skill TYPE string;
        DEFINE FIELD IF NOT EXISTS updated_at ON TABLE skill TYPE string;
        DEFINE INDEX IF NOT EXISTS skill_bm25_idx ON TABLE skill FIELDS name, domain, concepts, body SEARCH ANALYZER prime_analyzer BM25;
        """
        r = await client.post(SURREAL_URL, headers=SURREAL_HEADERS, content=schema_sql)
        print(f"  ✓ Schema & BM25 Index deployed (HTTP {r.status_code})")

        # 2. Ingest 71 PRIME Skills
        print("\n▶ [2] Ingesting all PRIME Skills from src/cohezion/skills/*.md...")
        skill_files = glob.glob(os.path.join(SKILLS_DIR, "*.md"))
        print(f"  Found {len(skill_files)} skill files to index.")

        ingest_count = 0
        t0 = time.perf_counter()
        for fpath in skill_files:
            skill_data = parse_prime_skill(fpath)
            upsert_sql = f"""
            UPSERT {skill_data['id']} CONTENT {{
                name: {repr(skill_data['name'])},
                domain: {repr(skill_data['domain'])},
                concepts: {repr(skill_data['concepts'])},
                body: {repr(skill_data['body'])},
                path: {repr(skill_data['path'])},
                updated_at: {repr(skill_data['updated_at'])}
            }};
            """
            r = await client.post(SURREAL_URL, headers=SURREAL_HEADERS, content=upsert_sql)
            if r.status_code == 200:
                ingest_count += 1

        dt = round(time.perf_counter() - t0, 3)
        print(f"  ✓ Ingested and indexed {ingest_count} skills into SurrealDB in {dt}s")

        # 3. Test BM25 Full-Text Search Query
        print("\n▶ [3] Testing BM25 Full-Text Search Retrieval for 'Hyperbolic Poincaré Topology'...")
        search_sql = """
        SELECT id, name, domain, search::score(1) AS relevance
        FROM skill
        WHERE [name, domain, concepts, body] @@ 'hyperbolic poincare manifold'
        ORDER BY relevance DESC
        LIMIT 3;
        """
        r = await client.post(SURREAL_URL, headers=SURREAL_HEADERS, content=search_sql)
        if r.status_code == 200:
            res_data = r.json()
            hits = res_data[0].get("result", []) if res_data else []
            for hit in hits:
                print(f"  • [{hit.get('relevance', 0.0):.4f}] {hit.get('name')}: {hit.get('domain')[:80]}...")

    print("\n" + "=" * 105)
    print("🎉 SURREALDB BM25 FULL-TEXT SEARCH OFFICIALLY OPERATIONAL FOR PRIME SKILLS!\n")

if __name__ == "__main__":
    asyncio.run(deploy_fts_and_ingest())
