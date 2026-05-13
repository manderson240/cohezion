"""NVIDIA Nemotron Reasoning Challenge — Pattern Induction Solver.

Approaches each problem type with a tailored symbolic solver:
- gravity: solve for g in d=0.5*g*t^2 from examples
- unit_conversion: find linear/non-linear mapping
- numeral: Roman numeral conversion
- bit_manip: brute-force search over bit operations
- equations: symbol substitution mapping
- encryption: character frequency/mapping analysis
"""

from __future__ import annotations

import csv
import random
import re
from itertools import combinations
from pathlib import Path

import requests


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
        # Clean up
        text = text.strip().strip('"').strip("'")
        return text
    except Exception:
        return ""


def solve_with_model(examples: list[tuple[str, str]], test_in: str, ptype: str) -> str:
    """Use Gemma-4 as fallback for hard problem types."""
    # Build a concise prompt with up to 4 examples
    prompt = "Solve the puzzle. Output the final answer ONLY, no explanation.\n\n"
    for inp, out in examples[:4]:
        prompt += f"{inp} = {out}\n"
    prompt += f"{test_in} ="

    return _call_model(prompt, max_tokens=64)


def parse_examples(prompt: str, ptype: str = "") -> list[tuple[str, str]]:
    """Extract input->output pairs from prompt text.

    Handles multiple formats:
    - "X -> Y" (bit_manip, equations)
    - "X becomes Y" (unit_conversion)
    - "For t = Xs, distance = Y m" (gravity)
    - "A -> B" with Roman numeral or number (numeral)
    - "text1 -> text2" (encryption)
    - "X = Y" (equations with equals sign)
    """
    pairs = []
    for line in prompt.split("\n"):
        line = line.strip()
        # Standard "->" pattern
        if " -> " in line and (not line.startswith("Here") and not line.startswith("Now")):
            parts = line.split(" -> ")
            if len(parts) == 2:
                pairs.append((parts[0].strip(), parts[1].strip()))
        # "becomes" pattern
        elif " becomes " in line and not line.startswith("Now"):
            parts = line.split(" becomes ")
            if len(parts) == 2:
                pairs.append((parts[0].strip(), parts[1].strip()))
        # Equations pattern: "X = Y" (only for equation problems)
        elif (
            ptype == "equations"
            and " = " in line
            and not line.startswith("Now")
            and not line.startswith("Here")
        ):
            parts = line.split(" = ")
            if len(parts) == 2:
                pairs.append((parts[0].strip(), parts[1].strip()))
        # Gravity pattern: "For t = Xs, distance = Y m"
        elif line.startswith("For t =") and "distance =" in line:
            m = re.search(r"t\s*=\s*([0-9.]+s?)", line)
            n = re.search(r"distance\s*=\s*([0-9.]+)\s*m", line)
            if m and n:
                pairs.append((m.group(1), n.group(1) + " m"))
    return pairs


def classify_problem(prompt: str) -> str:
    """Classify problem type from prompt text."""
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
    """Extract the test input from the prompt."""
    # Various patterns for test input
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
    # Fallback: look for last line that looks like input
    lines = [ln.strip() for ln in prompt.split("\n") if ln.strip()]
    for line in reversed(lines):
        if not line.startswith("In Alice") and " -> " not in line and " becomes " not in line:
            # Clean up: remove prefixes like "Now, determine..."
            if ":" in line:
                return line.split(":", 1)[1].strip()
            return line
    return ""


# ---------------------------------------------------------------------------
# Gravity solver
# ---------------------------------------------------------------------------
def _ls_fit(xs: list[float], ys: list[float]) -> float:
    """Least-squares fit y = g * x (no intercept)."""
    sum_xy = sum(x * y for x, y in zip(xs, ys))
    sum_x2 = sum(x * x for x in xs)
    return sum_xy / sum_x2 if sum_x2 != 0 else 0.0


def solve_gravity(examples: list[tuple[str, str]], test_t: str) -> str:
    """Solve gravity problems. Tries multiple physical models and picks best fit."""
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

    try:
        test_t_val = float(re.search(r"([0-9.]+)", test_t).group(1))
    except Exception:
        return "0.0"

    # Try multiple physical models: d = g * f(t) for different f
    models = [
        ("half_t2", lambda t: 0.5 * t * t, lambda g, t: 0.5 * g * t * t),
        ("t2", lambda t: t * t, lambda g, t: g * t * t),
        ("half_t3", lambda t: 0.5 * t * t * t, lambda g, t: 0.5 * g * t * t * t),
        ("t", lambda t: t, lambda g, t: g * t),
        ("t3", lambda t: t * t * t, lambda g, t: g * t * t * t),
    ]

    best_result = None
    best_mse = float("inf")

    for _model_name, feat_fn, pred_fn in models:
        try:
            xs = [feat_fn(t) for t in ts]
            g = _ls_fit(xs, ds)
            if g <= 0:
                continue
            mse = sum((pred_fn(g, t) - d) ** 2 for t, d in zip(ts, ds))

            # Precision voting: for this g, generate candidate formatted outputs
            # and pick the one matching the most training examples exactly
            raw_result = pred_fn(g, test_t_val)
            fmt = _format_number(raw_result, examples)

            if mse < best_mse:
                best_mse = mse
                best_result = fmt
        except Exception:
            continue

    if best_result is not None:
        return best_result
    return "0.0"


def _format_number(value: float, examples: list[tuple[str, str]]) -> str:
    """Format a number matching the precision of training examples."""
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
# Unit conversion solver
# ---------------------------------------------------------------------------
def solve_unit_conversion(examples: list[tuple[str, str]], test_x: str) -> str:
    """Find conversion formula from examples. Try linear first."""
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
    # Linear fit: y = a*x + b
    n = len(xs)
    sum_x = sum(xs)
    sum_y = sum(ys)
    sum_xy = sum(x * y for x, y in zip(xs, ys))
    sum_x2 = sum(x * x for x in xs)
    denom = n * sum_x2 - sum_x * sum_x
    if abs(denom) < 1e-10:
        # Try y = k * x (no offset)
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
    """Convert integer to Roman numeral."""
    val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
    syms = ["M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"]
    result = ""
    for v, s in zip(val, syms):
        while n >= v:
            result += s
            n -= v
    return result


def solve_numeral(examples: list[tuple[str, str]], test_n: str) -> str:
    """Convert number to numeral system (assumed Roman)."""
    try:
        n = int(re.search(r"([0-9]+)", test_n).group(1))
    except Exception:
        return ""
    return int_to_roman(n)


# ---------------------------------------------------------------------------
# Bit manipulation solver
# ---------------------------------------------------------------------------


def _lut_search(pairs: list[tuple[int, int]], max_k: int = 3) -> dict | None:
    """Find a k-ary Boolean function (truth table) for each output bit.

    For each of the 8 output bits, tries to express it as a Boolean function
    of k input bits (k=2..max_k). Returns a complete mapping {out_bit: (in_bits, tt)}
    if all 8 output bits are covered, or None if any bit can't be resolved.

    The truth table `tt` is an integer where bit `idx` = f(in_combo), and
    `idx` encodes the k input bits: idx = b0 | (b1 << 1) | (b2 << 2) | ...

    Search order: named 2-input functions (XOR, AND, OR, etc.) before arbitrary TTs,
    to avoid spurious matches from underspecified examples.
    """
    # k=2 named operations by preference (most common in bit-manip puzzles first)
    # truth table indexed by (b0, b1): b0 LSB, b1 next bit → idx = b0 + 2*b1
    # idx: (0,0)=0, (1,0)=1, (0,1)=2, (1,1)=3
    _named_tt_k2 = [
        6,  # XOR:  0^0=0,1^0=1,0^1=1,1^1=0 → 0110
        8,  # AND:  1 only when both 1     → 1000
        14,  # OR:   1 unless both 0        → 1110
        1,  # NOR:  NOT OR                 → 0001
        7,  # NAND: NOT AND                → 0111
        9,  # XNOR: NOT XOR               → 1001
        12,  # b1 identity: 0,0,1,1        → 1100
        10,  # b0 identity: 0,1,0,1        → 1010
        3,  # NOT b0: 1,0,1,0             → 0011
        5,  # NOT b1: 1,1,0,0             → 0101
        11,  # b0 OR NOT b1                → 1011
        13,  # NOT b0 OR b1                → 1101
        4,  # b0 AND NOT b1               → 0100
        2,  # NOT b0 AND b1               → 0010
        0,  # const 0                     → 0000
        15,  # const 1                     → 1111
    ]

    result = {}
    for out_bit in range(8):
        found = False
        # k=2: try named TTs first (in preference order), then arbitrary
        if not found:
            for in_bits in combinations(range(8), 2):
                obs: dict[int, int] = {}
                consistent = True
                for a, b in pairs:
                    idx = ((a >> in_bits[0]) & 1) | (((a >> in_bits[1]) & 1) << 1)
                    expected = (b >> out_bit) & 1
                    if idx in obs and obs[idx] != expected:
                        consistent = False
                        break
                    obs[idx] = expected
                if not consistent:
                    continue
                # Try named TTs first, then arbitrary
                for tt in _named_tt_k2:
                    if all((tt >> idx) & 1 == val for idx, val in obs.items()):
                        result[out_bit] = (in_bits, tt)
                        found = True
                        break
                if not found:
                    # Arbitrary TT (for exotic patterns)
                    for tt in range(16):
                        if tt in _named_tt_k2:
                            continue
                        if all((tt >> idx) & 1 == val for idx, val in obs.items()):
                            result[out_bit] = (in_bits, tt)
                            found = True
                            break
                if found:
                    break

        # k=3 fallback
        if not found and max_k >= 3:
            for in_bits in combinations(range(8), 3):
                obs_k3: dict[int, int] = {}
                consistent = True
                for a, b in pairs:
                    idx = sum(((a >> ib) & 1) << i for i, ib in enumerate(in_bits))
                    expected = (b >> out_bit) & 1
                    if idx in obs_k3 and obs_k3[idx] != expected:
                        consistent = False
                        break
                    obs_k3[idx] = expected
                if not consistent:
                    continue
                for tt in range(256):
                    if all((tt >> idx) & 1 == val for idx, val in obs_k3.items()):
                        result[out_bit] = (in_bits, tt)
                        found = True
                        break
                if found:
                    break

        if not found:
            return None
    return result


# ---------------------------------------------------------------------------
# Bit manipulation solver v2 — per-bit mapping + affine models + LUT
# ---------------------------------------------------------------------------
def solve_bit_manip(examples: list[tuple[str, str]], test_in: str) -> str:
    """Brute-force search over bit operations."""
    # Parse examples
    pairs = []
    for inp, out in examples:
        if len(inp) == 8 and set(inp).issubset({"0", "1"}):
            try:
                pairs.append((int(inp, 2), int(out, 2)))
            except Exception:
                pass
    if not pairs:
        return test_in

    # --- Phase 1: Per-bit mapping ---
    # For each output bit position (0 = LSB, 7 = MSB), check if it equals
    # any input bit, its NOT, or a constant
    def _bit_matches(out_bit: int, in_bit: int, invert: bool) -> bool:
        for a, b in pairs:
            expected = (b >> out_bit) & 1
            actual = (a >> in_bit) & 1
            if invert:
                actual = 1 - actual
            if expected != actual:
                return False
        return True

    # Phase 1 strategy: detect pure bit permutations and constant bits.
    # Inverted mappings (same-position NOT, cross-position NOT) are NOT handled here —
    # they cause spurious matches with small example sets and are better handled
    # globally by Phase 2 (XOR constant), Phase 3 (NOT), and Phase 4 (two-op).
    mapping: dict[int, tuple] = {}

    for out_bit in range(8):
        if all(((b >> out_bit) & 1) == 0 for _, b in pairs):
            mapping[out_bit] = ("const", 0, False)
        elif all(((b >> out_bit) & 1) == 1 for _, b in pairs):
            mapping[out_bit] = ("const", 1, False)
        else:
            # Direct permutation: output[out_bit] = input[in_bit] (any in_bit)
            for in_bit in range(8):
                if _bit_matches(out_bit, in_bit, False):
                    mapping[out_bit] = ("bit", in_bit, False)
                    break

    if len(mapping) == 8:
        # Validate: bit-type mappings must form a bijection (no two output bits from same input)
        source_bits = [v[1] for v in mapping.values() if v[0] == "bit"]
        is_bijection = len(source_bits) == len(set(source_bits))
        if is_bijection:
            try:
                test_val = int(test_in, 2)
                result = 0
                for out_bit in range(8):
                    typ, val, invert = mapping[out_bit]
                    if typ == "const":
                        bit = val
                    else:
                        bit = (test_val >> val) & 1
                    result |= bit << out_bit
                return f"{result:08b}"
            except Exception:
                pass

    # --- Phase 2: Affine model (XOR with constant and/or input mask) ---
    def _check_affine():
        for xor_const in range(256):
            # y = x ^ const
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

    # --- Phase 3: Unary ops ---
    unary_ops = [
        ("not", lambda x: (~x) & 0xFF),
        ("reverse", lambda x: int(f"{x:08b}"[::-1], 2)),
        ("flip", lambda x: x ^ 0xFF),
        ("shift_left_1", lambda x: (x << 1) & 0xFF),
        ("shift_right_1", lambda x: x >> 1),
        ("rot_left_1", lambda x: ((x << 1) & 0xFF) | (x >> 7)),
        ("rot_right_1", lambda x: (x >> 1) | ((x & 1) << 7)),
        ("shift_left_2", lambda x: (x << 2) & 0xFF),
        ("shift_right_2", lambda x: x >> 2),
        ("rot_left_2", lambda x: ((x << 2) & 0xFF) | (x >> 6)),
        ("rot_right_2", lambda x: (x >> 2) | ((x & 0x3) << 6)),
        ("shift_left_3", lambda x: (x << 3) & 0xFF),
        ("shift_right_3", lambda x: x >> 3),
        ("rot_left_3", lambda x: ((x << 3) & 0xFF) | (x >> 5)),
        ("rot_right_3", lambda x: (x >> 3) | ((x & 0x7) << 5)),
        ("shift_left_4", lambda x: (x << 4) & 0xFF),
        ("shift_right_4", lambda x: x >> 4),
        ("rot_left_4", lambda x: ((x << 4) & 0xFF) | (x >> 4)),
        ("rot_right_4", lambda x: (x >> 4) | ((x & 0xF) << 4)),
        ("reverse_nibble", lambda x: ((x & 0x0F) << 4) | ((x & 0xF0) >> 4)),
        ("not_reverse", lambda x: int(f"{(~x) & 0xFF:08b}"[::-1], 2)),
    ]

    for _name, op in unary_ops:
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

    # --- Phase 4: Two-op compositions of unary ops ---
    for _n1, o1 in unary_ops:
        for _n2, o2 in unary_ops:
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

    # --- Phase 5: Unary + constant ---
    for const in range(256):
        for _op_name, op_fn in [
            ("xor", lambda x, c: x ^ c),
            ("and", lambda x, c: x & c),
            ("or", lambda x, c: x | c),
            ("add", lambda x, c: (x + c) & 0xFF),
            ("sub", lambda x, c: (x - c) & 0xFF),
        ]:
            for _n1, o1 in unary_ops:
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
            # Constant then unary
            for _n2, o2 in unary_ops:
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

    # --- Phase 6a: Global uniform cross-bit pattern ---
    # Test: output[i] = f(input[i], input[(i + offset) % 8]) for ALL bits simultaneously.
    # Covers XOR/AND/OR of adjacent bits, which are common competition patterns.
    _cross_bit_funcs = [
        ("xor", lambda a, b: a ^ b),
        ("and", lambda a, b: a & b),
        ("or", lambda a, b: a | b),
        ("nand", lambda a, b: 1 - (a & b)),
        ("nor", lambda a, b: 1 - (a | b)),
        ("xnor", lambda a, b: 1 - (a ^ b)),
        ("a_and_not_b", lambda a, b: a & (1 - b)),
        ("not_a_and_b", lambda a, b: (1 - a) & b),
        ("a_only", lambda a, b: a),
        ("b_only", lambda a, b: b),
        ("not_a", lambda a, b: 1 - a),
        ("not_b", lambda a, b: 1 - b),
    ]
    for offset in range(1, 8):
        for _fname, ffn in _cross_bit_funcs:
            ok = True
            for a, b in pairs:
                for out_bit in range(8):
                    expected = (b >> out_bit) & 1
                    ai = (a >> out_bit) & 1
                    bi = (a >> ((out_bit + offset) % 8)) & 1
                    if ffn(ai, bi) != expected:
                        ok = False
                        break
                if not ok:
                    break
            if ok:
                try:
                    test_val = int(test_in, 2)
                    result = 0
                    for out_bit in range(8):
                        ai = (test_val >> out_bit) & 1
                        bi = (test_val >> ((out_bit + offset) % 8)) & 1
                        result |= ffn(ai, bi) << out_bit
                    return f"{result:08b}"
                except Exception:
                    pass

    # --- Phase 6b: Per-bit LUT synthesis (fallback for exotic patterns) ---
    # Each output bit is independently solved using a k-input Boolean function.
    lut_mapping = _lut_search(pairs, max_k=3)
    if lut_mapping is not None:
        try:
            test_val = int(test_in, 2)
            result = 0
            for out_bit in range(8):
                in_bits, tt = lut_mapping[out_bit]
                idx = sum(((test_val >> ib) & 1) << i for i, ib in enumerate(in_bits))
                bit = (tt >> idx) & 1
                result |= bit << out_bit
            return f"{result:08b}"
        except Exception:
            pass

    # --- Phase 7: Partial mapping fallback ---
    # If Phase 1 found >= 4 bits but not all 8, use known bits + zeros for unknown.
    if len(mapping) >= 4:
        try:
            test_val = int(test_in, 2)
            result = 0
            for out_bit in range(8):
                if out_bit not in mapping:
                    continue
                typ, val, invert = mapping[out_bit]
                if typ == "const":
                    bit = val
                else:
                    bit = (test_val >> val) & 1
                    if invert:
                        bit = 1 - bit
                result |= bit << out_bit
            return f"{result:08b}"
        except Exception:
            pass

    return test_in


# ---------------------------------------------------------------------------
# Equation solver (symbol substitution)
# ---------------------------------------------------------------------------
def solve_equations(examples: list[tuple[str, str]], test_in: str) -> str:
    """Try to infer transformation rule from examples.

    For symbol equations, try structural rules (first+last, reverse, etc.).
    For number equations, try digit-wise operations.
    """
    # Check if this is a number-based or symbol-based equation
    first_in = examples[0][0] if examples else ""
    has_digits = any(c.isdigit() for c in first_in)

    if has_digits:
        # Number equations: try digit-wise operations
        return _solve_number_equations(examples, test_in)
    else:
        # Symbol equations: try structural rules
        return _solve_symbol_equations(examples, test_in)


def _solve_symbol_equations(examples: list[tuple[str, str]], test_in: str) -> str:
    """Try structural transformations on symbol sequences."""
    rules = [
        # Position-based rules
        lambda s: s[0] + s[-1] if len(s) >= 2 else s,  # first+last
        lambda s: s[-1] + s[0] if len(s) >= 2 else s,  # last+first
        lambda s: s[::-1],  # reverse all
        lambda s: s[0] if s else "",  # first only
        lambda s: s[-1] if s else "",  # last only
        lambda s: s[::2],  # every other from start
        lambda s: s[1::2],  # every other from second
        lambda s: s[1:-1] if len(s) >= 3 else s,  # middle
        lambda s: s[0] + s[1:-1][::-1] + s[-1] if len(s) >= 3 else s,  # reverse middle
        lambda s: s[-1] + s[1:-1] + s[0] if len(s) >= 3 else s,  # swap ends
    ]
    # Also try character substitution (position-dependent)
    for rule in rules:
        ok = True
        for inp, out in examples:
            # Strip operators/backticks if present
            clean_inp = inp.strip("`'\\\"\n ")
            clean_out = out.strip("`'\\\"\n ")
            try:
                if rule(clean_inp) != clean_out:
                    ok = False
                    break
            except Exception:
                ok = False
                break
        if ok:
            try:
                clean_test = test_in.strip("`'\\\"\n ")
                return rule(clean_test)
            except Exception:
                pass
    # Fallback: try character mapping
    mapping = {}
    for inp, out in examples:
        # Try same-length matching
        if len(inp) == len(out):
            for c_in, c_out in zip(inp, out):
                if c_in not in mapping or mapping[c_in] == c_out:
                    mapping[c_in] = c_out
    result = ""
    for c in test_in:
        result += mapping.get(c, c)
    return result if result else test_in


def _solve_number_equations(examples: list[tuple[str, str]], test_in: str) -> str:
    """Try digit-wise operations for number equations."""
    # Parse operator
    # Check if test input has enough numeric parts to work with
    _num_parts = [p for p in re.split(r"[^0-9]", test_in) if p]
    if len(_num_parts) < 2:
        return test_in

    def apply_ops(a: int, b: int) -> list[int]:
        """Return results of various operations."""
        results = []
        da = [int(d) for d in str(a)]
        db = [int(d) for d in str(b)]
        results.append((a + b, "add"))
        results.append((abs(a - b), "sub"))
        results.append((a * b, "mul"))
        if b != 0:
            results.append((a // b, "div"))
        results.append((sum(da + db), "sum_digits"))
        results.append((abs(sum(da) - sum(db)), "diff_sum"))
        results.append((da[0] * 10 + db[-1] if da and db else 0, "first_last"))
        results.append(
            (
                int(str(da[0]) * 2 + str(sum(db)) + str(abs(db[0] - db[-1]))) if da and db else 0,
                "custom88",
            )
        )
        results.append((int("".join(map(str, da + db))), "concat"))
        return results

    # Find operation that matches all examples
    for _res, _op_name in apply_ops(0, 0):
        pass  # just to get list

    # Brute-force: try each flat operation, then depth-2 expression trees
    _base_ops = [
        lambda a, b: a + b,
        lambda a, b: abs(a - b),
        lambda a, b: a - b,
        lambda a, b: a * b,
        lambda a, b: a // b if b != 0 else 0,
        lambda a, b: a % b if b != 0 else 0,
        lambda a, b: max(a, b),
        lambda a, b: min(a, b),
        lambda a, b: a | b,
        lambda a, b: a & b,
        lambda a, b: a ^ b,
        lambda a, b: sum(int(d) for d in str(a) + str(b)),
        lambda a, b: abs(sum(int(d) for d in str(a)) - sum(int(d) for d in str(b))),
        lambda a, b: int(str(a) + str(b)),
        lambda a, b: int(str(b) + str(a)),
        lambda a, b: int(str(len(str(a))) + str(len(str(b)))),
        lambda a, b: len(str(a)) + len(str(b)),
        lambda a, b: len(str(a)) * len(str(b)),
    ]

    def _try_op(op_fn: object, examples: list, test_in: str) -> str | None:
        ok = True
        for inp, out in examples:
            try:
                parts = [p for p in re.split(r"[^0-9]", inp) if p]
                if len(parts) != 2:
                    continue
                a, b = int(parts[0]), int(parts[1])
                m = re.search(r"-?[0-9]+", out)
                if not m:
                    continue
                expected = int(m.group())
                if op_fn(a, b) != expected:
                    ok = False
                    break
            except Exception:
                ok = False
                break
        if ok:
            try:
                parts = [p for p in re.split(r"[^0-9]", test_in) if p]
                if len(parts) == 2:
                    a, b = int(parts[0]), int(parts[1])
                    return str(op_fn(a, b))
            except Exception:
                pass
        return None

    # Phase 1: flat operations
    for op_fn in _base_ops:
        result = _try_op(op_fn, examples, test_in)
        if result is not None:
            return result

    # Phase 2: depth-2 expression trees — op1(op2(a, b), c) for small constants
    # and op1(a, op2(a, b)) / op1(op2(a,b), a) / op1(op2(a,b), b)
    _small_consts = [1, 2, 3, 10, 100]
    for outer in _base_ops[:8]:  # most common outer ops
        for inner in _base_ops[:8]:
            for make_ab in [
                lambda a, b, f=inner: (f(a, b), a),
                lambda a, b, f=inner: (f(a, b), b),
                lambda a, b, f=inner: (a, f(a, b)),
                lambda a, b, f=inner: (b, f(a, b)),
            ]:

                def tree_op(
                    a: int, b: int, outer: object = outer, make_ab: object = make_ab
                ) -> int:
                    x, y = make_ab(a, b)
                    return outer(x, y)

                result = _try_op(tree_op, examples, test_in)
                if result is not None:
                    return result
        # op1(op2(a, b), small_const)
        for inner in _base_ops[:6]:
            for c in _small_consts:

                def tree_const(
                    a: int,
                    b: int,
                    outer: object = outer,
                    inner: object = inner,
                    c: int = c,
                ) -> int:
                    return outer(inner(a, b), c)

                result = _try_op(tree_const, examples, test_in)
                if result is not None:
                    return result

    # Fallback: try to extract last example's pattern
    return test_in


# ---------------------------------------------------------------------------
# Encryption solver with dictionary completion
# ---------------------------------------------------------------------------
# Common words observed in the competition's Alice-themed encryption puzzles
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
    "thunder",
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
    "sword",
    "shield",
    "armor",
    "helmet",
    "cape",
    "robe",
    "hat",
    "shoe",
    "boot",
    "glove",
    "belt",
    "bag",
    "box",
    "chest",
    "bottle",
    "cup",
    "plate",
    "bowl",
    "spoon",
    "fork",
    "knife",
    "candle",
    "lamp",
    "torch",
    "paper",
    "pen",
    "ink",
    "paint",
    "brush",
    "canvas",
    "frame",
    "picture",
    "photo",
    "camera",
    "film",
    "tape",
    "record",
    "disk",
    "card",
    "coin",
    "dollar",
    "cent",
    "euro",
    "pound",
    "yen",
    "price",
    "cost",
    "value",
    "worth",
    "rich",
    "poor",
    "wealth",
    "gold",
    "money",
    "cash",
    "bank",
    "shop",
    "store",
    "market",
    "trade",
    "sell",
    "buy",
    "pay",
    "spend",
    "save",
    "keep",
    "hold",
    "have",
    "own",
    "give",
    "take",
    "get",
    "find",
    "lose",
    "search",
    "seek",
    "hunt",
    "track",
    "trace",
    "mark",
    "sign",
    "signal",
    "code",
    "word",
    "letter",
    "note",
    "text",
    "line",
    "page",
    "chapter",
    "title",
    "name",
    "label",
    "tag",
    "brand",
    "logo",
]


def solve_encryption(examples: list[tuple[str, str]], test_in: str) -> str:
    """Word-level substitution cipher solver with vocabulary completion."""
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

    # Apply initial mapping
    test_words = test_in.split()
    result_words = []
    for tw in test_words:
        mapped = ""
        for c in tw:
            mapped += mapping.get(c, "?")
        result_words.append(mapped)

    # Dictionary completion for missing characters (unique + most-frequent ambiguous)
    changed = True
    while changed:
        changed = False
        for _i, (tw, pw) in enumerate(zip(test_words, result_words)):
            if "?" not in pw:
                continue
            pattern = pw.replace("?", "?")
            matches = [
                w
                for w in _ENCRYPTION_VOCAB
                if len(w) == len(pattern) and _match_pattern(pattern, w)
            ]
            if len(matches) >= 1:  # Accept even ambiguous (pick most frequent)
                best = matches[0]
                for c_in, c_out in zip(tw, best):
                    if c_in not in mapping:
                        mapping[c_in] = c_out
                        changed = True
        # Rebuild result words with updated mapping
        result_words = []
        for tw in test_words:
            mapped = ""
            for c in tw:
                mapped += mapping.get(c, "?")
            result_words.append(mapped)

    return " ".join(result_words)


def _match_pattern(pattern: str, word: str) -> bool:
    """Check if word matches a pattern with ? wildcards."""
    if len(pattern) != len(word):
        return False
    for p, w in zip(pattern, word):
        if p != "?" and p != w:
            return False
    return True


# ---------------------------------------------------------------------------
# Main solver
# ---------------------------------------------------------------------------
def solve(prompt: str) -> str:
    """Classify and solve a single problem."""
    ptype = classify_problem(prompt)
    test_input = extract_test_input(prompt)
    examples = parse_examples(prompt, ptype)

    if ptype == "gravity":
        return solve_gravity(examples, test_input)
    elif ptype == "unit_conversion":
        return solve_unit_conversion(examples, test_input)
    elif ptype == "numeral":
        return solve_numeral(examples, test_input)
    elif ptype == "bit_manip":
        # Try symbolic first, fallback to model
        result = solve_bit_manip(examples, test_input)
        if result == test_input or len(result) != 8:
            result = solve_with_model(examples, test_input, ptype)
        return result
    elif ptype == "equations":
        # Symbolic solver is very weak for equations; always try model
        result = solve_with_model(examples, test_input, ptype)
        return result
    elif ptype == "encryption":
        # Symbolic then model fallback
        result = solve_encryption(examples, test_input)
        # Check if result looks like real words (has vowels)
        if not any(c in result.lower() for c in "aeiou") or len(result.split()) != len(
            test_input.split()
        ):
            result = solve_with_model(examples, test_input, ptype)
        return result
    else:
        return solve_with_model(examples, test_input, ptype)


def evaluate(train_path: str, sample: int = 0) -> float:
    """Evaluate on a sample of training data."""
    with open(train_path) as f:
        rows = list(csv.DictReader(f))
    if sample and sample < len(rows):
        rows = random.sample(rows, sample)

    correct = 0
    for r in rows:
        pred = solve(r["prompt"])
        if pred.strip() == r["answer"].strip():
            correct += 1
    return correct / len(rows) * 100 if rows else 0.0


if __name__ == "__main__":
    data_dir = Path("/tmp")
    if not (data_dir / "train.csv").exists():
        data_dir = Path("/home/mike-anderson/dev/cohezion/data")

    # Evaluate on training sample (hybrid symbolic + model)
    sample_size = 500
    random.seed(42)
    acc = evaluate(str(data_dir / "train.csv"), sample=sample_size)
    print(f"Hybrid accuracy on {sample_size} training examples: {acc:.1f}%")
    print(f"METRIC reasoning_accuracy={acc:.1f}")
