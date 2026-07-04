"""Operator → local Omni planner delegation driver.

Per the user directive, this operator (the Claude session) acts as
orchestrator, validator, and verifier. All implementation work is
delegated to the local Omni planner on the OmniRouter (:13305). This
script is the bridge: it takes a chunk description + a target file path,
submits a chat-completion to the planner, parses the response, writes
the file, and runs the verification step.

Usage:
    python3 delegate_to_omni.py --chunk 1            # submit chunk 1 from the plan
    python3 delegate_to_omni.py --chunk 1 --dry-run  # show the prompt, don't send
    python3 delegate_to_omni.py --raw --file PATH --prompt '...'  # arbitrary code gen

The planner model is Qwen3.6-35B-A3B-MTP-GGUF (the only Qwen3.6 with
mtp+vision labels). It runs through the OmniRouter at
http://localhost:13305/v1/chat/completions.

Outputs:
    - Writes the parsed code block to the target file
    - Prints a JSON line per chunk: {chunk, file, status, lines, planner_seconds, draft_acceptance}
    - Exits 0 on success, 1 on planner/parse/write failure
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

import httpx


PLANNER_MODEL = "Qwen3.6-35B-A3B-MTP-GGUF"
OMNI_BASE = "http://localhost:13305/v1/chat/completions"
REPO_ROOT = Path("/home/mike-anderson/dev/cohezion").resolve()


# --- Chunk definitions (one per delegation unit in the plan) ----------------

CHUNKS: dict[str, dict] = {
    "1": {
        "title": "journey_loader.py (schema extraction)",
        "target": "src/cohezion/api/services/journey_loader.py",
        "system": (
            "You are a senior Python engineer on the Cohezion AMD-Strix-Halo platform. "
            "Read the existing `src/cohezion/api/journeys.py` lines 43-79 and produce a new module "
            "`src/cohezion/api/services/journey_loader.py` exporting `load_journey(journey_id)`, "
            "`load_all_journeys()`, `JOURNEY_DIR` constant, and `summarize(journey: dict) -> dict`. "
            "Same behavior, identical signatures. Keep the `Path('data/universe')` default. "
            "The module must remain pure I/O — no imports from `cohezion.*` (only stdlib). "
            "Use `from __future__ import annotations` and pathlib. "
            "Return ONLY the file contents in a single ```python fenced code block. No prose."
        ),
        "user": (
            "Read /home/mike-anderson/dev/cohezion/src/cohezion/api/journeys.py (focus on lines 43-79). "
            "Extract the journey I/O into a new module at "
            "/home/mike-anderson/dev/cohezion/src/cohezion/api/services/journey_loader.py. "
            "Exports: `load_journey(journey_id) -> dict | None`, "
            "`load_all_journeys() -> list[dict]`, `JOURNEY_DIR = Path('data/universe')`, "
            "`summarize(journey: dict) -> dict` with keys id/agent_name/intent/status/final_coherence/"
            "final_phi_score/trajectory_length (matching the legacy summarize inline at lines 105-115). "
            "Preserve the same return types and side effects. No prose, just the file."
        ),
    },
    "2": {
        "title": "journey_corpus_seeder.py (deterministic backfill)",
        "target": "src/cohezion/api/services/journey_corpus_seeder.py",
        "system": (
            "You are a senior Python engineer on the Cohezion platform. "
            "Read /home/mike-anderson/dev/cohezion/data/universe/journey_1773365054_936d9624.json "
            "for the on-disk schema. Then produce "
            "/home/mike-anderson/dev/cohezion/src/cohezion/api/services/journey_corpus_seeder.py. "
            "Public surface: `seed_stub_corpus(n: int = 8, *, seed: int = 42, force: bool = False) "
            "-> list[str]` (returns the list of journey_ids written). "
            "Idempotency: a `data/universe/.seed.flag` file marks the corpus as seeded. "
            "`force=True` rewrites regardless. Determinism: same seed+n always produces the same "
            "corpus. Each journey has: 12D `initial_axiomatic` (deterministic per-id via numpy RNG), "
            "2048D `initial_latent_embedding` (SHA-256 expanded), synthetic 256D `flume_z` field, "
            "20-step `trajectory[]` where each step is `{'state_12d': list(12 floats), 'coherence': float, "
            "'z_256': list(256 floats), 'timestamp': float}`, plus `final_coherence`, `final_phi_score`, "
            "`summary` (1-sentence), `precipitation_type` (1-2 words), `status='complete'`. "
            "Use `from __future__ import annotations`, pathlib, hashlib, json, logging, numpy. "
            "Return ONLY the file in a single ```python fenced block. No prose."
        ),
        "user": (
            "Read /home/mike-anderson/dev/cohezion/data/universe/journey_1773365054_936d9624.json. "
            "Then write the seeder module as specified. Use the same directory layout: "
            "data/universe/ for the JSON files. Make it idempotent with the .seed.flag marker. "
            "Make the trajectory steps a LERP between the initial 12D and a final 12D, with z_256 "
            "drawn from N(0.5, 0.1) clamped to [0,1] for the HIHO kernel. "
            "8 stub journeys by default. No prose, just the file."
        ),
    },
    "3": {
        "title": "journey_nexus.py service (the orchestration façade)",
        "target": "src/cohezion/api/services/journey_nexus.py",
        "system": (
            "You are a senior Python engineer on the Cohezion platform. "
            "Produce /home/mike-anderson/dev/cohezion/src/cohezion/api/services/journey_nexus.py. "
            "Public surface:\n"
            "```\n"
            "class JourneyNexus:\n"
            "    def __init__(self) -> None\n"
            "    async def subscribe(self, journey_id: str | None = None) -> AsyncIterator[EVOEvent]\n"
            "    async def narrate(self, journey_id: str, *, with_image: bool = False) -> NarrateResult\n"
            "    async def quadrature(self, journey_id: str, *, mode: Literal['preflight','full']='preflight') -> QuadratureOutcome\n"
            "    async def omni_chat(self, journey_id: str, message: str) -> OmniChatOutcome\n"
            "    def stream_snapshot(self) -> list[EVOEvent]\n"
            "    def add_event(self, event: EVOEvent) -> None  # for tests + Quadrature hook\n"
            "```\n"
            "Plus dataclasses: `EVOEvent(id, timestamp, z_256, state_12d, kind, voice, score, journey_id)`, "
            "`NarrateResult(journey_id, text, audio_b64, image_b64 | None, coherence)`, "
            "`QuadratureOutcome(approved, consensus_score, alignment_score, voice_responses, rejection_reason)`, "
            "`OmniChatOutcome(text, tool_calls, images_b64, audio_b64)`. "
            "Lazy imports of FLUME VAE, QuadratureNexus, OmniTier — never at module top. "
            "EVOStream is a `collections.deque(maxlen=256)` with a `threading.Lock`. "
            "Return ONLY the file in a single ```python fenced block. No prose."
        ),
        "user": (
            "Write the JourneyNexus service as specified. Use these imports as guidance: "
            "`from cohezion.inference.omni_tier import OmniTier, OmniRequest, OmniResult, build_omni_tier` "
            "and `from cohezion.swarm.quadrature_nexus import QuadratureNexus, QuadratureProposal, QuadratureResult` "
            "and `from cohezion.api.services.flume import get_vae, compute_coherence` and "
            "`from cohezion.api.services.journey_loader import load_journey, summarize`. "
            "The `subscribe()` async generator should yield from the EVOStream deque (with lock) and "
            "optionally filter by `journey_id`. The `add_event` method must append under the lock and "
            "drop oldest. The `quadrature()` method constructs a QuadratureProposal with "
            "`action='interpret_journey'`, `description=journey['intent']`, "
            "`context={'journey_id': ..., 'initial_12d': journey['initial_axiomatic']}`, "
            "`submitted_by='JourneyNexus'`, and calls `nexus.deliberate()`. Map the result into "
            "QuadratureOutcome. The `narrate()` method runs FLUME encode on the intent, computes "
            "the HIHO coherence, then calls `omni.tts_tier.speak()` for audio; if `with_image`, also "
            "calls `omni.image_tier.render()`. The `omni_chat()` method calls `omni.run(OmniRequest(...))` "
            "with the journey's intent as additional context. Use `import asyncio` for AsyncIterator, "
            "`from typing import AsyncIterator, Literal`. Return ONLY the file in a single ```python fenced block."
        ),
    },
    "4": {
        "title": "routes/journey_nexus.py (FastAPI adapter)",
        "target": "src/cohezion/api/routes/journey_nexus.py",
        "system": (
            "You are a senior Python/FastAPI engineer. "
            "Produce /home/mike-anderson/dev/cohezion/src/cohezion/api/routes/journey_nexus.py. "
            "Public routes (all under prefix='/journey-nexus'):\n"
            "- `GET /stream/evo` — SSE; proxies `nexus.subscribe()`; yields JSON per event: "
            "  `{'id', 'timestamp', 'z_256', 'state_12d', 'kind', 'voice', 'score', 'journey_id'}`. "
            "  Use `fastapi.responses.StreamingResponse` with `media_type='text/event-stream'`.\n"
            "- `GET /evo/snapshot` — JSON list of last N events.\n"
            "- `GET /quadrature/{journey_id}?mode=preflight|full` — returns QuadratureOutcome JSON.\n"
            "- `GET /narrate/{journey_id}?with_image=false` — returns NarrateResult JSON "
            "  (audio_b64, optional image_b64).\n"
            "- `POST /omni/{journey_id}` — body `OmniChatRequest(message: str)`; returns OmniChatOutcome JSON.\n"
            "Use Pydantic v2 syntax. Singleton JourneyNexus via `_get_nexus()`. "
            "Lazy service init with try/except. Use `from __future__ import annotations`. "
            "Return ONLY the file in a single ```python fenced block. No prose."
        ),
        "user": (
            "Write the FastAPI router as specified. Use the existing patterns from "
            "/home/mike-anderson/dev/cohezion/src/cohezion/api/journeys.py (router = APIRouter, "
            "logger, try/except in handlers). For SSE, generate `data: <json>\\n\\n` lines. "
            "Add proper error handling: HTTPException(404) for missing journey, HTTPException(500) "
            "for backend errors. The Pydantic models (OmniChatRequest) at the top. "
            "The `quadrature` endpoint must accept `mode` as a Query param. "
            "The narrate endpoint must accept `with_image` as a Query param. "
            "No prose, just the file."
        ),
    },
    "5": {
        "title": "EVOField.tsx (Three.js EVO scatter for the dashboard)",
        "target": "src/web/anima_dashboard/src/components/nexus/EVOField.tsx",
        "system": (
            "You are a senior React + Three.js engineer on the Cohezion platform. "
            "Read /home/mike-anderson/dev/cohezion/src/web/anima_dashboard/src/components/FlumeNavigator.tsx "
            "for the existing Three.js + R3F pattern. "
            "Produce /home/mike-anderson/dev/cohezion/src/web/anima_dashboard/src/components/nexus/EVOField.tsx. "
            "Component: `function EVOField({ events }: { events: EVOEvent[] }): JSX.Element`. "
            "Renders a Three.js `<Canvas>` with `<points>` from the events. Each event projects its "
            "z_256[0..3] to (x, y, z) on [-3, 3]. Color by voice: architect=cyan, engineer=orange, "
            "ethicist=violet, resource=green, unknown=white. Size = 0.05 + score*0.1. "
            "Add a translucent HIHO halo at (0.5, 0.5, 0.5) via `<mesh><sphereGeometry/><meshBasicMaterial "
            "color='gold' transparent opacity={0.15} /></mesh>`. Use TypeScript strict mode. "
            "No `any` types. Export the EVOEvent type. Return ONLY the file in a single ```tsx fenced block. No prose."
        ),
        "user": (
            "Write the EVOField component. Use `@react-three/fiber` and `@react-three/drei` "
            "if available; fall back to plain Three.js if not. The component should accept a list "
            "of EVOEvent-shaped objects and render a scatter. Import the EVOEvent type from "
            "`../hooks/useEVOStream` (the operator will create that hook separately). "
            "Wrap the Canvas in a fixed-aspect container. No prose, just the file."
        ),
    },
    "6": {
        "title": "QuadraturePanel.tsx (4-voice response cards)",
        "target": "src/web/anima_dashboard/src/components/nexus/QuadraturePanel.tsx",
        "system": (
            "You are a senior React/TypeScript engineer. "
            "Produce /home/mike-anderson/dev/cohezion/src/web/anima_dashboard/src/components/nexus/QuadraturePanel.tsx. "
            "Component: `function QuadraturePanel({ journeyId }: { journeyId: string }): JSX.Element`. "
            "Fetches `/api/journey-nexus/quadrature/{journeyId}?mode=...` on mount and on mode change. "
            "Displays: a top banner with approved=true/false, consensus score, alignment score; "
            "four voice cards (Architect/Engineer/Ethicist/Resource) with approval bar (0-1), "
            "concerns list, recommendations list. Mode toggle: preflight ↔ full. "
            "Use Tailwind. Use `useState` + `useEffect` for the fetch. TypeScript strict. No `any`. "
            "Return ONLY the file in a single ```tsx fenced block. No prose."
        ),
        "user": (
            "Write the QuadraturePanel component. Define the QuadratureOutcome TypeScript interface "
            "inline (matching the Python dataclass: approved: bool, consensus_score: number, "
            "alignment_score: number, voice_responses: {voice, approval_score, concerns, recommendations}[], "
            "rejection_reason?: string). Use Tailwind for styling (rounded cards, color-coded by voice). "
            "The mode toggle is a two-button pill at the top. No prose, just the file."
        ),
    },
    "7": {
        "title": "NarratePanel.tsx (TTS playback + image carousel)",
        "target": "src/web/anima_dashboard/src/components/nexus/NarratePanel.tsx",
        "system": (
            "You are a senior React/TypeScript engineer. "
            "Produce /home/mike-anderson/dev/cohezion/src/web/anima_dashboard/src/components/nexus/NarratePanel.tsx. "
            "Component: `function NarratePanel({ journeyId }: { journeyId: string }): JSX.Element`. "
            "Fetches `/api/journey-nexus/narrate/{journeyId}?with_image=true` on mount. "
            "Renders: the text in a styled blockquote, an HTML5 `<audio controls>` element with "
            "`src='data:audio/mpeg;base64,' + audio_b64`, a horizontal image carousel if image_b64 is set "
            "(`<img src='data:image/png;base64,' + image_b64 />`), a per-segment coherence timeline "
            "(sparkline from `trajectory[].coherence` if the loader returns it; otherwise a simple line "
            "showing 0.5). TypeScript strict. No `any`. Use Tailwind. "
            "Return ONLY the file in a single ```tsx fenced block. No prose."
        ),
        "user": (
            "Write the NarratePanel component. Define the NarrateResult interface inline. "
            "Use a single useEffect to fetch on mount. Display a loading state while fetching. "
            "The audio element should be controlled with autoplay disabled. "
            "The image carousel is a single `<img>` for now (no need for prev/next buttons). "
            "No prose, just the file."
        ),
    },
    "8": {
        "title": "AskOmni.tsx (chat box → OmniTier)",
        "target": "src/web/anima_dashboard/src/components/nexus/AskOmni.tsx",
        "system": (
            "You are a senior React/TypeScript engineer. "
            "Produce /home/mike-anderson/dev/cohezion/src/web/anima_dashboard/src/components/nexus/AskOmni.tsx. "
            "Component: `function AskOmni({ journeyId }: { journeyId: string }): JSX.Element`. "
            "Renders a scrollable message list + a textarea + a Send button. On Send, POSTs to "
            "`/api/journey-nexus/omni/{journeyId}` with `{'message': text}`. Displays the response: "
            "text in a bubble, audio as `<audio controls src='data:audio/mpeg;base64,...'>`, "
            "images as `<img src='data:image/png;base64,...' />`, and a tool-call log "
            "(tool_name, arguments, artefact_kind). TypeScript strict. No `any`. Use Tailwind. "
            "Return ONLY the file in a single ```tsx fenced block. No prose."
        ),
        "user": (
            "Write the AskOmni component. Use a simple `messages: Array<{role: 'user'|'assistant', text, audio_b64?, images_b64?, tool_calls?}>` "
            "state. Disable Send when input is empty. Show a typing indicator while POST is in flight. "
            "The tool-call log appears as a collapsible `<details>` per message. "
            "No prose, just the file."
        ),
    },
    "9": {
        "title": "useEVOStream.ts (SSE consumer hook)",
        "target": "src/web/anima_dashboard/src/hooks/useEVOStream.ts",
        "system": (
            "You are a senior React/TypeScript engineer. "
            "Produce /home/mike-anderson/dev/cohezion/src/web/anima_dashboard/src/hooks/useEVOStream.ts. "
            "Hook: `function useEVOStream(journeyId?: string): { events: EVOEvent[]; connected: boolean; "
            "error: string | null }`. Uses `useEffect` + `EventSource('/api/journey-nexus/stream/evo')`. "
            "On message, appends parsed JSON to events state. Reconnects on error with exponential "
            "backoff (1s, 2s, 4s, max 30s). Filters by journeyId if provided. Exports EVOEvent type. "
            "TypeScript strict. No `any`. Return ONLY the file in a single ```tsx fenced block. No prose."
        ),
        "user": (
            "Write the useEVOStream hook. The hook should cap events at 1000 to avoid memory blow-up. "
            "If EventSource is not available in the env, fall back to polling "
            "`/api/journey-nexus/evo/snapshot` every 5s. "
            "No prose, just the file."
        ),
    },
    "10": {
        "title": "journey-nexus/page.tsx (the main dashboard page)",
        "target": "src/web/anima_dashboard/src/app/journey-nexus/page.tsx",
        "system": (
            "You are a senior React/TypeScript engineer. "
            "Read /home/mike-anderson/dev/cohezion/src/web/anima_dashboard/src/app/page.tsx for the "
            "layout style and existing tab patterns. Produce "
            "/home/mike-anderson/dev/cohezion/src/web/anima_dashboard/src/app/journey-nexus/page.tsx. "
            "Page with: a header (title, journey selector dropdown populated from "
            "`/api/journeys` list), five tabs (EVO Stream, FLUME Field, Quadrature, Narrate, Ask). "
            "Each tab renders the corresponding component. State: selectedJourneyId (default to first "
            "in list). The EVO Stream tab uses useEVOStream(selectedJourneyId). "
            "TypeScript strict. No `any`. Use Tailwind. Use `'use client'` directive (Next.js App Router). "
            "Return ONLY the file in a single ```tsx fenced block. No prose."
        ),
        "user": (
            "Write the page. The five tabs route to the five component imports "
            "(`EVOField`, `QuadraturePanel`, `NarratePanel`, `AskOmni`, and a simple FLUME field "
            "that reuses EVOField with no event filter). The journey selector is a `<select>` "
            "at the top. The page is the Next.js client component, so add 'use client' at top. "
            "No prose, just the file."
        ),
    },
}


# --- Driver core ------------------------------------------------------------


_CODE_FENCE_RE = re.compile(
    r"```(?:python|tsx|typescript|ts|py)?\s*\n(.*?)```",
    flags=re.DOTALL,
)


def _extract_code(text: str) -> str | None:
    """Pull the first ```python or ```tsx fenced code block out of the response."""
    match = _CODE_FENCE_RE.search(text)
    if not match:
        return None
    return match.group(1).rstrip() + "\n"


def submit_chunk(chunk_id: str, *, dry_run: bool = False, timeout_s: float = 300.0) -> dict:
    """Submit a chunk to the local Omni planner and return the parse/write result."""
    if chunk_id not in CHUNKS:
        raise SystemExit(f"Unknown chunk: {chunk_id!r}. Valid: {sorted(CHUNKS)}")

    spec = CHUNKS[chunk_id]
    target = REPO_ROOT / spec["target"]

    if dry_run:
        return {
            "chunk": chunk_id,
            "title": spec["title"],
            "target": str(target),
            "system_preview": spec["system"][:200],
            "user_preview": spec["user"][:200],
            "dry_run": True,
        }

    payload = {
        "model": PLANNER_MODEL,
        "messages": [
            {"role": "system", "content": spec["system"]},
            {"role": "user", "content": spec["user"]},
        ],
        "max_tokens": 16384,
        "temperature": 0.0,
        # Qwen3.6 thinking mode burns tokens silently into `reasoning_content`,
        # leaving `content` empty with finish_reason=length. For code generation
        # we want the direct answer, not a thinking trace.
        "chat_template_kwargs": {"enable_thinking": False},
    }

    start = time.perf_counter()
    try:
        resp = httpx.post(OMNI_BASE, json=payload, timeout=timeout_s)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        return {
            "chunk": chunk_id,
            "status": "planner_error",
            "error": f"{type(exc).__name__}: {exc}",
            "elapsed_s": time.perf_counter() - start,
        }

    elapsed = time.perf_counter() - start
    body = resp.json()
    msg = body["choices"][0]["message"]
    content = msg.get("content", "")
    timings = body.get("timings", {})

    code = _extract_code(content)
    if code is None:
        return {
            "chunk": chunk_id,
            "status": "no_code_block",
            "raw_first_500": content[:500],
            "elapsed_s": elapsed,
            "predicted_tps": timings.get("predicted_per_second"),
        }

    # Write the file
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(code)

    return {
        "chunk": chunk_id,
        "title": spec["title"],
        "status": "ok",
        "file": str(target),
        "lines": code.count("\n"),
        "bytes": len(code),
        "elapsed_s": elapsed,
        "predicted_tps": timings.get("predicted_per_second"),
        "draft_n": timings.get("draft_n"),
        "draft_n_accepted": timings.get("draft_n_accepted"),
        "draft_acceptance_pct": (
            round(100 * timings["draft_n_accepted"] / timings["draft_n"], 1)
            if timings.get("draft_n")
            else None
        ),
    }


def submit_raw(target: str, prompt: str, *, system: str = "", timeout_s: float = 300.0) -> dict:
    """Ad-hoc code generation: pass any file path and a single prompt."""
    target_path = REPO_ROOT / target
    payload = {
        "model": PLANNER_MODEL,
        "messages": [
            {"role": "system", "content": system or "You are a senior engineer. Return ONLY a single fenced code block (```python or ```tsx). No prose."},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 16384,
        "temperature": 0.0,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    start = time.perf_counter()
    resp = httpx.post(OMNI_BASE, json=payload, timeout=timeout_s)
    resp.raise_for_status()
    elapsed = time.perf_counter() - start
    msg = resp.json()["choices"][0]["message"]
    code = _extract_code(msg.get("content", ""))
    if code is None:
        return {"status": "no_code_block", "raw": msg.get("content", "")[:500], "elapsed_s": elapsed}
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(code)
    return {
        "status": "ok",
        "file": str(target_path),
        "lines": code.count("\n"),
        "bytes": len(code),
        "elapsed_s": elapsed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chunk", help="Submit a chunk by id (1-10)")
    parser.add_argument("--dry-run", action="store_true", help="Show the prompt, don't send")
    parser.add_argument("--list", action="store_true", help="List available chunks and exit")
    parser.add_argument("--raw", action="store_true", help="Raw mode (use --file and --prompt)")
    parser.add_argument("--file", help="Target file path (relative to repo root, for --raw)")
    parser.add_argument("--prompt", help="User prompt (for --raw)")
    parser.add_argument("--system", default="", help="System prompt (for --raw)")
    args = parser.parse_args()

    if args.list:
        print(json.dumps({k: v["title"] for k, v in CHUNKS.items()}, indent=2))
        return 0

    if args.raw:
        if not args.file or not args.prompt:
            print("--raw requires --file and --prompt", file=sys.stderr)
            return 1
        result = submit_raw(args.file, args.prompt, system=args.system)
        print(json.dumps(result, indent=2))
        return 0 if result.get("status") == "ok" else 1

    if args.chunk:
        result = submit_chunk(args.chunk, dry_run=args.dry_run)
        print(json.dumps(result, indent=2))
        return 0 if result.get("status") in ("ok", None) else 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
