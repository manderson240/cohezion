import logging

from cohezion.compound.optimizer import SemanticContextRanker


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fidelity_test_ranker")


def test_ranker_fidelity():
    print("Starting Fidelity Test: SemanticContextRanker Relevance")

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
    # Recency bias might favor 6, 7, 3, 2.

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
