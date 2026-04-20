import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { Type } from "@sinclair/typebox";

export default function (pi: ExtensionAPI) {
  /**
   * Helper to execute the Cohezion KG CLI bridge via uv.
   */
  async function runKG(args: string[]): Promise<string> {
    const { stdout, stderr } = await pi.exec("uv", ["run", "python", "src/cohezion/knowledge_graph/cli.py", ...args]);
    if (stderr && !stdout) {
      throw new Error(`KG CLI Error: ${stderr}`);
    }
    return stdout;
  }

  // --- Tools ---

  pi.registerTool({
    name: "kg_search",
    label: "KG Search",
    description: "Search the Cohezion Knowledge Graph for learnings, patterns, and project history.",
    promptSnippet: "Search for compound patterns or project learnings",
    promptGuidelines: [
      "Use this when you need to understand 'how things are done' in this project beyond the current file context.",
      "Search for specifically 'Learning N' or 'PRIME' skills to get architectural guidance."
    ],
    parameters: Type.Object({
      query: Type.String({ description: "The search query" }),
      topK: Type.Optional(Type.Number({ description: "Number of results to return", default: 5 })),
    }),
    async execute(_id, params, _signal, _onUpdate, _ctx) {
      const output = await runKG(["search", params.query, "--top-k", String(params.topK ?? 5)]);
      return {
        content: [{ type: "text", text: output }],
        details: JSON.parse(output),
      };
    },
  });

  pi.registerTool({
    name: "kg_history",
    label: "KG History",
    description: "Retrieve recent agent execution records (journeys) to analyze how similar tasks were solved.",
    promptSnippet: "Fetch recent agent execution history",
    parameters: Type.Object({
      limit: Type.Optional(Type.Number({ description: "Number of records to retrieve", default: 20 })),
    }),
    async execute(_id, params, _signal, _onUpdate, _ctx) {
      const output = await runKG(["history", "--limit", String(params.limit ?? 20)]);
      return {
        content: [{ type: "text", text: output }],
        details: JSON.parse(output),
      };
    },
  });

  pi.registerTool({
    name: "kg_stats",
    label: "KG Stats",
    description: "Get high-level system statistics including total executions and average coherence.",
    promptSnippet: "Get aggregate project coherence and execution stats",
    parameters: Type.Object({}),
    async execute(_id, _params, _signal, _onUpdate, _ctx) {
      const output = await runKG(["stats"]);
      return {
        content: [{ type: "text", text: output }],
        details: JSON.parse(output),
      };
    },
  });

  // --- Commands ---

  pi.registerCommand("retro", {
    description: "Run a retrospective on the current session and generate a report.",
    handler: async (_args, ctx) => {
      const entries = ctx.sessionManager.getBranch();
      
      // Extract some basic facts from the session
      const intent = entries[0]?.message?.content?.[0]?.text || "Unknown intent";
      const modifiedFiles = new Set<string>();
      const createdFiles = new Set<string>();
      
      for (const entry of entries) {
        if (entry.type === "message" && entry.message.role === "toolResult") {
          const content = typeof entry.message.content === "string" 
            ? entry.message.content 
            : JSON.stringify(entry.message.content);
          
          // Heuristic to find files in tool results
          const paths = content.match(/\/?[\w\./-]+\.(py|md|ts|json|sql)/g) || [];
          paths.forEach(p => modifiedFiles.add(p));
        }
      }

      const facts = {
        intent,
        files_modified: Array.from(modifiedFiles),
        files_created: [], // Would require better tracking of 'write' vs 'edit'
        capabilities_used: ["pi-agent"],
        tests_passing: "unknown"
      };

      try {
        const report = await runKG(["retro", "--facts", JSON.stringify(facts)]);
        
        // Save report to KG reports directory
        const reportName = `RETRO_${Date.now()}.md`;
        const reportPath = `src/cohezion/knowledge_graph/reports/${reportName}`;
        await pi.exec("bash", ["-c", `echo \"${report.replace(/\\n/g, "\\n")}\" > ${reportPath}`]);
        
        ctx.ui.notify(`Retrospective report generated: ${reportName}`, "success");
        return `Session Retrospective completed. Report saved to ${reportPath}.\n\n${report}`;
      } catch (e: any) {
        ctx.ui.notify(`Retro failed: ${e.message}`, "error");
        return `Failed to run retrospection: ${e.message}`;
      }
    },
  });

  pi.on("session_start", async (_event, ctx) => {
    ctx.ui.notify("Cohezion KG harness loaded. Use /retro for session analysis.", "info");
  });
}
