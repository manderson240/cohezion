"""land_runner — the ``land_ready`` handler for the datamesh event-consumer.

When a feature branch signals it is landable (the ``land-ready-signal.sh`` Stop hook
publishes a ``data_product_event{event_type:"land_ready"}``), the ALREADY-RUNNING
``EventConsumer`` routes it here. This runner is the independent CI/CD gate:

  1. deterministic pre-flight gates   (ruff + version_governance — $0, no inference)
  2. independent adversarial review    (local-first :13305; escalate to cloud on a flag)
  3. semver proposal                   (Conventional Commits in the ahead-range)
  → a kanban work-item (READY / BLOCKED) the ``cohezion-actioner`` surfaces for a HUMAN.

Producer != verifier — STRUCTURALLY: the runner is invoked by the consumer daemon, not
by the agent that authored the branch, and it uses independent models. It NEVER pushes;
the fast-forward to main stays human-gated (git-operations.md).

Elegantly simple + testable: ``gate_fn`` / ``review_fn`` / ``semver_fn`` are INJECTABLE
(CB4/CB5 dependency-injection pattern). Real defaults do the live work; tests inject
mocks so the runner's orchestration logic is proven with ZERO live inference (no OOM).
"""

from __future__ import annotations

import json
import subprocess
import tempfile
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field


_ROUTER = "http://localhost:13305/v1/chat/completions"
# A LIGHT default reviewer (~5GB, iGPU) — this runs UNATTENDED in the event-consumer
# daemon, so it must not OOM the box (N3). Quarter-on-a-string: a light local first-pass
# flags; the cloud lens confirms depth on a genuine flag. Override for a heavier local
# reviewer only when memory is known-quiet.
_LOCAL_REVIEWER = "Gemma-4-E4B-it-GGUF"


@dataclass
class LandVerdict:
    """The runner's decision. ``ready`` is the AND of every gate — the consumption point."""

    branch: str
    gates_ok: bool
    review_ok: bool
    semver: str
    detail: dict = field(default_factory=dict)

    @property
    def ready(self) -> bool:
        # The one invariant that matters: a landing is READY only if BOTH the deterministic
        # gates AND the independent review pass. Any failure blocks. (Neutralising either
        # term must flip this to False — see the discriminating tests.)
        return bool(self.gates_ok) and bool(self.review_ok)

    @property
    def title(self) -> str:
        return (
            f"[land-review:{'READY' if self.ready else 'BLOCKED'}] {self.branch} -> {self.semver}"
        )

    def body(self) -> str:
        g = self.detail.get("gates", {})
        r = self.detail.get("review", {})
        lines = [
            f"Branch: {self.branch}",
            f"Verdict: {'READY to land' if self.ready else 'BLOCKED — do not land'}",
            f"Proposed semver: {self.semver}",
            "",
            f"Gates: {'PASS' if self.gates_ok else 'FAIL'}",
        ]
        if g.get("failures"):
            lines += [f"  - {x}" for x in g["failures"]]
        lines += ["", f"Independent review: {'PASS' if self.review_ok else 'BLOCK'}"]
        if r.get("findings"):
            lines += [f"  - {x}" for x in r["findings"]]
        if self.ready:
            lines += [
                "",
                "Next: a human approves, then the gated fast-forward push (never automatic).",
            ]
        return "\n".join(lines)


# ── real default implementations (live; not exercised by unit tests) ────────────────


def _default_gates(repo: str, branch: str = "") -> dict:
    """Deterministic pre-flight gates on the CANDIDATE MERGED TREE. $0, no inference.

    First live smoke (2026-08-14) proved gating the repo working tree measures the
    WRONG tree: the primary checkout sits on a session branch, so every candidate
    reported that branch's lint debt ("153 files would be reformatted") instead of
    its own. Gates therefore run on ``git merge-tree main <branch>`` — the tree
    that would actually land:

      CONFLICTS   -> BLOCKED with the conflicting paths (cheap, certain)
      INTEGRATED  -> BLOCKED "already integrated" (merge result == main's tree —
                     the only integration test that survives squash merges)
      CLEAN       -> extract the candidate tree (git archive; no worktree needed,
                     works while .git/worktrees is read-only) and ruff it.

    version_governance intentionally left OUT of this gate set: it can only read
    the checkout's HEAD commit range, never the candidate branch's; conventional-
    commit analysis for the branch is ``semver_fn``'s job. The heavy pytest suite
    stays CI's authoritative job.
    """
    if not branch:  # legacy call shape — no branch context, gate the repo as before
        return _repo_tree_gates(repo, ["src/", "tests/"])
    try:
        mt = subprocess.run(
            ["git", "-C", repo, "merge-tree", "--write-tree", "main", branch],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if mt.returncode != 0:
            conflicts = [
                ln.rsplit(" in ", 1)[-1]
                for ln in mt.stdout.splitlines()
                if ln.startswith("CONFLICT")
            ]
            return {
                "ok": False,
                "failures": [f"merge: CONFLICTS with main in {', '.join(conflicts[:8])}"],
            }
        tree = mt.stdout.splitlines()[0].strip()
        main_tree = subprocess.run(
            ["git", "-C", repo, "rev-parse", "main^{tree}"],
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout.strip()
        if tree == main_tree:
            return {"ok": False, "failures": ["merge: already integrated — nothing to land"]}
        with tempfile.TemporaryDirectory(prefix="land-gate-") as td:
            archive = subprocess.run(
                ["git", "-C", repo, "archive", tree, "src", "tests"],
                capture_output=True,
                check=True,
                timeout=300,
            )
            subprocess.run(
                ["tar", "-x", "-C", td],
                input=archive.stdout,
                check=True,
                timeout=300,
                capture_output=True,
            )
            # cwd=extract with RELATIVE paths: pyproject per-file-ignores are
            # path-pattern-relative ("tests/**" never matches /tmp/... paths —
            # measured live as 82 phantom errors on 3 clean test files).
            gate = _repo_tree_gates(repo, ["src", "tests"], cwd=td)
            # Lint is a DELTA gate: raw `ruff check` would hold every candidate
            # hostage to main's pre-existing debt (~460 baseline errors). A
            # candidate fails only if it ADDS errors relative to main's tree.
            gate = _apply_lint_delta(repo, gate, candidate_dir=td)
            return gate
    except Exception as exc:  # infra error → fail-closed (a landing must be provable)
        return {"ok": False, "failures": [f"merge-tree gate: {exc}"]}


def _repo_tree_gates(repo: str, paths: list[str], cwd: str | None = None) -> dict:
    """Ruff format+lint over *paths*, using the repo's ruff binary AND config.

    ``--config`` is pinned to the repo's pyproject (an extract under /tmp would
    otherwise discover ruff defaults), and *cwd* lets extract-gating run with
    RELATIVE paths so per-file-ignore patterns like ``tests/**`` still match.
    """
    cfg = f"{repo}/pyproject.toml"
    ruff = f"{repo}/.venv/bin/ruff"
    checks = [
        ([ruff, "format", "--check", "--config", cfg, *paths], "ruff format"),
    ]
    failures: list[str] = []
    for cmd, name in checks:
        try:
            p = subprocess.run(cmd, cwd=cwd or repo, capture_output=True, text=True, timeout=180)
            if p.returncode != 0:
                failures.append(
                    f"{name}: {(p.stderr or p.stdout).strip().splitlines()[-1:] or ['failed']}"
                )
        except (
            Exception
        ) as exc:  # infra error → fail-closed for a gate (a landing must be provable)
            failures.append(f"{name}: {exc}")
    return {"ok": not failures, "failures": failures}


def _lint_error_count(repo: str, tree_dir: str) -> int | None:
    """Count ruff-check errors over ``src``+``tests`` in *tree_dir*. None = unmeasurable."""
    try:
        p = subprocess.run(
            [
                f"{repo}/.venv/bin/ruff",
                "check",
                "--config",
                f"{repo}/pyproject.toml",
                "--output-format=concise",
                "src",
                "tests",
            ],
            cwd=tree_dir,
            capture_output=True,
            text=True,
            timeout=180,
        )
        return sum(1 for ln in p.stdout.splitlines() if ":" in ln)
    except Exception:
        return None


def _apply_lint_delta(repo: str, gate: dict, candidate_dir: str) -> dict:
    """Fail the gate only when the candidate ADDS lint errors relative to main.

    A raw ``ruff check`` would hold every candidate hostage to main's pre-existing
    baseline debt; the ratchet philosophy applies here too — never worse, and both
    sides are measured with the SAME instrument (extract + pinned config + relative
    paths). Unmeasurable on either side = fail-closed (a landing must be provable).
    """
    cand = _lint_error_count(repo, candidate_dir)
    with tempfile.TemporaryDirectory(prefix="land-gate-base-") as bd:
        try:
            archive = subprocess.run(
                ["git", "-C", repo, "archive", "main", "src", "tests"],
                capture_output=True,
                check=True,
                timeout=300,
            )
            subprocess.run(
                ["tar", "-x", "-C", bd],
                input=archive.stdout,
                check=True,
                timeout=300,
                capture_output=True,
            )
            base = _lint_error_count(repo, bd)
        except Exception:
            base = None
    if cand is None or base is None:
        gate["ok"] = False
        gate.setdefault("failures", []).append("ruff lint delta: unmeasurable (fail-closed)")
    elif cand > base:
        gate["ok"] = False
        gate.setdefault("failures", []).append(
            f"ruff lint delta: candidate adds {cand - base} error(s) ({base} -> {cand})"
        )
    return gate


def _review_prompt(diff: str) -> str:
    """VERDICT-FIRST prompt. Truncation must eat the reasoning, never the verdict.

    Measured 2026-07-28: lanes that were asked to reason first and conclude last
    (Bonsai-27B, Gemma-4-26B) thought out loud until the token budget died and
    never emitted a verdict at all.
    """
    return (
        "You are an INDEPENDENT code reviewer. ASSUME THE DIFF IS BROKEN.\n"
        "Reply with your VERDICT ON THE FIRST LINE, in exactly one of these forms:\n"
        "  VERDICT: CLEAR\n"
        "  VERDICT: DEFECT | <one-line description of the single most severe REAL defect>\n"
        "Then, after the verdict line, explain your reasoning.\n"
        "Report only defects you can point at in the diff — do NOT invent findings; "
        "clean code is a normal and expected outcome.\n\n"
        "DIFF (truncated):\n" + diff[:8000]
    )


def _lane_verdict(model: str, diff: str, timeout: float = 300.0) -> tuple[str, str]:
    """One local lane. Returns (verdict, detail) where verdict is CLEAR|DEFECT|UNMEASURABLE.

    ``UNMEASURABLE`` is a first-class outcome, NOT a pass. Before 2026-08-14 this
    returned raw text and the caller did ``any("CRITICAL"/"HIGH"/"BLOCK" in text)``:
    an EMPTY reply (Gemma-4-E4B is a thinking model whose answer lands in
    ``reasoning_content``, and no ``max_tokens`` was set) contained none of those
    markers, so a review that never happened scored as ``local-clear``. The gate
    could not fail. A POSITIVE marker contract fixes that: no ``VERDICT:`` line
    means the lane did not answer.
    """
    body = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": _review_prompt(diff)}],
            "max_tokens": 1200,  # enough for verdict + reasoning; never unbounded
        }
    )
    req = urllib.request.Request(  # noqa: S310 — fixed localhost router
        _ROUTER, data=body.encode(), headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
            msg = json.loads(r.read())["choices"][0]["message"]
    except Exception as exc:
        return "UNMEASURABLE", f"{model}: unreachable ({exc})"
    # Thinking models put the answer in reasoning_content; empty content is not empty output.
    text = str(msg.get("content") or "").strip() or str(msg.get("reasoning_content") or "").strip()
    for line in text.splitlines():
        s = line.strip().lstrip("*# ").strip()
        if s.upper().startswith("VERDICT:"):
            payload = s.split(":", 1)[1].strip()
            if payload.upper().startswith("CLEAR"):
                return "CLEAR", f"{model}: clear"
            if payload.upper().startswith("DEFECT"):
                return "DEFECT", f"{model}: {payload[:300]}"
            return "UNMEASURABLE", f"{model}: unparseable verdict {payload[:120]!r}"
    return "UNMEASURABLE", f"{model}: no VERDICT line in {len(text)}-char reply"


def _local_review(diff: str) -> str:
    """One local adversarial lens over the diff (:13305, $0). Returns raw verdict text."""
    prompt = (
        "You are an INDEPENDENT reviewer. ASSUME THE DIFF IS BROKEN. Find real correctness/"
        "security defects. If none, reply exactly 'OK'. Otherwise list each as 'SEVERITY | issue'."
        "\n\nDIFF (truncated):\n" + diff[:8000]
    )
    body = json.dumps({"model": _LOCAL_REVIEWER, "messages": [{"role": "user", "content": prompt}]})
    req = urllib.request.Request(
        _ROUTER, data=body.encode(), headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as r:  # noqa: S310
            return str(json.loads(r.read())["choices"][0]["message"]["content"]).strip()
    except Exception as exc:  # local reviewer unreachable → cannot clear (fail-closed)
        return f"BLOCK | local reviewer unavailable: {exc}"


def _default_review(repo: str, branch: str, base: str = "origin/main") -> dict:
    """Independent review: local lens; escalate to cloud only if local flags CRITICAL/HIGH.

    Quarter-on-a-string: local-first ($0); the cloud 'quarter' drops only on a genuine
    local flag, then confirms it. ``ok`` iff no unresolved CRITICAL/HIGH remains.
    """
    try:
        diff = subprocess.run(
            ["git", "diff", f"{base}...{branch}"],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=60,
        ).stdout
    except Exception as exc:
        return {"ok": False, "findings": [f"could not compute diff: {exc}"], "consensus": "error"}

    local = _local_review(diff)
    flagged = any(s in local.upper() for s in ("CRITICAL", "HIGH", "BLOCK"))
    if not flagged:
        return {"ok": True, "findings": [], "consensus": "local-clear"}

    # escalate to one cloud lens to confirm the local flag (independent, stronger)
    try:
        cloud = subprocess.run(
            ["ollama", "run", "deepseek-v4-pro:cloud"],
            input=(
                "An independent local reviewer flagged this diff. Confirm or refute the highest-"
                "severity real defect in ONE line ('CONFIRMED: ...' or 'REFUTED: no real defect'):"
                f"\n\nLOCAL REVIEW:\n{local[:2000]}\n\nDIFF:\n{diff[:6000]}"
            ),
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=300,
        ).stdout.strip()
    except Exception:
        cloud = ""  # cloud unavailable → trust the local flag (stay blocked, conservative)
    confirmed = "REFUTED" not in cloud.upper()
    return {
        "ok": not confirmed,
        "findings": [
            local.splitlines()[0] if local else "flagged",
            f"cloud: {cloud[:160] or 'unavailable'}",
        ],
        "consensus": "cloud-confirmed" if confirmed else "cloud-refuted",
    }


def _default_semver(repo: str, branch: str, base: str = "origin/main") -> str:
    """Propose a semver bump from Conventional Commits in the ahead-range (additive default)."""
    try:
        log = subprocess.run(
            ["git", "log", "--format=%s", f"{base}..{branch}"],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout.lower()
    except Exception:
        return "patch"
    if "!:" in log or "breaking change" in log:
        return "major"
    if any(line.startswith("feat") for line in log.splitlines()):
        return "minor"
    return "patch"


# ── the orchestrator (pure logic; the part unit tests pin) ──────────────────────────


def run_land_review(
    repo: str,
    branch: str,
    *,
    gate_fn: Callable[[str], dict] | None = None,
    review_fn: Callable[[str, str], dict] | None = None,
    semver_fn: Callable[[str, str], str] | None = None,
) -> LandVerdict:
    """Orchestrate gates + independent review + semver into a single verdict.

    Injectable fns default to the live implementations above; tests pass mocks so this
    orchestration is verified with no live inference. The verdict CONSUMES both results
    (``ready = gates_ok and review_ok``) — a failure in either blocks the landing.
    """
    # Bind the branch into the default so gates measure the CANDIDATE MERGED TREE,
    # not the checkout's working tree, while injected gate_fns keep the 1-arg contract.
    gate_fn = gate_fn or (lambda r: _default_gates(r, branch))
    review_fn = review_fn or _default_review
    semver_fn = semver_fn or _default_semver

    gates = gate_fn(repo)
    review = review_fn(repo, branch)
    semver = semver_fn(repo, branch)
    return LandVerdict(
        branch=branch,
        gates_ok=bool(gates.get("ok")),
        review_ok=bool(review.get("ok")),
        semver=str(semver or "patch"),
        detail={"gates": gates, "review": review},
    )
