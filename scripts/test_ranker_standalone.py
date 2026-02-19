import logging
from typing import Any


# Mock class copied from optimizer.py for standalone audit
class SemanticContextRanker:
    """
    Ranks message relevance based on current task context and keywords.
    """

    def rank_messages(
        self, messages: list[dict[str, str]], query: str
    ) -> list[dict[str, Any]]:
        """Rank messages by relevance to the query."""
        ranked = []
        keywords = set(query.lower().split())

        for idx, msg in enumerate(messages):
            content = msg.get("content", "").lower()
            score = 0.0

            # Keyword matches
            if any(kw in content for kw in keywords):
                score += 1.0

            # Recency bias (0.0 to 0.5)
            if messages:
                score += (idx / len(messages)) * 0.5

            ranked.append({"index": idx, "message": msg, "score": score})

        # Sort by score descending
        return sorted(ranked, key=lambda x: x["score"], reverse=True)


def test_ranker_fidelity():
    print("Starting Standalone Fidelity Test: SemanticContextRanker Relevance")

    # 1. Create a noisy conversation history
    messages = [
        {"role": "user", "content": "I like pizza with pineapple."},
        {
            "role": "assistant",
            "content": "Interesting choice. Pineapple is controversial.",
        },
        {
            "role": "user",
            "content": "Now, about the database schema for the user profiles.",
        },
        {"role": "assistant", "content": "The users table should have an email field."},
        {"role": "user", "content": "The weather is nice today."},
        {"role": "assistant", "content": "Yes, clear skies."},
        {"role": "user", "content": "We should use Postgres for the database."},
        {"role": "assistant", "content": "Postgres is great for relational data."},
        {"role": "user", "content": "I forgot my umbrella."},
        {"role": "assistant", "content": "Hope it doesn't rain."},
    ]

    # 2. Rank for "database"
    ranker = SemanticContextRanker()
    print("Ranking for 'database'...")
    ranked = ranker.rank_messages(messages, query="database")

    top_3_indices = [r["index"] for r in ranked[:3]]
    print(f"Top 3 indices: {top_3_indices}")

    # Expected indices related to database are 2, 3, 6, 7.
    # Recency bias favors later messages: index 6 (Postgres) should be high.
    # Recency of index 7 vs index 3 etc.

    relevant_count = 0
    for idx in top_3_indices:
        content = messages[idx]["content"].lower()
        if "database" in content or "user profiles" in content or "postgres" in content:
            print(f"✅ Relevant message found: {content[:50]}...")
            relevant_count += 1
        else:
            print(f"❌ IRRELEVANT message ranked in top 3: {content[:50]}...")

    if relevant_count >= 2:
        print("✅ SUCCESS: Ranker correctly prioritized relevant database context.")
    else:
        print(
            f"❌ FAILURE: Ranker failed to prioritize relevant context ({relevant_count}/3)."
        )


if __name__ == "__main__":
    test_ranker_fidelity()
