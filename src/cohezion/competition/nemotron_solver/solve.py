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
    # Build a concise prompt with 1-2 examples
    prompt = "Solve the puzzle. Output the final answer ONLY, no explanation.\n\n"
    for inp, out in examples[:2]:
        prompt += f"{inp} = {out}\n"
    prompt += f"{test_in} ="

    return _call_model(prompt, max_tokens=64)


def parse_examples(prompt: str) -> list[tuple[str, str]]:
    """Extract input->output pairs from prompt text.

    Handles multiple formats:
    - "X -> Y" (bit_manip, equations)
    - "X becomes Y" (unit_conversion)
    - "For t = Xs, distance = Y m" (gravity)
    - "A -> B" with Roman numeral or number (numeral)
    - "text1 -> text2" (encryption)
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
    lines = [l.strip() for l in prompt.split("\n") if l.strip()]
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
def solve_gravity(examples: list[tuple[str, str]], test_t: str) -> str:
    """Solve gravity problems: d = 0.5 * g * t^2. Infer g from examples."""
    gs = []
    for t_str, d_str in examples:
        try:
            t = float(re.search(r"([0-9.]+)", t_str).group(1))
            d = float(re.search(r"([0-9.]+)", d_str).group(1))
            g = 2 * d / (t * t)
            gs.append(g)
        except Exception:
            pass
    if not gs:
        return "0.0"
    g = sum(gs) / len(gs)
    try:
        test_t_val = float(re.search(r"([0-9.]+)", test_t).group(1))
    except Exception:
        return "0.0"
    result = 0.5 * g * test_t_val * test_t_val
    return _format_number(result, examples)

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
    # Candidate operations
    ops = [
        ("not", lambda x: (~x) & 0xFF),
        ("reverse", lambda x: int("{:08b}".format(x)[::-1], 2)),
        ("flip", lambda x: x ^ 0xFF),
        ("shift_left_1", lambda x: ((x << 1) & 0xFF)),
        ("shift_right_1", lambda x: (x >> 1)),
        ("rot_left_1", lambda x: ((x << 1) & 0xFF) | (x >> 7)),
        ("rot_right_1", lambda x: ((x >> 1) | ((x & 1) << 7))),
        ("reverse_nibble", lambda x: (((x & 0x0F) << 4) | ((x & 0xF0) >> 4))),
        ("swap_halves", lambda x: (((x & 0x0F) << 4) | ((x & 0xF0) >> 4))),
        ("not_reverse", lambda x: int("{:08b}".format((~x) & 0xFF)[::-1], 2)),
    ]
    # Also try combinations of 2 ops
    for name1, op1 in ops:
        ok = True
        for a, b in pairs:
            if op1(a) != b:
                ok = False
                break
        if ok:
            try:
                test_val = int(test_in, 2)
                return "{:08b}".format(op1(test_val))
            except Exception:
                pass
    # 2-op combinations
    for name1, op1 in ops:
        for name2, op2 in ops:
            ok = True
            for a, b in pairs:
                if op2(op1(a)) != b:
                    ok = False
                    break
            if ok:
                try:
                    test_val = int(test_in, 2)
                    return "{:08b}".format(op2(op1(test_val)))
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
    op_char = None
    for c in test_in:
        if c in "+-*/|\\&^%=" and not c.isdigit():
            op_char = c
            break
    if not op_char:
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
        results.append((int(str(da[0]) * 2 + str(sum(db)) + str(abs(db[0] - db[-1]))) if da and db else 0, "custom88"))
        results.append((int("".join(map(str, da + db))), "concat"))
        return results

    # Find operation that matches all examples
    for res, op_name in apply_ops(0, 0):
        pass  # just to get list

    # Actually brute-force: try each operation
    ops_to_try = [
        ("add", lambda a, b: a + b),
        ("sub", lambda a, b: abs(a - b)),
        ("mul", lambda a, b: a * b),
        ("div", lambda a, b: a // b if b != 0 else 0),
        ("mod", lambda a, b: a % b if b != 0 else 0),
        ("digit_sum", lambda a, b: sum(int(d) for d in str(a) + str(b))),
        ("digit_diff", lambda a, b: abs(sum(int(d) for d in str(a)) - sum(int(d) for d in str(b)))),
        ("first_digit", lambda a, b: int(str(a)[0]) if str(a) else 0),
        ("concat", lambda a, b: int(str(a) + str(b))),
        ("rev_concat", lambda a, b: int(str(b) + str(a))),
        ("len_concat", lambda a, b: int(str(len(str(a))) + str(len(str(b))))),
    ]

    for op_name, op_fn in ops_to_try:
        ok = True
        for inp, out in examples:
            try:
                parts = re.split(r"[^0-9]", inp)
                parts = [p for p in parts if p]
                if len(parts) != 2:
                    continue
                a, b = int(parts[0]), int(parts[1])
                expected = int(re.search(r"[0-9]+", out).group())
                if op_fn(a, b) != expected:
                    ok = False
                    break
            except Exception:
                ok = False
                break
        if ok:
            try:
                parts = re.split(r"[^0-9]", test_in)
                parts = [p for p in parts if p]
                if len(parts) == 2:
                    a, b = int(parts[0]), int(parts[1])
                    result = op_fn(a, b)
                    return str(result)
            except Exception:
                pass

    # Fallback: try to extract last example's pattern
    return test_in


# ---------------------------------------------------------------------------
# Encryption solver (character mapping with spaces)
# ---------------------------------------------------------------------------
def solve_encryption(examples: list[tuple[str, str]], test_in: str) -> str:
    """Word-level substitution cipher solver."""
    # Build per-word-length character mapping
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
    # Apply mapping word-by-word to test input
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
    """Classify and solve a single problem."""
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
        # Try symbolic first, fallback to model
        result = solve_bit_manip(examples, test_input)
        if result == test_input or len(result) != 8:
            result = solve_with_model(examples, test_input, ptype)
        return result
    elif ptype == "equations":
        # Symbolic then model fallback
        result = solve_equations(examples, test_input)
        if result == test_input:
            result = solve_with_model(examples, test_input, ptype)
        return result
    elif ptype == "encryption":
        # Symbolic then model fallback
        result = solve_encryption(examples, test_input)
        # Check if result looks like real words (has vowels)
        if not any(c in result.lower() for c in "aeiou") or len(result.split()) != len(test_input.split()):
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
    sample_size = 100
    random.seed(42)
    acc = evaluate(str(data_dir / "train.csv"), sample=sample_size)
    print(f"Hybrid accuracy on {sample_size} training examples: {acc:.1f}%")
    print(f"METRIC reasoning_accuracy={acc:.1f}")
