# Cohezion Pi Guides

Practical walkthroughs and guides for maximizing pi-coding-agent 0.67.2+ features in the Cohezion project.

## 📚 Guide Index

| Guide | Description | Time |
|-------|-------------|------|
| [Quick Start](00_QUICKSTART.md) | Get up and running in 5 minutes | 5 min |
| [Keybindings](01_KEYBINDINGS.md) | Kitty super-modified shortcuts | 10 min |
| [SDK Extensions](02_SDK_EXTENSIONS.md) | Inline extension factories | 20 min |
| [Multi-Prompt Workflow](03_MULTI_PROMPT.md) | Layered context with `--append-system-prompt` | 15 min |
| [Troubleshooting](99_TROUBLESHOOTING.md) | Common issues and fixes | Reference |

## 🎯 Learning Paths

### Path 1: User (Interactive Mode)

**Goal:** Use Pi effectively in the Cohezion project

1. [Quick Start](00_QUICKSTART.md) - Get running
2. [Keybindings](01_KEYBINDINGS.md) - Customize shortcuts
3. [Multi-Prompt Workflow](03_MULTI_PROMPT.md) - Optimize context
4. [Troubleshooting](99_TROUBLESHOOTING.md) - When things go wrong

### Path 2: Developer (SDK Integration)

**Goal:** Build custom integrations with Cohezion

1. [Quick Start](00_QUICKSTART.md) - Verify setup
2. [SDK Extensions Guide](02_SDK_EXTENSIONS.md) - Core concepts
3. `.pi/examples/sdk-embedded.ts` - Working example
4. [Troubleshooting](99_TROUBLESHOOTING.md) - Debug issues

### Path 3: Administrator (Workspace Setup)

**Goal:** Configure team-wide settings

1. Review `.pi/settings.json` configuration
2. [Keybindings](01_KEYBINDINGS.md) - Standardize shortcuts
3. [Multi-Prompt Workflow](03_MULTI_PROMPT.md) - Shared context
4. `.pi/RELEASE_HISTORY.md` - Full feature inventory

## 🚀 Quick Commands

```bash
# Start interactive session with Cohezion context
./pi-cohezion.sh

# Run SDK demo
uv run tsx .pi/examples/sdk-embedded.ts

# Validate configuration
python3 -c "import json; [json.load(open(f)) for f in [
    '.pi/settings.json',
    '.pi/keybindings.json',
    'package.json'
]]"

# View feature history
cat .pi/RELEASE_HISTORY.md
```

## 📁 File Reference

| File | Purpose |
|------|---------|
| `.pi/settings.json` | Main configuration |
| `.pi/keybindings.json` | Keyboard shortcuts |
| `.pi/APPEND_SYSTEM.md` | System prompt context |
| `.pi/FEATURES_0.67.2.md` | 0.67.2 feature docs |
| `.pi/RELEASE_HISTORY.md` | Complete release history |
| `.pi/examples/sdk-embedded.ts` | Working SDK example |
| `pi-cohezion.sh` | Wrapper script |

## 🆕 What's New in 0.67.2

1. **Multiple `--append-system-prompt` flags** - Layer context progressively
2. **Kitty super-modified keybindings** - Cmd/Win key shortcuts
3. **Inline extension factories** - Pass extensions directly to SDK

See [FEATURES_0.67.2.md](../FEATURES_0.67.2.md) for details.

## 🔗 External Resources

- [Pi Documentation](https://github.com/badlogic/pi-mono/tree/main/pi/packages/coding-agent/docs)
- [Pi Changelog](https://github.com/badlogic/pi-mono/blob/main/pi/packages/coding-agent/CHANGELOG.md)
- [Pi SDK Examples](https://github.com/badlogic/pi-mono/tree/main/pi/packages/coding-agent/examples/sdk)

---
*Part of the Cohezion Pi Setup - Last updated: 2026-04-15*
