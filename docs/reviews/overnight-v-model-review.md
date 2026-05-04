---
title: Overnight V-Model Adversarial Review — 3 Perspectives
date: 2026-05-02
session_branch: feat/autoharness-vmodel-wave1
reviewer_worktree: compound/overnight-v-model-reviewer (NOT CREATED — review executed in main checkout)
commits_reviewed:
  - fe68c0933 fix(nemotron): v5 training template — 3 critical bug fixes + 9500 symbolic examples
  - 4f304ea95 perf(nemotron): v5.1 encrypt_x4 upsampling (metric 203->476, 2.3x)
  - a78ac7f97 feat(autorun): 2-hour autonomous research driver
  - b8e776487 fix(autorun): prevent tight spin-loop at deadline + retirement criterion
---

# Overnight V-Model Adversarial Review

**Environmental note:** The designated reviewer worktree
(`/home/mike-anderson/dev/cohezion/.claude/worktrees/overnight-v-model-reviewer` on branch
`compound/overnight-v-model-reviewer`) was not created at session start. This review was conducted
from the main checkout on `feat/autoharness-vmodel-wave1` against HEAD commits.

**Missing file:** `scripts/research/nemotron_pipeline_bench.py` — listed in the task context but
not found anywhere in the repository (not in HEAD, not in any branch). No findings can be made for
this file. This is itself a gap: a file referenced as a session artifact should be committed or
its absence explained.

---

## Files Reviewed

| File | Last Session Commit |
|------|-------------------|
| `src/cohezion/integrations/kaggle_training_improved.py` | `4f304ea95` (v5.1) |
| `scripts/autorun_2h.py` | `b8e776487` (spin-loop fix) |
| `scripts/research/nemotron_pipeline_bench.py` | **NOT FOUND** |

---

## PERSPECTIVE 1 — Scientific Rigor (Code Correctness)

### P1.1 enable_input_require_grads() placement — PASS

`kaggle_training_improved.py:261-263`: `model = get_peft_model(model, lora_config)` is followed
immediately by `model.enable_input_require_grads()` and then `model.print_trainable_parameters()`.
This is the correct sequence: calling `enable_input_require_grads()` before `get_peft_model()` would
be a no-op on the wrong object; calling it after ensures PEFT's adapter forward hooks are wired
before the call. The gradient_checkpointing=True in TrainingArguments at line 319 confirms why
this call is mandatory.

### P1.2 extract_boxed() balanced-brace regex — PASS with WARN

Function at lines 269-283. Mental trace with `\boxed{\frac{1}{2}}`:
- `idx=0`, `start = 0 + 7 - 1 = 6`, `text[6]='{'`
- Loop: depth hits 0 at `i=18`; returns `text[7:18] = '\frac{1}{2}'` — **correct**.

Empirically verified:
```
extract_boxed(r'\boxed{42}')            -> '42'           PASS
extract_boxed(r'\boxed{\frac{1}{2}}')  -> '\frac{1}{2}'  PASS
extract_boxed(r'\boxed{\sqrt{3}/2}')   -> '\sqrt{3}/2'   PASS
extract_boxed('no boxed here')          -> None           PASS
```

**WARN:** The training-template `extract_boxed()` handles arbitrary nesting but the
`KaggleEvaluator.extract_answer()` in `src/cohezion/integrations/kaggle_eval.py:18` uses the
regex `r"\\boxed\{((?:[^{}]|\{[^{}]*\})+)\}"` which only handles 1 level of brace nesting.
For `\boxed{\frac{\sqrt{3}}{2}}` (3-level), the regex returns `[]` while extract_boxed returns
the correct content. Training rewards answers that the evaluation pipeline cannot extract — a
metric leak on 3+ level nested LaTeX answers. See P0 list.

### P1.3 label_pad_token_id=-100 consistency — PASS

`tokenize()` at lines 285-293 manually sets `labels = [-100] * len(prompt_ids) + ...` and truncates
to 2048. `DataCollatorForSeq2Seq` at lines 303-308 sets `label_pad_token_id=-100`. Both use -100
for masking; the collator pads already-masked labels to batched length using -100. No double-masking
inconsistency.

### P1.4 lora_alpha=64 with r=32 — PASS

Lines 253-260: `r=32, lora_alpha=64`. The 2x convention (alpha=2r) is the accepted practice for
stable training; it keeps the effective learning rate scale normalized. Correct.

### P1.5 Double-tokenization off-by-one — WARN (P1)

`tokenize()` at lines 285-293 tokenizes `prompt_text + completion` as `enc` and `prompt_text`
separately as `prompt_ids`. The label mask assumes `enc["input_ids"][:len(prompt_ids)]` == the
prompt prefix of the full encoding. This holds for most HF tokenizers on causal LMs without chat
templates, but breaks if the tokenizer appends an EOS or separator token when encoding `prompt_text`
alone (making `len(prompt_ids) > len(shared_prefix)`). A one-line check before training confirms
alignment:

```python
assert tokenizer(prompt_text)["input_ids"] == tokenizer(prompt_text + completion)["input_ids"][:len(tokenizer(prompt_text)["input_ids"])]
```

The Nemotron tokenizer (Mistral-style) does not add trailing EOS on bare tokenize, so this is
likely safe, but has not been structurally asserted. Downgraded to P1.

### PERSPECTIVE 1 POSITIVE: The `enable_input_require_grads()` placement and comment (line 262) is
exactly correct and the docstring at lines 86-99 provides actionable traceability for all 3 bug
fixes — this is the right level of inline documentation for a Kaggle training script.

---

## PERSPECTIVE 2 — Edge Case Hunter

### P2.1 Empty CSV (0-row DataFrame) — PASS

If no `train_file` is found (line 209): `df = pd.DataFrame({"prompt": ["What is 2+2?"], "answer": ["4"]})` —
a 1-row fallback. If the CSV exists but has 0 data rows after the header: `base_data` is empty,
`_encrypt` and `_other` are empty, `filtered_data` is empty, `Dataset.from_list([])` raises
`ValueError` ("empty list"). This will be caught by the outer `except Exception` at line 349 and
print `FATAL ERROR`. Not a silent failure, but training will abort with a non-descriptive error.
**WARN** — a guard `if not filtered_data: raise RuntimeError("No training examples")` at line 229
would give a clearer message.

### P2.2 All encryption examples filter out — PASS

`_encrypt = [r for r in base_data if len(r["answer"]) > 8 and r["answer"].replace(" ", "").isalpha()]`
(line 227). For a math-heavy training set, most answers (`42`, `1/2`, `x=3`) are NOT pure alpha.
If `_encrypt` is empty: `filtered_data = _other + [] * 4 = _other` — graceful degradation to
baseline data. **PASS**.

### P2.3 bit_manip category has 0 examples — PASS (non-applicable)

The training template has no category-level filtering. All rows from the CSV are included in
`base_data` regardless of category. `bit_manip` with 0 examples simply means fewer training samples
for that category — not a crash path.

### P2.4 kagglehub.model_download() returns bad path — PASS (partial)

Line 237: `if not model_path: raise RuntimeError(...)` handles `None` or empty string return.
If the path is non-empty but does not exist on disk, `AutoModelForCausalLM.from_pretrained()` at
line 244 raises `OSError: Can't load config from ...` which is caught by the outer except. No
silent failure. **PASS**.

### P2.5 pad_token_id == eos_token_id with DataCollatorForSeq2Seq — PASS (accepted risk)

Line 241-242: `tokenizer.pad_token = tokenizer.eos_token`. The collator uses `label_pad_token_id=-100`
(labels) and `pad_to_multiple_of=8` (inputs). Input padding uses `pad_token_id` for position
filling; `attention_mask` is set to 0 for pad positions. At training time the model correctly
ignores pad positions. This is standard practice for decoder-only models. **PASS** with the
acknowledged risk that inference without explicit attention_mask would be incorrect, but training
Trainer handles this automatically.

### PERSPECTIVE 2 POSITIVE: The fallback-data path (lines 209-211) ensures training does not abort
with a confusing ImportError if the competition data directory doesn't exist — the 1-row fallback
gives a runnable test even on a fresh Kaggle machine before data is attached.

---

## PERSPECTIVE 3 — V-Model Compliance

### P3.1 Structural tests for template markers — FAIL (P0)

`tests/integrations/test_kaggle_training.py` tests `cohezion.integrations.kaggle_training`
(the OLD module) with 3 behavioral tests: `generate_lora_config`, `generate_adapter_config`,
`prepare_notebook`. None of these exercise `KaggleTrainingManager.get_training_script_template()`
or the v5 marker set. No structural test verifies that bug-fix markers (`enable_input_require_grads`,
`DataCollatorForSeq2Seq`, `label_pad_token_id=-100`, `all-linear`, `lora_alpha=64`) are present in
the generated template string. The only gate is the smoke check in `drive_nemotron.py` — which is
on a separate branch (`kaggle/nemotron-june`) and (per P3.2) is stale.

### P3.2 Smoke check covers v5 markers — FAIL (P0, SHIP-BLOCKING)

`kaggle/nemotron-june:scripts/drive_nemotron.py:88-102` defines `v4_markers` dict (14 keys).
One required marker is:

```python
"enable_thinking=True":  "thinking mode (matches evaluation)",
```

Commit `fe68c0933` is documented as:

> Bug fix: enable_thinking=True removed from generate() — was silent TypeError for DeepSeek-R1-distill

The current template (`kaggle_training_improved.py`, lines 100-352) contains no occurrence of
`enable_thinking`. Verified with `grep`:

```
$ grep "enable_thinking" src/cohezion/integrations/kaggle_training_improved.py
90: - Bug fix: enable_thinking removed from generate() (TypeError for DeepSeek-R1-distill)
```

That occurrence is inside the docstring (line 90), NOT inside the template string that starts at
line 100. The smoke check searches `tmpl` (the return value of `get_training_script_template()`)
which is the raw string starting at line 100 — the docstring is not included. **The smoke check
will exit 1 on the current v5 template, blocking `drive_nemotron.py train`.**

**Fix:** Update `drive_nemotron.py` to remove the `"enable_thinking=True"` marker from `v4_markers`
and add the replacement v5 markers:
- `"enable_input_require_grads"` — new bug fix marker
- `"DataCollatorForSeq2Seq"` — already present in v4_markers as a different key
- Version bump the dict name from `v4_markers` to `v5_markers`

### P3.3 Documentation of bug fixes — PASS

The docstring at `kaggle_training_improved.py:86-99` explicitly names all 3 bug fixes with
one-sentence explanations of WHY each was needed (TypeError, zero-grad, regex correctness).
The commit message `fe68c0933` repeats these with "Adversarial review findings (2026-05-02)".
**PASS** — traceability requirements met.

### P3.4 autorun_2h.py — no V-Model harness — WARN (P2)

`scripts/autorun_2h.py` has no tests. The spin-loop fix (`b8e776487`) is a 3-line guard with
a comment. No test verifies that `asyncio.wait_for(timeout=negative)` is never called. A
structural test with `mock_timer` that sets `remaining_s = 5` and asserts the inner loop breaks
before calling `asyncio.wait_for` would catch regressions. Currently only manually verified
by the 1700-spurious-cycles observation.

### PERSPECTIVE 3 POSITIVE: The v5 training template docstring at lines 86-99 provides a
self-documenting, review-auditable change record within the code itself — the "Smoke check: 16/16
markers PASS" note in the commit indicates the review loop was completed. The commit message
quality is high and follows the adversarial-review traceability convention from `coding-standards.md`.

---

## Priority-Ordered Action Items

### P0 — Must Fix Before Submission

| ID | File | Line | Finding |
|----|------|------|---------|
| P0-1 | `kaggle/nemotron-june:scripts/drive_nemotron.py` | 92 | Remove `"enable_thinking=True"` from `v4_markers`; rename to `v5_markers`; add `"enable_input_require_grads"`. The current template does NOT contain this string → smoke check exits 1 → `train` subcommand is gated. |
| P0-2 | `src/cohezion/integrations/kaggle_eval.py` | 18 | Upgrade `boxed_regex` from 1-level to balanced-brace (or at least 2-level nesting). Training uses `extract_boxed()` which handles arbitrary nesting; eval uses a regex that returns `[]` for `\boxed{\frac{\sqrt{3}}{2}}`. Training and eval diverge for 3+ level answers. |
| P0-3 | `tests/integrations/test_kaggle_training.py` | — | Add structural tests for `get_training_script_template()` in `kaggle_training_improved.py` verifying all v5 markers are present in the returned string. Currently zero tests cover the v5 template content. |

### P1 — Should Fix Before Submission

| ID | File | Line | Finding |
|----|------|------|---------|
| P1-1 | `kaggle_training_improved.py` (template) | 285-293 | Add assertion or print confirming prefix-alignment of double tokenization: `assert prompt_ids == enc["input_ids"][:len(prompt_ids)]`. Silent label-mask misalignment if tokenizer adds trailing tokens on standalone prompt encoding. |
| P1-2 | `kaggle_training_improved.py` (template) | 229 | Add explicit guard: `if not filtered_data: raise RuntimeError("No training examples after filtering")`. Currently an empty dataset produces a confusing `ValueError` from `Dataset.from_list`. |

### P2 — Nice to Have

| ID | File | Line | Finding |
|----|------|------|---------|
| P2-1 | `scripts/autorun_2h.py` | 368-380 | Add unit test for the spin-loop guard: mock `timeit.default_timer()` to return `DEADLINE - 5` and assert the inner loop breaks before `asyncio.wait_for` is called with a negative timeout. |
| P2-2 | `scripts/research/nemotron_pipeline_bench.py` | — | File does not exist. If this script was created during the session and referenced in status docs, it should be committed or the reference removed from session notes. |
| P2-3 | `kaggle/nemotron-june:scripts/drive_nemotron.py` | 88 | The dict is named `v4_markers` but covers v5 changes. Rename to `v5_markers` for clarity. Low risk. |

---

## Summary Table

| Check | Perspective | Result |
|-------|-------------|--------|
| enable_input_require_grads placement | Scientific | PASS |
| extract_boxed balanced-brace logic | Scientific | PASS |
| extract_boxed vs kaggle_eval divergence | Scientific | WARN (P0) |
| label_pad_token_id consistency | Scientific | PASS |
| lora_alpha=64 2x convention | Scientific | PASS |
| Double-tokenization alignment | Scientific | WARN (P1) |
| Empty CSV → 0 training examples | Edge Case | WARN (P1) |
| _encrypt all filters out | Edge Case | PASS |
| bit_manip 0 examples | Edge Case | PASS |
| model_download bad path | Edge Case | PASS |
| pad_token==eos_token | Edge Case | PASS |
| Structural tests for v5 markers | V-Model | FAIL (P0) |
| Smoke check covers v5 markers | V-Model | FAIL (P0, SHIP-BLOCKING) |
| Bug fix documentation/comments | V-Model | PASS |
| autorun_2h harness coverage | V-Model | WARN (P2) |

**P0 count: 3 (1 ship-blocking)**
