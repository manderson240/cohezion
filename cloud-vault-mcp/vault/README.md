# Cloud Vault — Knowledge Base for Compound Engineering

This is a structured Obsidian vault designed for **compound engineering** — where every AI-assisted work session deposits reusable context that future sessions build upon.

## Structure

| Directory | Purpose |
|-----------|---------|
| `projects/` | Per-project documentation and index notes |
| `decisions/` | Architecture Decision Records (ADRs) |
| `patterns/` | Reusable solutions extracted from project work |
| `experiments/` | Hypotheses tested, methods used, results and learnings |
| `papers/` | Literature notes from arXiv and other sources |
| `daily/` | Daily development logs |
| `concepts/` | Evergreen notes on technical concepts |
| `tools/` | Notes on tools, configurations, environments |
| `inbox/` | Quick capture, unsorted notes |

## How It Works

### Via MCP Server (AI Agents)

Claude Code and other AI tools connect to this vault through the MCP server. They can:

- **Read and write notes** directly
- **Search** across all vault content
- **Log decisions** after making architectural choices
- **Log experiments** when trying new approaches
- **Extract patterns** when discovering reusable solutions
- **Find relevant context** before starting new work

### Via Obsidian (Human)

Open this vault in Obsidian for:

- Visual graph exploration of connections between notes
- Manual editing and organization
- Tag-based navigation
- Daily note writing

### Git Sync

The vault is a Git repository. Changes from the MCP server are auto-committed periodically. Local Obsidian instances sync via standard `git pull`/`git push`.

## Templates

Each directory contains a `_template.md` file. When creating notes via the MCP server, use `vault_create_from_template` with these template names:

- `decisions` — Architecture Decision Record
- `experiments` — Experiment log
- `patterns` — Reusable pattern
- `papers` — Paper/literature note
- `daily` — Daily development log
- `projects` — Project index note

Template variables use `{{variable_name}}` syntax. The `{{date}}` variable is auto-filled.

## Conventions

- **Wikilinks**: Use `[[note-name]]` for linking between notes
- **Tags**: Use frontmatter `tags:` array and inline `#tag` syntax
- **Filenames**: Use kebab-case for note files (e.g., `reward-shaping-curriculum.md`)
- **Dates**: ISO 8601 format (`YYYY-MM-DD`) in frontmatter and filenames
