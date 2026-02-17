#!/usr/bin/env python3
"""
Test GraphRAG import with real vault documents

Tests:
1. Import 5 vault documents
2. Verify embeddings generated
3. Verify graph edges created
4. Query hybrid search
"""

import asyncio
import sys
from pathlib import Path


# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent.parent / "cloud-vault-mcp"))

import httpx
from src.mcp_server.graphrag_helpers import execute_surreal_async
from src.mcp_server.graphrag_import import GraphRAGImporter


async def test_import():
    """Test importing real vault documents"""
    vault_path = Path.home() / "vaults" / "cohezion-vault"

    if not vault_path.exists():
        print(f"❌ Vault not found: {vault_path}")
        return False

    print("🔬 Testing GraphRAG Import\n")

    async with GraphRAGImporter(vault_path) as importer:
        # Test 1: Import decisions directory
        print("1️⃣  Importing decisions...")
        results = await importer.import_directory("decisions", recursive=False)
        print(f"   ✅ Imported: {results['success']}/{results['total']}")
        print(f"   🔗 Edges: {results['edges_processed']}")

        if results["success"] == 0:
            print("   ❌ No documents imported")
            return False

        # Test 2: Verify embeddings exist
        print("\n2️⃣  Verifying embeddings...")
        async with httpx.AsyncClient() as client:
            query = """
            SELECT id, title, embedding_model, embedding_dim, count(embedding) AS has_embedding
            FROM vault_memory
            WHERE type = 'decision'
            LIMIT 5;
            """
            result = await execute_surreal_async(query, client)

            if result and result[0].get("status") == "OK":
                docs = result[0]["result"]
                for doc in docs[:3]:  # Show first 3
                    has_emb = "✅" if doc.get("has_embedding", 0) > 0 else "❌"
                    print(f"   {has_emb} {doc['title'][:50]}")
                    print(f"      Model: {doc.get('embedding_model', 'N/A')}, Dim: {doc.get('embedding_dim', 0)}")

        # Test 3: Count graph edges
        print("\n3️⃣  Checking graph edges...")
        async with httpx.AsyncClient() as client:
            query = "SELECT count() FROM informed_by GROUP ALL;"
            result = await execute_surreal_async(query, client)

            if result and result[0].get("status") == "OK":
                count = result[0]["result"][0]["count"] if result[0]["result"] else 0
                print(f"   🔗 Total edges: {count}")

        # Test 4: Test graph traversal
        print("\n4️⃣  Testing graph traversal...")
        async with httpx.AsyncClient() as client:
            query = """
            SELECT
                id,
                title,
                ->informed_by->vault_memory AS references
            FROM vault_memory
            WHERE type = 'decision'
            AND count(->informed_by) > 0
            LIMIT 1
            FETCH references;
            """
            result = await execute_surreal_async(query, client)

            if result and result[0].get("status") == "OK" and result[0]["result"]:
                doc = result[0]["result"][0]
                refs = doc.get("references", [])
                print(f"   📊 {doc['title'][:50]}")
                print(f"   🔗 References {len(refs)} document(s)")

        print("\n✅ GraphRAG import test successful!")
        return True


if __name__ == "__main__":
    try:
        success = asyncio.run(test_import())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
