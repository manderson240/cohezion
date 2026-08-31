"""D3: async SurrealClient writes invoked from sync code without ``run_sync``.

Every public write on :class:`SurrealClient` is ``async def``. Calling one from a
synchronous function without ``await`` constructs the coroutine and DISCARDS it:
the write never happens, nothing raises, and the caller's ``try/except`` never
fires — so the feature looks wired while being dead.

``surreal_client.run_sync`` was written on 2026-07-30 explicitly to fix this, and
its own docstring names the two sites found live at the time
(``AutoDQA._persist_result`` and ``gemini_cli_tier._persist_tier_experience``).
Neither site was ever changed: the helper shipped, the fix did not.

Why ``await_count`` and not ``call_count``: an ``AsyncMock`` records a *call* the
moment the coroutine is constructed, which the broken code does. Only awaiting it
increments ``await_count``. ``call_count`` therefore passes against the broken
code and cannot discriminate — it is the wrong instrument for this defect.
"""

from __future__ import annotations

import ast
import pathlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# T2 discriminating: the write must actually be driven to completion
# ---------------------------------------------------------------------------


class TestAutoDQAPersistenceIsDriven:
    """AutoDQA._persist_result must AWAIT the async create, not merely call it."""

    def _result(self):
        from cohezion.compound.autodqa import AutoDQA

        dqa = AutoDQA(persist=False, notify_on_reject=False)
        return dqa, dqa.evaluate("a sufficiently long and specific answer here", "explain a thing")

    def test_persist_result_awaits_the_create_coroutine(self):
        """Broken impl builds the coroutine and drops it -> await_count == 0."""
        dqa, result = self._result()
        client = MagicMock()
        client.create = AsyncMock(return_value={"id": "autodqa_results:x"})

        with patch("cohezion.core.persistence.surreal_client.SurrealClient", return_value=client):
            dqa._persist_result(result)

        assert client.create.await_count == 1, (
            "AutoDQA._persist_result must AWAIT SurrealClient.create (via run_sync); "
            f"the coroutine was constructed {client.create.call_count} time(s) but "
            f"awaited {client.create.await_count} time(s) — the row is never written"
        )

    def test_row_payload_reaches_the_client(self):
        """The awaited call must carry the real table + fields (not an empty stub)."""
        dqa, result = self._result()
        client = MagicMock()
        client.create = AsyncMock(return_value=None)

        with patch("cohezion.core.persistence.surreal_client.SurrealClient", return_value=client):
            dqa._persist_result(result)

        table, payload = client.create.await_args[0]
        assert table == "autodqa_results"
        assert payload["task_id"] == result.task_id
        assert payload["score"] == result.verdict.score
        assert payload["quality_band"] == result.quality_band

    def test_persist_failure_stays_non_blocking(self):
        """A dead database must not propagate out of evaluate() (fail-open contract)."""
        from cohezion.compound.autodqa import AutoDQA

        client = MagicMock()
        client.create = AsyncMock(side_effect=RuntimeError("surreal down"))
        dqa = AutoDQA(persist=True, notify_on_reject=False)

        with patch("cohezion.core.persistence.surreal_client.SurrealClient", return_value=client):
            out = dqa.evaluate("a sufficiently long and specific answer here", "explain a thing")

        assert out.verdict is not None, "evaluate() must survive a failing persist"


class TestGeminiTierPersistenceIsDriven:
    """gemini_cli_tier._persist_tier_experience — same defect, same class."""

    def test_persist_tier_experience_awaits_the_create_coroutine(self):
        from cohezion.inference.gemini_cli_tier import _persist_tier_experience

        client = MagicMock()
        client.create = AsyncMock(return_value=None)

        with patch("cohezion.core.persistence.surreal_client.SurrealClient", return_value=client):
            _persist_tier_experience("npu", "a prompt", "an output", 12.5)

        assert client.create.await_count == 1, (
            "_persist_tier_experience must AWAIT SurrealClient.create (via run_sync); "
            f"constructed {client.create.call_count}, awaited {client.create.await_count}"
        )

    def test_tier_experience_payload_reaches_the_client(self):
        from cohezion.inference.gemini_cli_tier import _persist_tier_experience

        client = MagicMock()
        client.create = AsyncMock(return_value=None)

        with patch("cohezion.core.persistence.surreal_client.SurrealClient", return_value=client):
            _persist_tier_experience("igpu", "a prompt", "an output", 33.0)

        table, payload = client.create.await_args[0]
        assert table == "tier_experience"
        assert payload["tier"] == "igpu"
        assert payload["latency_ms"] == 33.0


# ---------------------------------------------------------------------------
# Class-level regression: keep the defect class at zero across all of src/
# ---------------------------------------------------------------------------

_ASYNC_METHODS = frozenset(
    {
        "is_alive",
        "ensure_active",
        "connect",
        "setup_schema",
        "store_node",
        "create",
        "query",
        "get_node",
        "query_similar",
        "get_all_nodes",
        "create_relationship",
        "get_relationships",
        "find_bridges",
        "close",
    }
)
_AWAIT_WRAPPERS = frozenset(
    {"run_sync", "run", "create_task", "ensure_future", "gather", "run_until_complete"}
)


def _unawaited_calls(path: pathlib.Path) -> list[tuple[int, str]]:
    """Un-awaited async calls on receivers PROVABLY bound to ``SurrealClient(...)``.

    Type-proving the receiver is what makes this usable: ``close``/``create``/``query``
    are also file-lock, Docker and thread methods, so matching the method NAME alone
    reports ~56 sites of which 54 are unrelated APIs. Binding the receiver to a
    ``SurrealClient()`` construction in the same module drops that to the real ones.
    """
    source = path.read_text(encoding="utf-8", errors="ignore")
    if "SurrealClient" not in source:
        return []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    bound: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            func = node.value.func
            name = (
                func.id
                if isinstance(func, ast.Name)
                else func.attr
                if isinstance(func, ast.Attribute)
                else None
            )
            if name == "SurrealClient":
                bound.update(ast.unparse(t) for t in node.targets)
    if not bound:
        return []

    awaited: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Await):
            awaited.add(id(node.value))
        elif isinstance(node, ast.Call):
            func = node.func
            wrapper = (
                func.id
                if isinstance(func, ast.Name)
                else func.attr
                if isinstance(func, ast.Attribute)
                else None
            )
            if wrapper in _AWAIT_WRAPPERS:
                awaited.update(id(a) for a in node.args)

    hits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or id(node) in awaited:
            continue
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr in _ASYNC_METHODS
            and ast.unparse(func.value) in bound
        ):
            hits.append((node.lineno, f"{ast.unparse(func.value)}.{func.attr}(...)"))
    return hits


def _src_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent.parent / "src"


class TestDefectClassStaysClosed:
    def test_no_unawaited_surreal_writes_in_src(self):
        """Any new sync caller of an async SurrealClient method fails here."""
        offenders = [
            f"{path.relative_to(_src_root().parent)}:{line}  {call}"
            for path in sorted(_src_root().rglob("*.py"))
            for line, call in _unawaited_calls(path)
        ]
        assert not offenders, (
            "async SurrealClient call(s) invoked from sync code without run_sync — "
            "the coroutine is discarded and the write silently never happens:\n  "
            + "\n  ".join(offenders)
        )

    def test_detector_fires_on_a_known_bad_shape(self, tmp_path):
        """Positive control: a scanner that never fires would pass the test above."""
        bad = tmp_path / "bad.py"
        bad.write_text(
            "from cohezion.core.persistence.surreal_client import SurrealClient\n"
            "def go():\n"
            "    client = SurrealClient()\n"
            "    client.create('t', {})\n"
        )
        assert _unawaited_calls(bad), "detector must flag a bare sync call"

    @pytest.mark.parametrize(
        "wrapped",
        [
            "    run_sync(client.create('t', {}))",
            "    asyncio.run(client.create('t', {}))",
        ],
    )
    def test_detector_silent_on_correctly_awaited_shapes(self, tmp_path, wrapped):
        """Negative control: wrapping in an await-driver must NOT be flagged."""
        good = tmp_path / "good.py"
        good.write_text(
            "from cohezion.core.persistence.surreal_client import SurrealClient, run_sync\n"
            "import asyncio\n"
            "def go():\n"
            "    client = SurrealClient()\n" + wrapped + "\n"
        )
        assert not _unawaited_calls(good), "correctly-driven call must not be flagged"

    def test_detector_ignores_same_named_methods_on_other_types(self, tmp_path):
        """A file-lock's .close() is not a SurrealClient write (false-positive guard)."""
        other = tmp_path / "other.py"
        other.write_text(
            "from cohezion.core.persistence.surreal_client import SurrealClient\n"
            "def go(lock):\n"
            "    client = SurrealClient()\n"
            "    lock.close()\n"
        )
        assert not _unawaited_calls(other), "unrelated receiver must not be flagged"
