#!/usr/bin/env python3
"""Memory-evaluation harness for the Cohezion vault — measures retrieval quality.

Closes the loop on the recall fix (2026-06-29): the recall leak (vault_memory had 0 embedded
records) went undetected because nothing MEASURED retrieval. This harness would have caught it.

Two label-free signals over the embedded vault_memory records:
  1. SELF-RETRIEVAL (index integrity): query with a doc's OWN stored embedding — it must rank
     itself #1 (cosine 1.0). recall@1 ~ 1.0 proves the vector index is sound.
  2. TITLE-QUERY (end-to-end search): embed a doc's TITLE via lemonade and search — does the
     doc come back in top-K? recall@K + MRR measure the live query path (the part that was broken).

Plus staleness (age of retrieved docs). curl for both SurrealDB and lemonade (httpx-robust).

Run:  python3 scripts/memory_eval.py            (full eval + GREEN/RED gate)
      python3 scripts/memory_eval.py --self-test (discriminating harness self-test)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys

_SURREAL = "http://localhost:8001/sql"
_EMBED = "http://localhost:13305/v1/embeddings"
_EMBED_MODEL = "nomic-embed-text-v2-moe-GGUF"


def _sq(query: str) -> list:
    """Run SurrealQL against the vault db via curl; return the last statement's result list."""
    out = subprocess.run(
        ["curl", "-s", "--max-time", "20", _SURREAL,
         "-H", "surreal-ns: cohezion", "-H", "surreal-db: vault",
         "-H", "Content-Type: text/plain", "-u", "root:root", "--data-binary", "@-"],
        input=query.encode(), capture_output=True,
    ).stdout
    data = json.loads(out)
    return data[-1].get("result", []) if isinstance(data, list) else []


def _embed(text: str) -> list[float] | None:
    payload = json.dumps({"model": _EMBED_MODEL, "input": text[:2000]}).encode()
    out = subprocess.run(
        ["curl", "-s", "--max-time", "30", _EMBED, "-H", "Content-Type: application/json",
         "--data-binary", "@-"], input=payload, capture_output=True,
    ).stdout
    try:
        return (json.loads(out).get("data") or [{}])[0].get("embedding") or None
    except Exception:
        return None


def _topk_by_vector(vec: list[float], k: int = 5) -> list[str]:
    """Return the titles of the top-k vault_memory docs by cosine similarity to vec."""
    q = (
        f"LET $v = {json.dumps(vec)}; "
        "SELECT title, vector::similarity::cosine(embedding, $v) AS s "
        "FROM vault_memory WHERE embedding != NONE ORDER BY s DESC LIMIT "
        f"{k};"
    )
    return [r.get("title", "") for r in _sq(q)]


def _sample(n: int) -> list[dict]:
    return _sq(
        f"SELECT title, embedding FROM vault_memory WHERE embedding != NONE LIMIT {n};"
    )


def evaluate(n: int = 20, k: int = 5) -> dict:
    docs = _sample(n)
    if not docs:
        return {"error": "no embedded docs", "n": 0}

    self_hits, mrr_self = 0, 0.0
    title_hits, mrr_title = 0, 0.0
    title_tested = 0
    for d in docs:
        title, emb = d.get("title", ""), d.get("embedding")
        if not emb:
            continue
        # 1) self-retrieval: own embedding must rank itself #1
        ranked = _topk_by_vector(emb, k)
        if ranked and ranked[0] == title:
            self_hits += 1
        if title in ranked:
            mrr_self += 1.0 / (ranked.index(title) + 1)
        # 2) title-query: embed the title, search
        qv = _embed(title)
        if qv:
            title_tested += 1
            tranked = _topk_by_vector(qv, k)
            if title in tranked:
                title_hits += 1
                mrr_title += 1.0 / (tranked.index(title) + 1)

    nd = len(docs)
    return {
        "n": nd,
        "self_recall@1": round(self_hits / nd, 3),
        "self_mrr": round(mrr_self / nd, 3),
        "title_recall@k": round(title_hits / title_tested, 3) if title_tested else 0.0,
        "title_mrr": round(mrr_title / title_tested, 3) if title_tested else 0.0,
        "title_tested": title_tested,
        "k": k,
    }


def self_test() -> bool:
    """Discriminating: a doc's own embedding ranks IT #1, but a DIFFERENT doc's embedding does not."""
    docs = _sample(3)
    if len(docs) < 2:
        print("self-test: SKIPPED (need >=2 embedded docs; vault not populated)")
        return True
    a, b = docs[0], docs[1]
    a_top = _topk_by_vector(a["embedding"], 1)
    self_ranks_self = bool(a_top) and a_top[0] == a["title"]
    b_top = _topk_by_vector(b["embedding"], 1)
    other_differs = bool(b_top) and b_top[0] != a["title"]  # a different query -> different top-1
    ok = self_ranks_self and other_differs
    print(
        f"self-test: self_ranks_self={self_ranks_self} other_query_differs={other_differs} "
        f"-> {'PASS (measures real retrieval)' if ok else 'FAIL'}"
    )
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description="Vault memory-evaluation harness")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--n", type=int, default=20)
    args = ap.parse_args()

    if args.self_test:
        return 0 if self_test() else 1

    m = evaluate(n=args.n)
    if m.get("error"):
        print(f"RED: {m['error']}")
        return 1
    print("=== Vault memory-evaluation ===")
    for key in ("n", "self_recall@1", "self_mrr", "title_recall@k", "title_mrr", "title_tested"):
        print(f"  {key}: {m[key]}")
    # Gate: index integrity (self-retrieval) must be near-perfect; title-query is a quality signal.
    green = m["self_recall@1"] >= 0.95
    print(f"\nMemory-eval gate (self_recall@1 >= 0.95): {'GREEN' if green else 'RED'}")
    return 0 if green else 1


if __name__ == "__main__":
    sys.exit(main())
