"""NVIDIA Nemotron Reasoning Challenge — Kaggle Notebook Submission.

This notebook implements a hybrid symbolic + local LLM solver.
- Symbolic solvers for: gravity, unit_conversion, numeral, bit_manip
- Model fallback (Gemma-4 via Lemonade on port 8002) for equations, encryption
"""
from __future__ import annotations

import csv
import random
import re
from pathlib import Path

import requests


# ---------------------------------------------------------------------------
# Model configuration
# ---------------------------------------------------------------------------
LEMONADE_API = "http://127.0.0.1:8002/v1"
MODEL_NAME = "Gemma-4-26B-A4B-it-GGUF"


def _call_model(prompt: str, max_tokens: int = 64) -> str:
    """Call local Gemma-4 via Lemonade with short, direct prompts."""
    req = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "max_tokens": max_tokens,
        "stream": False,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    try:
        r = requests.post(f"{LEMONADE_API}/chat/completions", json=req, timeout=30)
        r.raise_for_status()
        data = r.json()
        text = data["choices"][0]["message"]["content"]
        text = text.strip().strip('"').strip("'")
        return text
    except Exception:
        return ""


def solve_with_model(examples: list[tuple[str, str]], test_in: str, ptype: str) -> str:
    """Use Gemma-4 as fallback for hard problem types."""
    prompt = "Solve the puzzle. Output the final answer ONLY, no explanation.\n\n"
    for inp, out in examples[:4]:
        prompt += f"{inp} = {out}\n"
    prompt += f"{test_in} ="
    return _call_model(prompt, max_tokens=64)


def parse_examples(prompt: str) -> list[tuple[str, str]]:
    """Extract input->output pairs from prompt text."""
    pairs = []
    for line in prompt.split("\n"):
        line = line.strip()
        if " -> " in line and not line.startswith("Here") and not line.startswith("Now"):
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
    return pairs


def classify_problem(prompt: str) -> str:
    p = prompt.lower()
    if "bit manipulation" in p:
        return "bit_manip"
    elif "gravitational constant" in p or "falling distance" in p:
        return "gravity"
    elif "unit conversion" in p:
        return "unit_conversion"
    elif "equation" in p or "transformation rules" in p:
        return "equations"
    elif "numeral system" in p or "roman" in p:
        return "numeral"
    elif "encryption" in p or "decrypt" in p:
        return "encryption"
    return "unknown"


def extract_test_input(prompt: str) -> str:
    patterns = [
        r"determine the output for:\s*([0-9a-zA-Z\s.]+)",
        r"convert the following measurement:\s*([0-9.]+\s*m?)",
        r"write the number\s+([0-9]+)\s+in the",
        r"determine the result for:\s*([^\n]+)",
        r"decrypt the following text:\s*([^\n]+)",
        r"determine the falling distance for\s+t\s*=\s*([0-9.]+s?)",
    ]
    for pat in patterns:
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


def _format_number(value: float, examples: list[tuple[str, str]]) -> str:
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
        return f"{int(round(value))}"
    return f"{value:.{precision}f}"


# ---------------------------------------------------------------------------
# Gravity solver
# ---------------------------------------------------------------------------
def solve_gravity(examples: list[tuple[str, str]], test_t: str) -> str:
    ts, ds = [], []
    for t_str, d_str in examples:
        try:
            t = float(re.search(r"([0-9.]+)", t_str).group(1))
            d = float(re.search(r"([0-9.]+)", d_str).group(1))
            ts.append(t)
            ds.append(d)
        except Exception:
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
    except Exception:
        return "0.0"
    result = 0.5 * best_g * test_t_val * test_t_val
    return _format_number(result, examples)


# ---------------------------------------------------------------------------
# Unit conversion solver
# ---------------------------------------------------------------------------
def solve_unit_conversion(examples: list[tuple[str, str]], test_x: str) -> str:
    xs, ys = [], []
    for x_str, y_str in examples:
        try:
            x = float(re.search(r"([0-9.]+)", x_str).group(1))
            y = float(re.search(r"([0-9.]+)", y_str).group(1))
            xs.append(x)
            ys.append(y)
        except Exception:
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
        except Exception:
            return "0.0"
        return _format_number(k * test_val, examples)
    a = (n * sum_xy - sum_x * sum_y) / denom
    b = (sum_y - a * sum_x) / n
    try:
        test_val = float(re.search(r"([0-9.]+)", test_x).group(1))
    except Exception:
        return "0.0"
    result = a * test_val + b
    return _format_number(result, examples)


# ---------------------------------------------------------------------------
# Numeral solver (Roman numerals)
# ---------------------------------------------------------------------------
def int_to_roman(n: int) -> str:
    val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
    syms = ["M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"]
    result = ""
    for v, s in zip(val, syms):
        while n >= v:
            result += s
            n -= v
    return result


def solve_numeral(examples: list[tuple[str, str]], test_n: str) -> str:
    try:
        n = int(re.search(r"([0-9]+)", test_n).group(1))
    except Exception:
        return ""
    return int_to_roman(n)


# ---------------------------------------------------------------------------
# Bit manipulation solver v2
# ---------------------------------------------------------------------------
def solve_bit_manip(examples: list[tuple[str, str]], test_in: str) -> str:
    pairs = []
    for inp, out in examples:
        if len(inp) == 8 and set(inp).issubset({"0", "1"}):
            try:
                pairs.append((int(inp, 2), int(out, 2)))
            except Exception:
                pass
    if not pairs:
        return test_in

    def _check_per_bit_mapping():
        for out_bit in range(8):
            for in_bit in range(8):
                ok = True
                for a, b in pairs:
                    expected = (b >> out_bit) & 1
                    actual = (a >> in_bit) & 1
                    if expected != actual:
                        ok = False
                        break
                if ok:
                    yield ("bit", out_bit, in_bit, False)
                ok = True
                for a, b in pairs:
                    expected = (b >> out_bit) & 1
                    actual = 1 - ((a >> in_bit) & 1)
                    if expected != actual:
                        ok = False
                        break
                if ok:
                    yield ("bit", out_bit, in_bit, True)
            ok = True
            for a, b in pairs:
                if ((b >> out_bit) & 1) != 0:
                    ok = False
                    break
            if ok:
                yield ("const", out_bit, 0, False)
            ok = True
            for a, b in pairs:
                if ((b >> out_bit) & 1) != 1:
                    ok = False
                    break
            if ok:
                yield ("const", out_bit, 1, False)

    mapping = {}
    for typ, out_bit, val, invert in _check_per_bit_mapping():
        mapping[out_bit] = (typ, val, invert)

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
                result |= (bit << out_bit)
            return f"{result:08b}"
        except Exception:
            pass

    def _check_affine():
        for xor_const in range(256):
            ok = True
            for a, b in pairs:
                if (a ^ xor_const) != b:
                    ok = False
                    break
            if ok:
                return ("xor", xor_const)
        for and_const in range(256):
            ok = True
            for a, b in pairs:
                if (a & and_const) != b:
                    ok = False
                    break
            if ok:
                return ("and", and_const)
        for or_const in range(256):
            ok = True
            for a, b in pairs:
                if (a | or_const) != b:
                    ok = False
                    break
            if ok:
                return ("or", or_const)
        for add_const in range(256):
            ok = True
            for a, b in pairs:
                if ((a + add_const) & 0xFF) != b:
                    ok = False
                    break
            if ok:
                return ("add", add_const)
        return None

    affine = _check_affine()
    if affine:
        try:
            test_val = int(test_in, 2)
            op_name, const = affine
            if op_name == "xor":
                return f"{(test_val ^ const):08b}"
            elif op_name == "and":
                return f"{(test_val & const):08b}"
            elif op_name == "or":
                return f"{(test_val | const):08b}"
            elif op_name == "add":
                return f"{((test_val + const) & 0xFF):08b}"
        except Exception:
            pass

    unary_ops = [
        ("not", lambda x: (~x) & 0xFF),
        ("reverse", lambda x: int(f"{x:08b}"[::-1], 2)),
        ("flip", lambda x: x ^ 0xFF),
        ("shift_left_1", lambda x: ((x << 1) & 0xFF)),
        ("shift_right_1", lambda x: (x >> 1)),
        ("rot_left_1", lambda x: ((x << 1) & 0xFF) | (x >> 7)),
        ("rot_right_1", lambda x: ((x >> 1) | ((x & 1) << 7))),
        ("reverse_nibble", lambda x: (((x & 0x0F) << 4) | ((x & 0xF0) >> 4))),
        ("not_reverse", lambda x: int(f"{(~x) & 0xFF:08b}"[::-1], 2)),
    ]

    for name, op in unary_ops:
        ok = True
        for a, b in pairs:
            if op(a) != b:
                ok = False
                break
        if ok:
            try:
                test_val = int(test_in, 2)
                return f"{op(test_val):08b}"
            except Exception:
                pass

    for n1, o1 in unary_ops:
        for n2, o2 in unary_ops:
            ok = True
            for a, b in pairs:
                if o2(o1(a)) != b:
                    ok = False
                    break
            if ok:
                try:
                    test_val = int(test_in, 2)
                    return f"{o2(o1(test_val)):08b}"
                except Exception:
                    pass

    for const in range(256):
        for op_name, op_fn in [
            ("xor", lambda x, c: x ^ c),
            ("and", lambda x, c: x & c),
            ("or", lambda x, c: x | c),
            ("add", lambda x, c: (x + c) & 0xFF),
            ("sub", lambda x, c: (x - c) & 0xFF),
        ]:
            for n1, o1 in unary_ops:
                ok = True
                for a, b in pairs:
                    if op_fn(o1(a), const) != b:
                        ok = False
                        break
                if ok:
                    try:
                        test_val = int(test_in, 2)
                        return f"{op_fn(o1(test_val), const):08b}"
                    except Exception:
                        pass
            for n2, o2 in unary_ops:
                ok = True
                for a, b in pairs:
                    if o2(op_fn(a, const)) != b:
                        ok = False
                        break
                if ok:
                    try:
                        test_val = int(test_in, 2)
                        return f"{o2(op_fn(test_val, const)):08b}"
                    except Exception:
                        pass

    return test_in


# ---------------------------------------------------------------------------
# Equation solver
# ---------------------------------------------------------------------------
def solve_equations(examples: list[tuple[str, str]], test_in: str) -> str:
    return solve_with_model(examples, test_in, "equations")


# ---------------------------------------------------------------------------
# Encryption solver
# ---------------------------------------------------------------------------
def solve_encryption(examples: list[tuple[str, str]], test_in: str) -> str:
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
    test_words = test_in.split()
    result_words = []
    for tw in test_words:
        mapped = ""
        for c in tw:
            mapped += mapping.get(c, c)
        result_words.append(mapped)
    return " ".join(result_words)


# ---------------------------------------------------------------------------
# Main solver
# ---------------------------------------------------------------------------
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
        result = solve_bit_manip(examples, test_input)
        if result == test_input or len(result) != 8:
            result = solve_with_model(examples, test_input, ptype)
        return result
    elif ptype == "equations":
        return solve_equations(examples, test_input)
    elif ptype == "encryption":
        result = solve_encryption(examples, test_input)
        if not any(c in result.lower() for c in "aeiou") or len(result.split()) != len(test_input.split()):
            result = solve_with_model(examples, test_input, ptype)
        return result
    else:
        return solve_with_model(examples, test_input, ptype)


# ---------------------------------------------------------------------------
# Kaggle: read test.csv, write submission.csv
# ---------------------------------------------------------------------------
with open("/kaggle/input/nvidia-nemotron-model-reasoning-challenge/test.csv") as f:
    rows = list(csv.DictReader(f))

results = []
for r in rows:
    pred = solve(r["prompt"])
    results.append({"id": r["id"], "answer": pred.strip()})

with open("submission.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["id", "answer"])
    writer.writeheader()
    writer.writerows(results)

print(f"Generated {len(results)} predictions in submission.csv")
