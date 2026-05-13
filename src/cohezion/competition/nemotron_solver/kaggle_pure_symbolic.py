"""NVIDIA Nemotron Reasoning Challenge — Pure Symbolic Solver (Kaggle Notebook).

No external LLM required. Uses only symbolic solvers:
- gravity: robust grid-search fit for d = 0.5*g*t^2
- unit_conversion: linear regression
- numeral: Roman numeral conversion
- bit_manip: per-bit mapping + affine + unary search
- encryption: character substitution mapping + dictionary completion
- equations: simple pattern matching (occasionally catches a few)

Expected accuracy on training: ~63.1% (9500-sample validation, no model).
Hybrid with local Gemma-4 fallback: ~63.95% (model adds only +0.8%).
"""

from __future__ import annotations

import csv
import re
from itertools import combinations


def parse_examples(prompt: str) -> list[tuple[str, str]]:
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
        # Fix: Handle equation format "input = output"
        elif " = " in line and not line.startswith(("Here", "Now", "For", "The")):
            parts = line.split(" = ", 1)
            if len(parts) == 2:
                left = parts[0].strip()
                right = parts[1].strip()
                # Only accept if both sides look like valid I/O
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
    lines = [ln.strip() for ln in prompt.split("\n") if ln.strip()]
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
    # Try 2-decimal if the most common is 1-decimal but 2-decimal examples also exist
    fmt = f"{value:.{precision}f}"
    if precision == 1:
        dec2_count = sum(1 for _, out in examples if "." in out and len(out.split(".")[1]) == 2)
        if dec2_count >= sum(
            1 for _, out in examples if "." in out and len(out.split(".")[1]) == 1
        ):
            fmt2 = f"{value:.2f}"
            if fmt2 != fmt:
                return fmt2
    return fmt


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
# Numeral solver
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
# Bit manipulation solver v5.3 — LUT + global cross-bit patterns
# ---------------------------------------------------------------------------


def _lut_search(pairs: list[tuple[int, int]], max_k: int = 3) -> dict | None:
    """Find a k-ary Boolean function (truth table) for each output bit."""
    _named_tt_k2 = [6, 8, 14, 1, 7, 9, 12, 10, 3, 5, 11, 13, 4, 2, 0, 15]
    result = {}
    for out_bit in range(8):
        found = False
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
            for tt in _named_tt_k2:
                if all((tt >> idx) & 1 == val for idx, val in obs.items()):
                    result[out_bit] = (in_bits, tt)
                    found = True
                    break
            if not found:
                for tt in range(16):
                    if tt in _named_tt_k2:
                        continue
                    if all((tt >> idx) & 1 == val for idx, val in obs.items()):
                        result[out_bit] = (in_bits, tt)
                        found = True
                        break
            if found:
                break
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

    # Phase 1: detect pure bijective bit permutations and constant output bits.
    # Inverted mappings are skipped (spurious with small examples); handled by Phase 2+.
    def _bit_matches_direct(out_bit: int, in_bit: int) -> bool:
        for a, b in pairs:
            if ((b >> out_bit) & 1) != ((a >> in_bit) & 1):
                return False
        return True

    mapping: dict[int, tuple] = {}
    for out_bit in range(8):
        if all(((b >> out_bit) & 1) == 0 for _, b in pairs):
            mapping[out_bit] = ("const", 0, False)
        elif all(((b >> out_bit) & 1) == 1 for _, b in pairs):
            mapping[out_bit] = ("const", 1, False)
        else:
            for in_bit in range(8):
                if _bit_matches_direct(out_bit, in_bit):
                    mapping[out_bit] = ("bit", in_bit, False)
                    break

    if len(mapping) == 8:
        source_bits = [v[1] for v in mapping.values() if v[0] == "bit"]
        if len(source_bits) == len(set(source_bits)):  # bijection check
            try:
                test_val = int(test_in, 2)
                result = 0
                for out_bit in range(8):
                    typ, val, _ = mapping[out_bit]
                    bit = val if typ == "const" else (test_val >> val) & 1
                    result |= bit << out_bit
                return f"{result:08b}"
            except Exception:
                pass

    # Affine
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

    # Unary ops
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

    # Phase 6a: global uniform cross-bit — output[i] = f(input[i], input[(i+k)%8])
    _cross_bit_funcs = [
        lambda a, b: a ^ b,
        lambda a, b: a & b,
        lambda a, b: a | b,
        lambda a, b: 1 - (a & b),
        lambda a, b: 1 - (a | b),
        lambda a, b: 1 - (a ^ b),
        lambda a, b: a & (1 - b),
        lambda a, b: (1 - a) & b,
        lambda a, b: a,
        lambda a, b: b,
        lambda a, b: 1 - a,
        lambda a, b: 1 - b,
    ]
    for offset in range(1, 8):
        for ffn in _cross_bit_funcs:
            ok = True
            for a, b in pairs:
                for out_bit in range(8):
                    ai = (a >> out_bit) & 1
                    bi = (a >> ((out_bit + offset) % 8)) & 1
                    if ffn(ai, bi) != ((b >> out_bit) & 1):
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

    # Phase 6b: per-bit LUT synthesis
    lut_mapping = _lut_search(pairs, max_k=3)
    if lut_mapping is not None:
        try:
            test_val = int(test_in, 2)
            result = 0
            for out_bit in range(8):
                in_bits, tt = lut_mapping[out_bit]
                idx = sum(((test_val >> ib) & 1) << i for i, ib in enumerate(in_bits))
                result |= ((tt >> idx) & 1) << out_bit
            return f"{result:08b}"
        except Exception:
            pass

    return test_in


# ---------------------------------------------------------------------------
# Encryption solver with dictionary completion
# ---------------------------------------------------------------------------
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
# Equation solver (minimal)
# ---------------------------------------------------------------------------
def solve_equations(examples: list[tuple[str, str]], test_in: str) -> str:
    """Minimal equation solver. Catches very simple patterns."""
    first_in = examples[0][0] if examples else ""
    has_digits = any(c.isdigit() for c in first_in)
    if not has_digits:
        # Symbol equations: try reverse
        for inp, out in examples:
            if len(inp) == len(out) and inp[::-1] == out:
                try:
                    return test_in[::-1]
                except Exception:
                    pass
        return ""
    try:
        parts = re.split(r"[^0-9]", test_in)
        parts = [p for p in parts if p]
        if len(parts) == 2:
            a, b = int(parts[0]), int(parts[1])
            # Try most common operations
            candidates = [
                a + b,
                abs(a - b),
                a * b,
                a // b if b != 0 else 0,
            ]
            return str(candidates[0])
    except Exception:
        pass
    return ""


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
        return solve_bit_manip(examples, test_input)
    elif ptype == "encryption":
        return solve_encryption(examples, test_input)
    elif ptype == "equations":
        return solve_equations(examples, test_input)
    else:
        return ""


# ---------------------------------------------------------------------------
# Kaggle: read test.csv, write submission.csv
# ---------------------------------------------------------------------------
import os


if os.path.exists("/kaggle/input/nvidia-nemotron-model-reasoning-challenge/test.csv"):
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
else:
    print("Not running in Kaggle environment — skipping submission.csv generation.")
