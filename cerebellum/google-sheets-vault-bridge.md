---
title: "Google Sheets → Vault Bridge: Mobile Link Research Pipeline"
date: "2026-02-07"
tags: [pattern, integration, google-sheets, automation, haiku, cost-optimization]
aspect: thinker
neural:
  activation: 0.79
  stage: mature
  synapse_in: 20
  synapse_out: 13
---

## Problem

Research links captured on mobile via Google Sheets need to be researched, classified, and turned into structured vault notes. Processing 100 links with a full-capability model burns tokens fast (~100K+ per agent batch). Need a cost-effective pipeline that researches links, fills sheet metadata, generates vault notes, and tracks coverage.

## Solution

Four-stage pipeline using Haiku agents for research and batch Sheets API for updates.

### Stage 1 — Batch Research via Haiku Agents

Spawn parallel Haiku agents with `max_turns` caps to web-search each link and return structured JSON. Haiku is 1/3 the cost of Sonnet, 2x faster. `max_turns=5` prevents runaway token spend.

```
Task(
    subagent_type="general-purpose",
    model="haiku",
    max_turns=5,
    prompt="Research rows N-M. Return JSON: [{row, status, abstractions, domain, integration}]"
)
```

**Cost**: ~20K tokens per 10-row batch (vs ~100K+ with Opus/Sonnet).

### Stage 2 — Batch Sheet Update

One `values:batchUpdate` API call for all rows. Never update rows individually.

```python
# Always use the venv — never bare python3
/home/mike-anderson/dev/cohezion/cloud-vault-mcp/.venv/bin/python3

# Sheets API with ADC + quota project header
token = subprocess.check_output(
    ["gcloud", "auth", "application-default", "print-access-token"], text=True
).strip()

payload = {"valueInputOption": "RAW", "data": [
    {"range": "Sheet1!B{row}:E{row}", "values": [[status, abstractions, domain, integration]]}
    for row in results
]}
# POST to /values:batchUpdate with x-goog-user-project: cohezion-477604
```

### Stage 3 — Batch Vault Note Generation

Generate `papers/*.md` notes from sheet data. No additional web research needed — the abstractions already contain the key content.

Each note follows the template:
```markdown
---
title: "Short descriptive title"
date: 2026-02-07
tags: [domain-tag, topic-tag]
source: "original-url"
domain: "Domain Category"
---

# Short Title

## Summary
{abstractions from sheet}

## Key Findings
- {sentence 1 from abstractions}
- {sentence 2}

## Integration Point
{integration column from sheet}

## Relevance to Cohezion
{brief connection to Cohezion's domains}
```

### Stage 4 — Cleanup and Coverage Tracking

1. **Delete junk**: duplicates, generic site descriptions, broken links
2. **Rename to clean slugs**: `alphafold-cryo-em-structure-prediction` not `alphafold-cryo-em-protein-structure-prediction-for-automated-atomic-model-buildi`
3. **Add column F** ("Vault Note") to sheet — maps each row to its `papers/` filename via keyword matching
4. **Batch update** column F in one API call

## Sheet Schema

**Cohezion_Research** (ID: `1YcZObTni5L-VnA7O7TIl5ghoy-i3NfXuheFt_oFbmnk`)

| Column | Field | Source |
|--------|-------|--------|
| A | Link | Mobile capture |
| B | Status | Agent research (Researched / Inaccessible) |
| C | Key Abstractions | Agent research (1-2 sentence summary) |
| D | Domain | Agent research (e.g., Quantum Physics, AI Architecture) |
| E | Integration Point | Agent research (connection to Cohezion) |
| F | Vault Note | Cleanup script (papers/ filename) |

## Key Lessons

- **Haiku + max_turns is the cost lever**: 5x cheaper than Sonnet/Opus for web research tasks
- **Batch API calls always**: one `batchUpdate` for 100 rows vs 100 individual PUTs
- **Generate notes from sheet data, not fresh research**: the abstractions column already has the content
- **Teleport is cloud→local only**: don't use it for delegating local web research to cloud
- **Agents spawned with `bypassPermissions` still get blocked on Bash**: collect JSON results from agents and run sheet updates from the lead
- **Shortener URLs** (`search.app/`, `share.google/`) often can't be resolved — mark as Inaccessible rather than spinning

## When to Use

- Mobile capture → vault pipeline with 10+ links needing web research
- Any batch enrichment of a Google Sheet backed by vault notes
- Existing infra: `sheets_bridge.py`, ADC auth, `sheets_helper.py`

## When NOT to Use

- Single links — paste into `inbox/` and let the [[2026-02-07-event-driven-inbox-processor|inbox processor]] handle it
- Fewer than 5 links — manual is faster than pipeline overhead
- Links requiring deep analysis — use a full Sonnet/Opus agent with higher `max_turns`

## Related

- [[compound-engineering]] — this pipeline is compound engineering in action
- [[2026-02-07-event-driven-inbox-processor]] — single-note processing via watchdog
- [[2026-02-07-ai-research-agent-for-vault-notes]] — the original experiment that led to this pattern

## Decisions & Experiments
- 📋 [[2026-02-09-12d-graph-refined-plan]] - 12D Graph System - Refined Implementation Plan

## Related Concepts

- [[dna-origami-2d-semiconductor-patterning]]
- [[2026-02-14-phase-6a-automated-reasoning-chain-inference-complete]]
- [[2026-02-09-ai-model-strategy]]
- [[2026-02-09-fastmcp-asgi-integration-fix]]
- [[2026-02-14-graphrag-verification-and-integration-session]]
- [[entire-io-to-vault-mapping]]
- [[automated-concept-extraction]]
- [[sheetsbr idge-mcp-testing]]
