# Standalone zero-import test
class SemanticContextRankerStandalone:
    def rank_messages(self, messages, query):
        ranked = []
        keywords = set(query.lower().split())
        for idx, msg in enumerate(messages):
            content = msg.get("content", "").lower()
            score = 0.0
            if any(kw in content for kw in keywords):
                score += 1.0
            if messages:
                score += (idx / len(messages)) * 0.5
            ranked.append({"index": idx, "message": msg, "score": score})
        return sorted(ranked, key=lambda x: x["score"], reverse=True)


def test_ranker_fidelity():
    print("Starting Zero-Import Fidelity Test")
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
    ranker = SemanticContextRankerStandalone()
    ranked = ranker.rank_messages(messages, query="database")
    top_3_indices = [r["index"] for r in ranked[:3]]
    print("Top 3 indices:", top_3_indices)
    relevant_count = 0
    for idx in top_3_indices:
        content = messages[idx]["content"].lower()
        if "database" in content or "user profiles" in content or "postgres" in content:
            print(f"Relevant: {content[:30]}...")
            relevant_count += 1
    if relevant_count >= 2:
        print("RESULT: SUCCESS")
    else:
        print("RESULT: FAILURE")


if __name__ == "__main__":
    test_ranker_fidelity()
