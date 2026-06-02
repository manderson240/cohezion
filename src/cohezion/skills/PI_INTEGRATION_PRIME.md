---
name: pi-integration
description: "Integrate pi coding harness with Cohezion compound loop. Non-destructive code assistance using 12D journey tracking, pattern emergence, and skill genome refinement. Use when pi needs to query concept space, track trajectories, or leverage learned patterns from prior work."
metadata:
  version: "0.1"
---

# SKILL: PI_INTEGRATION_PRIME

## DOMAIN EXPERTISE

You are a bridge between the **pi coding agent** and **Cohezion compound infrastructure**.
Pi provides read/edit/write/bash tools. Cohezion provides journey tracking, pattern
emergence, and non-destructive skill refinement. Together they create autonomous,
learning-backed development.

## COHEZION CONCEPTS

### Pattern Space (195 skills)
All work happens against a backdrop of 195 PRIME skill genomes. Each skill is:
- **Content-addressed**: Named by semantic content, not file path
- **Evolving**: Versioned, refined from execution
- **Queryable**: Via `/cohezion skill <name>` or `@` autocomplete

### Journey Tracking (12D FLUME)
Every session is a trajectory through 12-dimensional axiomatic space:
- **Dimensions**: Novelty, Logic, Field, Energy, Time, Space, Emergence, Agency, Complexity, Adaptability, Fractal, Resonance
- **Points**: Each tool call becomes a `TrajectoryPoint`
- **Coherence**: Score 0.0-1.0 of alignment with intent

### Non-Destructive Operations
- **Relocation**: Deleted code moves to `.pi/archive/`
- **Append-only**: Skills gain refined patterns, never lose prior
- **Reversible**: Every state reachable via journey replay

## INSTRUCTION

### 1. Query Concept Space

When user asks anything, first query existing knowledge:

```bash
# List all available skills
pi /cohezion skills

# Find relevant patterns
pi /cohezion patterns "session management"

# Query vault for similar work
pi /cohezion vault "async retry handling"

# Materialize specific skill
pi /cohezion skill SESSION_MANAGER_PRIME
```

### 2. Check Alignment Gate

Before major edits, verify HIHO coherence:

```python
from cohezion.compound.request_alignment_analyzer import RequestAlignmentAnalyzer

analyzer = RequestAlignmentAnalyzer()
result = analyzer.analyze(
    request="Refactor compound session to use async",
    available_skills=["SESSION_MANAGER_PRIME", "ASYNC_PATTERNS_PRIME"],
    agent_context={"current_phase": "refactoring"}
)

if result.coherence < 0.5:
    print(f"Low alignment: {result.issues}")
    # Suggest decomposition or alternative approach
```

### 3. Non-Destructive Edit Pattern

```typescript
// In pi, before overwriting:
async function editFile(path: string, newContent: string) {
    // 1. Archive current state
    await pi.tools.bash(`cp ${path} .pi/archive/${path}.${Date.now()}`);

    // 2. Record trajectory point
    await journeyTracker.recordStep({
        operation: "edit",
        from_hash: await contentHash(oldContent),
        to_hash: await contentHash(newContent),
        coherence: alignmentResult.coherence
    });

    // 3. Apply edit
    await pi.tools.write(path, newContent);
}
```

### 4. Extract and Refine Patterns

After successful execution:

```python
from cohezion.compound.skill_refiner import SkillRefiner

refiner = SkillRefiner(mcp_client)
refiner.refine(
    skill_name="SESSION_MANAGER_PRIME",
    operation_type="transform",
    execution_result={
        "success": True,
        "duration_seconds": 4.2,
        "quality_score": 0.87
    },
    patterns_extracted=["async-warmup-pattern", "checkpoint-persistence"]
)
# Appends to skill file with version bump
```

### 5. Learn from Void

Anti-patterns are first-class:

```python
from cohezion.core.persistence.repositories.pattern_repository import PatternRepository

# When detecting problematic code
repo.store_anti_pattern({
    name="singleton-test-isolation",
    category="test-anti-pattern",
    code_example="with patch('module.attr'):",
    remediation="Patch at source: @patch('source.module.attr')",
    severity="high"
})
```

## PATTERNS

### Skill-First Development
1. Query `/cohezion skills` for relevant domain
2. Materialize highest confidence skill
3. Follow skill instructions
4. Record deviation if skill incomplete
5. Submit refinement back to skill genome

### Session as Trajectory
```
Session Start
    ↓ [alignment check: coherence 0.87]
Tool Execution (read → understand)
    ↓ [trajectory point: novelty + logic ↑]
Tool Execution (edit → transform)
    ↓ [trajectory point: field + time ↓]
Verification (bash → test)
    ↓ [trajectory point: resonance ↑]
Session End
    ↓ [coherence: 0.92, fitness: +0.05]
    └──→ Skill refinement triggered
```

### Archive-All Writing
Never overwrite without archival:
```bash
# pi extension enforces:
pre-write:
  - Calculate content hash
  - Copy to .pi/archive/hash.timestamp
  - Record archive event in trajectory
  - Then write new content
```

## INTEGRATION WITH PI

### Available Commands
- `/cohezion skills` - List 195 indexed skills
- `/cohezion patterns [query]` - Query pattern repository
- `/cohezion vault <query>` - Semantic vault search
- `/cohezion journey` - Show current session trajectory
- `/cohezion skill <name>` - Materialize specific skill

### Autocomplete
Type `@` in pi editor to fuzzy-search skills:
```
User types: @session
Suggestions:
  - SESSION_MANAGER_PRIME
  - SESSION_LIFECYCLE_PRIME
  - SESSION_CHECKPOINTING_PRIME
```

### Events
Pi extension listens for:
- `tool:before` - Alignment check, journey step start
- `tool:edit:success` - Pattern extraction, skill refinement
- `tool:write:before` - Archive existing content
- `startup` - Index skills, load patterns

## CITATIONS

- PI_INTEGRATION_PRIME (this skill)
- SELF_HEALING_PRIME (drift detection)
- SESSION_MANAGER_PRIME (warm-start/clean-shutdown)
- PATTERN_EMERGENCE_PRIME (mining from execution)
- HIHO_ALIGNMENT_PRIME (coherence gating)

## VERSION

v0.1 - Initial bridge between pi and Cohezion

## SEE ALSO

- `src/cohezion/compound/session_manager.py` - Session lifecycle
- `src/cohezion/compound/journey_tracker.py` - 12D trajectories
- `src/cohezion/compound/skill_refiner.py` - Skill genome refinement
- `src/cohezion/core/persistence/repositories/pattern_repository.py` - Pattern storage
- `.pi/extensions/cohezion-bridge.ts` - Pi integration extension

## CONFIGURATION

```typescript
// ~/.pi/settings.json
{
  "extensions": [".pi/extensions/cohezion-bridge.ts"],
  "cohezion": {
    "skillsDir": "src/cohezion/skills",
    "vaultEnabled": true,
    "patternBufferPath": ".pattern_buffer.json"
  }
}
```

## EMERGENCE

This skill is meta: it teaches pi how to use Cohezion, which
learns from every pi session, which refines this skill, which
teaches pi better...闭环. Closed loop. The system teaches itself
to teach itself.
