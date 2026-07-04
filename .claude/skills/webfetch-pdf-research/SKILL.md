---
name: webfetch-pdf-research
description: |
  Read and analyze PDFs from the web when WebFetch returns binary/error instead of text.
  Use when: (1) WebFetch on a .pdf URL says "binary content (application/pdf)" or fails to
  extract text, (2) user asks to research a PDF paper, (3) WebFetch saves a .pdf file
  to a local tool-results path. Key insight: WebFetch saves the PDF locally even when it
  can't parse the text — the Read tool can open that local .pdf path with pages= parameter
  and renders it visually. Then pass the visual content to Lemonade for analysis.
author: Claude Code
version: 1.0.0
source: session 2026-07-03 (Frank Nielsen entropy paper)
---

# WebFetch PDF Research Pattern

## Problem

`WebFetch(url="https://example.com/paper.pdf")` returns:
```
"Binary content (application/pdf, 2.4MB) also saved to /home/.../tool-results/webfetch-<id>.pdf"
```

The tool couldn't extract text from the PDF. But the file IS saved locally.

## Key Insight

The Read tool supports PDFs via the `pages` parameter and renders them **visually** (images).
The binary saved by WebFetch is a valid PDF — use Read on that local path.

## Solution

**Step 1:** Call WebFetch — even if it fails, note the `tool-results/webfetch-*.pdf` path in the output.

**Step 2:** Read the PDF using that local path with `pages="1-5"`:
```
Read(file_path="/home/.../tool-results/webfetch-<id>.pdf", pages="1-5")
```
This renders pages as images (multimodal). You see the typeset content including figures, formulas, and tables — exactly as a human would.

**Step 3:** Extract key information manually from the visual rendering (title, abstract, theorems, results).

**Step 4:** Feed a structured summary to Lemonade for analysis:
```
mcp__lemonade__lemonade_chat(
  model="llama3.2-1b-FLM",
  messages=[{"role": "user", "content": "Analyze these key points from [paper]:\n\n[your extracted summary]...\n\nWrite bullet points identifying Cohezion connection points."}],
  max_tokens=600
)
```

**Step 5:** Write vault entry with manual domain corrections on top of Lemonade output.

## Verification

Read tool returns visible PDF page images (not an error). The pages parameter is required for
PDFs over 10 pages — use `pages="1-5"` for the first read, then fetch later pages if needed.

## Limits

- `pages` max is 20 per Read call
- Read tool renders pages as visual screenshots — you see the typeset page
- Use multiple Read calls with different page ranges for long papers (e.g., "1-5", "6-10")
- Lemonade 1B model (llama3.2-1b-FLM) is adequate for tagging/connections on pre-extracted summaries but gets domain physics wrong — apply manual corrections for precision claims

## Example

```
# User says: "background lemonade research task https://example.com/paper.pdf"

# 1. Fetch (will fail for text but saves locally)
WebFetch(url="https://example.com/paper.pdf",
         prompt="Extract title, abstract, key results")
# Output: "Binary content... saved to /path/webfetch-abc123.pdf"

# 2. Read visually
Read(file_path="/path/webfetch-abc123.pdf", pages="1-5")
# → Renders 5 pages as images; you see typeset content

# 3. Analyze with Lemonade
mcp__lemonade__lemonade_chat(
  model="llama3.2-1b-FLM",
  messages=[{"role": "user", "content": "Analyze: [your extracted content]\n\nWrite 4-5 bullet points on Cohezion connection points."}],
  max_tokens=600
)

# 4. Write vault digest with domain corrections
mcp__claude_ai_Cohezion_Obsidian_Vault__vault_write(
  path="research/digests/YYYY-MM-DD-paper-slug.md",
  content="---\nname: ...\n---\n# Title\n[full analysis]"
)
```

## Workflow Integration

This pattern composes with `research-vault-surrealdb-pipeline`:
1. Use this skill to GET the PDF content (Steps 1-4 above)
2. Use `research-vault-surrealdb-pipeline` for the vault write + SurrealDB ingestion

## Path Convention

WebFetch tool-results paths follow this pattern:
```
/home/mike-anderson/.claude/projects/-home-mike-anderson-dev-cohezion/<session-id>/tool-results/webfetch-<timestamp>-<random>.pdf
```
The full path is printed in the WebFetch output — copy it verbatim.
