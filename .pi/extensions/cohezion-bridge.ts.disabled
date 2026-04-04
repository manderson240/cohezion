/**
 * Cohezion Bridge v2 - MCP-Powered Coherence Integration
 *
 * Connects pi to Cohezion via MCP:
 * - coherence.check_alignment (HIHO scoring)
 * - coherence.track_journey_step (12D FLUME)
 * - coherence.extract_pattern (FLUME encoding)
 * - coherence.refine_skill (PRIME skill updates)
 *
 * Non-destructive by design: all actions append, archive, or refine.
 */

import * as path from "path";
import { mkdir, readFile, writeFile, access, copyFile } from "fs/promises";
import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";

// MCP Client for coherence server
interface McpClient {
  callTool(name: string, args: Record<string, unknown>): Promise<unknown>;
}

interface CohezionConfig {
  skillsDir: string;
  projectRoot: string;
  vaultEnabled: boolean;
  patternBufferPath: string;
}

interface Pattern {
  name: string;
  category: string;
  description: string;
  file_paths: string[];
  code_example: string;
  confidence: number;
  embedding?: number[];
}

interface SkillMeta {
  name: string;
  description: string;
  file: string;
  version: string;
}

interface AlignmentResult {
  coherence: number;
  hiho_score: number;
  should_proceed: boolean;
  intent: string;
  intent_confidence: number;
  issues: string[];
}

export default function cohezionBridge(pi: ExtensionAPI) {
  let config: CohezionConfig | null = null;
  const skillIndex: Map<string, SkillMeta> = new Map();
  
  // MCP client (initialized lazily)
  let mcpClient: McpClient | null = null;
  
  function getMcpClient(): McpClient {
    if (!mcpClient) {
      // MCP client using pi's exec to call coherence server
      mcpClient = {
        async callTool(name: string, args: Record<string, unknown>): Promise<unknown> {
          const cmd = `echo '${JSON.stringify({ name, args })}' | uv run python src/cohezion/mcp/coherence_server.py --tool-call`;
          const result = await pi.exec("bash", ["-c", cmd], { timeout: 10000, cwd: config?.projectRoot });
          try {
            return JSON.parse(result.stdout);
          } catch {
            return { error: "Failed to parse MCP response" };
          }
        }
      };
    }
    return mcpClient;
  }

  // Initialize on session start
  pi.on("session_start", async (_event, ctx) => {
    config = {
      skillsDir: path.join(ctx.cwd, "src/cohezion/skills"),
      projectRoot: ctx.cwd,
      vaultEnabled: true,
      patternBufferPath: path.join(ctx.cwd, ".pattern_buffer.json"),
    };

    ctx.ui.notify("Cohezion Bridge: Initializing coherence systems...", "info");
    
    // Index skills
    await indexSkills(config.skillsDir);
    
    ctx.ui.notify(`Cohezion Bridge: ${skillIndex.size} skills ready`, "info");
  });

  // Pre-execution: HIHO alignment check via MCP
  pi.on("tool_call", async (event, ctx) => {
    if (!config) return;

    const intent = inferIntent(event.toolName, event.input);
    
    try {
      const mcp = getMcpClient();
      const result = await mcp.callTool("coherence.check_alignment", {
        intent,
        tool: event.toolName,
        context: JSON.stringify(event.input),
      }) as AlignmentResult;

      // Store alignment check in trajectory
      await recordJourneyStep({
        timestamp: Date.now(),
        operation: "alignment_check",
        tool: event.toolName,
        intent,
        files: extractFilePaths(event.input),
        coherence: result.coherence,
        tokens_used: 0,
      });

      // HIHO gate: block if coherence outside optimal band
      if (!result.should_proceed) {
        const coherenceVal = result.coherence ?? 0.5;
        const band = coherenceVal < 0.3 ? "too novel" : "over-constrained";
        const ok = await ctx.ui.confirm(
          "HIHO Alignment Check",
          `Coherence ${coherenceVal.toFixed(2)} (${band}). ${result.issues?.join("; ") ?? "Unknown issues"}. Proceed?`
        );
        if (!ok) {
          return { block: true, reason: `Blocked: coherence ${coherenceVal.toFixed(2)} outside HIHO band [0.3, 0.7]` };
        }
      }
    } catch (e) {
      // MCP coherence check failed - log but don't block
      ctx.ui.notify(`Coherence check failed: ${e}`, "warning");
    }
  });

  // Post-edit: Extract patterns with FLUME encoding
  pi.on("tool_result", async (event, ctx) => {
    if (!config) return;

    // Only process edit/write
    if (event.toolName !== "edit" && event.toolName !== "write") return;

    const filePath = typeof event.input.path === "string" ? event.input.path : null;
    if (!filePath) return;

    try {
      // Extract and encode pattern via MCP
      const mcp = getMcpClient();
      const result = await mcp.callTool("coherence.extract_pattern", {
        name: `pattern_${Date.now()}`,
        code: event.result?.content?.[0]?.text || "",
        category: "refactoring",
        description: `Edit to ${filePath}`,
        file_paths: [filePath],
      }) as { confidence?: number; name: string; has_flume_embedding: boolean };

      if (result && result.confidence && result.confidence > 0.7) {
        // Query similar patterns from vault
        const similar = await mcp.callTool("coherence.query_patterns", {
          query: result.name,
          limit: 3,
        }) as { patterns: Array<{ name: string; coherence: number }> };

        if (similar.patterns.length > 0) {
          ctx.ui.notify(`Similar patterns found: ${similar.patterns.map(p => p.name).join(", ")}`, "info");
        }

        // Trigger skill refinement if high confidence
        if (result.confidence > 0.85) {
          await refineSkill(result.name, filePath, ctx);
        }
      }

      // Check for degradation
      await checkDegradation(event, ctx);
    } catch (e) {
      // Pattern extraction failed - continue silently
      ctx.ui.notify(`Pattern extraction failed: ${e}`, "debug");
    }
  });

  // Register /cohezion commands
  pi.registerCommand("cohezion", {
    description: "Query the Cohezion concept space",
    handler: async (args, ctx) => {
      const parts = args.split(/\s+/);
      const action = parts[0];
      const query = parts.slice(1).join(" ");

      try {
        switch (action) {
          case "skills":
            ctx.ui.notify(listSkills(), "info");
            return;
          case "skill":
            ctx.ui.notify(await materializeSkill(query), "info");
            return;
          case "alignment":
            await ctx.ui.notify(await checkAlignmentInteractive(query, ctx), "info");
            return;
          case "trajectory":
            await ctx.ui.notify(await showTrajectory(), "info");
            return;
          case "hiho":
            await ctx.ui.notify(await calculateHiHo(query), "info");
            return;
          default:
            ctx.ui.notify(`Usage: /cohezion {skills|skill <name>|alignment <intent>|trajectory|hiho <coherence>}`, "info");
        }
      } catch (e) {
        ctx.ui.notify(`Command failed: ${e}`, "error");
      }
    },
  });

  // === Implementation Functions ===

  async function indexSkills(skillsDir: string) {
    try {
      const { stdout } = await pi.exec("find", [skillsDir, "-name", "*.md"], { timeout: 5000 });
      const files = stdout.split("\n").filter(Boolean);

      for (const file of files) {
        try {
          const content = await readFile(file, "utf-8");
          const meta = parseSkillMetadata(content);
          meta.file = path.basename(file);
          skillIndex.set(meta.name, meta);
        } catch {
          // Skip unreadable files
        }
      }
    } catch {
      // Skills dir might not exist
    }
  }

  function inferIntent(toolName: string, input: Record<string, unknown>): string {
    // Infer intent from tool and input
    const intentMap: Record<string, string[]> = {
      edit: ["transform", "refactor", "modify"],
      write: ["generate", "create", "produce"],
      bash: ["search", "analyze", "execute"],
      read: ["analyze", "inspect", "review"],
    };
    
    const verbs = intentMap[toolName.toLowerCase()] || ["execute"];
    
    if (typeof input === "object" && input !== null) {
      if (input.path) return `${verbs[0]} on ${input.path}`;
      if (input.command) return `${verbs[0]}: ${input.command}`;
    }
    return verbs[0];
  }

  function extractFilePaths(input: Record<string, unknown>): string[] {
    const paths: string[] = [];
    if (typeof input.path === "string") paths.push(input.path);
    if (typeof input.file === "string") paths.push(input.file);
    if (Array.isArray(input.files)) paths.push(...input.files.filter((f): f is string => typeof f === "string"));
    return paths;
  }

  async function recordJourneyStep(step: {
    timestamp: number;
    operation: string;
    tool: string;
    intent: string;
    files: string[];
    coherence: number;
    tokens_used: number;
  }): Promise<void> {
    if (!config) return;

    // Sync to MCP coherence server
    try {
      const mcp = getMcpClient();
      await mcp.callTool("coherence.track_journey_step", {
        task_description: step.intent,
        operation_type: step.tool === "edit" ? "transform" : 
                       step.tool === "write" ? "generate" : "analyze",
        coherence: step.coherence,
        efficiency: 0.8, // Placeholder
        success: true,
        metadata: {
          timestamp: step.timestamp,
          files: step.files,
        },
      });
    } catch (e) {
      // Trajectory recording failed - continue
      console.error("Journey tracking failed:", e);
    }

    // Also append to local trajectory
    const trajectoryPath = path.join(config.projectRoot, ".pi/trajectories/current.jsonl");
    try {
      await mkdir(path.dirname(trajectoryPath), { recursive: true });
      await writeFile(trajectoryPath, JSON.stringify(step) + "\n", { flag: "a" });
    } catch {
      // Local trajectory failed
    }
  }

  async function refineSkill(patternName: string, filePath: string, ctx: any) {
    if (!config) return;

    // Find matching skill
    const matchingSkill = Array.from(skillIndex.values()).find((s) =>
      filePath.toLowerCase().includes(s.name.toLowerCase())
    );

    if (!matchingSkill) return;

    // Call MCP to append refinement
    try {
      const mcp = getMcpClient();
      await mcp.callTool("coherence.refine_skill", {
        skill_name: matchingSkill.name,
        pattern: {
          name: patternName,
          description: `Refinement from ${filePath}`,
          code_example: "", // Would need to read actual code
          confidence: 0.9,
          coherence: 0.8,
        },
      });
      ctx.ui.notify(`Refined skill: ${matchingSkill.name}`, "info");
    } catch (e) {
      ctx.ui.notify(`Skill refinement failed: ${e}`, "warning");
    }
  }

  async function checkDegradation(event: any, ctx: any) {
    if (!config) return;

    try {
      const mcp = getMcpClient();
      const result = await mcp.callTool("coherence.detect_degradation", {
        metrics: {
          coherence: 0.5, // Would track from execution
          cache_hit_rate: 0.8,
          token_efficiency: 0.9,
          duration_seconds: 1.0,
          success_rate: 0.95,
        },
      }) as { has_critical: boolean; alerts: Array<{ severity: string; message: string }> };

      if (result.has_critical) {
        for (const alert of result.alerts) {
          if (alert.severity === "CRITICAL") {
            ctx.ui.notify(`CRITICAL: ${alert.message}`, "error");
          }
        }
      }
    } catch {
      // Degradation check failed silently
    }
  }

  async function checkAlignmentInteractive(query: string, ctx: any): Promise<string> {
    if (!config) return "Not initialized";
    if (!query) return "Usage: /cohezion alignment <intent>";

    try {
      const mcp = getMcpClient();
      const result = await mcp.callTool("coherence.check_alignment", {
        intent: query,
        tool: "interactive",
      }) as AlignmentResult;

      return `Coherence: ${(result.coherence ?? 0).toFixed(3)}
HIHO Score: ${(result.hiho_score ?? 0).toFixed(3)}
Intent: ${result.intent} (${((result.intent_confidence ?? 0) * 100).toFixed(0)}%)
Band: ${(result.coherence ?? 0.5) < 0.3 ? "TOO NOVEL" : (result.coherence ?? 0.5) > 0.7 ? "OVER-CONSTRAINED" : "OPTIMAL HIHO"}
Issue: ${result.issues?.join("; ") ?? "None"}`;
    } catch (e) {
      return `Alignment check failed: ${e}`;
    }
  }

  async function showTrajectory(): Promise<string> {
    if (!config) return "Not initialized";

    try {
      const mcp = getMcpClient();
      const result = await mcp.callTool("coherence.get_trajectory", {
        window: 5,
      }) as { points: Array<{ coherence: number; efficiency: number; timestamp: number }>; count: number };

      if (result.count === 0) return "No trajectory points recorded yet";

      const lines = result.points.map((p, i) => 
        `${i + 1}. Coherence: ${(p.coherence ?? 0).toFixed(2)}, Efficiency: ${(p.efficiency ?? 0).toFixed(2)}`
      );
      return `Recent trajectory (${result.count} points):\n${lines.join("\n")}`;
    } catch (e) {
      return `Trajectory query failed: ${e}`;
    }
  }

  async function calculateHiHo(query: string): Promise<string> {
    const coherence = parseFloat(query) || 0.5;
    
    try {
      const mcp = getMcpClient();
      const result = await mcp.callTool("coherence.calculate_hiho", {
        coherence,
      }) as { hiho_score: number; is_optimal: boolean; stability_band: string };

      return `Input coherence: ${(coherence ?? 0).toFixed(3)}
HIHO stability: ${(result.hiho_score ?? 0).toFixed(3)}
Optimal: ${result.is_optimal ? "YES" : "NO"}
Band: ${result.stability_band}`;
    } catch (e) {
      return `HIHO calculation failed: ${e}`;
    }
  }

  function listSkills(): string {
    if (skillIndex.size === 0) return "No skills indexed";
    return Array.from(skillIndex.values())
      .map((s) => `- ${s.name}: ${s.description.substring(0, 60)}...`)
      .join("\n");
  }

  async function materializeSkill(skillName: string): Promise<string> {
    if (!config) return "Not initialized";
    
    const skill = skillIndex.get(skillName.trim());
    if (!skill) {
      // Fuzzy search
      const matches = Array.from(skillIndex.values()).filter(s => 
        s.name.toLowerCase().includes(skillName.toLowerCase())
      );
      if (matches.length > 0) {
        return `Did you mean: ${matches.map(m => m.name).join(", ")}?`;
      }
      return `Skill not found: ${skillName}`;
    }

    try {
      const skillPath = path.join(config.skillsDir, skill.file);
      const content = await readFile(skillPath, "utf-8");
      return `## ${skill.name}\n${skill.description}\n\n\`\`\`\n${content.substring(0, 3000)}...\n\`\`\``;
    } catch {
      return `Failed to load skill: ${skillName}`;
    }
  }

  function parseSkillMetadata(content: string): SkillMeta {
    const nameMatch = content.match(/^# SKILL: (\w+)/m);
    const descMatch = content.match(/##? DESCRIPTION\s*\n\s*(.+?)(?=\n##|\n#|$)/s);

    return {
      name: nameMatch?.[1] || "unknown",
      description: descMatch?.[1] || "",
      file: "",
      version: "0.1",
    };
  }
}
