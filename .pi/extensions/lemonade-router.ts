/**
 * Lemonade Hardware Router — smart per-turn model routing for Pi agent.
 *
 * Provider registration is handled by ~/.pi/agent/models.json at startup.
 * This extension adds:
 *   1. Endpoint health check on session start (notification)
 *   2. Per-turn model selection via the `input` event
 *   3. Fire-and-forget Mycelium turn logging via the `turn_end` event
 *   4. Manual control via /lemonade slash command
 *
 * Routing tiers (all registered in models.json):
 *   NPU    :13306  gemma4-it:e2b                       ~2B   ack / one-liner turns
 *   REASON :13307  DeepSeek-Qwen3-8B-GGUF               8B   debug / explain / trace
 *   iGPU   :13307  user.Qwen3.6-35B-A3B-GGUF-Strix     35B   coding (default, 3B active MoE)
 *   CPU    :13307  Gemma-4-31B-it-GGUF                  31B   long analysis / architecture
 */

import type { ExtensionAPI, Model } from "@mariozechner/pi-coding-agent";

const LEMOND_BASE = "http://127.0.0.1:13307";
const FLM_NPU_BASE = "http://127.0.0.1:13306";
const COHEZION_BASE = "http://127.0.0.1:8080";

const TIER_MODELS = {
  npu:    "gemma4-it:e2b",
  reason: "DeepSeek-Qwen3-8B-GGUF",
  igpu:   "user.Qwen3.6-35B-A3B-GGUF-Strix-Q4_K_M",
  cpu:    "Gemma-4-31B-it-GGUF",
} as const;
type TierKey = keyof typeof TIER_MODELS;

// ── routing heuristics ────────────────────────────────────────────────────────

const ACK_RE =
  /^(ok|okay|yes|no|sure|done|thanks|good|great|sounds good|got it|continue|confirmed|looks good|lgtm|perfect|nice|cool|right|makes sense|agreed|proceed|go ahead|understood|alright|k|👍|✓)[\s.!?]*$/i;

// Chain-of-thought / debug / explain tasks — route to DeepSeek-Qwen3-8B reasoning model
const REASON_RE =
  /\b(debug|trace|why (is|does|did|would|can't|won't|isn't)|explain (how|why|what|this|the)|step.{0,5}by.{0,5}step|walk me through|how does .{0,40}work|what causes|root cause|investigate|diagnose|breakpoint|stack trace|what.{0,20}happening)\b/i;

const DEEP_RE =
  /\b(review all|audit|analyze the (entire|whole|full)|explain (how|why|what).{0,40}(across|throughout|system|codebase|architecture)|architecture|design (pattern|the|a)|multi[- ]file|trace through|walk.{0,15}through|deep dive|comprehensive|end.to.end)\b/i;

function pickTier(text: string): TierKey {
  const t = text.trim();
  if (t.length <= 60 && ACK_RE.test(t)) return "npu";
  if (t.length > 200 || DEEP_RE.test(t)) return "cpu";
  if (REASON_RE.test(t)) return "reason";
  return "igpu";
}

// ── health check ──────────────────────────────────────────────────────────────

async function isUp(base: string): Promise<boolean> {
  try {
    const r = await fetch(`${base}/v1/models`, { signal: AbortSignal.timeout(1500) });
    return r.ok;
  } catch {
    return false;
  }
}

// ── mycelium fire-and-forget ──────────────────────────────────────────────────

function logTurnToMycelium(tier: TierKey, modelId: string, promptChars: number, responseChars: number): void {
  const body = JSON.stringify({
    entry_id: `pi_${Date.now()}`,
    content: `Pi turn: tier=${tier} model=${modelId} prompt=${promptChars}c response=${responseChars}c`,
    domain: "pattern",
  });
  fetch(`${COHEZION_BASE}/api/mycelium/turn`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
    signal: AbortSignal.timeout(2000),
  }).catch(() => {}); // intentionally fire-and-forget
}

// ── extension ─────────────────────────────────────────────────────────────────

export default function lemonadeRouter(pi: ExtensionAPI) {
  let routingEnabled = true;
  let manualPin: TierKey | null = null;
  let activeTier: TierKey = "igpu";
  let activeModelId: string = TIER_MODELS.igpu;
  let lastPromptChars = 0;

  const endpointUp: Record<string, boolean> = {
    [FLM_NPU_BASE]: false,
    [LEMOND_BASE]: true,
  };

  function findLemonadeModel(
    ctx: { modelRegistry: { getModels(): Model<any>[] } },
    modelId: string,
  ): Model<any> | undefined {
    return ctx.modelRegistry
      .getModels()
      .find((m: any) => m.id === modelId && m.provider === "lemonade");
  }

  // ── session_start: probe endpoints ─────────────────────────────────────────

  pi.on("session_start", async (_event, ctx) => {
    const [npu, igpu] = await Promise.all([isUp(FLM_NPU_BASE), isUp(LEMOND_BASE)]);
    endpointUp[FLM_NPU_BASE] = npu;
    endpointUp[LEMOND_BASE] = igpu;

    const parts = [`iGPU :13307 ${igpu ? "✓" : "✗"}`, `NPU :13306 ${npu ? "✓" : "✗"}`];
    ctx.ui.notify(`🔥 Lemonade Router active — ${parts.join("  ")}`, igpu ? "info" : "warning");

    if (igpu) {
      const m = findLemonadeModel(ctx, TIER_MODELS.igpu);
      if (m) await pi.setModel(m);
    }
  });

  // ── input: route each turn ──────────────────────────────────────────────────

  pi.on("input", async (event, ctx) => {
    if (!routingEnabled) return { action: "continue" };

    lastPromptChars = event.text.length;
    const tierKey: TierKey = manualPin ?? pickTier(event.text);
    const modelId = TIER_MODELS[tierKey];

    const endpointBase = tierKey === "npu" ? FLM_NPU_BASE : LEMOND_BASE;
    const effectiveTierKey = endpointUp[endpointBase] ? tierKey : "igpu";
    const effectiveModelId = TIER_MODELS[effectiveTierKey];

    if (!endpointUp[LEMOND_BASE] && !endpointUp[FLM_NPU_BASE]) {
      ctx.ui.notify("⚠️  All Lemonade endpoints down", "warning");
      return { action: "continue" };
    }

    const model = findLemonadeModel(ctx, effectiveModelId);
    if (model) {
      await pi.setModel(model);
      activeTier = effectiveTierKey;
      activeModelId = effectiveModelId;

      if (effectiveTierKey === "npu") {
        ctx.ui.notify("⚡ NPU · 2B", "info");
      } else if (effectiveTierKey === "reason") {
        ctx.ui.notify("🧠 Reason · 8B", "info");
      } else if (effectiveTierKey === "cpu") {
        ctx.ui.notify("🏗️ CPU · 31B", "info");
      }
      // iGPU (default) is silent
    }
    return { action: "continue" };
  });

  // ── turn_end: fire-and-forget Mycelium logging ────────────────────────────
  // Fires once per user turn with the final assistant message.

  pi.on("turn_end", (event, _ctx) => {
    const content: { type: string; text?: string }[] = (event.message as any)?.content ?? [];
    const responseChars = content
      .filter((c) => c.type === "text")
      .reduce((acc, c) => acc + (c.text?.length ?? 0), 0);
    logTurnToMycelium(activeTier, activeModelId, lastPromptChars, responseChars);
  });

  // ── model_select: track manual user overrides ──────────────────────────────

  const LEGACY_LEMONADE = new Set(["Gemma-4-26B-A4B-it-GGUF"]);

  pi.on("model_select", (event, _ctx) => {
    const id = (event.model as any).id as string;
    const match = (Object.entries(TIER_MODELS) as [TierKey, string][]).find(([, v]) => v === id);
    if (match) {
      manualPin = match[0];
    } else if (LEGACY_LEMONADE.has(id)) {
      // Legacy lemonade models not in TIER_MODELS → pin to igpu tier silently
      manualPin = "igpu";
    } else {
      // Non-lemonade model selected — stand down entirely
      routingEnabled = false;
    }
  });

  // ── /lemonade command ──────────────────────────────────────────────────────

  pi.registerCommand({
    name: "lemonade",
    description: "Router: status | auto | off | pin <npu|reason|igpu|cpu>",
    handler: async (args, ctx) => {
      const [sub, tierArg] = (args ?? "").trim().split(/\s+/);

      if (!sub || sub === "status") {
        const cur = (ctx.getModel?.() as any)?.id ?? "—";
        const lines = [
          `routing: ${routingEnabled ? "auto" : "off"}  pin: ${manualPin ?? "none"}`,
          `active:  ${cur}  tier: ${activeTier}`,
          `iGPU :13307  ${endpointUp[LEMOND_BASE] ? "UP ✓" : "DOWN ✗"}`,
          `NPU  :13306  ${endpointUp[FLM_NPU_BASE] ? "UP ✓" : "DOWN ✗"}`,
          `tiers: npu(2B) → reason(8B) → igpu(35B-A3B) → cpu(31B)`,
        ];
        ctx.ui.notify(lines.join("\n"), "info");
        return;
      }
      if (sub === "auto") {
        routingEnabled = true;
        manualPin = null;
        ctx.ui.notify("Lemonade Router: auto-routing on", "info");
        return;
      }
      if (sub === "off") {
        routingEnabled = false;
        ctx.ui.notify("Lemonade Router: off — Ctrl+P to pick model", "info");
        return;
      }
      if (sub === "pin") {
        const valid: TierKey[] = ["npu", "reason", "igpu", "cpu"];
        if (!tierArg || !valid.includes(tierArg as TierKey)) {
          ctx.ui.notify(`/lemonade pin <${valid.join("|")}>`, "warning");
          return;
        }
        manualPin = tierArg as TierKey;
        routingEnabled = true;
        const m = findLemonadeModel(ctx, TIER_MODELS[manualPin]);
        if (m) await pi.setModel(m);
        ctx.ui.notify(`Pinned → ${TIER_MODELS[manualPin]}`, "info");
        return;
      }
      ctx.ui.notify("/lemonade [status|auto|off|pin <npu|reason|igpu|cpu>]", "warning");
    },
  });
}
