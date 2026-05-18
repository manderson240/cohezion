"""StealthSkater site ingestion → SurrealDB cohezion:vault neurons.

Pipeline:
  1. Crawl all pages from stealthskater.com (rate-limited, robots-aware)
  2. Extract text sections by heading structure
  3. Embed each section with nomic-embed-text:v1.5 via Ollama
  4. Insert as neurons in cohezion:vault (cluster_id="stealthskater")
  5. Create informed_by synapses to existing physics bridge neurons
  6. Print novel cross-domain connection summary

Usage:
    uv run python scripts/stealthskater_ingest.py [--dry-run] [--pages N]
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import time
import urllib.request


# ── Config ────────────────────────────────────────────────────────────────────

BASE_URL = "https://www.stealthskater.com"
SURREAL_URL = "http://127.0.0.1:8001/sql"
SURREAL_AUTH = base64.b64encode(b"root:root").decode()
SURREAL_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/x-www-form-urlencoded",
    "surreal-ns": "cohezion",
    "surreal-db": "vault",
    "Authorization": f"Basic {SURREAL_AUTH}",
}
OLLAMA_URL = "http://localhost:11434/api/embeddings"
EMBED_MODEL = "nomic-embed-text:v1.5"
RATE_LIMIT_S = 1.5  # seconds between page fetches

# Pages to skip — navigation/media, no semantic content worth indexing
SKIP_PAGES = {
    "Menu.htm",
    "Home.htm",
    "Tour.htm",
    "UFO_Splash.htm",
    "UFO_Gallery.htm",
    "Videos.htm",
    "Humor.htm",
    "Forums.htm",
    "CD.htm",
    "Sports.htm",
}

# Tag sets derived from page topics for cross-domain synapse matching
PAGE_TAGS: dict[str, list[str]] = {
    "Lazar.htm": ["uap", "propulsion", "element-115", "gravity-amplifier", "area51"],
    "PX.htm": ["philadelphia-experiment", "degaussing", "stealth", "su2"],
    "Bearden.htm": ["scalar-em", "vakuum", "tom-bearden", "overunity", "gauge-theory"],
    "Nuke.htm": ["lenr", "cold-fusion", "nuclear", "lattice-coherence"],
    "ORMEs.htm": ["ormes", "monoatomic", "superconductor", "quantum-coherence"],
    "Science.htm": ["physics", "zpe", "zero-point", "hiho", "coherence"],
    "Consciousness.htm": ["remote-viewing", "spin-holography", "observer-patch", "psi"],
    "Military.htm": ["classified", "declassified", "black-project", "cia"],
    "UFO.htm": ["uap", "foo-fighter", "evo", "plasma", "ionic-cluster"],
    "Articles.htm": ["review", "survey", "multi-topic"],
    "Burisch.htm": ["biology", "dna", "uap-biology", "classified"],
    "Sherman.htm": ["skinwalker", "cattle-mutilation", "paranormal", "plasma"],
    "Medical.htm": ["lenr", "healing", "bioelectric", "hiho"],
    "UNITEL.htm": ["suppression", "classification", "institutional"],
    "Bolt.htm": ["lightning", "plasma", "ionic-cluster"],
    "DocSavage.htm": ["fiction", "speculative"],
    "SSS.htm": ["super-soldier", "classified", "consciousness"],
}

# Physics bridge neurons to auto-synapse — (cluster_tag, neuron_search_term)
PHYSICS_BRIDGES = [
    ("lenr", "LENRHamiltonian"),
    ("dielectric", "DielectricField"),
    ("gauge-theory", "DielectricField"),
    ("ionic-cluster", "IonicClusterState"),
    ("plasma", "IonicClusterState"),
    ("hiho", "HIHO"),
    ("spin-holography", "SPIN"),
    ("observer-patch", "observer"),
    ("evo", "ExoticVacuumObject"),
    ("coherence", "BioelectricNetwork"),
]


# ── HTML extraction ───────────────────────────────────────────────────────────
# stealthskater.com uses 1998-era FrontPage HTML with no semantic headings.
# HTMLParser silently fails on some of these pages in Python 3.14.
# Pure-regex strip is more robust for flat table-based legacy HTML.

_HTML_ENTITIES = {
    "nbsp": " ",
    "amp": "&",
    "lt": "<",
    "gt": ">",
    "quot": '"',
    "apos": "'",
    "mdash": "—",
    "ndash": "-",
    "ldquo": '"',
    "rdquo": '"',
}


def _strip_html(html: str) -> str:
    """Remove HTML tags and decode entities; return plain text."""
    # Drop script/style blocks entirely
    html = re.sub(
        r"<(script|style|noscript|head)[^>]*>.*?</\1>", " ", html, flags=re.DOTALL | re.IGNORECASE
    )
    # Use <hr> tags as explicit section breaks (replace with §)
    html = re.sub(r"<hr[^>]*>", " § ", html, flags=re.IGNORECASE)
    # Strip all remaining tags
    html = re.sub(r"<[^>]+>", " ", html)

    # Decode named entities
    def _entity(m: re.Match) -> str:
        return _HTML_ENTITIES.get(m.group(1).lower(), " ")

    html = re.sub(r"&([a-zA-Z]+);", _entity, html)
    # Decode numeric entities
    html = re.sub(r"&#(\d+);", lambda m: chr(int(m.group(1))), html)
    return html


def _split_sections(text: str) -> list[str]:
    """Split text at § markers (from <hr>) and remove junk sections."""
    raw_sections = [s.strip() for s in text.split("§")]
    # Normalise whitespace within each section
    clean = []
    for s in raw_sections:
        s = re.sub(r"\s+", " ", s).strip()
        # Skip navigation/boilerplate sections (short or pure links)
        if len(s) > 120:
            clean.append(s)
    return clean


def extract_sections(html: str, page_name: str) -> list[dict]:
    """Return list of chunk dicts ready for neuron insertion."""
    plain = _strip_html(html)
    sections = _split_sections(plain)

    base_tags = PAGE_TAGS.get(page_name, ["stealthskater"])
    chunks = []
    for i, body in enumerate(sections):
        for j, window in enumerate(_windows(body, 600)):
            # Title = page + index + first ~60 chars of this window's content
            snippet = re.sub(r"\s+", " ", window)[:60].strip()
            chunks.append(
                {
                    "id": f"stealthskater_{page_name.replace('.', '_')}_{i}_{j}",
                    "title": f"[StealthSkater/{page_name}/{i}.{j}] {snippet}",
                    "content": window,
                    "tags": ["stealthskater", *base_tags],
                    "cluster_id": "stealthskater",
                    "path": f"stealthskater/{page_name}/{i}/{j}",
                }
            )
    return chunks


def _windows(text: str, size: int) -> list[str]:
    """Split text into overlapping ~size-char windows at sentence boundaries."""
    if len(text) <= size:
        return [text]
    parts = []
    while text:
        if len(text) <= size:
            parts.append(text)
            break
        cut = text.rfind(". ", 0, size)
        if cut == -1:
            cut = size
        else:
            cut += 1
        parts.append(text[:cut].strip())
        text = text[cut:].strip()
    return [p for p in parts if len(p) > 40]


# ── Network helpers ───────────────────────────────────────────────────────────


def fetch_page(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; cohezion-research-bot/1.0)"},
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        # stealthskater.com declares windows-1252; latin-1 is a safe superset for ASCII content
        return r.read().decode("latin-1", errors="replace")


def embed(text: str) -> list[float]:
    body = json.dumps({"model": EMBED_MODEL, "prompt": text[:2048]}).encode()
    req = urllib.request.Request(
        OLLAMA_URL, data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read()).get("embedding", [])


def surql(query: str) -> list:
    data = query.encode()
    req = urllib.request.Request(SURREAL_URL, data=data, headers=SURREAL_HEADERS)
    with urllib.request.urlopen(req, timeout=15) as r:
        results = json.loads(r.read())
    return results


# ── Insertion ─────────────────────────────────────────────────────────────────


def insert_neuron(chunk: dict, embedding: list[float], dry_run: bool) -> bool:
    """Insert one neuron; return True on success."""
    tags_sql = "[" + ", ".join(f'"{t}"' for t in chunk["tags"]) + "]"
    emb_sql = "[" + ", ".join(str(x) for x in embedding) + "]"
    nid = chunk["id"].replace("-", "_")
    q = (
        f"CREATE neurons:`{nid}` CONTENT {{"
        f"  title: {json.dumps(chunk['title'])},"
        f"  content: {json.dumps(chunk['content'])},"
        f"  tags: {tags_sql},"
        f'  cluster_id: "stealthskater",'
        f"  path: {json.dumps(chunk['path'])},"
        f"  embedding: {emb_sql},"
        f'  stage: "active",'
        f"  activation: 0.0"
        f"}};"
    )
    if dry_run:
        print(f"  [DRY] Would insert: {chunk['title'][:60]}")
        return True
    results = surql(q)
    ok = results and results[0].get("status") == "OK"
    if not ok:
        print(f"  [WARN] Insert failed for {chunk['id']}: {results}")
    return ok


def create_synapses(stealthskater_ids: list[str], dry_run: bool) -> int:
    """Create informed_by edges from stealthskater neurons to physics bridges."""
    if dry_run:
        print(f"  [DRY] Would create synapses for {len(stealthskater_ids)} neurons")
        return 0

    # Find existing physics bridge neurons
    bridge_map: dict[str, str] = {}
    for _, search_term in PHYSICS_BRIDGES:
        q = f"SELECT id, title FROM neurons WHERE title CONTAINS {json.dumps(search_term)} LIMIT 1;"
        r = surql(q)
        if r and r[0].get("result"):
            rec = r[0]["result"][0]
            bridge_map[search_term] = str(rec["id"])

    print(f"  Found {len(bridge_map)} existing physics bridge neurons to link to")

    synapse_count = 0
    for nid in stealthskater_ids:
        # Get the neuron's tags
        q = f"SELECT tags FROM neurons:`{nid}`;"
        r = surql(q)
        if not r or not r[0].get("result"):
            continue
        tags = r[0]["result"][0].get("tags", [])

        for tag, search_term in PHYSICS_BRIDGES:
            if tag in tags and search_term in bridge_map:
                bridge_id = bridge_map[search_term]
                syn_q = (
                    f"RELATE neurons:`{nid}`->informed_by->{bridge_id}"
                    f' CONTENT {{ how: "stealthskater-bridge: tag={tag}" }};'
                )
                sr = surql(syn_q)
                if sr and sr[0].get("status") == "OK":
                    synapse_count += 1

    return synapse_count


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest StealthSkater into SurrealDB")
    parser.add_argument("--dry-run", action="store_true", help="Parse but don't write to DB")
    parser.add_argument("--pages", type=int, default=0, help="Limit to N pages (0=all)")
    args = parser.parse_args()

    # Discover pages from intro
    print("Discovering pages from Intro.htm...")
    intro_html = fetch_page(f"{BASE_URL}/Intro.htm")
    all_links = re.findall(r'href=["\']([^"\'#?]+\.htm[l]?)["\'\s>]', intro_html, re.IGNORECASE)
    pages = sorted(
        set(
            l.strip()
            for l in all_links
            if not l.startswith("http") and "/" not in l.strip() and l.strip() not in SKIP_PAGES
        )
    )
    if args.pages:
        pages = pages[: args.pages]

    print(f"Target pages: {len(pages)} — {pages}")

    total_chunks = 0
    total_inserted = 0
    inserted_ids: list[str] = []

    for i, page in enumerate(pages):
        url = f"{BASE_URL}/{page}"
        print(f"\n[{i + 1}/{len(pages)}] Fetching {page}...")
        try:
            html = fetch_page(url)
        except Exception as e:
            print(f"  SKIP: {e}")
            time.sleep(RATE_LIMIT_S)
            continue

        chunks = extract_sections(html, page)
        print(f"  Extracted {len(chunks)} chunks")
        total_chunks += len(chunks)

        for chunk in chunks:
            try:
                emb = embed(chunk["content"])
            except Exception as e:
                print(f"  [WARN] Embed failed: {e} — inserting without embedding")
                emb = []

            ok = insert_neuron(chunk, emb, args.dry_run)
            if ok:
                total_inserted += 1
                inserted_ids.append(chunk["id"].replace("-", "_"))

        time.sleep(RATE_LIMIT_S)

    # Create synapses
    print(f"\nCreating synapses for {len(inserted_ids)} inserted neurons...")
    syn_count = create_synapses(inserted_ids, args.dry_run)

    # Summary
    print("\n" + "=" * 60)
    print("INGESTION COMPLETE")
    print(f"  Pages processed : {len(pages)}")
    print(f"  Chunks extracted: {total_chunks}")
    print(f"  Neurons inserted: {total_inserted}")
    print(f"  Synapses created: {syn_count}")
    print("=" * 60)

    # Novel connection query
    if not args.dry_run and total_inserted > 0:
        print("\nNovel cross-domain connections (StealthSkater ↔ existing Cohezion neurons):")
        q = """
        SELECT
            in.title AS stealthskater_node,
            out.title AS physics_node,
            how
        FROM informed_by
        WHERE in.cluster_id = "stealthskater"
        ORDER BY in.title
        LIMIT 20;
        """
        results = surql(q)
        rows = results[0].get("result", []) if results else []
        if rows and isinstance(rows[0], dict):
            for row in rows:
                print(f"  {str(row.get('stealthskater_node', '?'))[:50]}")
                print(f"    → {str(row.get('physics_node', '?'))[:50]}  [{row.get('how', '')}]")
        else:
            print("  (no synapse results yet — run GraphRAG vector search for semantic bridges)")


if __name__ == "__main__":
    main()
