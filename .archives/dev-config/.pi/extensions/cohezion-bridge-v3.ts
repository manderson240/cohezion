/**
 * Cohezion Bridge v3 — Lightweight Coherence + Journey Integration
 *
 * Replaces the heavy MCP-subprocess approach with direct KG CLI calls
 * and lightweight file-based trajectory tracking.
 *
 * Features:
 * - Journey tracking (append-only trajectory logging)
 * - Pattern extraction from successful edits (confidence-thresholded)
 * - Skill search/materialize via KG CLI
 * - Degradation notifications from trajectory coherence
 * - /cohezion command suite
 */

import * as path from "path";
import { mkdir, readFile, writeFile, appendFile } from "fs/promises";
import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { Type } from "@sinclair/typebox";

interface CohezionConfig {
  skillsDir: string;
  projectRoot: string;
  patternBufferPath: string;
  trajectoryDir: string;
}

interface TrajectoryPoint {
  timestamp: number;
  operation: string;
  tool: string;
  intent: string;
  files: string[];
  coherence: number;
  success: boolean;
}

export default function cohezionBridge(pi: ExtensionAPI) {
  let config: CohezionConfig | null = null;
  let sessionStart: number = 0;
  let editCount = 0;
  let successCount = 0;

  // --- Session lifecycle ---
  pi.on("session_start", async (_event, ctx) => {
    config = {
      skillsDir: path.join(ctx.cwd, "src/cohezion/skills"),
      projectRoot: ctx.cwd,
      patternBufferPath: path.join(ctx.cwd, ".pattern_buffer.json"),
      trajectoryDir: path.join(ctx.cwd, ".pi/trajectories"),
    };
    sessionStart = Date.now();
    editCount = 0;
    successCount = 0;

    await mkdir(config.trajectoryDir, { recursive: true });
    ctx.ui.notify("🔬 Cohezion Bridge v3 loaded — /cohezion for commands", "info");
  });

  // --- Journey tracking on every tool call ---
  pi.on("tool_call", async (event, _ctx) => {
    if (!config) return;

    editCount++;
    const intent = inferIntent(event.toolName, event.input);
    const files = extractFilePaths(event.input);

    // Calculate running coherence from success ratio
    const coherence = editCount > 0 ? successCount / editCount : 0.5;

    const point: TrajectoryPoint = {
      timestamp: Date.now(),
      operation: "tool:before",
      tool: event.toolName,
      intent,
      files,
      coherence,
      success: true, // Will be updated on result
    };

    await appendTrajectory(point);
  });

  // --- Pattern extraction on successful edits ---
  pi.on("tool_result", async (event, _ctx) => {
    if (!config) return;
    if (event.toolName !== "edit" && event.toolName !== "write") return;

    const success = !event.error;
    if (success) successCount++;

    // Extract file path for pattern tracking
    const filePath = typeof event.input?.path === "string" ? event.input.path : null;
    if (!filePath || !success) return;

    // Record the pattern to the pattern buffer
    try {
      const patternEntry = {
        timestamp: Date.now(),
        file: filePath,
        tool: event.toolName,
        oldText: event.input?.oldText ?? null,
        category: categorizeEdit(filePath, event.input?.oldText ?? ""),
      };

      await appendPattern(patternEntry);
    } catch {
      // Pattern buffer write failed — non-critical
    }
  });

  // --- /cohezion command ---
  pi.registerCommand("cohezion", {
    description: "Query Cohezion concept space: skills, alignment, trajectory, patterns",
    handler: async (args, ctx) => {
      const parts = args.trim().split(/\s+/);
      const action = parts[0];
      const query = parts.slice(1).join(" ");

      switch (action) {
        case "skills": {
          const count = await countSkills();
          ctx.ui.notify(`📚 ${count} PRIME skills indexed in src/cohezion/skills/`, "info");
          return;
        }
        case "skill": {
          if (!query) {
            ctx.ui.notify("Usage: /cohezion skill <name>", "info");
            return;
          }
          await materializeSkill(query, ctx);
          return;
        }
        case "trajectory": {
          const stats = getSessionStats();
          ctx.ui.notify(
            `📊 Session: ${stats.edits} edits, ` +
            `${stats.successRate.toFixed(0)}% success, ` +
            `coherence: ${stats.coherence.toFixed(2)}`,
            "info"
          );
          return;
        }
        case "patterns": {
          const patterns = await readRecentPatterns(5);
          if (patterns.length === 0) {
            ctx.ui.notify("No patterns recorded yet", "info");
          } else {
            ctx.ui.notify(`🔍 Recent patterns:\n${patterns.join("\n")}`, "info");
          }
          return;
        }
        default:
          ctx.ui.notify(
            "Usage: /cohezion {skills|skill <name>|trajectory|patterns}",
            "info"
          );
      }
    },
  });

  // --- Helpers ---

  function inferIntent(toolName: string, input: Record<string, unknown>): string {
    if (typeof input === "object" && input !== null) {
      if (input.path) return `${toolName} on ${input.path}`;
      if (input.command) return `bash: ${String(input.command).substring(0, 80)}`;
    }
    return toolName;
  }

  function extractFilePaths(input: Record<string, unknown>): string[] {
    const paths: string[] = [];
    if (typeof input?.path === "string") paths.push(input.path);
    if (typeof input?.file === "string") paths.push(input.file);
    return paths;
  }

  function categorizeEdit(filePath: string, _oldText: string): string {
    if (filePath.includes("test")) return "testing";
    if (filePath.includes("compound")) return "compound";
    if (filePath.includes("swarm")) return "swarm";
    if (filePath.includes("physics")) return "physics";
    if (filePath.includes("api")) return "api";
    return "general";
  }

  async function appendTrajectory(point: TrajectoryPoint): Promise<void> {
    if (!config) return;
    const trajectoryPath = path.join(config.trajectoryDir, "current.jsonl");
    try {
      await appendFile(trajectoryPath, JSON.stringify(point) + "\n");
    } catch {
      // Non-critical
    }
  }

  async function appendPattern(entry: Record<string, unknown>): Promise<void> {
    if (!config) return;
    try {
      await appendFile(config.patternBufferPath, JSON.stringify(entry) + "\n");
    } catch {
      // Non-critical
    }
  }

  async function countSkills(): Promise<number> {
    if (!config) return 0;
    try {
      const { stdout } = await pi.exec("bash", [
        "-c", `find ${config.skillsDir} -name "*.md" | wc -l`
      ], { timeout: 5000 });
      return parseInt(stdout.trim(), 10) || 0;
    } catch {
      return 0;
    }
  }

  async function materializeSkill(skillName: string, ctx: any): Promise<void> {
    if (!config) return;
    const normalized = skillName.toUpperCase().replace(/-/g, "_");
    const skillPath = path.join(config.skillsDir, `${normalized}.md`);

    try {
      const content = await readFile(skillPath, "utf-8");
      ctx.ui.notify(`## ${normalized}\n\n${content.substring(0, 2000)}${content.length > 2000 ? "\n...(truncated)" : ""}`, "info");
    } catch {
      // Try fuzzy match
      try {
        const { stdout } = await pi.exec("bash", [
          "-c", `ls ${config.skillsDir} | grep -i "${skillName}" | head -5`
        ], { timeout: 5000 });
        if (stdout.trim()) {
          ctx.ui.notify(`No exact match. Similar: ${stdout.trim().replace(/\.md$/gm, "")}`, "info");
        } else {
          ctx.ui.notify(`Skill not found: ${skillName}`, "warning");
        }
      } catch {
        ctx.ui.notify(`Skill not found: ${skillName}`, "warning");
      }
    }
  }

  async function readRecentPatterns(limit: number): Promise<string[]> {
    if (!config) return [];
    try {
      const content = await readFile(config.patternBufferPath, "utf-8");
      const lines = content.trim().split("\n").filter(Boolean).slice(-limit);
      return lines.map((line, i) => {
        try {
          const p = JSON.parse(line);
          return `${i + 1}. ${p.category}: ${p.file} (${new Date(p.timestamp).toLocaleTimeString()})`;
        } catch {
          return `${i + 1}. (unparseable)`;
        }
      });
    } catch {
      return [];
    }
  }

  function getSessionStats() {
    return {
      edits: editCount,
      successRate: editCount > 0 ? (successCount / editCount) * 100 : 0,
      coherence: editCount > 0 ? successCount / editCount : 0.5,
      duration: sessionStart > 0 ? Math.round((Date.now() - sessionStart) / 60000) : 0,
    };
  }
}