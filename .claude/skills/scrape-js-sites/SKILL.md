---
name: scrape-js-sites
description: |
  Scrape JavaScript-rendered websites using Playwright MCP when WebFetch fails.
  Use when: (1) user says "mine this site" or "scrape this website", (2) WebFetch
  returns only CSS classes, nav menus, or framework boilerplate instead of article
  content, (3) site uses React/Vue/Angular/Next.js (JS-rendered), (4) WebFetch
  returns < 500 words of meaningful content for a content-heavy page.
  Key insight: WebFetch fetches raw HTML before JS executes. Playwright MCP
  renders the page fully before extracting content.
author: Claude Code
version: 1.0.0
---

# Scrape JS-Rendered Sites with Playwright MCP

## Problem

`WebFetch` fetches raw HTML before JavaScript executes. Modern content sites
(Substack, Ghost, React/Next.js apps) render their content client-side, so
WebFetch returns only CSS framework code, navigation shells, or empty `<div>`
containers instead of the actual articles.

**Diagnostic signs WebFetch failed silently:**
- Output is mostly CSS class names (e.g. `bg-white text-gray-900 font-sans`)
- Output shows navigation/header but no article body
- Output is under 500 words for a page that clearly has content
- Output contains `<div id="__next">` or `<div id="root">` with no children

## Solution: Playwright MCP Browser Tools

Use the Playwright MCP tools that are available as `mcp__plugin_playwright_playwright__*`.

### Step 1: Navigate to the page

```
mcp__plugin_playwright_playwright__browser_navigate(url="https://example.com/article")
```

### Step 2: Take a snapshot to see interactive elements

```
mcp__plugin_playwright_playwright__browser_snapshot()
```

Returns an accessibility tree with element refs (e1, e2, ...) and text content.
This is your primary content extraction tool — it returns rendered text.

### Step 3: Extract content

The snapshot output contains the rendered text. Read it directly from the
snapshot result. For long articles, the full text is in the snapshot.

### Step 4: For multi-page mining (index → articles)

```python
# 1. Navigate to index/listing page
browser_navigate(url="https://site.com/stories")
# 2. Snapshot to see article links
browser_snapshot()
# 3. Note article URLs from snapshot output
# 4. Navigate to each article
browser_navigate(url="https://site.com/stories/article-1")
# 5. Snapshot to get full article text
browser_snapshot()
```

### Step 5: Click for pagination or "load more"

```
mcp__plugin_playwright_playwright__browser_click(element="Load more", ref="e42")
```

Then snapshot again to get the newly loaded content.

## Workflow for "Mine This Site" Tasks

1. **Start at the index/listing page** — find `/stories`, `/articles`, `/blog`, or `/posts`
2. **Snapshot the index** to extract article titles, URLs, and dates
3. **Prioritize articles** by relevance to the vault topic (EVOs, New Science, etc.)
4. **Navigate + snapshot each article** to extract full text
5. **Create vault notes** from extracted content using the `note` skill pattern
6. **Add bidirectional links** to existing related notes

## Vault Note Creation Pattern

After extracting content, create a note in the appropriate directory:
- **Research articles** → `sensory/` (research papers, external observations)
- **Concept explanations** → `cortex/` (if synthesizing into a concept note)
- **Raw intake for later processing** → `thalamus/` (inbox)

Use proper frontmatter (see vault-conventions.md):
```yaml
---
title: "Article Title"
date: 2026-03-11
tags: [research, evo, propulsion]
aspect: knower
source: "https://site.com/article-url"
author: "Author Name"
---
```

## Example: altpropulsion.com

```
# Failed approach:
WebFetch("https://www.altpropulsion.com/")
→ Returns CSS: "bg-white text-gray-900 font-sans..." (JS-rendered site)

# Working approach:
browser_navigate(url="https://www.altpropulsion.com/stories/")
browser_snapshot()
→ Returns full article listing with titles, dates, URLs

browser_navigate(url="https://www.altpropulsion.com/stories/practical-applications-of-evos")
browser_snapshot()
→ Returns full 3000-word article text
```

## Permission Note

The `mcp__plugin_playwright_playwright__browser_navigate` permission must be in
`.claude/settings.local.json`. Other Playwright tools are prompted per-use.
If you get a permission error on `browser_navigate`, add it to the allow list.

## Related Skills

- `note` — Create well-structured vault notes from extracted content
- `research-concept-note` — Create deeply-researched concept notes
- `daily-research` — Systematic daily research pipeline
