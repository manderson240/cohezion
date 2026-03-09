# Unified Context System for Cohezion

## Overview
Hierarchical, traceable context architecture optimizing for token efficiency and compound engineering.

## Structure

```
.context/
├── core/                          # Universal rules (token-lite)
│   ├── syntax-rules.md           # ~200 tokens - Python standards
│   ├── testing-rules.md          # ~250 tokens - Test patterns
│   └── compound-patterns.md        # ~300 tokens - Compound engineering
├── session/                       # Ephemeral context
│   └── current-session.md        # Active state, coherence tracking
├── skills/                        # Skill-specific overlays
│   └── compound-engineering/
│       └── context.yaml          # ~150 tokens when loaded
└── traceability/
    └── manifest.json             # Source mapping, token budgets
```

## Token Budget
- **Core**: 750 tokens (always loaded)
- **Skill Overlays**: 150 tokens each (on-demand)
- **Total Budget**: 1000 tokens
- **Efficiency Gain**: ~60% reduction vs AGENTS.md

## Traceability
Every rule traces to:
- Source document (e.g., AGENTS.md)
- Specific section
- Git commit hash
- Creation timestamp

## Loading Rules
1. Core context always loads first
2. Skill overlays loaded only when skill invoked
3. Coherence checked before each load
4. Session state tracks active context

## Quick Start
```bash
# Context is auto-loaded via .context/ manifest
# To load skill-specific context:
load_context skill compound-engineering
```

## FUTURE HOOKS
1. **Dynamic loading**: Auto-load skill context based on task detection
2. **Coherence monitoring**: Track context effectiveness per session
3. **Evolution tracking**: Retrospect on rule changes over time
