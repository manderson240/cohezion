---
title: "Fetching an X/Twitter post when WebFetch returns 402"
date: 2026-06-06
tags: [tooling, webfetch, twitter, x, research-loop, retro]
verified: true
---

# Retro — reading an X post the agent can't WebFetch

## Problem
A user shares `https://x.com/i/status/<id>` to "consider". `WebFetch` on x.com returns
**HTTP 402 Payment Required** (X gates the public read). The tweet text is unobtainable via the
normal path, and guessing its contents would be fabrication.

## Solution (verified 2026-06-06)
X's **public syndication endpoint** returns the tweet as JSON without auth:

```
https://cdn.syndication.twimg.com/tweet-result?id=<STATUS_ID>&token=<any-nonempty>
```

`WebFetch` on THAT URL returns the `text`, author (`user.screen_name`), media, and any quoted
tweet. Used successfully on status `2062930781945700861` (@googledevs "Gemma 4 QAT") — recovered
the full text + image alt, then the research-loop discipline took over (verify every HF id via
`model_info` before citing).

## Why it works
The syndication endpoint feeds embedded-tweet widgets, so it serves a lightweight unauthenticated
JSON for a single status id. The `token` param just needs to be present (any value).

## Caveats
- Single-tweet only — does not return a full thread (fetch each id separately).
- Deleted/protected/age-gated tweets return an error JSON — treat as "unobtainable", do NOT guess.
- This is the same lesson class as L367 / the read-only-mount merge: when one tool path is blocked,
  find the unauthenticated/alternate seam rather than fabricating.

## Related (already persisted)
- Wiring-sweep "script import is a static edge" methodology — `docs/audits/WIRING_SWEEP_LEDGER.md`
  (audio/ section): the orphan scan must cover `src/ tests/ scripts/`; a fast pre-scout is a
  candidate filter, not a verdict.
- "Consider [link]" filter: verify before adopting; decline products that conflict with local-$0
  (LangChain cloud microVMs, BigSet TS-SaaS); embrace verified on-philosophy levers (Gemma-4 QAT).
- Skill extraction (`/learn`) is blocked this session — `.claude/skills/` + `~/.claude/` are
  read-only mounts; durable learnings land in `docs/` instead.
