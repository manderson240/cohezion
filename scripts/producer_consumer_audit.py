#!/usr/bin/env python3
"""Producer/consumer audit of Cohezion modules using Lemonade local inference.

Calls Lemonade GAIA SDK REST API directly — zero Claude API tokens consumed.
Model: Gemma-4-E4B-it-GGUF (iGPU, ~5GB, Apache 2.0)

Usage:
    uv run python scripts/producer_consumer_audit.py
    uv run python scripts/producer_consumer_audit.py --output docs/audits/PRODUCER_CONSUMER_2026-06-23.md
"""

import argparse
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

LEMONADE_URL = "http://localhost:13305/v1/chat/completions"
# Env-overridable; default is a small fast model reliably in the local catalog.
# Override: PC_AUDIT_MODEL=<id> (e.g. Bonsai-8B-gguf / Gemma-4-31B-it-GGUF for deeper triage).
MODEL = os.environ.get("PC_AUDIT_MODEL", "Gemma-4-E2B-it-GGUF")
SRC_ROOT = Path(__file__).parent.parent / "src" / "cohezion"

SYSTEM_PROMPT = "You classify software modules by data-flow role. Output JSON only, no explanation, no markdown."

def _make_user_content(module_name: str, source: str) -> str:
    """Build classify prompt — avoid str.format() on source (brace collision)."""
    return (
        "Classify cohezion." + module_name
        + ". Role: PRODUCER, CONSUMER, PRODUCER+CONSUMER, or INFRASTRUCTURE.\n\n"
        "Source:\n" + source[:1500]
        + '\n\nJSON: {"role":"...","produces":"...","consumes":"...","wiring_gap":"..."}'
    )


def _extract_json(text: str) -> dict:
    """Extract first JSON object from model output (handles nesting + code fences)."""
    import re
    # Strip code fences
    text = re.sub(r'^```(?:json)?\n?', '', text.strip())
    text = re.sub(r'\n?```$', '', text.strip())
    # Try full text first
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    # Find outermost {...} by brace counting
    start = text.find('{')
    if start >= 0:
        depth, i = 0, start
        for i, ch in enumerate(text[start:], start):
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except json.JSONDecodeError:
                        break
    # Last resort: try to extract role keyword
    m = re.search(r'"role"\s*:\s*"([A-Z+]+)"', text)
    if m:
        return {"role": m.group(1), "produces": "", "consumes": "", "wiring_gap": "partial parse"}
    return {"role": "UNKNOWN", "produces": "", "consumes": "", "wiring_gap": "parse failed"}


def lemonade_classify(module_name: str, source: str, timeout: int = 30) -> dict:
    """Call Lemonade REST API to classify a module."""
    payload = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _make_user_content(module_name, source)},
        ],
        "max_tokens": 180,
        "temperature": 0.1,
    }).encode()

    req = urllib.request.Request(
        LEMONADE_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
            text = data["choices"][0]["message"]["content"].strip()
            return _extract_json(text)
    except Exception as e:
        return {"role": "ERROR", "produces": "", "consumes": "", "wiring_gap": str(e)[:80]}


def read_module_source(module_dir: Path) -> str:
    """Read first 80 lines from __init__.py or the .py file itself."""
    candidates = [
        module_dir / "__init__.py",
        module_dir.parent / f"{module_dir.name}.py",
    ]
    for path in candidates:
        if path.exists():
            lines = path.read_text(errors="replace").splitlines()[:80]
            return "\n".join(lines)
    return "(no source found)"


def check_lemonade() -> bool:
    """Verify Lemonade is online and model is available."""
    try:
        with urllib.request.urlopen("http://localhost:13305/v1/models", timeout=5) as r:
            data = json.loads(r.read())
            models = [m["id"] for m in data.get("data", [])]
            if MODEL not in models:
                print(f"[warn] {MODEL} not in catalog. Available: {models[:8]}")
                print(f"[info] Switch MODEL= to one of the above and retry.")
                return False
            print(f"[ok] {MODEL} ready on :13305 ({len(models)} models total)")
            return True
    except Exception as e:
        print(f"[error] Lemonade :13305 offline: {e}")
        return False


def audit(output_path: Path | None = None) -> list[dict]:
    if not check_lemonade():
        sys.exit(1)

    modules = sorted(
        [p.name for p in SRC_ROOT.iterdir()
         if p.is_dir() and not p.name.startswith("_") and not p.name == "__pycache__"]
        + [p.stem for p in SRC_ROOT.iterdir()
           if p.is_file() and p.suffix == ".py" and not p.name.startswith("_")]
    )

    results = []
    for i, mod in enumerate(modules):
        source = read_module_source(SRC_ROOT / mod)
        print(f"[{i+1:02d}/{len(modules):02d}] {mod}...", end=" ", flush=True)
        t0 = time.time()
        classification = lemonade_classify(mod, source)
        elapsed = time.time() - t0
        classification["module"] = mod
        results.append(classification)
        role = classification.get("role", "?")
        gap = (classification.get("wiring_gap") or "")[:60]
        print(f"{role} ({elapsed:.1f}s) {('⚠ ' + gap) if gap else ''}")

    # Write report
    report_lines = [
        "# Cohezion Producer/Consumer Audit",
        f"Generated: 2026-06-23 | Model: {MODEL} | Modules: {len(results)}",
        "",
        "## Summary",
        "",
        "| Module | Role | Wiring Gap |",
        "|--------|------|------------|",
    ]
    for r in results:
        gap = (r.get("wiring_gap") or "")[:80]
        report_lines.append(f"| `{r['module']}` | {r.get('role','?')} | {gap} |")

    for role_filter, heading in [
        ("PRODUCER", "## Producers"),
        ("CONSUMER", "## Consumers"),
        ("PRODUCER+CONSUMER", "## Producer+Consumer (bidirectional)"),
        ("INFRASTRUCTURE", "## Infrastructure"),
    ]:
        matching = [r for r in results if role_filter in r.get("role", "")]
        if matching:
            report_lines += ["", heading, ""]
            for r in matching:
                report_lines.append(f"### `{r['module']}`")
                if r.get("produces"):
                    report_lines.append(f"- **Produces:** {r['produces']}")
                if r.get("consumes"):
                    report_lines.append(f"- **Consumes:** {r['consumes']}")
                if r.get("wiring_gap"):
                    report_lines.append(f"- **Gap:** {r['wiring_gap']}")
                report_lines.append("")

    gaps = [r for r in results if r.get("wiring_gap") and r.get("role") not in ("ERROR", "UNKNOWN", "INFRASTRUCTURE")]
    if gaps:
        report_lines += ["## Critical Wiring Gaps", ""]
        for r in gaps:
            report_lines.append(f"- **{r['module']}** ({r.get('role','?')}): {r.get('wiring_gap','')}")

    report = "\n".join(report_lines)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report)
        print(f"\n[saved] {output_path}")
    else:
        print("\n" + report)

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Producer/consumer audit via local Lemonade")
    parser.add_argument("--output", help="Write markdown report to this path")
    args = parser.parse_args()
    audit(Path(args.output) if args.output else None)


if __name__ == "__main__":
    main()
