---
name: bmad-list-agents
description: List all available BMAD agents. Use to see who can help.
---

# List BMAD Agents

Discover all available BMAD agents across all modules.

## Usage

```bash
curl -X POST http://localhost:8361/tools/bmad_list_agents \
  -H "Content-Type: application/json" \
  -d '{"module": "bmm"}'  # Optional: filter by module
```

## Available Agents

### BMM (Business Method Module)
- **bmm-pm** - Product Manager
- **bmm-dev** - Developer
- **bmm-architect** - Software Architect
- **bmm-qa** - QA Engineer
- **bmm-sm** - Scrum Master

### GDS (Game Dev Studio)
- **gds-game-designer** - Game Designer
- **gds-game-dev** - Game Developer
- **gds-game-architect** - Game Architect

And many more...

## Using Agents

Agents can be activated via:
- `bmad_party_mode` for multi-agent collaboration
- Direct agent resource loading
- Claude Code prompts
