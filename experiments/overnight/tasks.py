"""Fixed 24-task suite with deterministic validators for the overnight loop.

Six categories x four tasks. Validators are pure functions (regex / exact /
json.loads / exec-assert) — no LLM judging, no answer leakage into prompts.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class SuiteTask:
    task_id: str
    category: str
    prompt: str
    validate: Callable[[str], bool]


def _regex(pattern: str, flags: int = re.IGNORECASE) -> Callable[[str], bool]:
    rx = re.compile(pattern, flags)
    return lambda text: bool(rx.search(text))


def _json_has(key: str, expected: object) -> Callable[[str], bool]:
    def check(text: str) -> bool:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            return False
        try:
            obj = json.loads(m.group(0))
        except json.JSONDecodeError:
            return False
        return isinstance(obj, dict) and obj.get(key) == expected

    return check


def _code_passes(fn_name: str, cases: list[tuple[tuple, object]]) -> Callable[[str], bool]:
    def check(text: str) -> bool:
        m = re.search(r"```(?:python)?\n(.*?)```", text, re.DOTALL)
        code = m.group(1) if m else text
        ns: dict = {}
        try:
            exec(code, {"__builtins__": __builtins__}, ns)  # noqa: S102 - local eval of local model output
            fn = ns.get(fn_name)
            if fn is None:
                return False
            return all(fn(*args) == want for args, want in cases)
        except Exception:
            return False

    return check


TASKS: list[SuiteTask] = [
    # --- categorical (yes/no, single word) ---
    SuiteTask("cat-prime", "categorical", "Is 97 a prime number? Answer with exactly one word: yes or no.", _regex(r"\byes\b")),
    SuiteTask("cat-leap", "categorical", "Was the year 1900 a leap year in the Gregorian calendar? Answer with exactly one word: yes or no.", _regex(r"\bno\b")),
    SuiteTask("cat-bigger", "categorical", "Which is larger: 2^10 or 10^3? Answer with exactly '2^10' or '10^3'.", _regex(r"2\s*\^\s*10|1024")),
    SuiteTask("cat-vowel", "categorical", "Does the word 'rhythm' contain the letter 'e'? Answer with exactly one word: yes or no.", _regex(r"\bno\b")),
    # --- short factual ---
    SuiteTask("fact-capital", "factual", "What is the capital city of Australia? Answer with just the city name.", _regex(r"\bCanberra\b")),
    SuiteTask("fact-element", "factual", "What is the chemical symbol for tungsten? Answer with just the symbol.", _regex(r"\bW\b", 0)),
    SuiteTask("fact-planet", "factual", "Which planet in our solar system has the most moons as of 2024? Answer with just the planet name.", _regex(r"\bSaturn\b")),
    SuiteTask("fact-author", "factual", "Who wrote the novel 'One Hundred Years of Solitude'? Answer with just the author's name.", _regex(r"M[aá]rquez")),
    # --- extraction ---
    SuiteTask("ext-price", "extraction", 'From this record, extract the price as a number only: {"sku": "A-113", "price": 42.75, "currency": "USD", "qty": 3}', _regex(r"42\.75")),
    SuiteTask("ext-email", "extraction", "Extract the email address from this text and output only the address: 'Contact our support lead (Maria Chen) at m.chen+help@example.org before Friday.'", _regex(r"m\.chen\+help@example\.org")),
    SuiteTask("ext-date", "extraction", "Extract the ISO date from this sentence, output only YYYY-MM-DD: 'The migration completed on 2025-11-30 after two delays.'", _regex(r"2025-11-30")),
    SuiteTask("ext-max", "extraction", "From this list of measurements [12.1, 9.8, 15.6, 14.9, 3.2], output only the largest value.", _regex(r"15\.6")),
    # --- arithmetic / reasoning ---
    SuiteTask("math-chain", "reasoning", "A warehouse has 240 boxes. 3/8 are shipped Monday, then 45 more on Tuesday. How many boxes remain? Show brief working, end with 'ANSWER: <number>'.", _regex(r"ANSWER:\s*105\b")),
    SuiteTask("math-pct", "reasoning", "A price drops from 80 to 62. What is the percentage decrease? End your reply with 'ANSWER: <number>%' rounded to one decimal.", _regex(r"ANSWER:\s*22\.5\s*%")),
    SuiteTask("math-lcm", "reasoning", "What is the least common multiple of 12 and 18? End your reply with 'ANSWER: <number>'.", _regex(r"ANSWER:\s*36\b")),
    SuiteTask("math-age", "reasoning", "Ana is twice as old as Ben. In 6 years the sum of their ages will be 48. How old is Ben now? End with 'ANSWER: <number>'.", _regex(r"ANSWER:\s*12\b")),
    # --- code generation ---
    SuiteTask("code-rev", "code", "Write a Python function `rev_words(s)` that reverses the order of words in a string. Words are separated by single spaces. Return only a python code block.", _code_passes("rev_words", [(("hello world",), "world hello"), (("a b c",), "c b a")])),
    SuiteTask("code-fib", "code", "Write a Python function `fib(n)` returning the nth Fibonacci number with fib(0)=0, fib(1)=1. Iterative, no recursion. Return only a python code block.", _code_passes("fib", [((0,), 0), ((1,), 1), ((10,), 55)])),
    SuiteTask("code-dedup", "code", "Write a Python function `dedup(xs)` that removes duplicates from a list while preserving first-seen order. Return only a python code block.", _code_passes("dedup", [(([3, 1, 3, 2, 1],), [3, 1, 2]), (([],), [])])),
    SuiteTask("code-caesar", "code", "Write a Python function `caesar(s, k)` that shifts lowercase letters by k (wrapping), leaving other characters unchanged. Return only a python code block.", _code_passes("caesar", [(("abc z", 1), "bcd a"), (("hello", 0), "hello")])),
    # --- structured JSON output ---
    SuiteTask("json-book", "json", 'Output a JSON object (no prose, no code fences) with keys "title" and "year" for the novel 1984 by George Orwell. Year as integer.', _json_has("year", 1949)),
    SuiteTask("json-triangle", "json", 'A triangle has sides 3, 4, 5. Output only a JSON object: {"is_right": <boolean>, "area": <number>}.', _json_has("area", 6)),
    SuiteTask("json-color", "json", 'Output only a JSON object mapping "red" to its lowercase hex code string "#ff0000" under the key "hex".', _json_has("hex", "#ff0000")),
    SuiteTask("json-count", "json", 'Count the vowels in "orchestration" and output only a JSON object: {"vowels": <integer>}.', _json_has("vowels", 5)),
]
