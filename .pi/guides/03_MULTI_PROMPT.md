# Multi-Prompt Workflow Guide
## Overview

The `--append-system-prompt` flag (0.67.2+) enables **layered context injection**, allowing multiple prompt segments to be appended with double-newline separation. This is useful for:

- Modular system prompt construction
- Project-specific rules
- Dynamic context injection
- Reusable prompt components

## Basic Usage

### Single Append (Traditional)

```bash
pi --append-system-prompt "You are a helpful coding assistant"
```

### Multiple Appends (0.67.2+)

```bash
pi \
  --append-system-prompt "You are in the Cohezion project" \
  --append-system-prompt "Use uv, never pip" \
  --append-system-prompt "Follow FLUME-First pattern"
```

**Resulting system prompt:**

```markdown
[Default system prompt]

You are in the Cohezion project

Use uv, never pip

Follow FLUME-First pattern
```

## Cohezion Wrapper Script

### Using `pi-cohezion.sh`

File: `pi-cohezion.sh`

```bash
#!/bin/bash

APPEND_FLAGS=(
  "--append-system-prompt" "You are operating in the Cohezion project..."
  "--append-system-prompt" "Critical rules: FLUME-First..."
  "--append-system-prompt" "Architecture: CompoundExecutor..."
  "--append-system-prompt" "Key commands: uv run pytest..."
)

pi "${APPEND_FLAGS[@]}" "$@"
```

### Interactive Mode

```bash
./pi-cohezion.sh
```

### Single Prompt Mode

```bash
./pi-cohezion.sh "Generate a test for compound executor"
```

### With Additional Context

```bash
./pi-cohezion.sh --append-system-prompt "Focus on error handling" "Refactor this code"
```

## Advanced Patterns

### Pattern 1: Role-Based Layers

```bash
ROLE="security-auditor"
MODE="strict"

pi \
  --append-system-prompt "Role: ${ROLE}" \
  --append-system-prompt "Mode: ${MODE}" \
  --append-system-prompt "Task: Review for vulnerabilities"
```

### Pattern 2: File-Based Context

```bash
# Load context from files
FLUME_CONTEXT=$(cat docs/flume-patterns.md)
VAULT_CONTEXT=$(cat docs/vault-guide.md)

pi \
  --append-system-prompt "${FLUME_CONTEXT}" \
  --append-system-prompt "${VAULT_CONTEXT}"
```

### Pattern 3: Conditional Appends

```bash
#!/bin/bash

FLAGS=()

# Add base Cohezion context
FLAGS+=("--append-system-prompt" "Base Cohezion context...")

# Conditionally add team-specific context
if [ -f ".team-context" ]; then
  FLAGS+=("--append-system-prompt" "$(cat .team-context)")
fi

# Add mode-specific context
case "${COHEZION_MODE:-}" in
  "test") FLAGS+=("--append-system-prompt" "Focus on testing...") ;;
  "debug") FLAGS+=("--append-system-prompt" "Focus on debugging...") ;;
esac

pi "${FLAGS[@]}" "$@"
```

### Pattern 4: Environment-Specific

```bash
#!/bin/bash

# production.sh
pi \
  --append-system-prompt "Environment: Production" \
  --append-system-prompt "Critical: No debugging in prod" \
  --append-system-prompt "Vault: Read-only mode"

# development.sh
pi \
  --append-system-prompt "Environment: Development" \
  --append-system-prompt "Debug mode enabled" \
  --append-system-prompt "Vault: Full access"
```

## Integration with CI/CD

### GitHub Actions

```yaml
# .github/workflows/cohezion-review.yml
- name: Review with Cohezion
  run: |
    ./pi-cohezion.sh \
      --append-system-prompt "PR Review Mode" \
      --append-system-prompt "Focus on: security, performance" \
      "Review these changes: $(gh pr diff)"
```

### Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

STAGED=$(git diff --cached --name-only)

pi \
  --append-system-prompt "Pre-commit review mode" \
  --append-system-prompt "Check for: secrets, large files" \
  --mode json \
  "Review staged files: ${STAGED}"
```

## Combining with Other Options

### With `--system-prompt` (Replace Default)

```bash
pi \
  --system-prompt "You are Cohezion Assistant" \
  --append-system-prompt "FLUME-First rules" \
  --append-system-prompt "Vault-First persistence"
```

### With Skills

```bash
pi \
  --append-system-prompt "Using cohezion-patterns skill" \
  /skill:cohezion-patterns \
  "Refactor using PRIME patterns"
```

### With Context Files

```bash
pi \
  --append-system-prompt "Reviewing architecture" \
  @ARCHITECTURE.md \
  @HARDWARE_PROFILE_PRIME.md \
  "Review for compliance"
```

## SDK Integration

### Dynamic Context in SDK

```typescript
import { createAgentSession, DefaultResourceLoader } from "@mariozechner/pi-coding-agent";

const contextLayers = [
  "Base Cohezion context...",
  "Project: ${projectName}",
  "Mode: ${currentMode}",
];

const loader = new DefaultResourceLoader({
  appendSystemPromptOverride: (base) => [
    ...base,
    ...contextLayers,
  ],
});

const { session } = await createAgentSession({ resourceLoader: loader });
```

## Best Practices

### DO's ✅

- **Keep layers focused**: Each append should cover one topic
- **Order matters**: Earlier appends appear first in prompt
- **Use scripts**: Wrap common patterns in executable scripts
- **Document intent**: Comment why each layer exists

### DON'Ts ❌

- **Don't append duplicates**: Check for redundancy
- **Don't overly fragment**: Too many small appends hurt readability
- **Don't use for secrets**: Appends appear in logs
- **Don't exceed context**: Monitor token usage

## Troubleshooting

### Debugging Appended Prompts

```bash
# Use --verbose to see full configuration
pi --verbose \
  --append-system-prompt "Test" \
  "Hello"

# Check logs for system prompt content
grep "system" ~/.pi/agent/logs/latest.log
```

### Order Issues

```bash
# ❌ Commands must come AFTER append flags
pi "prompt" --append-system-prompt "context"

# ✅ Append flags before command
pi --append-system-prompt "context" "prompt"
```

### Escaping Issues

```bash
# ❌ Double quotes in append
pi --append-system-prompt "Say "hello" politely"

# ✅ Use single quotes or escape
pi --append-system-prompt 'Say "hello" politely'
pi --append-system-prompt "Say \"hello\" politely"
```

## See Also

- [Quick Start](00_QUICKSTART.md)
- [SDK Extensions Guide](02_SDK_EXTENSIONS.md)
- [Troubleshooting](99_TROUBLESHOOTING.md)

---
*Part of the Cohezion Pi Setup - Last updated: 2026-04-15*
