# SDK Extensions Guide: Inline Extension Factories

Build embedded integrations with pi-coding-agent 0.67.2+ inline extension factories.

## Overview

Pi 0.67.2+ introduces **inline extension factories** - pass extension code directly to the SDK without external `.ts` files. Perfect for:
- Embedded integrations
- Custom entrypoints
- Programmatic control
- Testing extensions

## Quick Example

```typescript
import { createAgentSession, DefaultResourceLoader } from "@mariozechner/pi-coding-agent";

// Create loader with inline extension factory
const resourceLoader = new DefaultResourceLoader({
  extensionFactories: [
    (pi) => {
      // Inline extension - no .ts file needed!
      pi.on("agent_start", () => {
        console.log("Extension loaded!");
      });
    },
  ],
});

const { session } = await createAgentSession({ resourceLoader });
```

## Cohezion Example Walkthrough

### Full Working Example

File: `.pi/examples/sdk-embedded.ts`

```typescript
import {
  createAgentSession,
  DefaultResourceLoader,
  SessionManager,
  type ExtensionAPI,
} from "@mariozechner/pi-coding-agent";
import { Type } from "@sinclair/typebox";

// Extension 1: FLUME-First Enforcer
const flumeFirstExtension = (pi: ExtensionAPI) => {
  pi.on("agent_start", async () => {
    console.log("[Cohezion] 🔥 Session with FLUME-First enforcement");
  });

  pi.on("tool_call", async (event) => {
    console.log(`[Cohezion] Tool: ${event.toolName}`);
    
    if (event.toolName === "write" || event.toolName === "edit") {
      console.log("[Cohezion] ⚠️  FLUME-First reminder: encode new modules");
    }
    
    return undefined; // Don't block
  });

  pi.registerCommand("cohezion-status", {
    description: "Display system status",
    handler: async (_args, ctx) => {
      ctx.ui.notify("🌀 Cohezion online");
    },
  });
};

// Extension 2: Vault Logger
const vaultLoggerExtension = (pi: ExtensionAPI) => {
  pi.on("agent_end", async (event) => {
    const learnings = extractLearnings(event.messages);
    console.log(`[Vault] Persisting ${learnings.length} learnings`);
    // await mcp.vault_write({...})
  });
};

// Create session with multiple inline factories
const resourceLoader = new DefaultResourceLoader({
  extensionFactories: [flumeFirstExtension, vaultLoggerExtension],
});

const { session } = await createAgentSession({
  resourceLoader,
  sessionManager: SessionManager.inMemory(),
});
```

### Run the Example

```bash
# Option 1: With tsx
uv run tsx .pi/examples/sdk-embedded.ts

# Option 2: With bun
bun run .pi/examples/sdk-embedded.ts

# Option 3: With node + ts-node
npx ts-node .pi/examples/sdk-embedded.ts
```

## Extension API Reference

### Event Handlers

```typescript
pi.on("agent_start", async (event, ctx) => {
  // Event fired when agent starts
  // event.reason: "startup" | "reload" | "new" | "resume" | "fork"
});

pi.on("agent_end", async (event, ctx) => {
  // Event fired when agent completes
});

pi.on("tool_call", async (event, ctx) => {
  // Intercept tool calls
  // Can block by returning { block: true, reason: "..." }
  // Can mutate args by modifying event.input
});

pi.on("session_start", async (event, ctx) => {
  // Unified session event (replaces session_switch/session_fork)
  // event.previousSessionFile: previous session path
});
```

### Context Object

```typescript
interface ExtensionContext {
  ui: {
    notify: (message: string) => void;
    setHiddenThinkingLabel: (label: string) => void;
  };
  modelRegistry: ModelRegistry;
  signal: AbortSignal;  // 0.63.2+ - Forward cancellation
  compact: () => Promise<void>;
  
  // Tool and command access
  tools: ToolRegistry;
  commands: CommandRegistry;
}
```

### Registering Custom Tools

```typescript
import { defineTool } from "@mariozechner/pi-coding-agent";
import { Type } from "@sinclair/typebox";

// Method 1: Using defineTool (recommended)
const myTool = defineTool({
  name: "vault_write",
  description: "Write to Cohezion vault",
  parameters: Type.Object({
    path: Type.String(),
    content: Type.String(),
  }),
  execute: async (toolCallId, params, signal) => ({
    content: [{ type: "text", text: `Written to ${params.path}` }],
  }),
});

pi.registerTool(myTool);

// Method 2: Manual registration
pi.registerTool({
  name: "custom_bash",
  label: "Custom Bash",
  description: "Run bash with custom env",
  parameters: Type.Object({
    command: Type.String(),
    timeout: Type.Optional(Type.Number()),
  }),
  execute: async (toolCallId, params, signal, onUpdate, ctx) => {
    // Custom execution logic
    return {
      content: [{ type: "text", text: "Result" }],
      details: {},
    };
  },
});
```

### Registering Custom Commands

```typescript
pi.registerCommand("cohezion", {
  description: "Show Cohezion system info",
  handler: async (args, ctx) => {
    const info = `
🌀 Cohezion System Status
━━━━━━━━━━━━━━━━━━━━
FLUME VAE: Online (256D)
Compound: Ready
Swarm: Active
Vault: Connected
    `;
    ctx.ui.notify(info);
  },
});

// Usage in Pi:
// /cohezion
```

### Custom UI Components

```typescript
pi.on("agent_start", async (event, ctx) => {
  // Set custom thinking block label
  ctx.ui.setHiddenThinkingLabel("🔍 Cohezion reasoning...");
});
```

## Combining Inline and File Extensions

```typescript
const resourceLoader = new DefaultResourceLoader({
  // File-based extensions (loaded from disk)
  additionalExtensionPaths: [
    ".pi/extensions/cohezion-kg.ts",
    ".pi/extensions/ci-sentinel.ts",
  ],
  
  // Inline extensions (defined in code)
  extensionFactories: [
    flumeFirstExtension,
    vaultLoggerExtension,
    (pi) => {
      // Anonymous inline extension
      pi.on("tool_call", async (event) => {
        console.log(`Tool: ${event.toolName}`);
      });
    },
  ],
});
```

## Use Cases

### Testing Extensions

```typescript
// test-extension.ts
import { describe, it, expect } from "vitest";
import { DefaultResourceLoader } from "@mariozechner/pi-coding-agent";

describe("Cohezion Extension", () => {
  it("should register commands", async () => {
    const loader = new DefaultResourceLoader({
      extensionFactories: [
        (pi) => {
          pi.registerCommand("test", {
            description: "Test",
            handler: async () => {},
          });
        },
      ],
    });
    await loader.reload();
    
    const commands = loader.getCommands();
    expect(commands).toContainEqual(
      expect.objectContaining({ name: "test" })
    );
  });
});
```

### CI Integration

```typescript
// ci-runner.ts
import { createAgentSession } from "@mariozechner/pi-coding-agent";

const { session } = await createAgentSession({
  extensionFactories: [
    (pi) => {
      // Fail fast on errors
      pi.on("tool_call", async (event) => {
        if (event.toolName === "bash") {
          // Add CI-specific handling
        }
      });
    },
  ],
});

const result = await session.prompt("Run tests");
process.exit(result.failed ? 1 : 0);
```

### Custom Entrypoints

```typescript
// cohezion-agent.ts
#!/usr/bin/env tsx
import { createAgentSession, DefaultResourceLoader } from "@mariozechner/pi-coding-agent";

async function main() {
  const loader = new DefaultResourceLoader({
    extensionFactories: [cohezionSpecificLogic],
    appendSystemPromptOverride: (base) => [
      ...base,
      "## Cohezion Context",
      "This is a specialized Cohezion agent...",
    ],
  });

  const { session } = await createAgentSession({ resourceLoader: loader });
  
  // Run interactive or automated workflow
  await session.prompt(process.argv.slice(2).join(" "));
}

main();
```

## Runtime API (0.65.0+)

For advanced session management:

```typescript
import {
  createAgentSessionRuntime,
  createAgentSessionServices,
  SessionManager,
} from "@mariozechner/pi-coding-agent";

const runtime = await createAgentSessionRuntime(
  async ({ cwd, sessionManager, sessionStartEvent }) => {
    const services = await createAgentSessionServices({ cwd });
    return {
      ...(await createAgentSessionFromServices({
        services,
        sessionManager,
        sessionStartEvent,
      })),
      services,
      diagnostics: services.diagnostics,
    };
  },
  {
    cwd: process.cwd(),
    sessionManager: SessionManager.create(process.cwd()),
  }
);

// Session lifecycle
await runtime.newSession();
await runtime.switchSession("/path/to/session.jsonl");
await runtime.fork("entry-id");
```

## Debugging Extensions

```typescript
pi.on("agent_start", async (event, ctx) => {
  console.log("[Debug] Agent started:", event.reason);
});

pi.on("tool_call", async (event, ctx) => {
  console.log("[Debug] Tool call:", event.toolName, event.input);
  
  // Add before/after logging
  const start = Date.now();
  const result = await ctx.tools.execute(event.toolName, event.input);
  console.log(`[Debug] Tool took ${Date.now() - start}ms`);
  
  return result;
});
```

## Troubleshooting

### Extension Not Loading

```bash
# Enable verbose logging
PI_VERBOSE=1 uv run tsx .pi/examples/sdk-embedded.ts
```

### Type Errors

```bash
# Ensure TypeBox is installed
npm install @sinclair/typebox

# Or use in-memory types
const params = { type: "object", properties: { /* ... */ } };
```

### Async Context

```typescript
// ❌ Wrong: Top-level await not allowed in factory
const resourceLoader = new DefaultResourceLoader({
  extensionFactories: [
    async (pi) => { /* ❌ */ },
  ],
});

// ✅ Correct: Use event handlers for async work
(pi) => {
  pi.on("agent_start", async (event, ctx) => {
    // ✅ Async work here
    const data = await fetchData();
  });
}
```

## See Also

- [Pi Extensions Docs](https://github.com/badlogic/pi-mono/blob/main/pi/packages/coding-agent/docs/extensions.md)
- [Quick Start](00_QUICKSTART.md)
- [Troubleshooting](99_TROUBLESHOOTING.md)

---
*Part of the Cohezion Pi Setup - Last updated: 2026-04-15*
