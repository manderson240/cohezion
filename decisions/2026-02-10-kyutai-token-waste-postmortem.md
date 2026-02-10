---
title: "Kyutai MCP Server: Token Waste Postmortem"
date: "2026-02-10"
status: "complete"
tags: [decision, lessons-learned, token-efficiency, anti-pattern]
severity: "critical"
---

# Kyutai MCP Server: Token Waste Postmortem

**Severity**: Critical (61,000 token waste, 0% output)

---

## Executive Summary

Kyutai MCP Server project consumed ~61,000 tokens with 0% functional output. Classic case of over-engineering before validation. This postmortem extracts the [[implementation-first-infrastructure-later]] pattern and establishes [[token-efficiency]] as a core principle of [[compound-engineering]].

## The Numbers

| Metric | Value | Problem |
|--------|-------|---------|
| Research lines | 1,192 | Over-documented before validation |
| Test lines | 4,416 | 95% are `pass` placeholders |
| Implementation | 0 | No actual product |
| Dependencies | 73MB | Installed for nothing |
| Functional tests | 1/22 passing | Rest fail (no fixtures) |
| Token cost | ~61,000 | 7.6x over efficient path |

## What Went Wrong

### 1. Test-Driven Development Backwards
- **TDD**: Write test → Implement → Test passes
- **What happened**: Write 600 placeholder tests → Stop

### 2. No Template Reuse
- **Available**: cloud-vault-mcp (working FastMCP server)
- **What happened**: Started from scratch with empty dirs

### 3. Documentation Before Validation
- **Research doc**: 1,192 lines (5 APIs, 4 deployment paths)
- **Should have been**: 50-line quick ref for ONE API

### 4. Dependencies Before Implementation
- **Installed**: 73MB node_modules (jest, typescript, 289 packages)
- **Used**: 0% (no implementation exists)

## Root Cause

**Violated [[compound-engineering|Compound Engineering]] Principle**: "Validate before scaling"

The project scaled to production-ready test infrastructure before proving the concept works. This is the inverse of the [[implementation-first-infrastructure-later]] pattern.

## Correct Approach

### Phase 1: Minimal Viable (2-3 hours, ~8,000 tokens)

See [[implementation-first-infrastructure-later]] for the full pattern.

```bash
# Copy working template
cp -r cloud-vault-mcp kyutai-mcp
cd kyutai-mcp

# Add ONE tool
# src/mcp_server/pocket_tts.py
async def speak_text(text: str) -> dict:
    model = TTSModel.load_model()
    audio = model.generate_audio(text)
    return {"audio_base64": base64.encode(audio)}

# Register tool in server.py
@mcp.tool()
def tts_speak(text: str) -> str:
    return await pocket_tts.speak_text(text)

# Write 5 REAL tests
# tests/test_pocket_tts.py (20 lines)
```

**Result**: Working TTS in 2-3 hours

### Phase 2: Only If Phase 1 Works
- Add transcription (if needed)
- Add 5 more tests
- Document what actually works

## Token Efficiency

| Approach | Tokens | Output |
|----------|--------|--------|
| **Current** | 61,000 | 0% |
| **Efficient** | 8,000 | 100% |
| **Savings** | 53,000 (87%) | ∞% improvement |

## Key Learnings

### ❌ Don't Do:
1. Write elaborate test infrastructure for code that doesn't exist
2. Document every possible API before using one
3. Install 73MB dependencies "just in case"
4. Ignore working templates

### ✅ Do This:
1. Copy working template (cloud-vault-mcp)
2. Implement simplest version first (ONE tool)
3. Write 5 tests AFTER it works
4. Only scale if validated

## Decision

**Archive current work**: `kyutai-mcp-server/` → `kyutai-mcp-server-archive/`
**Delete waste**: 73MB node_modules
**Document lessons**: This file
**Restart**: Use cloud-vault-mcp template if needed

## Patterns Extracted

**New Pattern**: [[implementation-first-infrastructure-later]]

**New Concept**: [[token-efficiency]]

```markdown
1. Copy working template
2. Implement ONE feature (100-200 lines)
3. Test it manually (does it work?)
4. Write 5 automated tests
5. Only then: scale if valuable
```

**Anti-Pattern**: "Infrastructure First, Hope Implementation Follows"

```markdown
1. Research every possible API (1,192 lines)
2. Write 600 placeholder tests (4,416 lines)
3. Install all dependencies (73MB)
4. Never implement anything
5. Result: 0% functional
```

## Cost Analysis

**Total waste**: ~61,000 tokens, 8+ hours, 73MB disk
**Could have built**: 5+ working MCP tools with real tests
**Lesson**: Token economy is real. Validate first, scale second.

---

**Status**: ✅ Lessons Documented & Integrated
**Patterns Extracted**: [[implementation-first-infrastructure-later]]
**Concepts Created**: [[token-efficiency]]
**Related Decisions**: [[2026-02-10-phase-a-implementation-complete]]
**Related Concepts**: [[compound-engineering]], [[context-management]]
