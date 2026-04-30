---
name: eigent-search-configuration
description: >
  How to configure web search in Eigent. Only Google Search is active —
  Tavily, DuckDuckGo, Brave, Exa are all commented out in the source.
  Covers required env vars, where to get API credentials, and the UI prompt meaning.
trigger: "eigent search | eigent web search | eigent google api | search_toolkit"
---

# Eigent Web Search Configuration

**Verified against:** Eigent v0.0.90, `app/agent/toolkit/search_toolkit.py`, 2026-04-29

## What Actually Works

Only **Google Search** is active. `get_can_use_tools()` has one live path:

```python
# ACTIVE — fires when either key is present
if env_not_empty("cloud_api_key") or env("GOOGLE_API_KEY"):
    tools.append(FunctionTool(search_toolkit.search_google))

# ALL COMMENTED OUT:
# if env("TAVILY_API_KEY"):   ← does nothing
# if env("BRAVE_API_KEY"):    ← does nothing
# if env("EXA_API_KEY"):      ← does nothing
# if env("LINKUP_API_KEY"):   ← does nothing
```

## Required Credentials

Add to `~/.eigent/.env`:

```bash
GOOGLE_API_KEY=your-google-api-key
SEARCH_ENGINE_ID=your-programmable-search-engine-id
```

**Critical:** The env var is `SEARCH_ENGINE_ID` — NOT `GOOGLE_SEARCH_ENGINE_ID`.

### How to Get Them

**Google API Key:**
1. [console.cloud.google.com](https://console.cloud.google.com) → Create project
2. APIs & Services → Enable **Custom Search API**
3. Credentials → Create API Key

**Search Engine ID:**
1. [programmablesearchengine.google.com](https://programmablesearchengine.google.com)
2. Create new search engine → enable "Search the entire web"
3. Copy the **Search engine ID** (not the API key — these are different)

## How It Works in Code

When `GOOGLE_API_KEY` is set, `search_google()` uses it directly via CAMEL's
`BaseSearchToolkit.search_google()`. Without it, falls back to
`cloud_search_google()` which requires Eigent's cloud `cloud_api_key`.

## What the Eigent UI "Needs Two Keys" Prompt Means

The Eigent Settings dialog asking for two keys is referring to exactly:
1. `GOOGLE_API_KEY`
2. `SEARCH_ENGINE_ID`

## Note on Tavily

Tavily (`TAVILY_API_KEY`) is **intentionally disabled** in Eigent's source —
the `tavily_search` method exists but is commented out in `get_can_use_tools()`.
Setting `TAVILY_API_KEY` in `.env` has zero effect on Eigent.
The key can still be useful for cohezion's own `SearchToolkit` which does use Tavily.
