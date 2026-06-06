---
title: "Running an HONEST local-VLM accuracy bake-off (pre-registration + isolated sidecar)"
date: 2026-06-06
tags: [vlm, llama-mtmd, lemonade, experiment-methodology, measurement-integrity, retro, verified]
verified: true
---

# Retro — how to run a defensible local image→text accuracy experiment ($0, no live-fleet impact)

Generalized from the item-18 LFM2.5-VL bake-off (verified 2026-06-06). Reusable for ANY
"does small local model X match/beat baseline Y" question.

## The five moves that make it honest

1. **Verify assets before pulling** (research discipline). `huggingface_hub.list_repo_files(repo)` →
   confirm the GGUF *and* the `mmproj-*.gguf` exist before downloading. Targeted `hf_hub_download`
   of just the two files you need, not `lemonade pull` (which can grab every quant).

2. **Serve VLMs via the `llama-mtmd-cli` sidecar — NOT a lemonade port.** lemonade `load` has **no
   `--mmproj` flag**; the multimodal binary is bundled at
   `~/.cache/lemonade/bin/llamacpp/rocm-stable/llama-mtmd-cli`. Invoking it directly
   (`-m model.gguf --mmproj mmproj.gguf --image x.png -p "…" --temp 0`) loads-runs-exits per call:
   **zero resident model, no port, no eviction risk to live Hermes** on 13305/13307. This is the
   safe way to run model experiments on a shared, memory-tight, live box. (Also reachable via
   lemonade `--llamacpp-args "--mmproj …"` passthrough, or a pull-time `--checkpoint`/`--label
   …:vision`/`collection.omni`.)

3. **Separate the SERVING smoke from the ACCURACY proof.** A serving smoke = "does the image reach
   the model and shape output at all?" Generate an image with text YOU control and check the output
   *contains* it (a genuine pixel-misread like Cohezion→Cohesion is a GOOD sign — it proves real
   reading, not prompt echo). This is NOT an accuracy claim and must never be reported as one.

4. **PRE-REGISTER the metric + verdict before seeing data.** Write the rule down (in the harness
   docstring) first: e.g. mean VALUE-RECALL (fraction of GT leaf values appearing,
   alphanumeric-boundary, in temp=0 output); flip the verified-pin IFF `recall(small) >=
   recall(baseline)`. Then **accept the result as written** — including an honest NULL. (Item 18:
   LFM 0.771 < Qwen2.5-VL-7B 0.864 → NULL, `verified_working` stayed False. Pre-registration is
   what makes accepting that principled rather than p-hacking toward a flip.)

5. **Never self-author ground truth.** Generating images from known YAML and "extracting" them is
   circular — grading your own answer key. Use a PUBLIC labeled set (CORD-v2 / FUNSD / OmniDocBench
   via `datasets`) or the user's real labeled docs. A user's "do anything" authorization does NOT
   substitute for ground truth (the charter honesty mandate overrides the grant).

## Operational gates honored
- K1/rule-5 OOM: `free -h` before any load; box held ≥25 GiB avail, swap 37% (<50% ceiling); the
  7B baseline (~4.5 GB) + tiny LFM both fit. Reload-per-image trades speed for zero resident memory.
- Fair metric: value-recall is presence-based, applied IDENTICALLY to both models, so the COMPARISON
  is fair even though it isn't structural exact-match. State that caveat explicitly.

## Reusable instrument
`scripts/experiments/lfm_vl_extraction_bakeoff.py` — pre-registered metric/verdict, runs two models
over a manifest of `{image, gt_values}`, prints per-image + mean + verdict, writes a result JSON.
Copy + swap the two model paths for the next bake-off.

## Caveat that bounds the conclusion
CORD is receipts. A model TUNED for extraction (LFM-Extract) may do better on the user's specific
document types than on a generic benchmark — so a public-set NULL is "doesn't beat a bigger general
VLM on CORD," not "useless." Offer a re-run on the user's real docs.
