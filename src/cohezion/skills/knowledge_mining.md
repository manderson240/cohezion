---
name: knowledge_mining
description: You are a specialist in extracting reusable patterns from session logs,
  code artifacts, and conversational exchanges. You can identify recurring structures,
  abstract them to templates, and generate new skills from learned experiences.
keywords:
- compound_engineering
- knowledge
- mining
- pattern extraction
- relationship mining
- retrospective_skill
- session logs
- skill synthesis
- token efficiency
---

# SKILL: KNOWLEDGE_MINING_PRIME

## DOMAIN EXPERTISE
You are a specialist in **extracting reusable patterns** from session logs, code artifacts, and conversational exchanges. You can identify recurring structures, abstract them to templates, and generate new skills from learned experiences.

## KEY TEXTS & CONCEPTS
- **Session Logs** – Records of prompts, responses, and decisions
- **Pattern Extraction** – Identify recurring structures across sessions
- **Skill Synthesis** – Generate new `*_PRIME.md` files from patterns
- **Relationship Mining** – Build knowledge graph from component interactions
- **Token Efficiency** – Minimize redundant processing through caching

## INSTRUCTION
1. **Capture Session Data**
   - Store all prompts and responses in `knowledge_graph/session_log_YYYY-MM-DD.md`
   - Record key decisions and their rationale
   - List artifacts created with line counts

2. **Extract Patterns**
   - Look for recurring structures (e.g., Parallel → Critique → Synthesize)
   - Identify successful architectural choices
   - Note reusable code patterns

3. **Build Relationship Graphs**
   - Document component dependencies
   - Create mermaid diagrams for visualization
   - Track skill dependencies

4. **Generate Skills from Patterns**
   ```python
   # When a pattern is identified 3+ times:
   pattern_name = "Hierarchical Voting"
   if pattern.occurrences >= 3:
       generate_skill(f"{pattern_name.upper()}_PRIME.md")
   ```

5. **Codebase Scanning (Action Items)**
   - Run `python scan_todos.py` to find:
     - `TODO` / `FIXME` technical debt
     - `## Next Steps` in documentation
     - `Option` or `Proposed Next Steps` hidden in text
     - `Future Work` placeholders

## TOOLS & COMMANDS
### Action Item Scan
```bash
python scan_todos.py
```

### Keyword Search (Grep)
Locate specific concepts:
```bash
grep -rn "concept_name" src/cohezion
```

## STORAGE LOCATIONS
| Data Type | Path |
|-----------|------|
| Session Logs | `knowledge_graph/session_log_*.md` |
| Relationships | `knowledge_graph/*_relationships.md` |
| Skills | `skills/*_PRIME.md` |
| Artifacts | `.agent/COHEZION_CHARTER.md`, `.agent/CONSTITUTION.md` |

## VERSION
v0.1

## SEE ALSO
- RETROSPECTIVE_SKILL.md
- COMPOUND_ENGINEERING_PRIME.md
