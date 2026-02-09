# Cohezion Vault

Knowledge base for the Cohezion agentic AI framework, managed as an Obsidian vault.

## Structure

| Directory | Purpose | Template |
|-----------|---------|----------|
| `inbox/` | New unsorted notes — triage point for raw ideas | None |
| `decisions/` | Architecture Decision Records (ADRs) | `status: proposed` with Context/Decision/Consequences/Alternatives |
| `experiments/` | Hypothesis testing and results | `status: in-progress` with Hypothesis/Method/Results/Learnings |
| `patterns/` | Reusable solutions and code patterns | Problem/Solution/Code Example/When to Use |
| `papers/` | Research papers and references | — |
| `daily/` | Daily notes and logs | Tasks/Notes/Learnings |
| `projects/` | Project-level tracking | `status: active` with Overview/Goals/Current Status/Key Decisions |
| `concepts/` | Core concepts and definitions | — |
| `attachments/` | Binary files and images | — |

## Conventions

- Notes use YAML frontmatter with `title`, `date`, `status`, and `tags` fields
- Tags are arrays in frontmatter (e.g., `tags: [decision, architecture]`)
- Templates in each directory use `_template.md` naming
- Obsidian wiki-links (`[[note]]`) are used for cross-referencing

## MCP Integration

- **Cloud Vault MCP Server** on port 8360 — programmatic vault access
- **Claude Code MCP Plugin** on port 22360 — IDE integration

## Working with This Vault

- When fleshing out inbox notes, research the topic thoroughly and write structured content in-place
- Respect existing frontmatter schemas when creating notes in templated directories
- Keep notes atomic and cross-linked where relevant
- When moving notes from `inbox/` to a permanent directory, add appropriate frontmatter
