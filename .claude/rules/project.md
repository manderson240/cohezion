# Project: Cohezion Vault

**Last Updated:** 2026-02-19

## Overview

Knowledge persistence system for the Cohezion agentic AI framework. Obsidian vault containing 84+ research papers, architectural decisions, patterns, and lessons learned across project phases. Includes custom 3D graph visualization plugin and MCP server for programmatic access.

## Technology Stack

### 3D Graph Plugin
- **Language:** TypeScript 4.7.4
- **Framework:** Obsidian Plugin API
- **3D Engine:** Three.js 0.150.0
- **Force Simulation:** D3-force 3.0.0
- **Build Tool:** esbuild 0.13.12
- **Testing:** Jest 30.2.0
- **Package Manager:** npm

### MCP Server
- **Language:** Python 3.10+
- **Framework:** FastMCP 0.1.0+
- **Web Server:** Uvicorn + Starlette
- **Data Validation:** Pydantic 2.0+
- **Testing:** pytest 7.0+
- **Formatting:** black (line-length 100)
- **Linting:** ruff + mypy

## Directory Structure

```
cohezion-vault/
├── prefrontal/          Architecture Decision Records (ADRs)
├── laboratory/        Hypothesis testing and validation
├── cerebellum/           Reusable solutions and code patterns
├── sensory/             Research papers (84+ papers)
├── motor/           Project-level tracking
├── hippocampus/              Daily notes and logs
├── thalamus/              Unsorted notes (triage point)
├── cortex/           Core concepts and definitions
├── obsidian-plugin/
│   └── 3d-graph-plugin/  TypeScript plugin for 3D visualization
└── mcp-server/         Python FastMCP server
```

## Key Files

**Configuration:**
- `obsidian-plugin/3d-graph-plugin/package.json` - Plugin dependencies
- `mcp-server/pyproject.toml` - MCP server configuration
- `CLAUDE.md` - Project instructions for Claude Code

**Documentation:**
- `README.md` - Vault overview and status
- `obsidian-plugin/3d-graph-plugin/README.md` - Plugin usage guide
- `mcp-server/README.md` - MCP server documentation

## Development Commands

### 3D Graph Plugin (TypeScript)

```bash
cd obsidian-plugin/3d-graph-plugin

# Install dependencies
npm install

# Development (watch mode)
npm run dev

# Build production
npm run build

# Run tests
npm test

# Lint code
npm run lint
```

**Output:** `main.js` (bundled plugin file)

### MCP Server (Python)

```bash
cd mcp-server

# Install dependencies
pip install -e ".[dev]"

# Run server
uvicorn kyutai_mcp.main:app --reload

# Run tests
pytest

# Format code
black .

# Lint code
ruff .

# Type check
mypy .
```

**Entry Point:** `kyutai_mcp.main:main`

## Architecture Notes

### 3D Graph Plugin
- **8 Semantic Dimensions:** Connectivity, conceptual depth, temporal distribution, cross-domain presence, completion maturity, recency, semantic similarity, domain clustering
- **Force-Directed Layout:** Physics simulation for natural paper clustering
- **Data Loading:** Automatically loads from `.claude/3d-graph-data.json`
- **Performance:** Adjustable quality settings, optimized for 84+ nodes

### MCP Server
- **Port:** 8360 (Cloud Vault MCP)
- **Tools:** VaultOps, CompoundOps, ObsidianOps, Teleport, SheetsBridge, SurrealDB
- **Integration:** Programmatic vault access via MCP protocol

### Vault Conventions
- **Frontmatter:** YAML with `title`, `date`, `status`, `tags` (arrays)
- **Links:** Obsidian wiki-links `[[note]]`
- **Templates:** `_template.md` in each directory
- **Notes:** Atomic, cross-linked where relevant
