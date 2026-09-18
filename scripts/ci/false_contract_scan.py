#!/usr/bin/env python3
"""False-contract scan — does the producer do what its NAME promises?

Fourth sibling of the existing structural gates:

    dormancy_scan.py       -> has a consumer?
    phantom_attr_scan.py   -> does the attribute exist?
    doc_code_consistency.py-> do the docs tell the truth?
    (this)                 -> does the producer do what its NAME promises?

ORIGIN. ``CrossSessionEventBridge.publish_and_persist`` had five production consumers
and persisted nothing: it called ``event_bus.publish_sync()`` and returned True, never
touching ``self.surreal_client`` declared on the same class. ``dormancy_scan`` reported
"all 19 curated capabilities have production consumers" — green, and correct, because
it asks a different question. A producer WITH consumers can still be a no-op.

AST-BASED, NOT REGEX, and that is the whole point. This defect class *is* "the docstring
says it, the code doesn't", so a ``grep`` for ``surreal`` matches the very docstring that
lies. Only real ``ast.Name`` / ``ast.Attribute`` / ``ast.Call`` references in the body
count; ``ast.Constant`` strings and comments (which the parser discards) never do.

SCOPE. Name-vs-body only. The sibling "unawaited coroutine" check sketched in the
originating report is deliberately NOT implemented here: it requires resolving whether a
call target is async, which is type inference. mypy already does that correctly and
default-on (``[unused-coroutine]``), and this repo already gates it through
``scripts/ci/mypy_ratchet.py``. An AST approximation of a check we already have would be
strictly worse.

PRECISION OVER RECALL. The shape is a heuristic, not a verdict: of the ``_and_`` names
read during the originating audit, roughly half were honest. Findings are therefore
restricted to a curated registry, exactly like ``dormancy_scan``. A scanner that cries
wolf trains people to ignore it. ``--sweep`` shows every candidate for triage without
gating on it.

Usage:
  python scripts/ci/false_contract_scan.py --self-test   # must pass before the gate runs
  python scripts/ci/false_contract_scan.py               # gate (exit 1 on a finding)
  python scripts/ci/false_contract_scan.py --sweep       # advisory: every candidate
"""

from __future__ import annotations

import argparse
import ast
import sys
import tempfile
import warnings
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SRC_ROOT = REPO_ROOT / "src" / "cohezion"

# A promised verb -> the tokens that would evidence it actually happening in the body.
# Matching is substring-on-identifier, so "surreal_client" satisfies "surreal".
#
# EVERY set must contain its own verb. Omitting it produced a false positive on the very
# first real-tree sweep: `reconcile_and_persist` ends in `return self.bridge.persist(mark)`
# — it persists by delegating to a collaborator literally named `persist` — and was
# flagged because "persist" was missing from its own token set.
PROMISE_TOKENS: dict[str, frozenset[str]] = {
    "persist": frozenset(
        {"persist", "surreal", "client", "db", "store", "save", "write", "upsert", "flush"}
    ),
    # "sync_config_file": ConfigSyncEngine's entry point, which owns the write + git commit.
    # regenerate_and_commit commits by delegating to it (same shape as the `persist` case).
    "commit": frozenset({"git", "repo", "commit", "subprocess", "index", "sync_config_file"}),
    "publish": frozenset({"bus", "publish", "emit", "event", "broadcast"}),
    "emit": frozenset({"emit", "bus", "event", "publish", "signal"}),
    "register": frozenset({"registry", "register", "add", "record"}),
    "store": frozenset({"store", "db", "cache", "write", "save", "surreal"}),
    "save": frozenset({"save", "write", "dump", "store", "persist"}),
    "notify": frozenset({"notify", "alert", "send", "telegram", "webhook"}),
    "cache": frozenset({"cache", "memo", "store"}),
}

# Curated registry: functions whose name-vs-body contract is GATED.
# Add an entry when a false contract is fixed, so it cannot silently regress.
# Format: "<path relative to src/cohezion>::<function name>"
REGISTRY: frozenset[str] = frozenset(
    {
        "core/cross_session_event_bridge.py::publish_and_persist",
        "config/configuration_orchestrator.py::regenerate_and_commit",
        "memory/autopoietic_memory_fabric.py::reconcile_and_persist",
        "core/config_templates.py::generate_executable_and_register",
        "core/config_templates.py::generate_and_register",
        "flume/train.py::_save_and_emit",
        "inference/delegation_logger.py::_surreal_and_mesh_push",
    }
)


class Finding:
    """One function whose name promises a collaborator its body never references."""

    def __init__(self, path: str, func: str, lineno: int, verb: str) -> None:
        self.path = path
        self.func = func
        self.lineno = lineno
        self.verb = verb

    @property
    def key(self) -> str:
        return f"{self.path}::{self.func}"

    def __str__(self) -> str:
        return (
            f"{self.path}:{self.lineno}: {self.func}() promises '{self.verb}' "
            f"but no {sorted(PROMISE_TOKENS[self.verb])[:3]}... reference appears in the body"
        )


def _body_identifiers(func: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    """Every identifier REALLY referenced in the body, lowercased.

    Deliberately excludes ``ast.Constant`` — a collaborator named only inside a
    docstring or a string literal is exactly the lie this scanner exists to catch.
    Comments never reach the AST at all, so they are excluded for free.
    """
    names: set[str] = set()
    for node in ast.walk(func):
        if isinstance(node, ast.Name):
            names.add(node.id.lower())
        elif isinstance(node, ast.Attribute):
            names.add(node.attr.lower())
        elif isinstance(node, ast.arg):
            names.add(node.arg.lower())
    # The function's own name is not evidence that it did the work.
    names.discard(func.name.lower())
    return names


def _declines_explicitly(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """True if the body raises ``NotImplementedError`` as a direct statement.

    A false contract is *claiming success you did not achieve*. Raising is the opposite:
    the caller is told, loudly and unmissably, that the work did not happen. Flagging it
    would punish the honest fix and leave the gate permanently red on any acknowledged
    stub — which is how a gate gets disabled.

    Restricted to direct children of the function body on purpose: a
    ``NotImplementedError`` buried inside one arm of a conditional does not make the
    other arms honest.
    """
    for stmt in func.body:
        if not isinstance(stmt, ast.Raise) or stmt.exc is None:
            continue
        exc = stmt.exc
        target = exc.func if isinstance(exc, ast.Call) else exc
        if isinstance(target, ast.Name) and target.id == "NotImplementedError":
            return True
        if isinstance(target, ast.Attribute) and target.attr == "NotImplementedError":
            return True
    return False


def _promised_verbs(func_name: str) -> list[str]:
    """Verbs a ``<a>_and_<b>`` name promises and that we know how to check."""
    if "_and_" not in func_name:
        return []
    parts = func_name.lower().strip("_").split("_and_")
    verbs: list[str] = []
    for part in parts:
        for token in part.split("_"):
            if token in PROMISE_TOKENS and token not in verbs:
                verbs.append(token)
    return verbs


def check_source(source: str, path: str) -> list[Finding]:
    """Parse one module and return its false-contract findings."""
    try:
        with warnings.catch_warnings():
            # Some modules contain invalid escape sequences in string literals. That is
            # a real (unrelated) lint issue; it must not drown this scanner's output.
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(source)
    except SyntaxError:
        return []

    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        verbs = _promised_verbs(node.name)
        if not verbs:
            continue
        if _declines_explicitly(node):
            continue
        identifiers = _body_identifiers(node)
        for verb in verbs:
            tokens = PROMISE_TOKENS[verb]
            satisfied = any(tok in ident for ident in identifiers for tok in tokens)
            if not satisfied:
                findings.append(Finding(path, node.name, node.lineno, verb))
    return findings


def scan_tree(root: Path) -> tuple[list[Finding], int]:
    """Scan every module under ``root``. Returns (findings, candidates_examined)."""
    findings: list[Finding] = []
    candidates = 0
    for py in sorted(root.rglob("*.py")):
        rel = py.relative_to(root).as_posix()
        try:
            source = py.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", SyntaxWarning)
                tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and _promised_verbs(
                node.name
            ):
                candidates += 1
        findings.extend(check_source(source, rel))
    return findings, candidates


# --------------------------------------------------------------------------------------
# Self-test. The gate MUST NOT run unless this passes: an unrun scanner is worse than no
# scanner, because a green from it is mistaken for evidence.
# --------------------------------------------------------------------------------------

_FIXTURE_FALSE_CONTRACT_PERSIST = '''
class Bridge:
    def publish_and_persist(self, event):
        """Synchronously dispatch event onto local bus and queue for persistence."""
        self.event_bus.publish_sync(event)
        return True
'''

_FIXTURE_FALSE_CONTRACT_COMMIT = '''
class Orch:
    async def regenerate_and_commit(self, filename, reason="manual"):
        """Regenerate config file and commit to git."""
        # Phase 4: Generate new content from vault
        # Phase 4: Create git commit
        logger.info("Successfully regenerated")
        return True
'''

_FIXTURE_HONEST = '''
def _save_and_emit(model, bus):
    """Checkpoint the model and announce it."""
    save_checkpoint(model)
    bus.emit(PrecipitationEvent(kind="checkpoint"))
'''

_FIXTURE_DOCSTRING_ONLY = '''
def write_and_store(payload):
    """Writes the payload and stores it in the surreal_client cache db."""
    # stores it via surreal_client
    return len(payload)
'''

# Both fixtures below were added because the FIRST sweep of the real tree produced a
# wrong answer for each. They are regression guards for the scanner itself.

_FIXTURE_DELEGATES_TO_COLLABORATOR = '''
class Fabric:
    def reconcile_and_persist(self):
        """Reconcile the fabric and persist the result."""
        mark = self.build_mark()
        return self.bridge.persist(mark)
'''

_FIXTURE_HONEST_DELEGATE_COMMIT = """
class Orch:
    async def regenerate_and_commit(self, filename):
        result = await self.sync_engine.sync_config_file(filename)
        return bool(result.get("synced"))
"""

_FIXTURE_HONEST_REFUSAL = '''
class Orch:
    async def regenerate_and_commit(self, filename):
        """Not implemented — raises rather than reporting success it did not achieve."""
        if filename not in ("CLAUDE.md",):
            return False
        raise NotImplementedError("neither regenerates nor commits")
'''


def _self_test() -> int:
    """Four fixtures the gate must classify correctly, plus the zero-candidate guard."""
    failures: list[str] = []

    def expect(name: str, source: str, should_flag: bool, verb: str | None = None) -> None:
        found = check_source(source, f"<fixture:{name}>")
        flagged = bool(found)
        if flagged != should_flag:
            failures.append(
                f"{name}: expected {'a finding' if should_flag else 'silence'}, "
                f"got {[str(f) for f in found] or 'silence'}"
            )
            return
        if should_flag and verb is not None and not any(f.verb == verb for f in found):
            failures.append(f"{name}: flagged, but not for the promised verb {verb!r}")

    # 1. The real F5 case: name promises persistence, body only touches the bus.
    expect("publish_and_persist", _FIXTURE_FALSE_CONTRACT_PERSIST, True, "persist")
    # 2. The real F2 case: name promises a commit, body is comments and a lie.
    expect("regenerate_and_commit", _FIXTURE_FALSE_CONTRACT_COMMIT, True, "commit")
    # 3. NEGATIVE CONTROL. Both halves genuinely present -> must stay silent. Without
    #    this the scanner could "pass" by flagging everything.
    expect("_save_and_emit", _FIXTURE_HONEST, False)
    # 4. Proves AST, not grep: the collaborator appears ONLY in a docstring and comment.
    #    A regex implementation passes this fixture and is wrong.
    expect("docstring_only", _FIXTURE_DOCSTRING_ONLY, True, "store")
    # 4b. NEGATIVE CONTROL from the first real sweep: persistence delegated to a
    #     collaborator literally named `persist`. Flagged until "persist" was added to
    #     its own token set. A false positive here discredits the whole gate.
    expect("delegates_to_collaborator", _FIXTURE_DELEGATES_TO_COLLABORATOR, False)
    # 4c. NEGATIVE CONTROL: an explicit refusal is honest, not a false contract. Without
    #     this the gate stays red on every acknowledged stub and gets switched off.
    expect("honest_refusal", _FIXTURE_HONEST_REFUSAL, False)
    # 4d. NEGATIVE CONTROL: the commit is delegated to the sync engine (the real
    #     post-fix shape of regenerate_and_commit).
    expect("delegate_commit", _FIXTURE_HONEST_DELEGATE_COMMIT, False)

    # 5. The precondition that must be able to fail. `producer_consumer_audit.py` was
    #    unlandable because it scored "0 producers / 0 consumers" as VERIFIED — absent
    #    measurement reported as success. Zero candidates is a BROKEN INSTRUMENT here.
    with tempfile.TemporaryDirectory() as tmp:
        empty = Path(tmp)
        (empty / "nothing.py").write_text("def plain(): return 1\n")
        _, candidates = scan_tree(empty)
        if candidates != 0:
            failures.append("zero-candidate fixture unexpectedly found candidates")
        # and the gate must treat that as failure, not as a pass:
        if _gate_verdict([], candidates) == 0:
            failures.append(
                "zero candidates was scored as PASS — this is the "
                "producer_consumer_audit defect (absent measurement as success)"
            )

    if failures:
        print("SELF-TEST FAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("SELF-TEST PASSED (6 fixtures):")
    print("  flagged   : publish_and_persist, regenerate_and_commit (the two real cases)")
    print("  flagged   : docstring-only mention  -> proves AST-based, not grep")
    print("  silent    : _save_and_emit          -> both halves genuinely present")
    print("  silent    : delegated .persist()    -> real-sweep false positive, guarded")
    print("  silent    : NotImplementedError     -> an explicit refusal is honest")
    print("  FAILURE   : zero-candidate run      -> absent measurement is never a pass")
    return 0


def _gate_verdict(findings: list[Finding], candidates: int) -> int:
    """Exit code for the gate. Zero candidates is a failure, never a pass."""
    if candidates == 0:
        return 1
    return 1 if findings else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="verify the scanner itself")
    parser.add_argument(
        "--sweep", action="store_true", help="advisory: report every candidate, do not gate"
    )
    args = parser.parse_args()

    if args.self_test:
        return _self_test()

    if not SRC_ROOT.is_dir():
        print(f"FAIL: source root not found: {SRC_ROOT}")
        return 1

    findings, candidates = scan_tree(SRC_ROOT)

    if args.sweep:
        print(f"Candidates examined: {candidates}")
        print(f"Flagged (advisory, unfiltered): {len(findings)}")
        for f in sorted(findings, key=lambda x: x.key):
            marker = "GATED" if f.key in REGISTRY else "     "
            print(f"  [{marker}] {f}")
        return 0

    gated = [f for f in findings if f.key in REGISTRY]
    verdict = _gate_verdict(gated, candidates)

    if candidates == 0:
        print("FAIL: zero candidates examined — the scanner found nothing to check.")
        print("      That is a broken instrument, not a clean tree.")
        return 1

    if gated:
        print(f"FAIL: {len(gated)} false contract(s) in the curated registry:")
        for f in sorted(gated, key=lambda x: x.key):
            print(f"  - {f}")
        return verdict

    print(
        f"OK: {candidates} candidate(s) examined, "
        f"{len(REGISTRY)} registered contract(s) honest "
        f"({len(findings) - len(gated)} unregistered candidate(s) flagged advisory-only; "
        f"run --sweep to triage)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
