#!/usr/bin/env python3
"""ACT-step probe CLI: can a LOCAL model turn one task into a red->green commit?

Thin CLI over ``cohezion.compound.autonomous_loop.act_loop`` (the loop was extracted
there on 2026-09-21 so ``LocalImprovementExecutor`` can consume it).

Usage:
  act_probe.py --repo R --file src/x.py --target fn --oracle tests/t.py \
      [--extra-test tests/u.py ...] --task-id ID --task "text" --model M
  act_probe.py --self-test
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from cohezion.compound.autonomous_loop.act_loop import (
    act_loop,
    git,
    make_chat_fn,
)


# ---------------------------------------------------------------- self-test
def self_test() -> int:
    """Fake model: a known-good edit must be committed, a known-bad one never."""
    good = "def value():\n    return 2\n"
    bad = "def value():\n    return 3\n"
    results = {}
    for label, replies in {
        "good": [bad, good],
        "bad": [bad, bad, "no fence here"],
        "flaky": ["RAISE", "RAISE", good],
    }.items():
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            (repo / "src/pkg").mkdir(parents=True)
            (repo / "tests").mkdir()
            (repo / "src/pkg/__init__.py").write_text("")
            (repo / "src/pkg/mod.py").write_text('"""m."""\n\n\ndef value():\n    return 1\n')
            (repo / "tests/test_mod.py").write_text(
                "from pkg.mod import value\n\n\ndef test_v():\n    assert value() == 2\n"
            )
            for c in (
                ["init", "-q"],
                ["config", "user.email", "t@t"],
                ["config", "user.name", "t"],
                ["add", "."],
                ["commit", "-q", "-m", "base"],
            ):
                git(repo, *c)
            it = iter(replies)

            def fake(prompt: str, _it: Any = it) -> dict[str, Any]:
                r = next(_it)
                if r == "RAISE":
                    raise TimeoutError("simulated router timeout")
                return {"text": f"```python\n{r}```" if "def" in r else r}

            res = act_loop(
                repo=repo,
                file="src/pkg/mod.py",
                targets=["value"],
                oracle="tests/test_mod.py",
                extra_tests=[],
                task="make value() return 2",
                task_id="self-test",
                model="fake",
                chat=fake,
                python=sys.executable,
                max_iters=1 if label == "flaky" else len(replies),
                call_backoff_s=0.0,
                log=repo / "log.jsonl",
            )
            n_commits = len(git(repo, "log", "--oneline").splitlines())
            results[label] = (res["status"], n_commits, (repo / "src/pkg/mod.py").read_text())
    checks = {
        "good edit committed": results["good"][:2] == ("GREEN", 2)
        and "return 2" in results["good"][2],
        "bad edit never committed": results["bad"][:2] == ("EXHAUSTED", 1),
        "bad edit rolled back": "return 1" in results["bad"][2],
        "router timeouts do not consume iterations": results["flaky"][:2] == ("GREEN", 2),
    }
    failed = [k for k, v in checks.items() if not v]
    if failed:
        print(f"act_probe self-test FAILED: {failed} {results}")
        return 1
    print("act_probe self-test OK: good edit committed, bad edit rejected + rolled back")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--repo", type=Path, default=Path.cwd())
    ap.add_argument("--file")
    ap.add_argument("--target", action="append", default=[])
    ap.add_argument("--oracle")
    ap.add_argument("--extra-test", action="append", default=[])
    ap.add_argument("--task")
    ap.add_argument("--task-id")
    ap.add_argument(
        "--model",
        action="append",
        default=[],
        help="preference order; each call uses the first CURRENTLY RESIDENT one (repeatable)",
    )
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("--max-iters", type=int, default=5)
    ap.add_argument("--max-tokens", type=int, default=3072)
    ap.add_argument("--timeout", type=float, default=180)
    ap.add_argument(
        "--log",
        type=Path,
        default=Path(os.environ.get("TMPDIR", "/tmp")) / "act_probe_log.jsonl",
    )
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    models = a.model or ["Qwen3-Coder-30B-A3B-Instruct-GGUF", "Gemma-4-31B-it-GGUF"]
    chat = make_chat_fn(models, max_tokens=a.max_tokens, timeout=a.timeout)
    res = act_loop(
        repo=a.repo,
        file=a.file,
        targets=a.target,
        oracle=a.oracle,
        extra_tests=a.extra_test,
        task=a.task,
        task_id=a.task_id,
        model="|".join(models),
        chat=chat,
        python=a.python,
        max_iters=a.max_iters,
        log=a.log,
    )
    print(json.dumps(res))
    return 0 if res["status"] == "GREEN" else 1


if __name__ == "__main__":
    sys.exit(main())
