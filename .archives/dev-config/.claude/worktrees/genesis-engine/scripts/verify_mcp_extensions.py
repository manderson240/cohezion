import json

from cohezion.skills.cohezion_mcp import CohezionMCP


def verify_mcp_extensions():
    print("--- 1. Testing Residency Anchors ---")
    mcp = CohezionMCP()
    anchors = mcp.get_truth_anchors({})
    print(json.dumps(anchors, indent=2))

    print("\n--- 2. Testing Memory Persistence ---")
    fact = "The Cohezion system is always aware of its residency on the Strix Halo substrate."
    print(f"Remembering Fact: {fact}")
    remember_res = mcp.remember_fact({"fact": fact, "category": "residency"})
    print(json.dumps(remember_res, indent=2))

    print("\nQuerying Memory...")
    recall_res = mcp.recall_context({"query": "Where does the system reside?"})
    print(json.dumps(recall_res, indent=2))

    print("\n--- 3. Testing Daily Scout Trigger ---")
    scout_res = mcp.daily_scout_research({})
    print(json.dumps(scout_res, indent=2))


if __name__ == "__main__":
    verify_mcp_extensions()
