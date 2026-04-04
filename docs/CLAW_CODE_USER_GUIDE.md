# Claw-Code User Guide

## Quick Start

### 1. Build Claw-Code

```bash
cd claw-code
cargo build --release
```

The binary is at `target/release/claw`.

### 2. Start the Ollama Proxy

```bash
./scripts/start-ollama-proxy.sh
```

This starts the proxy on port 8082 by default.

### 3. Run Claw-Code

```bash
cd claw-code
ANTHROPIC_BASE_URL=http://localhost:8082 ANTHROPIC_API_KEY=unused \
  ./target/release/claw --model haiku
```

## Model Mapping

| Claude Model | Ollama Model | Size | Description |
|--------------|--------------|------|-------------|
| `haiku` | `phi3:mini` | 2.2GB | Fast, lightweight |
| `sonnet` | `gemma4:e4b` | 9.6GB | Balanced |
| `opus` | `gemma4:26b` | 17GB | Most capable |

## System Configuration

### AMD GPU Optimization

This system uses AMD ROCm with GTT (Graphics Translation Table) for memory:
- **Total GTT**: 137GB (shared system memory)
- **VRAM**: 512MB (GPU local memory)
- **Architecture**: gfx1151 (Radeon Pro)

### Ollama Settings for Large Models

Create/edit `~/.ollama/ollama.env`:

```bash
# For systems with 128GB+ RAM
OLLAMA_MAX_LOADED_MODELS=2
OLLAMA_NUM_PARALLEL=1
OLLAMA_MAX_QUEUE=10

# Keep models loaded longer
OLLAMA_KEEP_ALIVE=30m

# Flash attention for faster inference
OLLAMA_FLASH_ATTENTION=1
```

### Memory Management

```bash
# Check available memory before running large models
free -h

# Stop all running models to free memory
ollama stop $(ollama ps --format json | jq -r '.[].name')

# Run with specific context size
OLLAMA_CONTEXT_WINDOW=8192 ollama run gemma4:26b
```

## Available Commands

### Interactive REPL

```bash
# Start interactive session
./target/release/claw

# With specific model
./target/release/claw --model sonnet
```

### Single Prompt

```bash
# One-shot prompt
./target/release/claw prompt "explain Rust ownership"
```

### Slash Commands

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/status` | Show session status |
| `/model [name]` | Switch model |
| `/clear` | Clear session history |
| `/cost` | Show token usage |
| `/diff` | Show git diff |
| `/commit` | Generate and create commit |
| `/memory` | Show loaded instructions |

## MCP Integration

Claw-code connects to Cohezion's MCP servers:

- **cohezion-skills**: Skill management
- **cohezion-bmad**: BMAD data access
- **cohezion-research**: Research tools
- **cohezion-surreal**: SurrealDB operations
- **cohezion-swarm**: Swarm coordination
- **cohezion-knowledge**: Knowledge graph

### Using MCP Tools

```bash
# MCP tools are automatically available prefixed with mcp__
# Example tools:
# - mcp__cohezion_skills__list_skills
# - mcp__cohezion_bmad__query
# - mcp__cohezion_surreal__query
```

## Workflow Examples

### Code Review

```bash
./target/release/claw --model sonnet <<EOF
Review the code in src/cohezion/compound/cache.py for:
1. Memory leaks
2. Thread safety issues
3. Performance optimizations
EOF
```

### Documentation Generation

```bash
./target/release/claw --model haiku prompt "Generate API docs for src/cohezion/mcp/"
```

### Research with MCP

```bash
./target/release/claw --model opus <<EOF
Use cohezion-research to:
1. Find papers on "attention mechanisms"
2. Summarize key findings
3. Store results in knowledge graph
EOF
```

## Troubleshooting

### Model Won't Load

```bash
# Check if model exists
ollama list | grep gemma4

# Pull if missing
ollama pull gemma4:26b
```

### Out of Memory

```bash
# Stop all models
ollama stop $(ollama ps -q 2>/dev/null)

# Use smaller context
OLLAMA_CONTEXT_WINDOW=4096 ollama run gemma4:e4b
```

### Proxy Connection Failed

```bash
# Check proxy is running
ss -tlnp | grep 8082

# Restart proxy
pkill -f ollama-proxy
./scripts/start-ollama-proxy.sh
```

### Slow Response

```bash
# Use smaller model for faster responses
./target/release/claw --model haiku --model sonnet prompt "task"

# Or use phi3 directly
ollama run phi3:mini
```

## Performance Tips

1. **Use the smallest model that works** - `haiku` (phi3:mini) is much faster than `opus`
2. **Keep models loaded** - Ollama caches models; avoid `ollama stop` between requests
3. **Batch requests** - Multiple prompts in one session share context
4. **Adjust context window** - Smaller context = faster inference
5. **Monitor memory** - Check `free -h` and `rocm-smi` before large tasks

## Advanced Configuration

### Custom Model Mapping

Edit `scripts/ollama-proxy.py`:

```python
MODEL_MAP = {
    "haiku": "phi3:mini",        # 2.2GB
    "sonnet": "gemma4:e4b",      # 9.6GB  
    "opus": "gemma4:26b",        # 17GB
    "custom": "your-model:tag",  # Add custom mappings
}
```

### Multiple Proxies

```bash
# Run proxy on different port
python3 scripts/ollama-proxy.py 8083 &
ANTHROPIC_BASE_URL=http://localhost:8083 ./target/release/claw
```

### Environment Variables

```bash
# Override base URL
ANTHROPIC_BASE_URL=http://localhost:8082

# API key (not needed for Ollama)
ANTHROPIC_API_KEY=unused

# Model selection
CLAW_MODEL=haiku

# Permission mode
CLAW_PERMISSION_MODE=workspace-write
```