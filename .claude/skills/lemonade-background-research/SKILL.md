---
name: lemonade-background-research
description: |
  Spawn a background Agent() to research a URL or paper description using local Lemonade
  inference. Each agent fetches content, reasons with local model, writes a vault digest,
  and returns structured bullet findings. Use when the user asks for a background research
  task or when batching multiple URLs in parallel at $0 cost.
  Key timing: Gemma-4-E4B-it-GGUF ~38s / 500 tokens (reliable default).
  deepseek-r1-0528-8b-FLM: requires explicit pre-warm; hits 60s MCP cap at ~800+ tokens.
  Always note timeout status in digest frontmatter.
author: Claude Code
version: 1.1.0
---

# Lemonade Background Research Agent

## Problem

User asks to research a URL or paper (often several at once) using local inference. The work
should happen in the background — spawned as an Agent() — while the main session continues.
Each agent must: fetch content, reason locally, write a durable vault digest, return bullets.

## Trigger

- User says: `"background lemonade research task <url>"` or `"lemonade research <description>"`
- Batching multiple URLs: spawn one Agent per URL in a single message (parallel execution)

## Lemonade Model Reality (empirical 2026-07-03/04, 20-article batch)

| Model | Speed | Max reliable tokens | Notes |
|---|---|---|---|
| `Gemma-4-E4B-it-GGUF` | ~38s / 500 tok | ~500 | **Default.** Reliable at ≤500 tok; also times out at longer prompts. |
| `llama3.2-1b-FLM` | 91 tok/s prefill | ~400 | Fast path, good for summaries. |
| `deepseek-r1-0528-8b-FLM` | 10.65 TPS | ~200 | Needs pre-warm; times out at 800+ tok. |

**Rule**: Use `Gemma-4-E4B-it-GGUF` by default. Keep prompts under 500 output tokens.
If Lemonade times out, agents should fall back to training knowledge and flag `lemonade_timeout: true`.
Agents with training-knowledge fallback are still useful — the digest should note the confidence level.

**Timeout behavior**: MCP `lemonade_chat` has a 60-second hard cap. Both deepseek-r1 (at 800+ tok)
and Gemma-4-E4B at longer prompts hit this. When timeout occurs, note `lemonade_timeout: true` in
the vault digest frontmatter. The HTTP 500 error indicates OmniRouter cold start — retry or use
training knowledge fallback.

## Agent Prompt Template

```python
Agent(
    description="Research <brief topic>",
    prompt="""
Fetch and research this URL: <url>

Steps:
1. Fetch the content:
   - For web articles: use WebFetch(url="<url>")
   - For GitHub repos: use Bash to run gh api repos/<owner>/<repo> plus readme fetch
   - For arXiv papers: use WebFetch(url="https://arxiv.org/abs/<id>") or fetch PDF

2. Extract the key content (trim to ~2000 words max, discard nav/ads/footers)

3. Analyze with Lemonade using mcp__lemonade__lemonade_chat:
   - model: "Gemma-4-E4B-it-GGUF"
   - max_tokens: 500
   - temperature: 0.1
   - prompt: "Context: [paste trimmed content]. For Cohezion (compound AI orchestration,
     local AMD silicon inference, SurrealDB, skill refinement loop): 1. What is this?
     2. Relevance to Cohezion? 3. Integration opportunity or action? Be concise."

4. Write vault digest using mcp__claude_ai_Cohezion_Obsidian_Vault__vault_write:
   path: "research/digests/<YYYY-MM-DD>-<slug>.md"
   content: see Digest Frontmatter Schema below

5. Return structured bullet findings (see Return Format below)
""",
    run_in_background=True,
)
```

## Digest Frontmatter Schema

```markdown
---
url: <original url>
date: <YYYY-MM-DD>
model: <model used, e.g. Gemma-4-E4B-it-GGUF>
lemonade_timeout: false          # set true if MCP hit 60s cap
tokens_used: <approximate>
verdict: ADOPT | ADAPT | MONITOR | SKIP
---

# <Title or Paper Name>

## Summary
<2-3 sentences>

## Cohezion Relevance
<1-3 bullets>

## Action
<ADOPT: integration path | ADAPT: what to change | MONITOR: what to watch | SKIP: why>
```

## Return Format (bullets for main session)

The background agent should return its findings in this format so the coordinator can
synthesize them:

```
**<Title/URL slug>** — <verdict>
- What: <one line>
- Cohezion: <one line on relevance>
- Action: <specific integration path or "no action">
- Lemonade: <model used>, <time>s / <tokens> tok [TIMEOUT if applicable]
```

## Parallel Batch Pattern

To research multiple URLs simultaneously, spawn all agents in a single message:

```python
# Single message, multiple Agent() calls — they run in parallel
Agent(description="Research URL 1", prompt="...", run_in_background=True)
Agent(description="Research URL 2", prompt="...", run_in_background=True)
Agent(description="Research URL 3", prompt="...", run_in_background=True)
```

**Pre-warm if using deepseek-r1** (do this ONCE before spawning):
```bash
curl -s -X POST http://localhost:13305/api/v1/load \
  -H "Content-Type: application/json" \
  -d '{"model_name": "deepseek-r1-0528-8b-FLM"}'
```

**Synthesis**: after agents complete, a fork agent (subagent_type="fork") synthesizes all
findings — it has full context and can call advisor() before writing the final summary.

## Corpus Variant (index page + multi-document fetch)

When the user says `"background lemonade learning corpus <url>"` or the URL is a directory/index
(e.g. course scribe notes, paper collections, GitHub repo with many files), use this deeper pattern:

```
1. Fetch the index page to get the full document list
2. Identify 3-5 most relevant documents (by title relevance to session goal)
3. Fetch each individually with WebFetch
4. In the Lemonade prompt: synthesize ACROSS all documents, not just one
5. Digest structure: add a "Lecture/Document Index" section listing all items found
6. Flag which individual documents were actually read vs index-only
```

Example corpus prompt structure:
```
"I have read the following documents from [source]: [list]. Synthesize the top theoretical
results across all of them. Focus on: [session-relevant dimensions]. For each result,
note which document it came from."
```

Key insight: course scribe notes, reading lists, and paper collections can yield calibration
insights that no single paper would surface (e.g. MIT 6.897 → `_MIN_SAMPLES=2` is the
theoretical floor from competitive analysis; raise to 5).

## Verification

- Each agent returns non-empty bullet findings
- Vault digest exists at `research/digests/<date>-<slug>.md`
- `lemonade_timeout` in frontmatter correctly reflects whether MCP timed out

## Common Failure Modes

| Symptom | Fix |
|---|---|
| deepseek-r1 times out (60s MCP cap) | Switch to Gemma-4-E4B-it-GGUF or pre-warm first |
| Agent returns empty | Lemonade model not loaded; check `mcp__lemonade__lemonade_list_models()` |
| Content too long for Lemonade | Trim to ~2000 words; focus on abstract/intro/conclusions |
| Vault write fails | Use vault_write not vault_log_decision for digests; check path format |

## References

- `lemonade-url-research-task` skill (vault v1.4.0) — full model selection guide, GitHub/Playwright patterns
- `research-paper-integration` skill — arXiv papers with falsifiability checks
- `vault_write` MCP tool — writes to research/digests/ path in vault
