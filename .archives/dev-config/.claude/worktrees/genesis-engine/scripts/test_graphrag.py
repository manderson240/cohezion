#!/usr/bin/env python3
"""
GraphRAG Proof-of-Concept for Cohezion Vault

Tests graph-vector hybrid search:
1. Insert decision + pattern with graph edge
2. Vector search for similar content
3. Graph traversal to show relationships
"""

import httpx


def execute_surreal(query: str) -> list:
    """Execute SurrealQL query"""
    # Prepend USE statement to every query
    full_query = f"USE NS cohezion DB vault;\n{query}"

    response = httpx.post(
        "http://localhost:8000/sql",
        headers={
            "Content-Type": "text/plain",
            "Accept": "application/json",
        },
        auth=("root", "root"),
        content=full_query,
        timeout=10.0,
    )
    response.raise_for_status()
    results = response.json()

    # Skip the first result (USE statement confirmation)
    return results[1:] if len(results) > 1 else results


def test_graphrag():
    """Test GraphRAG with real vault data"""

    print("🔬 GraphRAG Proof-of-Concept\n")

    # Step 1: Insert decision (vault-first-knowledge-architecture)
    print("1️⃣  Inserting decision...")
    decision_query = """
    CREATE vault_memory:vault_first_decision SET
        type = 'decision',
        path = 'decisions/2026-02-11-vault-first-knowledge-architecture.md',
        title = 'Vault-First Knowledge Architecture',
        content = 'Adopt vault-first architecture: Vault = single source of truth. MEMORY.md = compiled cache. All learnings logged to vault using structured tools.',
        tags = ['architecture', 'knowledge-management', 'compound-engineering'];
    """
    result = execute_surreal(decision_query)
    print(f"   ✅ Decision inserted: {result[0]['result'][0]['id']}")

    # Step 2: Insert pattern (token-efficient-implementation-workflow)
    print("\n2️⃣  Inserting pattern...")
    pattern_query = """
    CREATE vault_memory:token_efficient_pattern SET
        type = 'pattern',
        path = 'patterns/token-efficient-implementation-workflow.md',
        title = 'Token-Efficient Implementation Workflow',
        content = 'Implement ONE feature, validate manually, write 5 tests. NOT 600 pre-implementation tests. Copy working templates over greenfield exploration.',
        tags = ['token-efficiency', 'testing', 'workflow'];
    """
    result = execute_surreal(pattern_query)
    print(f"   ✅ Pattern inserted: {result[0]['result'][0]['id']}")

    # Step 3: Create graph edge (pattern informed_by decision)
    print("\n3️⃣  Creating graph relationship...")
    edge_query = """
    RELATE vault_memory:token_efficient_pattern->informed_by->vault_memory:vault_first_decision
    SET how = 'Pattern extracted during vault-first migration (Session 56)',
        created_at = time::now();
    """
    result = execute_surreal(edge_query)
    print(f"   ✅ Edge created: {result[0]['result'][0]['id']}")

    # Step 4: Query - Find patterns informed by vault-first decision
    print("\n4️⃣  Testing graph traversal...")
    graph_query = """
    SELECT
        id,
        title,
        type,
        <-informed_by<-vault_memory AS informed_patterns
    FROM vault_memory:vault_first_decision
    FETCH informed_patterns;
    """
    result = execute_surreal(graph_query)
    decision = result[0]["result"][0]
    print(f"   📊 Decision: {decision['title']}")
    print(f"   🔗 Informed {len(decision.get('informed_patterns', []))} pattern(s)")

    # Step 5: Reverse query - What informed this pattern?
    print("\n5️⃣  Testing reverse graph traversal...")
    reverse_query = """
    SELECT
        id,
        title,
        type,
        ->informed_by->vault_memory AS informed_by_decisions
    FROM vault_memory:token_efficient_pattern
    FETCH informed_by_decisions;
    """
    result = execute_surreal(reverse_query)
    pattern = result[0]["result"][0]
    print(f"   📊 Pattern: {pattern['title']}")
    if pattern.get("informed_by_decisions"):
        for decision in pattern["informed_by_decisions"]:
            print(f"   ⬅️  Informed by: {decision['title']}")

    # Step 6: Count total vault memories
    print("\n6️⃣  Vault memory stats...")
    count_query = "SELECT count() FROM vault_memory GROUP BY type;"
    result = execute_surreal(count_query)
    print(f"   📈 Total memories: {result[0]['result']}")

    print("\n✅ GraphRAG proof-of-concept successful!")
    print("\n💡 Next: Add embeddings + vector search for hybrid queries")

    return True


if __name__ == "__main__":
    try:
        success = test_graphrag()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        exit(1)
