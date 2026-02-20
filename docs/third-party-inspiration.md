# Third-Party Inspiration & Attribution

This document lists external projects that inspired COHEZION's architecture and design patterns.

---

## Claude Pilot

**Project**: [Claude Pilot](https://github.com/maxritter/claude-pilot)
**Author**: Max Ritter
**License**: Proprietary source-available
**Inspiration Date**: February 2026

### What We Learned

Claude Pilot demonstrated sophisticated patterns for AI-assisted development:

1. **Hooks Pipeline Architecture**: Lifecycle events with quality enforcement hooks
2. **Context Preservation**: Seamless session continuation across context clears
3. **Intelligence Routing**: Strategic model deployment (Opus for planning, Sonnet for execution)
4. **Worktree Isolation**: Safe experimentation without repository corruption
5. **Quality Enforcement**: Real-time linting, formatting, and type-checking

### Our Implementation

We implemented **our own versions from scratch** using COHEZION-native primitives:

- **Hooks Pipeline**: `src/cohezion/hooks/` with JourneyTracker integration
- **Session Persistence**: Enhanced `SessionPersistence` with vault-backed state
- **Intelligence Routing**: Extended `CostAwareRouter` with task classification
- **Worktree Management**: Existing `WorktreeOrchestrator` with added features

### License Compliance

Pilot's license prohibits redistribution, derivative works, and competitive use. We respect these terms by:

- ✅ **Not copying code** - all implementations written from scratch
- ✅ **Not creating derivative work** - independent architecture using COHEZION patterns
- ✅ **Clear attribution** - documenting Pilot as inspiration source
- ✅ **Independent innovation** - adding COHEZION-specific enhancements (12D trajectories, HIHO stability, FLUME integration)

See `docs/pilot-inspiration.md` for detailed pattern analysis.

---

## Adding New Attributions

When learning from external projects:

1. **Document the inspiration** in this file
2. **Note the license** and our compliance approach
3. **Implement from scratch** - never copy code
4. **Add value** - enhance with COHEZION-specific innovations
5. **Give credit** - clear attribution in code comments and docs

---

**Last Updated**: 2026-02-20
