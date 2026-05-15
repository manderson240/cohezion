"""Adversarial batch Z64: task_manager callback routing + audit_log timestamp filter.

Real bugs found:
1. TaskManager stores on_complete and on_error in the same list — both fire on
   every outcome regardless of success/failure.
2. AuditLogger.query() iterates date-partitioned files but never filters individual
   entry timestamps — returns entries outside the requested time window.
3. AuditLogger.export_for_compliance(format='csv') returns empty string with no
   header row when the result set is empty.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime


# ---------------------------------------------------------------------------
# Module 1: core/task_manager.py — on_complete/on_error callback routing
# ---------------------------------------------------------------------------


class TestTaskManagerCallbackRouting:
    def setup_method(self):
        from cohezion.core.task_manager import reset_task_manager

        reset_task_manager()

    async def _make_manager(self):
        from cohezion.core.task_manager import TaskManager

        return TaskManager()

    def test_on_error_not_called_on_success(self):
        """on_error must NOT fire when a task completes successfully.

        BUG: both callbacks go into the same list (_callbacks[task_id]).
        The success path iterates the whole list, triggering on_error even
        when the task succeeded.
        """
        error_calls = []

        async def on_error(info):
            error_calls.append(info.status)

        async def run():
            mgr = await self._make_manager()

            async def succeed():
                return 42

            await mgr.create_task(succeed(), name="ok", on_error=on_error)
            await asyncio.sleep(0.05)

        asyncio.run(run())
        assert error_calls == [], f"on_error fired {error_calls} on a successful task"

    def test_on_complete_not_called_on_failure(self):
        """on_complete must NOT fire when a task raises an exception.

        BUG: same list — the failure path iterates every callback, including
        on_complete, so callers get a 'success' signal after a crash.
        """
        complete_calls = []

        async def on_complete(info):
            complete_calls.append(info.status)

        async def run():
            mgr = await self._make_manager()

            async def fail():
                raise ValueError("boom")

            await mgr.create_task(fail(), name="bad", on_complete=on_complete)
            await asyncio.sleep(0.05)

        asyncio.run(run())
        assert complete_calls == [], f"on_complete fired {complete_calls} on a failing task"

    def test_on_complete_fires_exactly_once_on_success(self):
        """on_complete must fire exactly once when task succeeds."""
        results = []

        async def on_complete(info):
            results.append("complete")

        async def run():
            mgr = await self._make_manager()

            async def succeed():
                return 1

            await mgr.create_task(succeed(), on_complete=on_complete)
            await asyncio.sleep(0.05)

        asyncio.run(run())
        assert results == ["complete"]

    def test_on_error_fires_exactly_once_on_failure(self):
        """on_error must fire exactly once when task raises."""
        results = []

        async def on_error(info):
            results.append("error")

        async def run():
            mgr = await self._make_manager()

            async def fail():
                raise RuntimeError("expected")

            await mgr.create_task(fail(), on_error=on_error)
            await asyncio.sleep(0.05)

        asyncio.run(run())
        assert results == ["error"]

    def test_both_callbacks_provided_correct_routing(self):
        """When both are provided, each fires exactly once for its outcome."""
        complete_calls = []
        error_calls = []

        async def on_complete(info):
            complete_calls.append("complete")

        async def on_error(info):
            error_calls.append("error")

        async def run():
            mgr = await self._make_manager()

            async def succeed():
                return 99

            await mgr.create_task(succeed(), on_complete=on_complete, on_error=on_error)
            await asyncio.sleep(0.05)

        asyncio.run(run())
        assert complete_calls == ["complete"]
        assert error_calls == [], f"on_error fired incorrectly: {error_calls}"


# ---------------------------------------------------------------------------
# Module 2: security/audit_log.py — timestamp filter + empty CSV header
# ---------------------------------------------------------------------------


class TestAuditLogQueryFilter:
    def _make_logger(self, tmp_path):
        from cohezion.security.audit_log import AuditLogger

        return AuditLogger(log_path=str(tmp_path), retention_days=90)

    def _entry(self, ts: datetime, agent: str = "a1", resource: str = "/r"):
        from cohezion.security.audit_log import AuditAction, AuditLogEntry

        return AuditLogEntry(
            timestamp=ts,
            agent_id=agent,
            action=AuditAction.READ,
            resource=resource,
        )

    def test_query_excludes_entries_before_start_time(self, tmp_path):
        """Entries logged before start_date must not appear in query results.

        BUG: query() iterates date-partitioned files by day but never checks
        entry.timestamp against start_date/end_date. Entries from 00:00 on a
        matching day are returned even when start_date is 14:00 the same day.
        """
        al = self._make_logger(tmp_path)
        day = datetime(2026, 5, 15, tzinfo=UTC)

        al.log(self._entry(datetime(2026, 5, 15, 0, 30, tzinfo=UTC)))  # before window
        al.log(self._entry(datetime(2026, 5, 15, 11, 0, tzinfo=UTC)))  # in window
        al.log(self._entry(datetime(2026, 5, 15, 23, 30, tzinfo=UTC)))  # after window

        results = al.query(
            start_date=datetime(2026, 5, 15, 10, 0, tzinfo=UTC),
            end_date=datetime(2026, 5, 15, 12, 0, tzinfo=UTC),
        )
        timestamps = [r.timestamp for r in results]
        assert len(results) == 1, f"Expected 1 entry in 10:00-12:00 window, got {len(results)}: {timestamps}"

    def test_query_excludes_entries_after_end_time(self, tmp_path):
        """Entries logged after end_date must not appear in results."""
        al = self._make_logger(tmp_path)

        al.log(self._entry(datetime(2026, 5, 15, 8, 0, tzinfo=UTC)))  # in window
        al.log(self._entry(datetime(2026, 5, 15, 20, 0, tzinfo=UTC)))  # after window

        results = al.query(
            start_date=datetime(2026, 5, 15, 0, 0, tzinfo=UTC),
            end_date=datetime(2026, 5, 15, 12, 0, tzinfo=UTC),
        )
        assert len(results) == 1

    def test_empty_csv_export_has_header_row(self, tmp_path):
        """CSV export with no matching entries must still include the header row.

        BUG: export_for_compliance writes header only inside 'if entries:' block.
        An empty result returns '' — compliance parsers that expect a header crash.
        """
        al = self._make_logger(tmp_path)
        csv_out = al.export_for_compliance(
            start_date=datetime(2020, 1, 1, tzinfo=UTC),
            end_date=datetime(2020, 1, 2, tzinfo=UTC),
            format="csv",
        )
        assert "timestamp" in csv_out, f"Empty CSV must contain header row, got: {csv_out!r}"
        assert "agent_id" in csv_out

    def test_nonempty_csv_export_still_correct(self, tmp_path):
        """CSV export with entries must include header + data rows."""
        al = self._make_logger(tmp_path)
        al.log(self._entry(datetime(2026, 5, 15, 10, 0, tzinfo=UTC), agent="x", resource="/y"))

        csv_out = al.export_for_compliance(
            start_date=datetime(2026, 5, 15, tzinfo=UTC),
            end_date=datetime(2026, 5, 16, tzinfo=UTC),
            format="csv",
        )
        lines = [l for l in csv_out.strip().splitlines() if l]
        assert len(lines) == 2  # header + 1 data row
        assert "timestamp" in lines[0]
        assert "x" in csv_out
