import asyncio
import os

from surrealdb import AsyncSurreal



async def init_brand_db():
    """Initializes SurrealDB with Cohezion branding tokens."""
    db_url = os.environ.get("SURREALDB_URL", "ws://localhost:8000/rpc")

    async with AsyncSurreal(db_url) as db:
        await db.signin({"user": "root", "pass": "root"})
        await db.use("cohezion", "identity")

        # Upsert the primary brand identity
        brand_data = {
            "name": "Cohezion",
            "tagline": "The Nexus of Coherence",
            "philosophy": "Organic Modularity",
            "colors": {
                "nexus_green": "#00FF00",
                "matte_black": "#0A0A0A",
                "silicon_silver": "#C0C0C0",
                "earth_blue": "#0077BE",
            },
            "motifs": ["Performance Delta", "Lattice Grid", "Open Singularity"],
            "logo_path": "/home/mike-anderson/.gemini/antigravity/brain/2affbcca-b8be-4a9f-a143-509531a03543/cohezion_nexus_logo_refined_1769101905406.png",
            "last_updated": "2026-01-22T12:15:00Z",
        }

        await db.create("brand_identity:nexus", brand_data)
        print("Cohezion Brand Identity successfully projected into SurrealDB.")


if __name__ == "__main__":
    asyncio.run(init_brand_db())
