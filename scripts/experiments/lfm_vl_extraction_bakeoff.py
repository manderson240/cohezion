"""Item 18 accuracy bake-off: LFM2.5-VL-1.6B-Extract vs a larger baseline VLM.

PRE-REGISTERED metric + verdict (set before running, to avoid post-hoc bias):
  - metric: per-image VALUE-RECALL = fraction of ground-truth leaf values that appear
    (normalized, alphanumeric-boundary) in the model's free-form output. Mean over N images.
  - verdict: flip verified_working IFF mean_recall(LFM) >= mean_recall(baseline). LFM is already
    the smaller model (file size), so the spec's "at lower VRAM" is satisfied by construction.
  - empty output is counted (recall 0) and reported as a parse_failure, never silently dropped.

This is an ACCURACY proof on a PUBLIC labeled set (CORD-v2 receipts) — distinct from the earlier
serving smoke. Each model runs via the isolated llama-mtmd-cli sidecar (no lemonade port, no Hermes
impact). Reproducible: `python scripts/experiments/lfm_vl_extraction_bakeoff.py <manifest.json>`.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

_MTMD = Path.home() / ".cache/lemonade/bin/llamacpp/rocm-stable/llama-mtmd-cli"
_PROMPT = "Extract all fields from this receipt as YAML key: value pairs."


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def _recall(output: str, gt_values: list[str]) -> tuple[float, int, int]:
    no = _norm(output)
    matched = 0
    considered = 0
    for v in gt_values:
        nv = _norm(v)
        if len(nv) < 2:
            continue
        considered += 1
        if re.search(rf"(?<![a-z0-9]){re.escape(nv)}(?![a-z0-9])", no):
            matched += 1
    return (matched / considered if considered else 0.0), matched, considered


def _run_one(model: str, mmproj: str, image: str, *, n_predict: int = 256) -> str:
    proc = subprocess.run(
        [
            str(_MTMD), "-m", model, "--mmproj", mmproj, "--image", image,
            "-p", _PROMPT, "-n", str(n_predict), "--temp", "0",
        ],
        capture_output=True, text=True, timeout=600,
    )
    return proc.stdout.strip()


def evaluate(model: str, mmproj: str, manifest: list[dict]) -> dict:
    per_image = []
    parse_failures = 0
    for item in manifest:
        out = _run_one(model, mmproj, item["image"])
        if not out:
            parse_failures += 1
        r, matched, considered = _recall(out, item["gt_values"])
        per_image.append({"image": Path(item["image"]).name, "recall": r,
                          "matched": matched, "considered": considered, "empty": not out})
    mean = sum(p["recall"] for p in per_image) / len(per_image) if per_image else 0.0
    return {"mean_recall": mean, "parse_failures": parse_failures, "per_image": per_image,
            "model_size_mb": Path(model).stat().st_size // (1024 * 1024)}


def main() -> None:
    manifest = json.loads(Path(sys.argv[1]).read_text())
    base = Path(sys.argv[1]).parent.parent  # $TMPDIR/lfmvl
    models = {
        "LFM2.5-VL-1.6B": (base / "LFM2.5-VL-1.6B-Extract-Q4_0.gguf",
                           base / "mmproj-LFM2.5-VL-1.6B-Extract-F16.gguf"),
        "Qwen2.5-VL-7B": (base / "Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf",
                          base / "mmproj-Qwen2.5-VL-7B-Instruct-Q8_0.gguf"),
    }
    results = {}
    for name, (m, mm) in models.items():
        print(f"=== {name} ===", flush=True)
        res = evaluate(str(m), str(mm), manifest)
        results[name] = res
        print(f"  mean_recall={res['mean_recall']:.3f}  size={res['model_size_mb']}MB  "
              f"parse_failures={res['parse_failures']}", flush=True)
    lfm = results["LFM2.5-VL-1.6B"]["mean_recall"]
    bench = results["Qwen2.5-VL-7B"]["mean_recall"]
    verdict = "FLIP verified_working" if lfm >= bench else "honest NULL (LFM < baseline)"
    print(f"\nVERDICT: LFM={lfm:.3f} vs baseline={bench:.3f} → {verdict}")
    Path(sys.argv[1]).parent.joinpath("bakeoff_result.json").write_text(
        json.dumps({"results": results, "lfm_recall": lfm, "baseline_recall": bench,
                    "verdict": verdict}, indent=1))


if __name__ == "__main__":
    main()
