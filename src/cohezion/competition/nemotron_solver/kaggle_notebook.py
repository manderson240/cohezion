import contextlib
import csv
import os


INPUT_PATH = None
for base_path in ["/kaggle/input/nvidia-nemotron-model-reasoning-challenge", "/kaggle/input"]:
    if os.path.exists(base_path):
        for root, _dirs, files in os.walk(base_path):
            for f in files:
                if f.lower().endswith(".csv") and "test" in f.lower():
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
    precision = max(set(decimals), key=decimals.count) if decimals else 0
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


def solve_gravity(examples, test_t):
    ts, ds = [], []
    for t_str, d_str in examples:
        try:
            t = float(__import__("re").search(r"([0-9.]+)", t_str).group(1))
            d = float(__import__("re").search(r"([0-9.]+)", d_str).group(1))
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
        test_t_val = float(__import__("re").search(r"([0-9.]+)", test_t).group(1))
    except Exception:
        return "0.0"
    result = 0.5 * best_g * test_t_val * test_t_val
    fmt = _format_number(result, examples)
    if "." in fmt:
        parts = fmt.split(".")
        if len(parts[1]) == 1:
            fmt2 = f"{result:.2f}"
            dec1_count = sum(1 for _, out in examples if "." in out and len(out.split(".")[1]) == 1)
            dec2_count = sum(1 for _, out in examples if "." in out and len(out.split(".")[1]) == 2)
            if dec2_count >= dec1_count:
                return fmt2
    return fmt


def solve_unit_conversion(examples, test_x):
    xs, ys = [], []
    for x_str, y_str in examples:
        try:
            x = float(__import__("re").search(r"([0-9.]+)", x_str).group(1))
            y = float(__import__("re").search(r"([0-9.]+)", y_str).group(1))
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
            test_val = float(__import__("re").search(r"([0-9.]+)", test_x).group(1))
        except Exception:
            return "0.0"
        return _format_number(k * test_val, examples)
    a = (n * sum_xy - sum_x * sum_y) / denom
    b = (sum_y - a * sum_x) / n
    try:
        test_val = float(__import__("re").search(r"([0-9.]+)", test_x).group(1))
    except Exception:
        return "0.0"
    return _format_number(a * test_val + b, examples)


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


def solve_bit_manip(examples, test_in):
    pairs = []
    for inp, out in examples:
        if len(inp) == 8 and set(inp).issubset({"0", "1"}):
            with contextlib.suppress(Exception):
                pairs.append((int(inp, 2), int(out, 2)))
    if not pairs:
        return test_in

    # Phase 1: Per-bit mapping (fast path)
    mapping = {}
    for out_bit in range(8):
        for in_bit in range(8):
            ok = True
            for a, b in pairs:
                if ((b >> out_bit) & 1) != ((a >> in_bit) & 1):
                    ok = False
                    break
            if ok:
                mapping[out_bit] = ("bit", in_bit, False)
                break
            ok = True
            for a, b in pairs:
                if ((b >> out_bit) & 1) != (1 - ((a >> in_bit) & 1)):
                    ok = False
                    break
            if ok:
                mapping[out_bit] = ("bit", in_bit, True)
                break
        if out_bit not in mapping:
            ok = True
            for a, b in pairs:
                if ((b >> out_bit) & 1) != 0:
                    ok = False
                    break
            if ok:
                mapping[out_bit] = ("const", 0, False)
            else:
                ok = True
                for a, b in pairs:
                    if ((b >> out_bit) & 1) != 1:
                        ok = False
                        break
                if ok:
                    mapping[out_bit] = ("const", 1, False)

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
        except Exception:
            pass

    # Phase 2: XOR-linear model (GF(2) linear algebra)
    try:
        test_val = int(test_in, 2)
        result = 0
        for out_bit in range(8):
            matched = False
            for r_shift in range(9):
                for subset in __import__("itertools").combinations(range(8), r_shift):
                    for const in [0, 1]:
                        ok = True
                        for a, b in pairs:
                            val = const
                            for j in subset:
                                val ^= (a >> j) & 1
                            if val != ((b >> out_bit) & 1):
                                ok = False
                                break
                        if ok:
                            bit_val = const
                            for j in subset:
                                bit_val ^= (test_val >> j) & 1
                            result |= bit_val << out_bit
                            matched = True
                            break
                    if matched:
                        break
                if matched:
                    break
            if not matched:
                result = None
                break
        if result is not None:
            return f"{result:08b}"
    except Exception:
        pass

    # Phase 3: Affine constants
    for xor_const in range(256):
        ok = True
        for a, b in pairs:
            if (a ^ xor_const) != b:
                ok = False
                break
        if ok:
            try:
                return f"{(int(test_in, 2) ^ xor_const):08b}"
            except Exception:
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
            except Exception:
                pass
    for or_const in range(256):
        ok = True
        for a, b in pairs:
            if (a | or_const) != b:
                ok = False
                break
        if ok:
            try:
                return f"{(int(test_in, 2) | or_const):08b}"
            except Exception:
                pass
    for add_const in range(256):
        ok = True
        for a, b in pairs:
            if ((a + add_const) & 0xFF) != b:
                ok = False
                break
        if ok:
            try:
                return f"{((int(test_in, 2) + add_const) & 0xFF):08b}"
            except Exception:
                pass

    # Phase 4: Unary ops
    unary_ops = [
        ("not", lambda x: (~x) & 0xFF),
        ("reverse", lambda x: int(f"{x:08b}"[::-1], 2)),
        ("flip", lambda x: x ^ 0xFF),
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


def solve_encryption(examples, test_in):
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
            mapped += mapping.get(c, "?")
        result_words.append(mapped)

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
            if len(matches) >= 1:
                best = matches[0]
                for c_in, c_out in zip(tw, best):
                    if c_in not in mapping:
                        mapping[c_in] = c_out
                        changed = True
        result_words = []
        for tw in test_words:
            mapped = ""
            for c in tw:
                mapped += mapping.get(c, "?")
            result_words.append(mapped)

    return " ".join(result_words)


def solve_equations(examples, test_in):
    first_in = examples[0][0] if examples else ""
    has_digits = any(c.isdigit() for c in first_in)
    if not has_digits:
        for inp, out in examples:
            if len(inp) == len(out) and inp[::-1] == out:
                try:
                    return test_in[::-1]
                except Exception:
                    pass
        return ""
    try:
        parts = __import__("re").split(r"[^0-9]", test_in)
        parts = [p for p in parts if p]
        if len(parts) == 2:
            a, b = int(parts[0]), int(parts[1])
            return str(a + b)
    except Exception:
        pass
    return ""


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
