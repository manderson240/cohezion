---
name: bmad-list-workflows
description: List all available BMAD workflows. Use to discover capabilities.
---

# List BMAD Workflows

Discover all available BMAD workflows across all modules.

## Usage

```bash
curl -X POST http://localhost:8361/tools/bmad_list_workflows \
  -H "Content-Type: application/json" \
  -d '{"module": "bmm"}'  # Optional: filter by module
```

## Available Modules

- **bmm** - Business Method Module (PRDs, stories, sprints)
- **gds** - Game Dev Studio (Game design, architecture)
- **cis** - Creative Intelligence Suite (Brainstorming, design thinking)
- **tea** - Test Architecture Enterprise (Testing, CI/CD)
- **bmb** - BMAD Builder (Create agents, workflows)
- **core** - Core utilities

## Output

Returns a list of workflow IDs and names that you can use with other BMAD commands.
