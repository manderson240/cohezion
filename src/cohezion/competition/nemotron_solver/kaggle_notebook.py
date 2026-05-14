import csv
import math
import os
import re
from collections import Counter
from itertools import combinations


INPUT_PATH = None
for base_path in ["/kaggle/input/nvidia-nemotron-model-reasoning-challenge", "/kaggle/input"]:
    if os.path.exists(base_path):
        for root, dirs, files in os.walk(base_path):
            for f in files:
                if f.lower().endswith(".csv"):
                    if "test" in f.lower():
                        INPUT_PATH = root
                        break
            if INPUT_PATH:
                break
    if INPUT_PATH:
        break

if INPUT_PATH is None:
    raise FileNotFoundError("Could not find test.csv in /kaggle/input")

test_files = [f for f in os.listdir(INPUT_PATH) if "test" in f.lower() and f.endswith(".csv")]
if not test_files:
    raise FileNotFoundError("No test CSV found")

test_path = os.path.join(INPUT_PATH, test_files[0])

with open(test_path) as f:
    test_rows = list(csv.DictReader(f))

# ========== Solver code ==========


def parse_examples(prompt):
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
            m = __import__("re").search(r"t\s*=\s*([0-9.]+s?)", line)
            n = __import__("re").search(r"distance\s*=\s*([0-9.]+)\s*m", line)
            if m and n:
                pairs.append((m.group(1), n.group(1) + " m"))
    return pairs


def classify_problem(prompt):
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


def extract_test_input(prompt):
    patterns = [
        r"determine the output for:\s*([0-9a-zA-Z\s.]+)",
        r"convert the following measurement:\s*([0-9.]+\s*m?)",
        r"write the number\s+([0-9]+)\s+in the",
        r"determine the result for:\s*([^\n]+)",
        r"decrypt the following text:\s*([^\n]+)",
        r"determine the falling distance for\s+t\s*=\s*([0-9.]+s?)",
    ]
    for pat in patterns:
        m = __import__("re").search(pat, prompt, __import__("re").IGNORECASE)
        if m:
            return m.group(1).strip()
    lines = [l.strip() for l in prompt.split("\n") if l.strip()]
    for line in reversed(lines):
        if not line.startswith("In Alice") and " -> " not in line and " becomes " not in line:
            if ":" in line:
                return line.split(":", 1)[1].strip()
            return line
    return ""


def _format_number(value, examples):
    decimals = []
    for _, out in examples:
        m = __import__("re").search(r"([0-9]+\.([0-9]+))", out)
        if m:
            decimals.append(len(m.group(2)))
    if decimals:
        precision = max(set(decimals), key=decimals.count)
    else:
        precision = 0
    if precision == 0:
        return f"{int(round(value))}"
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


def _ls_fit_nb(xs, ys):
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
            g = _ls_fit_nb(xs, ds)
            if g <= 0:
                continue
            mse = sum((pred_fn(g, t) - d) ** 2 for t, d in zip(ts, ds))

            # Precision voting: pick precision maximizing exact matches on examples
            fmt = _precision_vote(g, pred_fn)

            if mse < best_mse:
                best_mse = mse
                best_result = fmt
        except Exception:
            continue

    if best_result is not None:
        return best_result
    return "0.0"


def solve_unit_conversion(examples, test_x):
    xs, ys = [], []
    for x_str, y_str in examples:
        try:
            xs.append(float(re.search(r"([0-9.]+)", x_str).group(1)))
            ys.append(float(re.search(r"([0-9.]+)", y_str).group(1)))
        except Exception:
            pass
    if len(xs) < 2:
        return "0.0"
    try:
        test_val = float(re.search(r"([0-9.]+)", test_x).group(1))
    except Exception:
        return "0.0"

    def _mse(preds):
        return sum((p - y) ** 2 for p, y in zip(preds, ys))

    def _hits(preds):
        return sum(
            1
            for p, y in zip(preds, ys)
            if _format_number(p, examples) == _format_number(y, examples)
        )

    best_result = None
    best_score = (-1, 0, float("inf"))

    def _cand(pred_test, pred_train, n_params=1):
        nonlocal best_result, best_score
        score = (_hits(pred_train), -n_params, -_mse(pred_train))
        if score > best_score:
            best_score = score
            best_result = _format_number(pred_test, examples)

    n = len(xs)
    sum_x, sum_y = sum(xs), sum(ys)
    # 1. Proportional y = k*x (1 param, simpler)
    # Try LSQ mean AND per-example k_i (fixes ±0.01 precision errors)
    if sum_x != 0:
        k = sum_y / sum_x
        _cand(k * test_val, [k * x for x in xs], n_params=1)
        for k_i in (y / x for x, y in zip(xs, ys) if x != 0):
            _cand(k_i * test_val, [k_i * x for x in xs], n_params=1)
    # 2. Linear y = a*x + b (2 params)
    sum_xy = sum(x * y for x, y in zip(xs, ys))
    sum_x2 = sum(x * x for x in xs)
    denom = n * sum_x2 - sum_x * sum_x
    if abs(denom) > 1e-10:
        a = (n * sum_xy - sum_x * sum_y) / denom
        b = (sum_y - a * sum_x) / n
        _cand(a * test_val + b, [a * x + b for x in xs], n_params=2)
    nl_models = [
        (lambda x: 1.0 / x if x != 0 else None, lambda k, x: k / x if x != 0 else 0),
        (lambda x: math.sqrt(x) if x >= 0 else None, lambda k, x: k * math.sqrt(abs(x))),
        (lambda x: x * x, lambda k, x: k * x * x),
        (lambda x: x * x * x, lambda k, x: k * x * x * x),
    ]
    for feat_fn, pred_fn in nl_models:
        try:
            feats = [feat_fn(x) for x in xs]
            if any(f is None for f in feats):
                continue
            k = _ls_fit_nb(feats, ys)
            if k == 0:
                continue
            _cand(pred_fn(k, test_val), [pred_fn(k, x) for x in xs], n_params=1)
        except Exception:
            continue
    return best_result if best_result is not None else "0.0"


def int_to_roman(n):
    val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
    syms = ["M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"]
    result = ""
    for v, s in zip(val, syms):
        while n >= v:
            result += s
            n -= v
    return result


def solve_numeral(examples, test_n):
    try:
        n = int(__import__("re").search(r"([0-9]+)", test_n).group(1))
    except Exception:
        return ""
    return int_to_roman(n)


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
        _named_tt_k3 = [
            0b10010110,
            0b01101001,
            0b11101000,
            0b00010111,
            0b10000000,
            0b11111110,
            0b01111111,
            0b00000001,
            0b11110000,
            0b11001100,
            0b10101010,
            0b00001111,
            0b00110011,
            0b01010101,
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

    # Unary ops
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
    # Only run if we have time budget. Uses 12 most common ops: 12^3 = 1728 combinations.
    _fast_ops = unary_ops[:16]  # 16 ops = 16^3=4096 combos; covers all 4-bit shifts/rots
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
    _bin_fns_55 = [
        (lambda a, b: a ^ b),
        (lambda a, b: a & b),
        (lambda a, b: a | b),
        (lambda a, b: (a + b) & 0xFF),
        (lambda a, b: (a - b) & 0xFF),
        (lambda a, b: (b - a) & 0xFF),
        (lambda a, b: (a * b) & 0xFF),
        (lambda a, b: (~(a & b)) & 0xFF),
        (lambda a, b: (~(a | b)) & 0xFF),
        (lambda a, b: (~(a ^ b)) & 0xFF),
    ]
    for _n1, o1 in unary_ops:
        for _n2, o2 in unary_ops:
            if o1 is o2:
                continue
            for bf in _bin_fns_55:
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

    for const in range(256):
        for _op_name, op_fn in [
            ("xor", lambda x, c: x ^ c),
            ("and", lambda x, c: x & c),
            ("or", lambda x, c: x | c),
            ("add", lambda x, c: (x + c) & 0xFF),
            ("sub", lambda x, c: (x - c) & 0xFF),
            ("mul", lambda x, c: (x * c) & 0xFF),
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


def _match_pattern(pattern, word):
    if len(pattern) != len(word):
        return False
    for p, w in zip(pattern, word):
        if p != "?" and p != w:
            return False
    return True


def _try_caesar_nb(examples, test_in):
    """Caesar (uniform) + Vigenere (cycling key len 1-6) detection."""

    def _apply(text, key):
        out, ki = "", 0
        for c in text:
            if c.isalpha():
                base = ord("a") if c.islower() else ord("A")
                out += chr((ord(c) - base + key[ki % len(key)]) % 26 + base)
                ki += 1
            else:
                out += c
        return out

    for key_len in range(1, 7):
        key = [None] * key_len
        ok = True
        for inp, out in examples:
            ki = 0
            for ci, co in zip(inp, out):
                if ci.isalpha() and co.isalpha():
                    s = (ord(co.lower()) - ord(ci.lower())) % 26
                    if key[ki % key_len] is None:
                        key[ki % key_len] = s
                    elif key[ki % key_len] != s:
                        ok = False
                        break
                    ki += 1
            if not ok:
                break
        if ok and all(k is not None for k in key):
            return _apply(test_in, key)
    return None


def _nb_build_mapping_voting(examples):
    """Majority-vote char mapping across aligned word pairs."""
    from collections import Counter

    votes = {}
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
    return {ci: cnt.most_common(1)[0][0] for ci, cnt in votes.items() if cnt}


def solve_encryption(examples, test_in):
    caesar = _try_caesar_nb(examples, test_in)
    if caesar is not None:
        return caesar

    # Voting-based mapping
    mapping = _nb_build_mapping_voting(examples)

    runtime_counts = Counter()
    for _, out in examples:
        for w in out.split():
            runtime_counts[w.lower()] += 1
    runtime_vocab = sorted(runtime_counts.keys(), key=lambda w: -runtime_counts[w])
    combined_vocab = runtime_vocab + [w for w in _ENCRYPTION_VOCAB if w not in runtime_counts]

    test_words = test_in.split()
    result_words = ["".join(mapping.get(c, "?") for c in tw) for tw in test_words]

    # Score all non-conflicting candidates, pick best (most confirmed chars)
    changed = True
    while changed:
        changed = False
        for _i, (tw, pw) in enumerate(zip(test_words, result_words)):
            if "?" not in pw:
                continue
            candidates = []
            for cand in combined_vocab:
                if len(cand) != len(pw) or not _match_pattern(pw, cand):
                    continue
                conflict = any(
                    (ci in mapping and mapping[ci] != co)
                    or (
                        co in mapping.values()
                        and mapping.get(ci) != co
                        and next((k for k, v in mapping.items() if v == co), None) != ci
                    )
                    for ci, co in zip(tw, cand)
                )
                if not conflict:
                    score = sum(1 for ci, co in zip(tw, cand) if mapping.get(ci) == co)
                    candidates.append((score, cand))
            if candidates:
                candidates.sort(key=lambda x: -x[0])
                best = candidates[0][1]
                for ci, co in zip(tw, best):
                    if ci not in mapping:
                        mapping[ci] = co
                        changed = True
        result_words = ["".join(mapping.get(c, "?") for c in tw) for tw in test_words]

    return " ".join(result_words)


def _symbol_eq_nb(examples, test_in):
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
    for rule in rules:
        ok = True
        for inp, out in examples:
            ci, co = inp.strip("`'\" "), out.strip("`'\" ")
            try:
                if rule(ci) != co:
                    ok = False
                    break
            except Exception:
                ok = False
                break
        if ok:
            try:
                return rule(test_in.strip("`'\" "))
            except Exception:
                pass
    return test_in


def _nb_dsum(n):
    return sum(int(d) for d in str(abs(n)))


def _nb_dprod(n):
    p = 1
    for d in str(abs(n)):
        p *= int(d)
    return p


def _nb_drev(n):
    return int(str(abs(n))[::-1])


def solve_equations(examples, test_in):
    from math import gcd as _gcd

    first_in = examples[0][0] if examples else ""
    if not any(c.isdigit() for c in first_in):
        return _symbol_eq_nb(examples, test_in)

    def _pn(s):
        return [int(p) for p in re.split(r"[^0-9]+", s) if p]

    def _po(s):
        m = re.search(r"-?[0-9]+", s)
        return int(m.group()) if m else None

    # Phase 0: single-input unary
    _unary = [
        lambda a: a,
        lambda a: -a,
        lambda a: _nb_dsum(a),
        lambda a: _nb_dprod(a),
        lambda a: _nb_drev(a),
        lambda a: len(str(abs(a))),
        lambda a: _nb_dsum(_nb_dsum(a)),
        lambda a: a * a,
        lambda a: a * a * a,
        lambda a: a + 1,
        lambda a: a - 1,
        lambda a: a * 2,
        lambda a: a * 10,
        lambda a: a // 10,
        lambda a: a % 10,
        lambda a: a // 2,
    ]
    tn = _pn(test_in)
    if len(tn) == 1:
        for fn in _unary:
            ok = True
            for inp, out in examples:
                ns = _pn(inp)
                exp = _po(out)
                if len(ns) != 1 or exp is None:
                    ok = False
                    break
                try:
                    if fn(ns[0]) != exp:
                        ok = False
                        break
                except Exception:
                    ok = False
                    break
            if ok:
                try:
                    return str(fn(tn[0]))
                except Exception:
                    pass

    _base_ops = [
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
        lambda a, b: _nb_dsum(a) + _nb_dsum(b),
        lambda a, b: abs(_nb_dsum(a) - _nb_dsum(b)),
        lambda a, b: _nb_dsum(a) * _nb_dsum(b),
        lambda a, b: int(str(abs(a)) + str(abs(b))),
        lambda a, b: int(str(abs(b)) + str(abs(a))),
        lambda a, b: len(str(abs(a))) + len(str(abs(b))),
        lambda a, b: len(str(abs(a))) * len(str(abs(b))),
        lambda a, b: abs(len(str(abs(a))) - len(str(abs(b)))),
        lambda a, b: _nb_dprod(a) + _nb_dprod(b),
        lambda a, b: _nb_dprod(a) * b,
        lambda a, b: a * _nb_dsum(b),
        lambda a, b: _nb_drev(a) + b,
        lambda a, b: _nb_drev(a + b),
        lambda a, b: _gcd(abs(a), abs(b)) if (a or b) else 0,
        lambda a, b: (abs(a * b) // _gcd(abs(a), abs(b))) if _gcd(abs(a), abs(b)) else 0,
        lambda a, b: (a + b) * (a - b),
        lambda a, b: a * a + b * b,
        lambda a, b: a * a - b * b,
    ]

    def _try_bin(op_fn):
        ok = True
        for inp, out in examples:
            try:
                p = _pn(inp)
                if len(p) != 2:
                    continue
                exp = _po(out)
                if exp is None:
                    continue
                if op_fn(p[0], p[1]) != exp:
                    ok = False
                    break
            except Exception:
                ok = False
                break
        if ok:
            try:
                p = _pn(test_in)
                if len(p) == 2:
                    return str(op_fn(p[0], p[1]))
            except Exception:
                pass
        return None

    for op in _base_ops:
        r = _try_bin(op)
        if r is not None:
            return r

    # Phase 1b: ternary
    _ternary = [
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
        lambda a, b, c: _nb_dsum(a) + _nb_dsum(b) + _nb_dsum(c),
        lambda a, b, c: int(str(abs(a)) + str(abs(b)) + str(abs(c))),
        lambda a, b, c: a * b - c,
        lambda a, b, c: abs(a - b - c),
        lambda a, b, c: a * a + b * b + c * c,
    ]

    def _try_ter(op_fn):
        ok = True
        for inp, out in examples:
            try:
                p = _pn(inp)
                if len(p) != 3:
                    continue
                exp = _po(out)
                if exp is None:
                    continue
                if op_fn(p[0], p[1], p[2]) != exp:
                    ok = False
                    break
            except Exception:
                ok = False
                break
        if ok:
            try:
                p = _pn(test_in)
                if len(p) == 3:
                    return str(op_fn(p[0], p[1], p[2]))
            except Exception:
                pass
        return None

    for op in _ternary:
        r = _try_ter(op)
        if r is not None:
            return r

    # Phase 2: depth-2 binary trees
    for outer in _base_ops[:10]:
        for inner in _base_ops[:10]:
            for make_ab in [
                lambda a, b, f=inner: (f(a, b), a),
                lambda a, b, f=inner: (f(a, b), b),
                lambda a, b, f=inner: (a, f(a, b)),
                lambda a, b, f=inner: (b, f(a, b)),
            ]:

                def tree_op(a, b, outer=outer, make_ab=make_ab):
                    x, y = make_ab(a, b)
                    return outer(x, y)

                r = _try_bin(tree_op)
                if r is not None:
                    return r
        for inner in _base_ops[:6]:
            for c in [1, 2, 3, 10, 100]:

                def tree_const(a, b, outer=outer, inner=inner, c=c):
                    return outer(inner(a, b), c)

                r = _try_bin(tree_const)
                if r is not None:
                    return r
    return test_in


def solve(prompt):
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


# ========== Generate submission ==========
results = []
for r in test_rows:
    pred = solve(r["prompt"])
    results.append({"id": r["id"], "answer": pred.strip()})

with open("submission.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["id", "answer"])
    writer.writeheader()
    writer.writerows(results)

print(f"Generated {len(results)} predictions in submission.csv")
