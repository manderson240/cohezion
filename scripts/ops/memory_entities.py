"""Deterministic entity linking for the memory corpus: `mentions` and `co_mentions` edges.

No LLM. A backticked token becomes an edge endpoint ONLY if it resolves exactly to something that
exists (a repo file, a python module, a skill, another memory node). Ambiguous tokens (a basename
shared by several files) are counted and dropped, never guessed. Every edge carries the sentence it
came from, so a wrong edge is traceable to its evidence.

Compounding: the resolved endpoints are what make the cue-gated extractor (memory_facts.py) cheap
and precise — its only worthwhile input is a sentence holding TWO resolved entities. Three edge
strengths result: mem_mentions (file->entity), mem_co_mentions (entity~entity in one sentence),
and — from memory_facts — asserts (cue-verified relation).

Usage: python scripts/ops/memory_entities.py [--write] [--who-mentions TOKEN]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import urllib.request
from base64 import b64encode
from itertools import combinations
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent))
from memory_facts import MEM, norm, sentences


REPO = Path("/home/mike-anderson/dev/cohezion")
SKILL_DIRS = (
    Path("/home/mike-anderson/.claude/skills"),
    Path("/home/mike-anderson/vaults/cohezion-vault/skills"),
)
SQL = "http://localhost:8001/sql"
_SPAN = re.compile(r"`([^`\n]{2,100})`")


def slug(text: str) -> str:
    return re.sub(r"\W+", "_", text.strip().lower()).strip("_")


class Resolver:
    """Exact-match resolver. ``resolve`` returns (kind, canonical) or None; never guesses."""

    def __init__(self, memory_stems: set[str], skills: set[str], repo_files: set[str]) -> None:
        self.memory = {slug(m): m for m in memory_stems}
        self.skills = {slug(k): k for k in skills}
        self.files = repo_files
        self.by_base: dict[str, list[str]] = {}
        for f in repo_files:
            self.by_base.setdefault(Path(f).name.lower(), []).append(f)
        self.ambiguous = 0

    def resolve(self, token: str) -> tuple[str, str] | None:
        parts = token.strip().split()
        if not parts:
            return None
        t = parts[0].strip("()[],.:;'\"").removeprefix("./").removesuffix("()")
        if not t:
            return None
        if t in self.files:
            return "file", t
        dotted = t.replace(".", "/")
        for cand in (f"{dotted}.py", f"src/{dotted}.py"):
            if cand in self.files:
                return "module", cand
        if "." in Path(t).name or "/" not in t:
            hits = self.by_base.get(Path(t).name.lower(), [])
            if len(hits) == 1 and "." in Path(t).name:
                return "file", hits[0]
            if len(hits) > 1 and "." in Path(t).name:
                self.ambiguous += 1
                return None
        if slug(t) in self.memory:
            return "memory", self.memory[slug(t)]
        if slug(t) in self.skills:
            return "skill", self.skills[slug(t)]
        return None


def node_id(stem: str) -> str:
    """Record-id tail for a memory node — MUST match index_memory.py (case is preserved)."""
    return re.sub(r"[^A-Za-z0-9_]", "_", stem)


def entity_id(kind: str, canonical: str) -> str:
    return (
        f"memory:{node_id(canonical)}"
        if kind == "memory"
        else f"graph_entity:{kind}_{slug(canonical)}"
    )


def edges_for(source: str, text: str, resolver: Resolver) -> tuple[list[dict], list[dict]]:
    """(mentions, co_mentions) for one memory file. ``source`` is the file stem."""
    mentions, co = [], []
    seen: set[tuple[str, str, str]] = set()
    for sent in sentences(text, min_len=8):
        found: dict[str, tuple[str, str]] = {}
        for span in _SPAN.findall(sent):
            hit = resolver.resolve(span)
            if hit and norm(hit[1]) != norm(source):
                found[entity_id(*hit)] = hit
        for eid, (kind, canon) in found.items():
            key = ("m", source, eid + sent)
            if key not in seen:
                seen.add(key)
                mentions.append(
                    {
                        "source": source,
                        "entity": eid,
                        "kind": kind,
                        "canonical": canon,
                        "sentence": sent,
                    }
                )
        for a, b in combinations(sorted(found), 2):
            co.append({"source": source, "a": a, "b": b, "sentence": sent})
    return mentions, co


def edge_key(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def build_resolver() -> Resolver:
    files = set(
        subprocess.run(
            ["git", "-C", str(REPO), "ls-files"], capture_output=True, text=True, check=True
        ).stdout.split("\n")
    ) - {""}
    stems = {p.stem for p in MEM.glob("*.md") if p.name != "MEMORY.md"}
    skills = {p.parent.name for d in SKILL_DIRS if d.exists() for p in d.glob("*/SKILL.md")}
    return Resolver(stems, skills, files)


def surreal(query: str) -> list[dict]:
    req = urllib.request.Request(
        SQL, query.encode(),
        {"surreal-ns": "cohezion", "surreal-db": "main", "Content-Type": "text/plain",
         "Accept": "application/json", "Authorization": "Basic " + b64encode(b"root:root").decode()},
    )  # fmt: skip
    with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310
        return json.load(resp)


def write_edges(mentions: list[dict], co: list[dict], run_id: str, chunk: int = 40) -> int:
    """Idempotent upsert (deterministic edge ids). Returns statement-level ERROR count — the
    HTTP status is 200 even when a statement fails, so every result is inspected."""
    stmts: list[str] = []
    for m in mentions:
        k, src, dst = (
            edge_key("m", m["source"], m["entity"], m["sentence"]),
            node_id(m["source"]),
            m["entity"],
        )
        body = json.dumps(
            {
                "kind": m["kind"],
                "sentence": m["sentence"],
                "run_id": run_id,
                "method": "backtick-exact",
            }
        )
        if dst.startswith("graph_entity:"):
            stmts.append(
                f"UPSERT {dst} CONTENT {json.dumps({'kind': m['kind'], 'canonical': m['canonical']})};"
            )
        stmts.append(
            f"DELETE mem_mentions:⟨{k}⟩; LET $d = {body}; RELATE memory:{src}->mem_mentions:⟨{k}⟩->{dst} CONTENT $d;"
        )
    for c in co:
        k = edge_key("c", c["source"], c["a"], c["b"], c["sentence"])
        body = json.dumps({"source": c["source"], "sentence": c["sentence"], "run_id": run_id})
        stmts.append(
            f"DELETE mem_co_mentions:⟨{k}⟩; LET $d = {body}; RELATE {c['a']}->mem_co_mentions:⟨{k}⟩->{c['b']} CONTENT $d;"
        )
    errors = 0
    for i in range(0, len(stmts), chunk):
        for r in surreal("\n".join(stmts[i : i + chunk])):
            if r.get("status") != "OK":
                errors += 1
                print("statement error:", str(r.get("result") or r)[:300], file=sys.stderr)
    return errors


def who_mentions(token: str, resolver: Resolver) -> list[dict]:
    hit = resolver.resolve(token)
    if not hit:
        return []
    eid = entity_id(*hit)
    rows = surreal(f"SELECT in AS memory, sentence FROM mem_mentions WHERE out = {eid};")[0].get(
        "result", []
    )
    return rows


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--who-mentions")
    args = ap.parse_args(argv)
    resolver = build_resolver()
    if args.who_mentions:
        for r in who_mentions(args.who_mentions, resolver):
            print(f"{r['memory']}: {r['sentence'][:140]}")
        return 0
    mentions, co = [], []
    for path in sorted(MEM.glob("*.md")):
        if path.name != "MEMORY.md":
            m, c = edges_for(path.stem, path.read_text(errors="replace"), resolver)
            mentions += m
            co += c
    kinds: dict[str, int] = {}
    for m in mentions:
        kinds[m["kind"]] = kinds.get(m["kind"], 0) + 1
    print(
        f"mentions={len(mentions)} {kinds} co_mentions={len(co)} ambiguous_dropped={resolver.ambiguous}"
    )
    if args.write:
        errs = write_edges(mentions, co, run_id="entities-v2")
        print(f"written; statement errors={errs}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
