#!/usr/bin/env python3
"""
Kernel Pattern Embeddings Pipeline

Uses local embedding models to create a retrieval-augmented knowledge base
of GPU kernel optimization patterns.

Features:
- Embed successful kernel optimization patterns
- Store in ChromaDB for retrieval
- Query patterns relevant to current optimization task
- Update embeddings from new session results

Usage:
    python embeddings.py index                    # Index all session patterns
    python embeddings.py query "MLA optimization" # Query patterns
    python embeddings.py stats                  # Show embedding stats
"""

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


# Check for chromadb
try:
    import chromadb
    from chromadb.config import Settings

    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    print("Warning: chromadb not installed. Run: pip install chromadb")

# Check for sentence-transformers
try:
    from sentence_transformers import SentenceTransformer

    ST_AVAILABLE = True
except ImportError:
    ST_AVAILABLE = False
    print("Warning: sentence-transformers not installed. Run: pip install sentence-transformers")


@dataclass
class KernelPattern:
    """A GPU kernel optimization pattern."""

    id: str
    category: str  # "mla", "gemm", "moe"
    title: str
    description: str
    code_snippet: str
    outcome: str  # "success", "failure", "partial"
    performance_delta: str  # "~20% faster", "~2x slower", etc.
    source_session: str
    source_file: str


class KernelEmbedder:
    """Embeds and retrieves GPU kernel optimization patterns."""

    COLLECTION_NAME = "kernel_patterns"

    def __init__(self, persist_dir: str = None):
        if not CHROMADB_AVAILABLE:
            raise RuntimeError("chromadb required. Install: pip install chromadb")

        if persist_dir is None:
            persist_dir = Path(__file__).parent / "chroma_db"

        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(path=str(self.persist_dir))

        # Try to get existing collection or create new
        try:
            self.collection = self.client.get_collection(self.COLLECTION_NAME)
            print(f"Loaded existing collection with {self.collection.count()} patterns")
        except:
            self.collection = self.client.create_collection(
                self.COLLECTION_NAME, metadata={"description": "GPU kernel optimization patterns"}
            )
            print("Created new collection")

        # Initialize embedder (use local Ollama or fallback)
        if ST_AVAILABLE:
            # Use local sentence-transformers model
            self.embedder = SentenceTransformer("snowflake-arctic-embed2")
            self.embedding_model = "snowflake-arctic-embed2"
        else:
            # Fall back to Ollama
            self.embedder = None
            self.embedding_model = "ollama:nomic-embed-text"

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed texts using available embedder."""
        if self.embedder:
            embeddings = self.embedder.encode(texts).tolist()
        else:
            # Use Ollama API
            import urllib.error
            import urllib.request

            embeddings = []
            for text in texts:
                data = json.dumps({"model": "nomic-embed-text", "prompt": text}).encode()

                req = urllib.request.Request(
                    "http://localhost:11434/api/embeddings",
                    data=data,
                    headers={"Content-Type": "application/json"},
                )

                try:
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        result = json.loads(resp.read())
                        embeddings.append(result["embedding"])
                except Exception as e:
                    print(f"Embedding failed: {e}")
                    # Return zero vector as fallback
                    embeddings.append([0.0] * 768)

        return embeddings

    def index_patterns(self, patterns: list[KernelPattern]) -> int:
        """Index a list of kernel patterns."""
        if not patterns:
            print("No patterns to index")
            return 0

        print(f"Indexing {len(patterns)} patterns...")

        # Prepare data
        ids = [p.id for p in patterns]
        documents = [self._pattern_to_doc(p) for p in patterns]
        embeddings = self.embed_texts(documents)
        metadatas = [self._pattern_to_meta(p) for p in patterns]

        # Add to collection
        self.collection.add(
            ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas
        )

        print(f"Indexed {len(patterns)} patterns (total: {self.collection.count()})")
        return len(patterns)

    def query(self, query: str, top_k: int = 5, category: str = None) -> list[dict]:
        """Query for relevant patterns."""
        # Embed query
        query_embedding = self.embed_texts([query])[0]

        # Build where filter if category specified
        where = {"category": category} if category else None

        # Query
        results = self.collection.query(
            query_embeddings=[query_embedding], n_results=top_k, where=where
        )

        # Format results
        patterns = []
        for i in range(len(results["ids"][0])):
            patterns.append(
                {
                    "id": results["ids"][0][i],
                    "document": results["documents"][0][i],
                    "distance": results["distances"][0][i],
                    "metadata": results["metadatas"][0][i],
                }
            )

        return patterns

    def delete_pattern(self, pattern_id: str) -> bool:
        """Delete a pattern by ID."""
        try:
            self.collection.delete(ids=[pattern_id])
            print(f"Deleted pattern: {pattern_id}")
            return True
        except Exception as e:
            print(f"Delete failed: {e}")
            return False

    def clear(self):
        """Clear all patterns."""
        self.client.delete_collection(self.COLLECTION_NAME)
        self.collection = self.client.create_collection(self.COLLECTION_NAME)
        print("Cleared all patterns")

    def stats(self) -> dict:
        """Get collection statistics."""
        count = self.collection.count()

        # Get category distribution
        all_data = self.collection.get()
        categories = {}
        for meta in all_data["metadatas"]:
            cat = meta.get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1

        return {
            "total_patterns": count,
            "categories": categories,
            "embedding_model": self.embedding_model,
        }

    def _pattern_to_doc(self, p: KernelPattern) -> str:
        """Convert pattern to document string."""
        return f"""## {p.title}

**Category:** {p.category}
**Outcome:** {p.outcome} ({p.performance_delta})
**Source:** {p.source_session}

### Description
{p.description}

### Code Snippet
```python
{p.code_snippet}
```
"""

    def _pattern_to_meta(self, p: KernelPattern) -> dict:
        """Convert pattern to metadata."""
        return {
            "category": p.category,
            "outcome": p.outcome,
            "source_session": p.source_session,
            "indexed_at": datetime.now().isoformat(),
        }


def extract_patterns_from_session(session_dir: Path) -> list[KernelPattern]:
    """Extract kernel patterns from a session directory."""
    patterns = []

    # Find challengers
    challengers_dir = session_dir / "challengers"
    if not challengers_dir.exists():
        return patterns

    for kernel_dir in challengers_dir.iterdir():
        if not kernel_dir.is_dir():
            continue

        kernel_type = kernel_dir.name  # mla, gemm, moe

        for challenger_file in kernel_dir.glob("*.py"):
            content = challenger_file.read_text()

            # Extract docstring
            docstring = ""
            if '"""' in content:
                parts = content.split('"""')
                if len(parts) >= 3:
                    docstring = parts[1].strip()

            # Extract code snippet (first 50 lines)
            code_lines = content.split("\n")[:50]
            code_snippet = "\n".join(code_lines)

            # Determine outcome from filename/content
            outcome = "partial"
            if "aiter" in challenger_file.name.lower():
                outcome = "partial"  # Baseline comparison
            elif "mfma" in challenger_file.name.lower():
                outcome = "unknown"  # New approach, not tested
            elif "v1" in challenger_file.name.lower():
                outcome = "partial"

            # Create pattern
            pattern = KernelPattern(
                id=f"{session_dir.name}_{kernel_type}_{challenger_file.stem}",
                category=kernel_type,
                title=docstring.split("\n")[0] if docstring else challenger_file.stem,
                description=docstring[100:500] if len(docstring) > 100 else docstring,
                code_snippet=code_snippet,
                outcome=outcome,
                performance_delta="untested",
                source_session=session_dir.name,
                source_file=str(challenger_file.relative_to(session_dir)),
            )
            patterns.append(pattern)

    return patterns


def main():
    parser = argparse.ArgumentParser(description="Kernel Pattern Embeddings")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("stats", help="Show embedding stats")

    index_parser = subparsers.add_parser("index", help="Index session patterns")
    index_parser.add_argument("--session", help="Specific session directory")
    index_parser.add_argument(
        "--sessions-dir",
        default="/home/mike-anderson/dev/cohezion/research/challenges/luma_amd_speedrun/sessions",
        help="Sessions directory",
    )

    query_parser = subparsers.add_parser("query", help="Query patterns")
    query_parser.add_argument("query", help="Query string")
    query_parser.add_argument("--top-k", type=int, default=5, help="Number of results")
    query_parser.add_argument("--category", help="Filter by category (mla/gemm/moe)")

    subparsers.add_parser("clear", help="Clear all patterns")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    # Initialize embedder
    persist_dir = Path(__file__).parent / "chroma_db"
    embedder = KernelEmbedder(persist_dir=persist_dir)

    if args.command == "stats":
        stats = embedder.stats()
        print("\n=== EMBEDDING STATS ===")
        print(f"Total patterns: {stats['total_patterns']}")
        print(f"Embedding model: {stats['embedding_model']}")
        print("\nBy category:")
        for cat, count in stats["categories"].items():
            print(f"  {cat}: {count}")

    elif args.command == "index":
        if args.session:
            # Index single session
            session_dir = Path(args.sessions_dir) / args.session
            patterns = extract_patterns_from_session(session_dir)
        else:
            # Index all sessions
            sessions_dir = Path(args.sessions_dir)
            patterns = []
            for session in sessions_dir.iterdir():
                if session.is_dir():
                    patterns.extend(extract_patterns_from_session(session))

        if patterns:
            embedder.index_patterns(patterns)
        else:
            print("No patterns found")

    elif args.command == "query":
        results = embedder.query(args.query, top_k=args.top_k, category=args.category)

        print(f"\n=== QUERY: {args.query} ===")
        print(f"Results: {len(results)}\n")

        for i, result in enumerate(results, 1):
            print(f"{i}. [{result['metadata']['category']}] {result['id']}")
            print(f"   Distance: {result['distance']:.4f}")
            print(f"   Outcome: {result['metadata']['outcome']}")
            print(f"   {result['document'][:200]}...")
            print()

    elif args.command == "clear":
        confirm = input("Clear ALL patterns? (yes/no): ")
        if confirm.lower() == "yes":
            embedder.clear()


if __name__ == "__main__":
    main()
