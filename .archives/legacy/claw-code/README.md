# Claw-Code Integration

This directory contains the Rust CLI implementation integrated from [ultraworkers/claw-code](https://github.com/ultraworkers/claw-code).

## Building

```bash
cd claw-code
cargo build --release
```

The binary will be at `target/release/claw`.

## Using with Ollama

A proxy is required to use Anthropic-format clients with Ollama. The proxy converts Anthropic API requests to Ollama's native format.

### Start the Proxy

```bash
./scripts/start-ollama-proxy.sh
```

This starts the proxy on port 8082 by default.

### Run Claw-Code

```bash
cd claw-code
ANTHROPIC_BASE_URL=http://localhost:8082 ANTHROPIC_API_KEY=unused ./target/release/claw --model haiku
```

### Model Mapping

| Claude Model | Ollama Model |
|-------------|---------------|
| haiku | phi3:mini |
| sonnet | gemma4:e4b |
| opus | gemma4:26b |

## Architecture

### Crates

- **api**: Anthropic API client with streaming support
- **claw-cli** (rusty-claude-cli): Main CLI binary
- **commands**: Slash commands implementation
- **compat-harness**: Compatibility layer
- **runtime**: Config loading, MCP client, permissions
- **tools**: Built-in tool implementations (bash, read, write, etc.)

### MCP Integration

Claw-code supports MCP (Model Context Protocol) servers. Configuration is loaded from `.claude/mcp.json` files.

### Key Files

- `claw-code/.claude.json`: MCP server configuration (configured for cohezion servers)
- `claw-code/.claude/settings.json`: Settings (simplified for claw compatibility)
- `scripts/ollama-proxy.py`: Anthropic-to-Ollama API translator

## Cohezion Integration

The MCP servers from cohezion are configured in `.claude.json`:
- cohezion-bmad: BMAD data access
- cohezion-skills: Skills management
- cohezion-research: Research tools
- cohezion-surreal: SurrealDB operations
- cohezion-swarm: Swarm coordination
- cohezion-knowledge: Knowledge graph