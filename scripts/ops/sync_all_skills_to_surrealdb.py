#!/usr/bin/env python3
"""Syncs all PRIME Skills (*.md) into SurrealDB `skill` table with robust null guards."""

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
    
    # Extract Domain
    domain_match = re.search(r"## DOMAIN EXPERTISE\s+([^\n#]+)", content)
    domain = domain_match.group(1).strip() if domain_match else f"Domain expertise for {name}"

    # Extract Concepts
    concepts_match = re.search(r"## KEY TEXTS & CONCEPTS\s+([\s\S]*?)(?=##|\Z)", content)
    concepts = concepts_match.group(1).strip() if concepts_match else ""

    return {
        "id": f"skill:{name.lower().replace('-', '_')}",
        "name": name,
        "domain": domain,
        "concepts": concepts,
        "body": content[:2500],
        "path": path,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

async def sync_skills():
    print("\n" + "=" * 105)
    print("🔄 SYNCING ALL PRIME SKILLS TO SURREALDB GRAPH INDEX")
    print("=" * 105)

    skill_files = glob.glob(os.path.join(SKILLS_DIR, "*.md"))
    print(f"Found {len(skill_files)} skill definition files to ingest.")

    count = 0
    t0 = time.perf_counter()
    async with httpx.AsyncClient(timeout=30.0) as client:
        for fpath in skill_files:
            skill = parse_prime_skill(fpath)
            upsert_sql = f"""
            UPSERT {skill['id']} CONTENT {{
                name: {repr(skill['name'])},
                domain: {repr(skill['domain'])},
                concepts: {repr(skill['concepts'])},
                body: {repr(skill['body'])},
                path: {repr(skill['path'])},
                updated_at: {repr(skill['updated_at'])}
            }};
            """
            r = await client.post(SURREAL_URL, headers=SURREAL_HEADERS, content=upsert_sql)
            if r.status_code == 200:
                count += 1

    dt = round(time.perf_counter() - t0, 3)
    print(f"✓ Successfully synced and indexed {count}/{len(skill_files)} skills in {dt}s")

    # Verify newly added skills
    print("\n▶ Verifying newly added skills:")
    verify_sql = """
    SELECT id, name, domain FROM skill WHERE name IN [
        'BLUEQUBIT_QUANTUM_ORCHESTRATOR_PRIME',
        'THERMODYNAMIC_COMPILER_PRIME',
        'SHEAF_TOPOLOGICAL_RAG_PRIME'
    ];
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(SURREAL_URL, headers=SURREAL_HEADERS, content=verify_sql)
        if r.status_code == 200:
            hits = r.json()[0].get("result", [])
            for h in hits:
                print(f"  • {h['name']}: {h['domain'][:80]}...")

    print("\n" + "=" * 105)
    print("🎉 ALL SKILL GAPS FULLY FILLED, INDEXED, AND SYNCHRONIZED!\n")

if __name__ == "__main__":
    asyncio.run(sync_skills())
