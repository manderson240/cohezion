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

    def _norm(s: str) -> str:
        """Strip trailing zeros: '55.30' → '55.3', '55.00' → '55'."""
        if "." in s:
            s = s.rstrip("0").rstrip(".")
        return s

    def _precision_vote(g_val: float, pred_fn: object) -> str:
        """Find the precision that maximizes exact matches on training examples."""
        best_prec, best_hits = 0, -1
        for prec in range(5):
            hits = 0
            for t, d in zip(ts, ds):
                pred = pred_fn(g_val, t)
                fmt_d = str(int(round(pred))) if prec == 0 else f"{pred:.{prec}f}"
                d_m = re.search(r"([0-9]+\.?[0-9]*)", str(d))
                if d_m and (_norm(fmt_d) == _norm(d_m.group(1))):
                    hits += 1
            if hits > best_hits:
                best_hits = hits
                best_prec = prec
        raw = pred_fn(g_val, test_t_val)
        if best_prec == 0:
            return str(int(round(raw)))
        return _norm(f"{raw:.{best_prec}f}")

    for _model_name, feat_fn, pred_fn in models:
        try:
            xs = [feat_fn(t) for t in ts]
            g = _ls_fit(xs, ds)
            if g <= 0:
                continue
            mse = sum((pred_fn(g, t) - d) ** 2 for t, d in zip(ts, ds))
            fmt = _precision_vote(g, pred_fn)
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
    """Find conversion formula from examples. Tries linear and non-linear fits."""
    import math

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

    try:
        test_val = float(re.search(r"([0-9.]+)", test_x).group(1))
    except Exception:
        return "0.0"

    def _mse(preds: list[float]) -> float:
        return sum((p - y) ** 2 for p, y in zip(preds, ys))

    def _hits(pred_vals: list[float]) -> int:
        return sum(
            1
            for pv, yv in zip(pred_vals, ys)
            if _format_number(pv, examples) == _format_number(yv, examples)
        )

    best_result = None
    # Track by (hits, -n_params, -mse) — more hits > fewer params > lower mse
    best_score: tuple[int, int, float] = (-1, 0, float("inf"))

    def _candidate(pred_test: float, pred_train: list[float], n_params: int = 1) -> None:
        nonlocal best_result, best_score
        h = _hits(pred_train)
        mse = _mse(pred_train)
        score = (h, -n_params, -mse)
        if score > best_score:
            best_score = score
            best_result = _format_number(pred_test, examples)

    # 1. Proportional: y = k*x (1 param — simpler, run first)
    # Try both LSQ mean AND each per-example k_i = y_i/x_i (fixes ±0.01 precision errors)
    n = len(xs)
    sum_x, sum_y = sum(xs), sum(ys)
    if sum_x != 0:
        k_lsq = sum_y / sum_x
        _candidate(k_lsq * test_val, [k_lsq * x for x in xs], n_params=1)
        for k_i in (y / x for x, y in zip(xs, ys) if x != 0):
            _candidate(k_i * test_val, [k_i * x for x in xs], n_params=1)

    # 2. Linear fit: y = a*x + b (2 params)
    sum_xy = sum(x * y for x, y in zip(xs, ys))
    sum_x2 = sum(x * x for x in xs)
    denom = n * sum_x2 - sum_x * sum_x
    if abs(denom) > 1e-10:
        a = (n * sum_xy - sum_x * sum_y) / denom
        b = (sum_y - a * sum_x) / n
        _candidate(a * test_val + b, [a * x + b for x in xs], n_params=2)

    # 3. Non-linear candidates: y = k/x, y = k*sqrt(x), y = k*x^2, y = k*x^3
    nl_models = [
        (lambda x: 1.0 / x if x != 0 else None, lambda k, x: k / x if x != 0 else 0),
        (lambda x: math.sqrt(x) if x >= 0 else None, lambda k, x: k * math.sqrt(abs(x))),
        (lambda x: x * x, lambda k, x: k * x * x),
        (lambda x: x * x * x, lambda k, x: k * x * x * x),
        (
            lambda x: math.log(x) if x > 0 else None,
            lambda k, x: k * math.log(abs(x)) if x != 0 else 0,
        ),
    ]
    for feat_fn, pred_fn in nl_models:
        try:
            feats = [feat_fn(x) for x in xs]
            if any(f is None for f in feats):
                continue
            sf = sum(feats)
            if abs(sf) < 1e-10:
                continue
            k = _ls_fit(feats, ys)
            if k == 0:
                continue
            _candidate(pred_fn(k, test_val), [pred_fn(k, x) for x in xs], n_params=1)
        except Exception:
            continue

    return best_result if best_result is not None else "0.0"


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

        # k=3 fallback — try named 3-input functions first to reduce spurious matches
        # Named k=3 TTs (indexed by b0|b1<<1|b2<<2): majority, XOR3, AND3, OR3, etc.
        _named_tt_k3 = [
            # XOR of all 3: output = b0^b1^b2
            # (0,0,0)=0,(1,0,0)=1,(0,1,0)=1,(1,1,0)=0,(0,0,1)=1,(1,0,1)=0,(0,1,1)=0,(1,1,1)=1
            0b10010110,  # XOR3 = 150
            # XNOR3 (NOT XOR3)
            0b01101001,  # XNOR3 = 105
            # Majority (at least 2 of 3)
            0b11101000,  # MAJ = 232
            # Minority (NOT majority)
            0b00010111,  # NMIN = 23
            # AND3
            0b10000000,  # AND3 = 128
            # OR3
            0b11111110,  # OR3 = 254
            # NAND3
            0b01111111,  # NAND3 = 127
            # NOR3
            0b00000001,  # NOR3 = 1
            # b2 identity (last bit passes through): b2
            0b11110000,  # b2 = 240
            # b1 identity
            0b11001100,  # b1 = 204
            # b0 identity
            0b10101010,  # b0 = 170
            # NOT b2
            0b00001111,  # NOT b2 = 15
            # NOT b1
            0b00110011,  # NOT b1 = 51
            # NOT b0
            0b01010101,  # NOT b0 = 85
        ]
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
                # Try named k=3 functions first, then arbitrary
                # Only try named TTs (no arbitrary fallback — too slow and underdetermined)
                for tt in _named_tt_k3:
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
        for mul_const in range(256):
            ok = True
            for a, b in pairs:
                if ((a * mul_const) & 0xFF) != b:
                    ok = False
                    break
            if ok:
                return ("mul", mul_const)
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
            elif op_name == "mul":
                return f"{((test_val * const) & 0xFF):08b}"
        except Exception:
            pass

    # --- Phase 3: Unary ops ---
    def _gray_code(x: int) -> int:
        return x ^ (x >> 1)

    def _degray(x: int) -> int:
        r = x
        for _ in range(4):
            r ^= r >> 1
        return r & 0xFF

    def _popcount_byte(x: int) -> int:
        return bin(x).count("1")

    def _parity(x: int) -> int:
        return _popcount_byte(x) & 1

    def _swap_adj_bits(x: int) -> int:
        return ((x & 0xAA) >> 1) | ((x & 0x55) << 1)

    def _rev_bits_in_nibbles(x: int) -> int:
        lo = int(f"{x & 0xF:04b}"[::-1], 2)
        hi = int(f"{(x >> 4) & 0xF:04b}"[::-1], 2)
        return lo | (hi << 4)

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
        # Extended ops (hardware/crypto bit manipulation patterns)
        ("gray_code", _gray_code),
        ("degray", _degray),
        ("swap_adj_bits", _swap_adj_bits),
        ("rev_bits_in_nibbles", _rev_bits_in_nibbles),
        ("rot_left_5", lambda x: ((x << 5) & 0xFF) | (x >> 3)),
        ("rot_right_5", lambda x: (x >> 5) | ((x & 0x1F) << 3)),
        ("rot_left_6", lambda x: ((x << 6) & 0xFF) | (x >> 2)),
        ("rot_right_6", lambda x: (x >> 6) | ((x & 0x3F) << 2)),
        ("rot_left_7", lambda x: ((x << 7) & 0xFF) | (x >> 1)),
        ("rot_right_7", lambda x: (x >> 7) | ((x & 0x7F) << 1)),
        ("not_rot_left_1", lambda x: (~((x << 1) & 0xFF | (x >> 7))) & 0xFF),
        ("not_rot_right_1", lambda x: (~((x >> 1) | ((x & 1) << 7))) & 0xFF),
        # Bit-count and parity ops (defined above but previously missing from list)
        ("popcount", _popcount_byte),
        ("parity_byte", lambda x: 0xFF if (_popcount_byte(x) & 1) else 0x00),
        ("popcount_spread", lambda x: ((1 << _popcount_byte(x)) - 1) & 0xFF),
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

    # --- Phase 4.5: Three-op compositions (subset of unary ops for tractability) ---
    # 16 ops = 16^3 = 4096 combos (covers all 3-bit shift/rot variants plus gray/swap)
    _fast_ops = unary_ops[:16]  # not, reverse, flip, shifts/rots 1-4, nibble swap
    for _n1, o1 in _fast_ops:
        for _n2, o2 in _fast_ops:
            for _n3, o3 in _fast_ops:
                ok = True
                for a, b in pairs:
                    if o3(o2(o1(a))) != b:
                        ok = False
                        break
                if ok:
                    try:
                        test_val = int(test_in, 2)
                        return f"{o3(o2(o1(test_val))):08b}"
                    except Exception:
                        pass

    # --- Phase 5.5: Two-unary binary ops: binary_fn(unary1(x), unary2(x)) ---
    # Covers patterns like (x >> 4) ^ (x & 0x0F), (x << 3) XOR rotr1(x), x*x mod 256, etc.
    _bin_fns = [
        (lambda a, b: a ^ b),
        (lambda a, b: a & b),
        (lambda a, b: a | b),
        (lambda a, b: (a + b) & 0xFF),
        (lambda a, b: (a - b) & 0xFF),
        (lambda a, b: (b - a) & 0xFF),
        (lambda a, b: (a * b) & 0xFF),  # multiply: covers x*x, x*reverse(x), etc.
        (lambda a, b: (~(a & b)) & 0xFF),  # NAND
        (lambda a, b: (~(a | b)) & 0xFF),  # NOR
        (lambda a, b: (~(a ^ b)) & 0xFF),  # XNOR
    ]
    for _n1, o1 in unary_ops:
        for _n2, o2 in unary_ops:
            if o1 is o2:
                continue  # skip trivial self-combinations (handled by Phase 2/3)
            for bf in _bin_fns:
                ok = True
                for a, b in pairs:
                    if bf(o1(a), o2(a)) != b:
                        ok = False
                        break
                if ok:
                    try:
                        test_val = int(test_in, 2)
                        return f"{bf(o1(test_val), o2(test_val)):08b}"
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
        lambda s: s[0] + s[-1] if len(s) >= 2 else s,
        lambda s: s[-1] + s[0] if len(s) >= 2 else s,
        lambda s: s[::-1],
        lambda s: s[0] if s else "",
        lambda s: s[-1] if s else "",
        lambda s: s[::2],
        lambda s: s[1::2],
        lambda s: s[1:-1] if len(s) >= 3 else s,
        lambda s: s[0] + s[1:-1][::-1] + s[-1] if len(s) >= 3 else s,
        lambda s: s[-1] + s[1:-1] + s[0] if len(s) >= 3 else s,
        # Extended structural rules
        lambda s: "".join(sorted(s)),
        lambda s: "".join(sorted(s, reverse=True)),
        lambda s: "".join(dict.fromkeys(s)),
        lambda s: str(len(s)),
        lambda s: s + s,
        lambda s: s[0] * len(s),
        lambda s: s[: len(s) // 2],
        lambda s: s[len(s) // 2 :],
        lambda s: s[::3],
        lambda s: s[:3] if len(s) >= 3 else s,
        lambda s: s[-3:] if len(s) >= 3 else s,
        lambda s: s[1:] + s[0],
        lambda s: s[-1] + s[:-1],
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


def _dsum(n: int) -> int:
    return sum(int(d) for d in str(abs(n)))


def _dprod(n: int) -> int:
    p = 1
    for d in str(abs(n)):
        p *= int(d)
    return p


def _drev(n: int) -> int:
    return int(str(abs(n))[::-1])


def _solve_number_equations(examples: list[tuple[str, str]], test_in: str) -> str:
    """Infer numeric rule from examples; handles 1-, 2-, 3-input equations."""
    from math import gcd as _gcd

    def _parse_nums(s: str) -> list[int]:
        return [int(p) for p in re.split(r"[^0-9]+", s) if p]

    def _parse_out(s: str) -> int | None:
        m = re.search(r"-?[0-9]+", s)
        return int(m.group()) if m else None

    # ── single-input unary rules ────────────────────────────────────────────
    _unary_ops: list[tuple[str, object]] = [
        ("identity", lambda a: a),
        ("neg", lambda a: -a),
        ("dsum", _dsum),
        ("dprod", _dprod),
        ("drev", _drev),
        ("dcount", lambda a: len(str(abs(a)))),
        ("dsum2", lambda a: _dsum(_dsum(a))),  # digital root step
        ("sq", lambda a: a * a),
        ("cube", lambda a: a * a * a),
        ("a+1", lambda a: a + 1),
        ("a-1", lambda a: a - 1),
        ("a*2", lambda a: a * 2),
        ("a*10", lambda a: a * 10),
        ("a//10", lambda a: a // 10),
        ("a%10", lambda a: a % 10),
        ("a//2", lambda a: a // 2),
    ]

    def _try_unary(examples: list, test_in: str) -> str | None:
        test_nums = _parse_nums(test_in)
        if len(test_nums) != 1:
            return None
        for _name, fn in _unary_ops:
            ok = True
            for inp, out in examples:
                ns = _parse_nums(inp)
                expected = _parse_out(out)
                if len(ns) != 1 or expected is None:
                    ok = False
                    break
                try:
                    if fn(ns[0]) != expected:
                        ok = False
                        break
                except Exception:
                    ok = False
                    break
            if ok:
                try:
                    return str(fn(test_nums[0]))
                except Exception:
                    pass
        return None

    # ── binary ops (expanded to 30) ─────────────────────────────────────────
    _base_ops: list[object] = [
        lambda a, b: a + b,
        lambda a, b: a - b,
        lambda a, b: abs(a - b),
        lambda a, b: a * b,
        lambda a, b: a // b if b != 0 else 0,
        lambda a, b: a % b if b != 0 else 0,
        lambda a, b: b - a,
        lambda a, b: max(a, b),
        lambda a, b: min(a, b),
        lambda a, b: a | b,
        lambda a, b: a & b,
        lambda a, b: a ^ b,
        lambda a, b: _dsum(a) + _dsum(b),
        lambda a, b: abs(_dsum(a) - _dsum(b)),
        lambda a, b: _dsum(a) * _dsum(b),
        lambda a, b: int(str(abs(a)) + str(abs(b))),
        lambda a, b: int(str(abs(b)) + str(abs(a))),
        lambda a, b: len(str(abs(a))) + len(str(abs(b))),
        lambda a, b: len(str(abs(a))) * len(str(abs(b))),
        lambda a, b: abs(len(str(abs(a))) - len(str(abs(b)))),
        lambda a, b: _dprod(a) + _dprod(b),
        lambda a, b: _dprod(a) * b,
        lambda a, b: a * _dsum(b),
        lambda a, b: _drev(a) + b,
        lambda a, b: _drev(a + b),
        lambda a, b: _gcd(abs(a), abs(b)) if (a != 0 or b != 0) else 0,
        lambda a, b: (abs(a * b) // _gcd(abs(a), abs(b))) if _gcd(abs(a), abs(b)) else 0,
        lambda a, b: (a + b) * (a - b),
        lambda a, b: a * a + b * b,
        lambda a, b: a * a - b * b,
    ]

    def _try_binary(op_fn: object, examples: list, test_in: str) -> str | None:
        ok = True
        for inp, out in examples:
            try:
                ns = _parse_nums(inp)
                if len(ns) != 2:
                    continue
                expected = _parse_out(out)
                if expected is None:
                    continue
                if op_fn(ns[0], ns[1]) != expected:
                    ok = False
                    break
            except Exception:
                ok = False
                break
        if ok:
            try:
                ns = _parse_nums(test_in)
                if len(ns) == 2:
                    return str(op_fn(ns[0], ns[1]))
            except Exception:
                pass
        return None

    # ── 3-input ternary ops ─────────────────────────────────────────────────
    _ternary_ops: list[object] = [
        lambda a, b, c: a + b + c,
        lambda a, b, c: a + b - c,
        lambda a, b, c: a - b + c,
        lambda a, b, c: a * b + c,
        lambda a, b, c: a * b * c,
        lambda a, b, c: (a + b) * c,
        lambda a, b, c: a * (b + c),
        lambda a, b, c: a + b * c,
        lambda a, b, c: max(a, b, c),
        lambda a, b, c: min(a, b, c),
        lambda a, b, c: a | b | c,
        lambda a, b, c: a & b & c,
        lambda a, b, c: a ^ b ^ c,
        lambda a, b, c: _dsum(a) + _dsum(b) + _dsum(c),
        lambda a, b, c: int(str(abs(a)) + str(abs(b)) + str(abs(c))),
        lambda a, b, c: a * b - c,
        lambda a, b, c: abs(a - b - c),
        lambda a, b, c: a * a + b * b + c * c,
    ]

    def _try_ternary(op_fn: object, examples: list, test_in: str) -> str | None:
        ok = True
        for inp, out in examples:
            try:
                ns = _parse_nums(inp)
                if len(ns) != 3:
                    continue
                expected = _parse_out(out)
                if expected is None:
                    continue
                if op_fn(ns[0], ns[1], ns[2]) != expected:
                    ok = False
                    break
            except Exception:
                ok = False
                break
        if ok:
            try:
                ns = _parse_nums(test_in)
                if len(ns) == 3:
                    return str(op_fn(ns[0], ns[1], ns[2]))
            except Exception:
                pass
        return None

    # ── run all phases ──────────────────────────────────────────────────────
    # Phase 0: single-input
    result = _try_unary(examples, test_in)
    if result is not None:
        return result

    # Phase 1: flat binary
    for op_fn in _base_ops:
        result = _try_binary(op_fn, examples, test_in)
        if result is not None:
            return result

    # Phase 1b: flat ternary
    for op_fn in _ternary_ops:
        result = _try_ternary(op_fn, examples, test_in)
        if result is not None:
            return result

    # Phase 2: depth-2 binary trees
    _small_consts = [1, 2, 3, 10, 100]
    for outer in _base_ops[:10]:
        for inner in _base_ops[:10]:
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

                result = _try_binary(tree_op, examples, test_in)
                if result is not None:
                    return result
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

                result = _try_binary(tree_const, examples, test_in)
                if result is not None:
                    return result

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


def _try_caesar_cipher(examples: list[tuple[str, str]], test_in: str) -> str | None:
    """Try Caesar (uniform shift) and Vigenere (cycling key, len 1-6) ciphers."""

    def _apply_vigenere(text: str, key: list[int]) -> str:
        result = ""
        ki = 0
        for c in text:
            if c.isalpha():
                base = ord("a") if c.islower() else ord("A")
                result += chr((ord(c) - base + key[ki % len(key)]) % 26 + base)
                ki += 1
            else:
                result += c
        return result

    def _extract_alpha_shifts(inp: str, out: str) -> list[int]:
        shifts = []
        for ci, co in zip(inp, out):
            if ci.isalpha() and co.isalpha():
                shifts.append((ord(co.lower()) - ord(ci.lower())) % 26)
        return shifts

    # Try Vigenere with key lengths 1..6
    for key_len in range(1, 7):
        # Build candidate key from first example's alpha characters
        candidate_key: list[int | None] = [None] * key_len
        ok = True
        for inp, out in examples:
            shifts = _extract_alpha_shifts(inp, out)
            for i, s in enumerate(shifts):
                pos = i % key_len
                if candidate_key[pos] is None:
                    candidate_key[pos] = s
                elif candidate_key[pos] != s:
                    ok = False
                    break
            if not ok:
                break
        if ok and all(k is not None for k in candidate_key):
            return _apply_vigenere(test_in, candidate_key)  # type: ignore[arg-type]

    return None


def _enc_build_mapping_voting(examples: list[tuple[str, str]]) -> dict[str, str]:
    """Build char mapping via majority vote across all aligned word pairs."""
    from collections import Counter

    votes: dict[str, Counter] = {}
    for inp, out in examples:
        iws = inp.split()
        ows = out.split()
        if len(iws) != len(ows):
            continue
        for iw, ow in zip(iws, ows):
            if len(iw) == len(ow):
                for ci, co in zip(iw, ow):
                    if ci not in votes:
                        votes[ci] = Counter()
                    votes[ci][co] += 1
    # Majority vote per input char (break ties by frequency)
    return {ci: cnt.most_common(1)[0][0] for ci, cnt in votes.items() if cnt}


def _enc_candidate_score(tw: str, word: str, mapping: dict[str, str]) -> int:
    """Score a candidate word by how many characters it confirms vs introduces."""
    confirmed = sum(1 for ci, co in zip(tw, word) if mapping.get(ci) == co)
    return confirmed


def solve_encryption(examples: list[tuple[str, str]], test_in: str) -> str:
    """Word-level substitution cipher solver with voting mapping + Caesar detection."""
    from collections import Counter

    # Fast path: detect Caesar cipher (uniform shift)
    caesar = _try_caesar_cipher(examples, test_in)
    if caesar is not None:
        return caesar

    # Build character mapping via majority vote (more robust than first-seen)
    mapping = _enc_build_mapping_voting(examples)

    # Runtime vocabulary: extract from example OUTPUTS (frequency-ranked)
    runtime_word_counts: Counter = Counter()
    for _, out in examples:
        for w in out.split():
            runtime_word_counts[w.lower()] += 1
    runtime_vocab = sorted(runtime_word_counts.keys(), key=lambda w: -runtime_word_counts[w])
    combined_vocab = runtime_vocab + [w for w in _ENCRYPTION_VOCAB if w not in runtime_word_counts]

    # Apply initial mapping
    test_words = test_in.split()
    result_words = ["".join(mapping.get(c, "?") for c in tw) for tw in test_words]

    # Dictionary completion with consistency checking.
    # For each ambiguous word, score all non-conflicting candidates and pick best.
    changed = True
    while changed:
        changed = False
        for _i, (tw, pw) in enumerate(zip(test_words, result_words)):
            if "?" not in pw:
                continue
            # Find all non-conflicting candidates
            candidates = []
            for cand in combined_vocab:
                if len(cand) != len(pw) or not _match_pattern(pw, cand):
                    continue
                conflict = False
                for ci, co in zip(tw, cand):
                    if ci in mapping and mapping[ci] != co:
                        conflict = True
                        break
                    if co in mapping.values() and mapping.get(ci) != co:
                        existing = next((k for k, v in mapping.items() if v == co), None)
                        if existing is not None and existing != ci:
                            conflict = True
                            break
                if not conflict:
                    score = _enc_candidate_score(tw, cand, mapping)
                    candidates.append((score, cand))
            if candidates:
                # Pick highest-scoring (most confirmed chars), then vocabulary order
                candidates.sort(key=lambda x: -x[0])
                best = candidates[0][1]
                for ci, co in zip(tw, best):
                    if ci not in mapping:
                        mapping[ci] = co
                        changed = True
        result_words = ["".join(mapping.get(c, "?") for c in tw) for tw in test_words]

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
        # Symbolic solver — model fallback not reliable
        result = solve_bit_manip(examples, test_input)
        if not result or len(result) != 8:
            result = test_input  # return test_input rather than garbage from model
        return result
    elif ptype == "equations":
        # Symbolic only — model fallback is slow (7s/call) and inaccurate (0%)
        result = solve_equations(examples, test_input)
        return result if result else test_input
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
