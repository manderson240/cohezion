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


def _default_gates(repo: str) -> dict:
    """Deterministic pre-flight gates: ruff format/check + version_governance. $0, no inference.

    The heavy full pytest suite is CI's authoritative job; the runner does the fast
    deterministic pre-flight so a BLOCKED verdict is cheap and certain.
    """
    checks = [
        (["uv", "run", "--no-sync", "ruff", "format", "--check", "src/", "tests/"], "ruff format"),
        (
            ["uv", "run", "--no-sync", "python", "scripts/ci/version_governance.py"],
            "version_governance",
        ),
    ]
    failures: list[str] = []
    for cmd, name in checks:
        try:
            p = subprocess.run(cmd, cwd=repo, capture_output=True, text=True, timeout=180)
            if p.returncode != 0:
                failures.append(
                    f"{name}: {(p.stderr or p.stdout).strip().splitlines()[-1:] or ['failed']}"
                )
        except (
            Exception
        ) as exc:  # infra error → fail-closed for a gate (a landing must be provable)
            failures.append(f"{name}: {exc}")
    return {"ok": not failures, "failures": failures}


def _local_review(diff: str) -> str:
    """One local adversarial lens over the diff (:13305, $0). Returns raw verdict text."""
    prompt = (
        "You are an INDEPENDENT reviewer. ASSUME THE DIFF IS BROKEN. Find real correctness/"
        "security defects. If none, reply exactly 'OK'. Otherwise list each as 'SEVERITY | issue'."
        "\n\nDIFF (truncated):\n" + diff[:8000]
    )
    body = json.dumps({"model": _LOCAL_REVIEWER, "messages": [{"role": "user", "content": prompt}]})
    req = urllib.request.Request(  # noqa: S310 — fixed localhost router
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
    gate_fn = gate_fn or _default_gates
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
