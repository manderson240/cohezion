"""Which local models can be TRUSTED as verifiers? Overnight calibration, $0.

WHY
---
This session repeatedly used a local lane to check claims, and repeatedly hedged about
whether that was sound:
  * a Gemma-4-E4B lane reviewed 6 port-classification sites and agreed with me 6/6 -- I
    flagged that agreement is weaker evidence than divergence, but never measured it;
  * bus intel from coherence-fhr says the Qwen3 family FABRICATES under find-defects
    mandates (Qwen3-8B and Qwen3-Coder-30B), treated as a family trait;
  * vault skills warn CHECK THE QUANT and that locals narrate exhaustively rather than judge.
All of that is folklore until measured against ground truth.

GROUND TRUTH (the part that makes this falsifiable)
---------------------------------------------------
Today's research produced 49 claims verified by REGEX against their source documents --
not by a model. Those are the SUPPORTED cases. The REFUTED cases are mutations of the same
facts (a changed number, a swapped name), and each mutation is itself regex-verified ABSENT
from the source. So both labels are deterministic and no model authored either side.

A model that answers SUPPORTED on a regex-absent mutation is fabricating agreement. That is
exactly the failure mode that makes a verifier worthless, and it is what this measures.

METRICS / GATES (declared before running)
-----------------------------------------
  false_support_rate  = P(says SUPPORTED | truth REFUTED)   <- the fabrication metric
  false_refute_rate   = P(says REFUTED  | truth SUPPORTED)
  parse_failure_rate  = unparseable / no verdict
  accuracy            = correct / parsed

  USABLE AS VERIFIER iff false_support_rate < 0.10 AND parse_failure_rate < 0.10

A model that always says REFUTED scores false_support_rate = 0 but is useless, so
false_refute_rate is reported alongside and a degenerate constant answerer is flagged.

FLEET DISCIPLINE
----------------
max_loaded_models is 3 and other sessions share this box. Models are run SERIALLY -- one
model, all claims, then hand over -- per the exclusive-slot lesson (interleaving thrashes
the slot with 13-37 s swaps). Every call is wrapped and checkpointed to JSONL so an
overnight run survives a wedged model, and resumes instead of restarting.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path


ROUTER = "http://localhost:13305/v1/chat/completions"
OUT_DIR = Path("/tmp/claude-1000/verifier_gauntlet")
CHECKPOINT = OUT_DIR / "results.jsonl"
CLAIMS_FILE = OUT_DIR / "claims.json"

MODELS = [
    "Gemma-4-E4B-it-GGUF",  # relied on for every research lane today — calibrate first
    "Qwen3.6-35B-A3B-MTP-GGUF",  # resident; Qwen family predicted to fabricate
    "DeepSeek-Qwen3-8B-GGUF",  # resident
    "Gemma-4-31B-it-GGUF",  # resident (shared with another session)
]

SOURCES = {
    "insum": "/tmp/claude-1000/-home-mike-anderson-dev-cohezion/"
    "77b9f9d6-a892-437e-8955-a03417eee46a/scratchpad/sources/insum.txt",
    "qlora": "/tmp/claude-1000/-home-mike-anderson-dev-cohezion/"
    "77b9f9d6-a892-437e-8955-a03417eee46a/scratchpad/sources/qlora.txt",
    "smolvla": "/tmp/claude-1000/smolvla.txt",
    "aicodeguide": "/tmp/claude-1000/aicodeguide.md",
}

# (doc, true_fact, mutated_fact) — true must be PRESENT, mutation must be ABSENT.
# Facts are drawn from today's regex-verified sets (13/13, 15/15, 21/21).
FACT_PAIRS = [
    ("insum", "GroupCOO", "GroupCSR"),
    ("insum", "BlockGroupCOO", "BlockGroupELL"),
    ("insum", "tl.dot", "tl.matmul"),
    ("insum", "TorchSparse", "TorchDense"),
    ("insum", "cuSPARSE", "cuDENSE"),
    ("insum", "Tensor Core", "Vector Core"),
    ("insum", "TorchInductor", "TorchDeductor"),
    ("insum", "Structured SpMM", "Structured SpGEMM"),
    ("qlora", "adamw_8bit", "adamw_4bit"),
    ("qlora", "load_in_4bit", "load_in_3bit"),
    ("qlora", "gate_proj", "gateway_proj"),
    ("qlora", "lora_alpha=16", "lora_alpha=64"),
    ("qlora", "max_steps=30", "max_steps=90"),
    ("qlora", "2e-4", "7e-4"),
    ("qlora", "Qwen2.5-1.5B-Instruct", "Qwen2.5-7.5B-Instruct"),
    ("qlora", "unsloth", "unstitch"),
    ("smolvla", "LIBERO", "LIBERIA"),
    ("smolvla", "Meta-World", "Meta-Realm"),
    ("smolvla", "SmolVLM-2", "SmolVLM-9"),
    ("smolvla", "flow matching", "flux matching"),
    ("smolvla", "OpenVLA", "OpenVLX"),
    ("smolvla", "action chunk", "action shard"),
    ("smolvla", "0.45B", "0.85B"),
    ("smolvla", "Octo", "Octavia"),
    ("aicodeguide", "docs/specs.md", "docs/blueprint.md"),
    ("aicodeguide", "AGENTS.md", "ROBOTS.md"),
    ("aicodeguide", "docs/todo.md", "docs/backlog.md"),
    ("aicodeguide", "Model Context Protocol", "Machine Context Protocol"),
    ("aicodeguide", "Aider", "Aidra"),
    ("aicodeguide", "Playwright", "Playmaker"),
]

# Thinking-model budget trap (hit during the smoke test, skill:
# thinking-model-token-budget-gate-trap). Gemma-4 streams a chain-of-thought block first;
# at 160 tokens it was truncated BEFORE emitting any verdict, scoring UNPARSED. That would
# have inflated parse_failure for every thinking model — a measurement artefact, not a model
# property. Two independent mitigations: ask the server to suppress reasoning, AND give a
# budget well clear of the cliff in case a model ignores the flag.
MAX_TOKENS = 1200
TIMEOUT_S = 180
DELAY_S = 1.0  # be gentle on a shared router
EXCERPT_CHARS = 5000
GATE_FALSE_SUPPORT = 0.10
GATE_PARSE_FAILURE = 0.10


def excerpt_around(text: str, needle: str, width: int = EXCERPT_CHARS) -> str:
    i = text.find(needle)
    if i < 0:
        i = len(text) // 2
    lo = max(0, i - width // 2)
    return text[lo : lo + width]


def build_claims() -> list[dict]:
    """Both labels regex-derived. A pair is dropped unless truth AND mutation both check out."""
    claims, dropped = [], []
    for doc, true_fact, mutated in FACT_PAIRS:
        text = Path(SOURCES[doc]).read_text()
        if true_fact not in text:
            dropped.append((doc, true_fact, "TRUE FACT ABSENT"))
            continue
        if mutated in text:
            dropped.append((doc, mutated, "MUTATION PRESENT — not a valid negative"))
            continue
        ex = excerpt_around(text, true_fact)
        if true_fact not in ex:
            dropped.append((doc, true_fact, "fact outside excerpt window"))
            continue
        claims.append({"doc": doc, "claim": true_fact, "truth": "SUPPORTED", "excerpt": ex})
        claims.append({"doc": doc, "claim": mutated, "truth": "REFUTED", "excerpt": ex})
    if dropped:
        print(f"dropped {len(dropped)} invalid pairs:")
        for d in dropped:
            print("   ", d)
    return claims


PROMPT = (
    "You are a strict fact-checker. Decide whether the SOURCE EXCERPT contains the exact "
    "term or value in the CLAIM.\n\n"
    "Answer with EXACTLY one word on the first line: SUPPORTED or REFUTED.\n"
    "SUPPORTED = the exact term/value appears in the excerpt.\n"
    "REFUTED = it does not appear. Do not infer, do not accept near-matches.\n\n"
    "CLAIM: {claim}\n\n=== SOURCE EXCERPT ===\n{excerpt}\n=== END EXCERPT ===\n"
)


def ask(model: str, claim: dict) -> dict:
    body = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": PROMPT.format(**claim)}],
            "max_tokens": MAX_TOKENS,
            "temperature": 0.0,
            # Keeps the answer in `content` instead of streaming it all into
            # `reasoning_content` (defect 4dd925b0081f). Harmless on models that ignore it.
            "reasoning_format": "none",
        }
    ).encode()
    req = urllib.request.Request(  # noqa: S310
        ROUTER, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:  # noqa: S310 (localhost)
            payload = json.loads(r.read())
        msg = payload["choices"][0]["message"]
        text = (msg.get("content") or "") or (msg.get("reasoning_content") or "")
        err = None
    except (urllib.error.URLError, OSError, KeyError, ValueError, TimeoutError) as e:
        text, err = "", f"{type(e).__name__}: {e}"
    dt = round(time.perf_counter() - t0, 2)

    up = text.upper()
    # Take the FIRST verdict token that appears — a model that hedges then commits still
    # gets scored on its commitment, but "SUPPORTED" buried after "REFUTED" is not a pass.
    pos_s, pos_r = up.find("SUPPORTED"), up.find("REFUTED")
    if pos_s < 0 and pos_r < 0:
        verdict = "UNPARSED"
    elif pos_s < 0:
        verdict = "REFUTED"
    elif pos_r < 0:
        verdict = "SUPPORTED"
    else:
        verdict = "SUPPORTED" if pos_s < pos_r else "REFUTED"

    return {
        "model": model,
        "doc": claim["doc"],
        "claim": claim["claim"],
        "truth": claim["truth"],
        "verdict": verdict,
        "seconds": dt,
        "error": err,
        "raw": text[:220],
    }


def load_done() -> set[tuple[str, str, str]]:
    done = set()
    if CHECKPOINT.exists():
        for line in CHECKPOINT.read_text().splitlines():
            try:
                r = json.loads(line)
                done.add((r["model"], r["doc"], r["claim"]))
            except (json.JSONDecodeError, KeyError):
                continue
    return done


def summarise() -> None:
    rows = [json.loads(x) for x in CHECKPOINT.read_text().splitlines() if x.strip()]
    print("\n" + "=" * 92)
    print(
        f"{'model':30s} {'n':>4} {'acc':>7} {'falseSUP':>9} {'falseREF':>9} {'unparsed':>9} {'s/call':>7}"
    )
    print("=" * 92)
    for model in MODELS:
        rs = [r for r in rows if r["model"] == model]
        if not rs:
            continue
        n = len(rs)
        unparsed = sum(r["verdict"] == "UNPARSED" for r in rs)
        neg = [r for r in rs if r["truth"] == "REFUTED"]
        pos = [r for r in rs if r["truth"] == "SUPPORTED"]
        fs = sum(r["verdict"] == "SUPPORTED" for r in neg) / max(1, len(neg))
        fr = sum(r["verdict"] == "REFUTED" for r in pos) / max(1, len(pos))
        parsed = [r for r in rs if r["verdict"] != "UNPARSED"]
        acc = sum(r["verdict"] == r["truth"] for r in parsed) / max(1, len(parsed))
        spc = sum(r["seconds"] for r in rs) / n
        pf = unparsed / n
        usable = fs < GATE_FALSE_SUPPORT and pf < GATE_PARSE_FAILURE
        degenerate = len({r["verdict"] for r in parsed}) == 1
        flag = "USABLE" if usable else "NOT-USABLE"
        if degenerate:
            flag += " (DEGENERATE: one answer for everything)"
        print(f"{model:30s} {n:4d} {acc:7.3f} {fs:9.3f} {fr:9.3f} {pf:9.3f} {spc:7.1f}  {flag}")
    print("=" * 92)
    print(f"gates: false_support < {GATE_FALSE_SUPPORT}, parse_failure < {GATE_PARSE_FAILURE}")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    claims = build_claims()
    CLAIMS_FILE.write_text(json.dumps(claims, indent=2))
    n_pos = sum(c["truth"] == "SUPPORTED" for c in claims)
    print(
        f"claim set: {len(claims)} ({n_pos} SUPPORTED / {len(claims) - n_pos} REFUTED), "
        f"all labels regex-derived"
    )

    done = load_done()
    if done:
        print(f"resuming — {len(done)} results already checkpointed")

    with CHECKPOINT.open("a") as fh:
        for model in MODELS:  # SERIAL by model: never interleave, the slot thrashes
            todo = [c for c in claims if (model, c["doc"], c["claim"]) not in done]
            if not todo:
                print(f"[{model}] already complete")
                continue
            print(f"[{model}] {len(todo)} claims", flush=True)
            for i, c in enumerate(todo, 1):
                rec = ask(model, c)
                fh.write(json.dumps(rec) + "\n")
                fh.flush()
                if i % 10 == 0 or rec["error"]:
                    print(
                        f"  {model} {i}/{len(todo)}  last={rec['verdict']} "
                        f"{rec['seconds']}s err={rec['error']}",
                        flush=True,
                    )
                time.sleep(DELAY_S)

    summarise()


if __name__ == "__main__":
    main()
