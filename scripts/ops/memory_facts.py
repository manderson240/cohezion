"""Deterministic-first fact extraction for the memory corpus (provenance-carrying candidate edges).

Design (2026-09-29, after a live probe): a local LLM given a closed predicate list returned
schema-valid, verbatim-grounded triples with WRONG predicates ("estimator *contradicts* hotswap",
"calculator *depends_on* dormant"). Verbatim grounding alone therefore proves nothing about the
relation. So the LLM never chooses the predicate: it returns (subject, cue, object), all copied
from ONE sentence, and this module maps the cue to a predicate through a fixed lexicon and checks
the three appear in order. The LLM proposes spans; code decides what they mean.

Output is CANDIDATE facts with full provenance (file, sentence, char offsets, model, run id).
Nothing here writes to ``relates_to``, which stays wikilink-only ground truth.

Usage: python scripts/ops/memory_facts.py [--limit N] [--write]   (default: dry-run to JSONL)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
import time
import urllib.request
from pathlib import Path


MEM = Path("/home/mike-anderson/.claude/projects/-home-mike-anderson-dev-cohezion/memory")
ROUTER = "http://localhost:13305/v1/chat/completions"
MODEL = "Qwen3.6-35B-A3B-MTP-GGUF"

# cue phrase (lowercase, verbatim in the sentence) -> predicate. The ONLY source of predicates.
CUES: dict[str, str] = {
    "consumed by": "consumed_by", "used by": "consumed_by", "called by": "consumed_by",
    "read by": "consumed_by", "consumes": "uses", "uses": "uses", "calls": "uses",
    "implements": "implements", "supersedes": "supersedes", "replaces": "supersedes",
    "replaced by": "replaced_by", "depends on": "depends_on", "requires": "depends_on",
    "verified by": "verified_by", "tested by": "verified_by", "checked by": "verified_by",
    "caused by": "caused_by", "due to": "caused_by", "part of": "part_of",
    "belongs to": "part_of", "contradicts": "contradicts", "conflicts with": "contradicts",
    "resolved by": "resolved_by", "fixed by": "resolved_by", "derived from": "derived_from",
    "generated from": "derived_from",
}  # fmt: skip
_CUE_RE = re.compile(r"\b(?:" + "|".join(sorted(CUES, key=len, reverse=True)) + r")\b")
_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z`\[(*])|\n+")
_STRIP = re.compile(r"[`*_]")


def norm(text: str) -> str:
    """Case/whitespace/markdown-insensitive form used for every verbatim comparison."""
    return re.sub(r"\s+", " ", _STRIP.sub("", text)).strip().lower()


def sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT.split(text) if len(s.strip()) > 20]


def has_cue(sentence: str) -> bool:
    """Cheap pre-filter: a sentence with no lexicon cue cannot yield a verifiable fact."""
    return bool(_CUE_RE.search(norm(sentence)))


def verify(subject: str, cue: str, obj: str, sentence: str) -> str | None:
    """Return the predicate iff subject, cue, object all occur in ``sentence`` in that order.

    Pure and deterministic. None means REJECTED — never a guess.
    """
    s, c, o, hay = norm(subject), norm(cue), norm(obj), norm(sentence)
    predicate = CUES.get(c)
    if not (s and o and predicate) or s == o:
        return None
    i = hay.find(s)
    j = hay.find(c, i + len(s)) if i >= 0 else -1
    k = hay.find(o, j + len(c)) if j >= 0 else -1
    return predicate if k >= 0 else None


_SCHEMA = {
    "type": "object",
    "properties": {"facts": {"type": "array", "items": {
        "type": "object",
        "properties": {"subject": {"type": "string"}, "cue": {"type": "string"},
                       "object": {"type": "string"}},
        "required": ["subject", "cue", "object"]}}},
    "required": ["facts"],
}  # fmt: skip
_PROMPT = (
    "From the SENTENCE, extract relations. For each, copy verbatim: subject (a named thing), "
    "cue (the exact words linking them, e.g. 'consumed by', 'depends on'), object (a named "
    "thing). Subject, cue and object must appear in the sentence in that order. Return an empty "
    "list if the sentence states no such relation. Do not infer.\n\nSENTENCE:\n"
)


def propose(sentence: str, model: str = MODEL, timeout: int = 120) -> list[dict]:
    """Ask the local router for candidate spans. Thinking is OFF: a thinking model burns the
    whole budget in reasoning and returns empty content (finish_reason=length)."""
    body = {
        "model": model, "temperature": 0, "max_tokens": 700,
        "chat_template_kwargs": {"enable_thinking": False},
        "messages": [{"role": "user", "content": _PROMPT + sentence}],
        "response_format": {"type": "json_schema", "json_schema": {
            "name": "facts", "schema": _SCHEMA, "strict": True}},
    }  # fmt: skip
    req = urllib.request.Request(
        ROUTER, json.dumps(body).encode(), {"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        content = json.load(resp)["choices"][0]["message"].get("content") or ""
    try:
        return [f for f in json.loads(content).get("facts", []) if isinstance(f, dict)]
    except json.JSONDecodeError:
        return []


def extract_file(path: Path, run_id: str, model: str = MODEL) -> tuple[list[dict], int]:
    """(verified facts with provenance, number of proposed triples) for one memory file."""
    text = path.read_text(errors="replace")
    body = text.split("\n---", 1)[-1] if text.startswith("---") else text
    verified, proposed = [], 0
    for sent in filter(has_cue, sentences(body)):
        for f in propose(sent, model):
            proposed += 1
            pred = verify(f.get("subject", ""), f.get("cue", ""), f.get("object", ""), sent)
            if pred:
                key = hashlib.sha256(f"{norm(f['subject'])}|{pred}|{norm(f['object'])}".encode())
                verified.append({
                    "id": key.hexdigest()[:16], "subject": f["subject"].strip(), "predicate": pred,
                    "object": f["object"].strip(), "source": path.stem, "sentence": sent,
                    "model": model, "run_id": run_id, "status": "candidate",
                })  # fmt: skip
    return verified, proposed


def placebo_pass_rate(facts: list[dict], seed: int = 0) -> float:
    """Control: re-verify every fact against a DIFFERENT fact's sentence. A gate that can
    discriminate must reject nearly all of them; a high rate means the gate proves nothing."""
    if len(facts) < 2:
        return float("nan")
    rng = random.Random(seed)
    hits = 0
    for f in facts:
        other = rng.choice([g for g in facts if g["sentence"] != f["sentence"]] or facts)
        hits += bool(
            verify(
                f["subject"],
                _cue_for(f),
                f["object"],
                other["sentence"],
            )
        )
    return hits / len(facts)


def _cue_for(fact: dict) -> str:
    """Any lexicon cue that maps to the fact's predicate (used only by the placebo control)."""
    return next(c for c, p in CUES.items() if p == fact["predicate"])


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--out", default="memory_facts.jsonl")
    args = ap.parse_args(argv)
    run_id = time.strftime("%Y%m%dT%H%M%S")
    files = sorted(MEM.glob("*.md"))
    files = [f for f in files if f.name != "MEMORY.md"][: args.limit]
    facts, proposed = [], 0
    for path in files:
        got, n = extract_file(path, run_id)
        facts.extend(got)
        proposed += n
        print(f"{path.stem[:50]:50} proposed={n:3} verified={len(got):3}", flush=True)
    Path(args.out).write_text("\n".join(json.dumps(f) for f in facts) + "\n")
    rate = len(facts) / proposed if proposed else float("nan")
    print(f"TOTAL proposed={proposed} verified={len(facts)} gate_pass={rate:.2%} "
          f"placebo_pass={placebo_pass_rate(facts):.2%} -> {args.out}")  # fmt: skip
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
