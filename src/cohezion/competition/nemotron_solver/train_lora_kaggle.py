#!/usr/bin/env python3
"""Nemotron LoRA SFT Training Notebook for Kaggle GPU.

Trains a LoRA rank-32 adapter on NVIDIA-Nemotron-3-Nano-30B-A3B-BF16
using SFT data generated from symbolic solvers.

This is designed to run as a Kaggle notebook with GPU accelerator.

Key design decisions (following tonghuikang Progress Prize winner):
- Masked token training: loss only on completion tokens (not prompt)
- All 9,500 training examples with ground truth answers
- LoRA rank 32 (competition max)
- Token limit 8192
- Answers in \\boxed{} format

Usage:
    Upload to Kaggle as notebook, enable GPU accelerator (P100 or T4 x2)
"""

import contextlib
import csv
import math
import os
import re

import torch
from datasets import Dataset
from peft import LoraConfig, TaskType, get_peft_model
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
)


# ── Constants ────────────────────────────────────────────────────────────
MODEL_ID = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16"
PROMPT_SUFFIX = (
    "\nPlease put your final answer inside `\\boxed{}`. For example: `\\boxed{your answer}`"
)
TOKEN_LIMIT = 4096  # Reduced for GPU memory
IGNORE_INDEX = -100


# ── Symbolic Solvers ───────────────────────────────────────────────────
def parse_examples(prompt: str) -> list[tuple[str, str]]:
    """Parse I/O examples from prompt."""
    pairs = []
    for line in prompt.split("\n"):
        line = line.strip()
        if " -> " in line and not line.startswith(("Here", "Now")):
            parts = line.split(" -> ")
            if len(parts) == 2:
                pairs.append((parts[0].strip(), parts[1].strip()))
        elif " becomes " in line and not line.startswith("Now"):
            parts = line.split(" becomes ")
            if len(parts) == 2:
                pairs.append((parts[0].strip(), parts[1].strip()))
        elif line.startswith("For t =") and "distance =" in line:
            m = re.search(r"t\s*=\s*([0-9.]+s?)", line)
            n = re.search(r"distance\s*=\s*([0-9.]+)\s*m", line)
            if m and n:
                pairs.append((m.group(1), n.group(1) + " m"))
        elif " = " in line and not line.startswith(("Here", "Now", "For", "The")):
            parts = line.split(" = ", 1)
            if len(parts) == 2:
                left, right = parts[0].strip(), parts[1].strip()
                if left and right and left not in ("d", "distance", "t", "g"):
                    pairs.append((left, right))
    return pairs


def classify_problem(prompt: str) -> str:
    p = prompt.lower()
    if "bit manipulation" in p:
        return "bit_manip"
    elif "gravitational constant" in p or "falling distance" in p:
        return "gravity"
    elif "unit conversion" in p:
        return "unit_conversion"
    elif "equation" in p or "transformation rule" in p:
        return "equations"
    elif "numeral system" in p or "roman" in p:
        return "numeral"
    elif "cipher" in p or "encrypt" in p or "decrypt" in p or "secret code" in p:
        return "encryption"
    return "unknown"


def compare_answers(predicted: str, ground_truth: str) -> bool:
    predicted = predicted.strip()
    ground_truth = ground_truth.strip()
    if predicted.lower() == ground_truth.lower():
        return True
    if re.fullmatch(r"[01]+", ground_truth):
        return predicted.lower() == ground_truth.lower()
    try:
        return math.isclose(float(predicted), float(ground_truth), rel_tol=1e-2, abs_tol=1e-5)
    except (ValueError, TypeError):
        return False


# ── Simplified Solvers (inline, no external deps) ──────────────────────
def int_to_roman(n: int) -> str:
    val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
    syms = ["M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"]
    result = ""
    for v, s in zip(val, syms):
        while n >= v:
            result += s
            n -= v
    return result


def solve_gravity(examples, test_t: str) -> str:
    ts, ds = [], []
    for t_str, d_str in examples:
        try:
            t = float(re.search(r"([0-9.]+)", t_str).group(1))
            d = float(re.search(r"([0-9.]+)", d_str).group(1))
            ts.append(t)
            ds.append(d)
        except (ValueError, AttributeError):
            pass
    if not ts or len(ts) < 2:
        return "0.0"
    xs = [0.5 * t * t for t in ts]
    sum_xy = sum(d * x for d, x in zip(ds, xs))
    sum_x2 = sum(x * x for x in xs)
    g_ls = sum_xy / sum_x2 if sum_x2 != 0 else 0.0
    best_g = g_ls
    best_err = float("inf")
    candidates = [g_ls]
    for t, d in zip(ts, ds):
        if t > 0:
            candidates.append(2 * d / (t * t))
    for g0 in candidates:
        for step in [0.01, 0.005, 0.002, 0.001]:
            for offset in range(-5, 6):
                g = g0 + offset * step
                err = sum((0.5 * g * t * t - d) ** 2 for t, d in zip(ts, ds))
                if err < best_err:
                    best_err = err
                    best_g = g
    try:
        test_t_val = float(re.search(r"([0-9.]+)", test_t).group(1))
    except (ValueError, AttributeError):
        return "0.0"
    result = 0.5 * best_g * test_t_val * test_t_val
    # Format
    decimals = []
    for _, out in examples:
        m = re.search(r"([0-9]+\.([0-9]+))", out)
        if m:
            decimals.append(len(m.group(2)))
    if decimals:
        precision = max(set(decimals), key=decimals.count)
    else:
        precision = 0
    if precision == 0:
        return f"{int(round(result))}"
    return f"{result:.{precision}f}"


def solve_unit_conversion(examples, test_x: str) -> str:
    xs, ys = [], []
    for x_str, y_str in examples:
        try:
            x = float(re.search(r"([0-9.]+)", x_str).group(1))
            y = float(re.search(r"([0-9.]+)", y_str).group(1))
            xs.append(x)
            ys.append(y)
        except (ValueError, AttributeError):
            pass
    if len(xs) < 2:
        return "0.0"
    n = len(xs)
    sum_x = sum(xs)
    sum_y = sum(ys)
    sum_xy = sum(x * y for x, y in zip(xs, ys))
    sum_x2 = sum(x * x for x in xs)
    denom = n * sum_x2 - sum_x * sum_x
    if abs(denom) < 1e-10:
        k = sum_y / sum_x if sum_x != 0 else 1.0
        try:
            test_val = float(re.search(r"([0-9.]+)", test_x).group(1))
        except (ValueError, AttributeError):
            return "0.0"
        return f"{k * test_val:.2f}"
    a = (n * sum_xy - sum_x * sum_y) / denom
    b = (sum_y - a * sum_x) / n
    try:
        test_val = float(re.search(r"([0-9.]+)", test_x).group(1))
    except (ValueError, AttributeError):
        return "0.0"
    result = a * test_val + b
    # Format
    decimals = []
    for _, out in examples:
        m = re.search(r"([0-9]+\.([0-9]+))", out)
        if m:
            decimals.append(len(m.group(2)))
    if decimals:
        precision = max(set(decimals), key=decimals.count)
    else:
        precision = 2
    return f"{result:.{max(precision, 2)}f}"


def solve_numeral(examples, test_n: str) -> str:
    try:
        n = int(re.search(r"([0-9]+)", test_n).group(1))
    except (ValueError, AttributeError):
        return ""
    return int_to_roman(n)


def solve_bit_manip(examples, test_in: str) -> str:
    pairs = []
    for inp, out in examples:
        if len(inp) == 8 and set(inp).issubset({"0", "1"}):
            with contextlib.suppress(ValueError):
                pairs.append((int(inp, 2), int(out, 2)))
    if not pairs:
        return test_in
    # Per-bit mapping
    mapping = {}
    for out_bit in range(8):
        found = False
        for in_bit in range(8):
            ok = True
            for a, b in pairs:
                if ((b >> out_bit) & 1) != ((a >> in_bit) & 1):
                    ok = False
                    break
            if ok:
                mapping[out_bit] = ("bit", in_bit, False)
                found = True
                break
        if not found:
            for in_bit in range(8):
                ok = True
                for a, b in pairs:
                    if ((b >> out_bit) & 1) != (1 - ((a >> in_bit) & 1)):
                        ok = False
                        break
                if ok:
                    mapping[out_bit] = ("bit", in_bit, True)
                    found = True
                    break
        if not found:
            ok = True
            for a, b in pairs:
                if ((b >> out_bit) & 1) != 0:
                    ok = False
                    break
            if ok:
                mapping[out_bit] = ("const", 0, False)
                found = True
            else:
                ok = True
                for a, b in pairs:
                    if ((b >> out_bit) & 1) != 1:
                        ok = False
                        break
                if ok:
                    mapping[out_bit] = ("const", 1, False)
                    found = True
    if len(mapping) == 8:
        try:
            test_val = int(test_in, 2)
            result = 0
            for out_bit in range(8):
                typ, val, invert = mapping[out_bit]
                if typ == "const":
                    bit = val
                else:
                    bit = (test_val >> val) & 1
                    if invert:
                        bit = 1 - bit
                result |= bit << out_bit
            return f"{result:08b}"
        except (ValueError, TypeError):
            pass
    # XOR/AND/OR/ADD affine
    for xor_const in range(256):
        ok = True
        for a, b in pairs:
            if (a ^ xor_const) != b:
                ok = False
                break
        if ok:
            try:
                return f"{(int(test_in, 2) ^ xor_const):08b}"
            except (ValueError, TypeError):
                pass
    for and_const in range(256):
        ok = True
        for a, b in pairs:
            if (a & and_const) != b:
                ok = False
                break
        if ok:
            try:
                return f"{(int(test_in, 2) & and_const):08b}"
            except (ValueError, TypeError):
                pass
    # Unary ops
    unary_ops = [
        ("not", lambda x: (~x) & 0xFF),
        ("reverse", lambda x: int(f"{x:08b}"[::-1], 2)),
        ("shift_left_1", lambda x: (x << 1) & 0xFF),
        ("shift_right_1", lambda x: x >> 1),
        ("rot_left_1", lambda x: ((x << 1) & 0xFF) | (x >> 7)),
        ("rot_right_1", lambda x: (x >> 1) | ((x & 1) << 7)),
    ]
    for _name, op in unary_ops:
        ok = True
        for a, b in pairs:
            if op(a) != b:
                ok = False
                break
        if ok:
            try:
                return f"{op(int(test_in, 2)):08b}"
            except (ValueError, TypeError):
                pass
    return test_in


_ENCRYPTION_VOCAB = [
    "the",
    "follows",
    "dragon",
    "teacher",
    "writes",
    "creates",
    "draws",
    "student",
    "rabbit",
    "studies",
    "discovers",
    "secret",
    "found",
    "mouse",
    "dreams",
    "chases",
    "reads",
    "king",
    "sees",
    "watches",
    "queen",
    "hatter",
    "knight",
    "explores",
    "bird",
    "imagines",
    "wizard",
    "turtle",
    "castle",
    "cat",
    "alice",
    "garden",
    "princess",
    "colorful",
    "puzzle",
    "bright",
    "forest",
    "book",
    "clever",
    "key",
    "dark",
    "mirror",
    "treasure",
    "silver",
    "beyond",
    "inside",
    "in",
    "hidden",
    "curious",
    "around",
    "above",
    "wise",
    "potion",
    "near",
    "door",
    "golden",
    "under",
    "through",
    "mysterious",
    "magical",
    "strange",
    "story",
    "crystal",
    "message",
    "map",
    "ancient",
    "village",
    "mountain",
    "wonderland",
    "cave",
    "school",
    "valley",
    "island",
    "palace",
    "library",
    "ocean",
    "tower",
    "diamond",
    "crown",
    "river",
    "bridge",
    "cloud",
    "star",
    "moon",
    "sun",
    "fire",
    "water",
    "earth",
    "wind",
    "shadow",
    "light",
    "path",
    "road",
    "tree",
    "flower",
    "grass",
    "stone",
    "sand",
    "snow",
    "rain",
    "storm",
    "whisper",
    "laughter",
    "silence",
    "echo",
    "song",
    "dance",
    "music",
    "magic",
    "spell",
    "herb",
    "gem",
    "jewel",
    "ring",
]


def solve_encryption(examples, test_in: str) -> str:
    mapping = {}
    for inp, out in examples:
        inp_words = inp.split()
        out_words = out.split()
        if len(inp_words) != len(out_words):
            continue
        for iw, ow in zip(inp_words, out_words):
            if len(iw) == len(ow):
                for c_in, c_out in zip(iw, ow):
                    if c_in not in mapping:
                        mapping[c_in] = c_out
    result_words = []
    for tw in test_in.split():
        mapped = "".join(mapping.get(c, "?") for c in tw)
        result_words.append(mapped)
    # Dictionary completion
    changed = True
    while changed:
        changed = False
        for _i, (tw, pw) in enumerate(zip(test_in.split(), result_words)):
            if "?" not in pw:
                continue
            matches = [
                w
                for w in _ENCRYPTION_VOCAB
                if len(w) == len(pw) and all(p == "?" or p == w for p, w in zip(pw, w))
            ]
            if len(matches) == 1:
                best = matches[0]
                for c_in, c_out in zip(tw, best):
                    if c_in not in mapping:
                        mapping[c_in] = c_out
                        changed = True
        result_words = ["".join(mapping.get(c, "?") for c in tw) for tw in test_in.split()]
    return " ".join(result_words)


def solve_equations(examples, test_in: str) -> str:
    # Strategy 1: Delete chars absent from all outputs
    all_input_chars = set()
    all_output_chars = set()
    for inp, out in examples:
        all_input_chars.update(set(inp))
        all_output_chars.update(set(out))
    delete_set = set(c for c in all_input_chars if c not in all_output_chars)
    if delete_set:
        pred = "".join(c for c in test_in if c not in delete_set)
        all_match = all(
            "".join(c for c in inp if c not in delete_set) == out for inp, out in examples
        )
        if all_match:
            return pred
    # Strategy 2: Numeric operations
    first_in = examples[0][0] if examples else ""
    if any(c.isdigit() for c in first_in):
        for inp, out in examples:
            # Try simple numeric ops
            pass
    return ""


def extract_test_input(prompt: str) -> str:
    for pat in [
        r"determine the output for:\s*([0-9a-zA-Z\s.]+)",
        r"convert the following measurement:\s*([0-9.]+\s*m?)",
        r"write the number\s+([0-9]+)\s+in the",
        r"determine the result for:\s*([^\n]+)",
        r"decrypt the following text:\s*([^\n]+)",
        r"determine the falling distance for\s+t\s*=\s*([0-9.]+s?)",
        r"What is ([\w]+) in",
    ]:
        m = re.search(pat, prompt, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    lines = [l.strip() for l in prompt.split("\n") if l.strip()]
    for line in reversed(lines):
        if not line.startswith("In Alice") and " -> " not in line and " becomes " not in line:
            if ":" in line:
                return line.split(":", 1)[1].strip()
            return line
    return ""


def solve(prompt: str) -> str:
    ptype = classify_problem(prompt)
    test_input = extract_test_input(prompt)
    examples = parse_examples(prompt)
    if ptype == "gravity":
        return solve_gravity(examples, test_input)
    elif ptype == "unit_conversion":
        return solve_unit_conversion(examples, test_input)
    elif ptype == "numeral":
        return solve_numeral(examples, test_input)
    elif ptype == "bit_manip":
        return solve_bit_manip(examples, test_input)
    elif ptype == "encryption":
        return solve_encryption(examples, test_input)
    elif ptype == "equations":
        return solve_equations(examples, test_input)
    return ""


# ── Reasoning trace generators ──────────────────────────────────────────
def trace_numeral(prompt, answer):
    return f"I need to convert this numeral. Applying Roman numeral conversion rules.\nI=1, V=5, X=10, L=50, C=100, D=500, M=1000.\nSubtraction rule for smaller-before-larger values.\nConverting step by step: the result is \\boxed{{{answer}}}"


def trace_gravity(prompt, answer):
    return f"I need to find the falling distance using d = 0.5 × g × t².\nDetermining g from the examples using least-squares fit.\nApplying to the query time.\nCalculating: d = 0.5 × g × t² = \\boxed{{{answer}}}"


def trace_unit_conversion(prompt, answer):
    return f"Unit conversion with linear relationship.\nFitting y = a×x + b from example pairs.\nApplying conversion: the answer is \\boxed{{{answer}}}"


def trace_bit_manip(prompt, answer):
    return f"Finding the bit manipulation output.\nAnalyzing per-bit mapping and affine patterns (XOR, AND, OR, shifts, rotations).\nAfter pattern analysis: \\boxed{{{answer}}}"


def trace_encryption(prompt, answer):
    return f"Decoding with substitution cipher from examples.\nBuilding character mapping and completing with vocabulary context.\nThe decoded message is: \\boxed{{{answer}}}"


def trace_equations(prompt, answer):
    return f"Finding the transformation output.\nAnalyzing patterns from the examples.\nBased on the rule: \\boxed{{{answer}}}"


TRACE_GENERATORS = {
    "numeral": trace_numeral,
    "gravity": trace_gravity,
    "unit_conversion": trace_unit_conversion,
    "bit_manip": trace_bit_manip,
    "encryption": trace_encryption,
    "equations": trace_equations,
}


# ── Build SFT Data ─────────────────────────────────────────────────────
def build_training_data(train_csv_path: str) -> tuple[list[dict], dict]:
    training_data = []
    stats = {}
    with open(train_csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row["id"]
            prompt = row["prompt"]
            answer = row["answer"].strip()
            category = classify_problem(prompt)
            stats.setdefault(category, {"total": 0, "correct": 0})
            stats[category]["total"] += 1
            # Verify with symbolic solver
            try:
                pred = solve(prompt)
                verified = compare_answers(pred, answer)
            except Exception:
                verified = False
            if verified:
                stats[category]["correct"] += 1
            # Generate trace
            trace_fn = TRACE_GENERATORS.get(category, trace_equations)
            if verified:
                reasoning = trace_fn(prompt, answer)
            else:
                reasoning = f"Analyzing this step by step.\n\\boxed{{{answer}}}"
            completion = f"{reasoning}\n\n\\boxed{{{answer}}}<|im_end|>"
            training_data.append(
                {
                    "id": pid,
                    "category": category,
                    "prompt": prompt,
                    "completion": completion,
                    "answer": answer,
                    "verified": verified,
                }
            )
    return training_data, stats


# ── Tokenization ───────────────────────────────────────────────────────
def tokenize_with_mask(prompt_text, completion_text, tokenizer, max_length=TOKEN_LIMIT):
    prompt_with_suffix = prompt_text + PROMPT_SUFFIX
    prompt_ids = tokenizer.apply_chat_template(
        [{"role": "user", "content": prompt_with_suffix}],
        tokenize=True,
        add_generation_prompt=True,
        enable_thinking=True,
    )
    if hasattr(prompt_ids, "keys") and "input_ids" in prompt_ids:
        prompt_ids = list(prompt_ids["input_ids"])
    completion_ids = tokenizer.encode(completion_text, add_special_tokens=False)
    input_ids = prompt_ids + completion_ids
    labels = [IGNORE_INDEX] * len(prompt_ids) + completion_ids
    if len(input_ids) > max_length:
        input_ids = input_ids[:max_length]
        labels = labels[:max_length]
    return {"input_ids": input_ids, "attention_mask": [1] * len(input_ids), "labels": labels}


# ══════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════
def main():
    # Detect Kaggle environment
    KAGGLE_INPUT = "/kaggle/input/nvidia-nemotron-model-reasoning-challenge"
    TRAIN_CSV = (
        os.path.join(KAGGLE_INPUT, "train.csv") if os.path.exists(KAGGLE_INPUT) else "train.csv"
    )
    OUTPUT_DIR = (
        "/kaggle/working/nemotron_lora"
        if os.path.exists("/kaggle/working")
        else "./nemotron_lora_output"
    )
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 60)
    print("Nemotron LoRA SFT Training (Kaggle GPU)")
    print("=" * 60)

    # Step 1: Build SFT data
    print("\n[1/5] Building SFT training data...")
    training_data, stats = build_training_data(TRAIN_CSV)
    total = sum(s["total"] for s in stats.values())
    verified = sum(s["correct"] for s in stats.values())
    print(f"  Total: {total}, Verified: {verified} ({verified / total * 100:.1f}%)")

    # Step 2: Load tokenizer and model
    print(f"\n[2/5] Loading model: {MODEL_ID}")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
        max_memory={0: "14GiB"},  # Leave room for T4/P100 16GB VRAM
    )
    total_params = sum(p.numel() for p in model.parameters()) / 1e9
    print(f"  Model: {total_params:.1f}B params")

    # Step 3: Tokenize
    print(f"\n[3/5] Tokenizing {len(training_data)} examples...")
    all_ids, all_masks, all_labels, all_cats = [], [], [], []
    for entry in training_data:
        tok = tokenize_with_mask(entry["prompt"], entry["completion"], tokenizer)
        all_ids.append(tok["input_ids"])
        all_masks.append(tok["attention_mask"])
        all_labels.append(tok["labels"])
        all_cats.append(entry["category"])
    dataset = Dataset.from_dict(
        {
            "input_ids": all_ids,
            "attention_mask": all_masks,
            "labels": all_labels,
            "category": all_cats,
        }
    )
    split = dataset.train_test_split(test_size=0.05, seed=42)
    print(f"  Train: {len(split['train'])}, Eval: {len(split['test'])}")

    # Step 4: Setup LoRA
    print("\n[4/5] Setting up LoRA (rank=32)...")
    peft_config = LoraConfig(
        r=32,
        lora_alpha=64,
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
        lora_dropout=0.05,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    )
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()

    # Step 5: Train
    print("\n[5/5] Training...")
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        num_train_epochs=3,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=16,
        learning_rate=2e-4,
        lr_scheduler_type="cosine",
        warmup_ratio=0.05,
        bf16=True,
        logging_steps=10,
        save_steps=200,
        save_total_limit=2,
        eval_strategy="no",
        report_to="none",
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        max_grad_norm=1.0,
        weight_decay=0.01,
        remove_unused_columns=False,
        dataloader_pin_memory=False,
        dataloader_num_workers=0,
    )

    class MaskedDataCollator:
        def __init__(self, tokenizer, max_length=TOKEN_LIMIT):
            self.tokenizer = tokenizer
            self.max_length = max_length

        def __call__(self, features):
            batch = {
                "input_ids": [],
                "attention_mask": [],
                "labels": [],
            }
            for f in features:
                ids = f["input_ids"][: self.max_length]
                batch["input_ids"].append(ids)
                batch["attention_mask"].append([1] * len(ids))
                batch["labels"].append(f["labels"][: self.max_length])
            # Pad
            max_len = max(len(ids) for ids in batch["input_ids"])
            pad_id = self.tokenizer.pad_token_id or 0
            for i in range(len(batch["input_ids"])):
                pad_len = max_len - len(batch["input_ids"][i])
                batch["input_ids"][i] = batch["input_ids"][i] + [pad_id] * pad_len
                batch["attention_mask"][i] = batch["attention_mask"][i] + [0] * pad_len
                batch["labels"][i] = batch["labels"][i] + [IGNORE_INDEX] * pad_len
            batch = {k: torch.tensor(v) for k, v in batch.items()}
            return batch

    collator = MaskedDataCollator(tokenizer)

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=split["train"],
        data_collator=collator,
    )

    trainer.train()

    # Save adapter
    adapter_dir = os.path.join(OUTPUT_DIR, "final_adapter")
    model.save_pretrained(adapter_dir)
    tokenizer.save_pretrained(adapter_dir)

    # Create submission.zip
    import zipfile

    submission_path = os.path.join(OUTPUT_DIR, "submission.zip")
    with zipfile.ZipFile(submission_path, "w") as zf:
        for fname in ["adapter_config.json", "adapter_model.safetensors"]:
            fpath = os.path.join(adapter_dir, fname)
            if os.path.exists(fpath):
                zf.write(fpath, fname)
                print(f"  Added {fname} ({os.path.getsize(fpath) / 1e6:.1f} MB)")
    print(f"\nSubmission saved to: {submission_path}")

    # Evaluate on first 100 training examples
    print("\nEvaluating on training sample...")
    model.eval()
    correct = 0
    total_eval = 0
    for entry in training_data[:100]:
        prompt = entry["prompt"]
        ground_truth = entry["answer"]
        try:
            inputs = tokenizer.apply_chat_template(
                [{"role": "user", "content": prompt + PROMPT_SUFFIX}],
                tokenize=True,
                add_generation_prompt=True,
                enable_thinking=True,
                return_tensors="pt",
            ).to(model.device)
            with torch.no_grad():
                outputs = model.generate(inputs, max_new_tokens=256, do_sample=False)
            response = tokenizer.decode(outputs[0][inputs.shape[-1] :], skip_special_tokens=True)
            boxed = re.findall(r"\\boxed\{([^}]*)(?:\}|$)", response)
            predicted = boxed[-1].strip() if boxed else response.strip().split("\n")[-1]
            total_eval += 1
            if compare_answers(predicted, ground_truth):
                correct += 1
        except Exception:
            total_eval += 1
    if total_eval > 0:
        print(f"  Eval: {correct}/{total_eval} ({correct / total_eval * 100:.1f}%)")

    print(f"\nTraining complete. Adapter at: {adapter_dir}")
    print(f"Submission: {submission_path}")


if __name__ == "__main__":
    main()
