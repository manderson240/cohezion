import tiktoken


def estimate_tokens(text: str, model="gpt-4"):
    enc = tiktoken.encoding_for_model(model)
    return len(enc.encode(text))


# Scenario: Searching for a skill and reading its content
manual_prompt = """
I need to search for a skill related to 'FLUME' in the 'src/cohezion/skills' directory.
I will run 'ls src/cohezion/skills' and then 'grep -i "FLUME" src/cohezion/skills/*.md' to find it.
Wait, I see 'FLUME_ENCODING_PRIME.md'. Let me read it.
'cat src/cohezion/skills/FLUME_ENCODING_PRIME.md'
Now I have the content: "This skill defines the 12D state vector..."
"""

mcp_tool_call = """
call_tool("cohezion-skills", "search_skills_by_concept", {"concept": "FLUME"})
-> returns ["FLUME_ENCODING_PRIME"]
call_tool("cohezion-skills", "read_skill_content", {"skill_name": "FLUME_ENCODING_PRIME"})
-> returns "This skill defines the 12D state vector..."
"""

t1 = estimate_tokens(manual_prompt)
t2 = estimate_tokens(mcp_tool_call)

print(f"Manual Orchestration Baseline: ~{t1} tokens")
print(f"MCP Tool-Based Orchestration: ~{t2} tokens")
print(f"Token Reduction: {((t1 - t2) / t1) * 100:.1f}%")

# Scenario 2: Complex Graph Traversal in SurrealDB
manual_sql_code = """
import asyncio
from cohezion.core.persistence.surreal_client import SurrealClient
async def traverse():
    c = SurrealClient()
    await c.connect()
    # Find all nodes related to 'HIHO' through 'influences' edges
    res = await c.query("SELECT ->influences->universe_nodes.* FROM universe_nodes WHERE content CONTAINS 'HIHO'")
    print(res)
    await c.close()
asyncio.run(traverse())
"""

mcp_sql_call = """
call_tool("surrealmcp", "query", {"sql": "SELECT ->influences->universe_nodes.* FROM universe_nodes WHERE content CONTAINS 'HIHO'"})
"""

t3 = estimate_tokens(manual_sql_code)
t4 = estimate_tokens(mcp_sql_call)

print(f"\nManual DB Client Code: ~{t3} tokens")
print(f"MCP DB Tool Call: ~{t4} tokens")
print(f"Token Reduction: {((t3 - t4) / t3) * 100:.1f}%")
