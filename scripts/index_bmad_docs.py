#!/usr/bin/env python3
"""
BMAD Doc Indexer - Index all BMAD documentation.

Usage:
    python3 scripts/index_bmad_docs.py

This will:
1. Connect to SurrealDB
2. Index all 696 BMAD markdown files
3. Generate embeddings using Ollama
4. Store in vector database
5. Report statistics
"""

import asyncio
import sys
from pathlib import Path


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cohezion.mcp.servers.doc.indexer import index_bmad_docs


async def main():
    """Index all BMAD documentation."""
    print("🚀 Starting BMAD Documentation Indexing")
    print("=" * 60)

    try:
        # Index all BMAD docs
        results = await index_bmad_docs()

        print("\n" + "=" * 60)
        print("📊 Indexing Complete!")
        print("=" * 60)

        total_files = 0
        total_chunks = 0
        total_tokens = 0

        for library_id, result in results.items():
            print(f"\n📚 {library_id}:")
            print(f"   Files: {result['files_indexed']}")
            print(f"   Chunks: {result['chunks_created']}")
            print(f"   Tokens: {result['total_tokens']:,}")

            total_files += result["files_indexed"]
            total_chunks += result["chunks_created"]
            total_tokens += result["total_tokens"]

        print("\n" + "=" * 60)
        print("📈 Total Statistics:")
        print(f"   Libraries: {len(results)}")
        print(f"   Files: {total_files}")
        print(f"   Chunks: {total_chunks}")
        print(f"   Tokens: {total_tokens:,}")
        print("=" * 60)

        print("\n✅ Ready for queries!")
        print("   Test: curl -X POST http://localhost:8364/tools/query-docs \\")
        print('        -d \'{"libraryId": "bmad/bmm", "query": "create PRD"}\'')

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
