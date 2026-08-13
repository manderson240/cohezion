"""RS5 — the datamesh bus must DISPATCH residency events to the admission gate.

Audit finding 2026-08-03: `ResidencyService` shipped with `handle_event`, a publish hook,
and a consumption invariant (RS1) proving the event->gate hop works WHEN CALLED — and had
**zero** production instantiations. Nothing published `model_needed`, nothing routed it.
The bus carried eight event types and none were residency events.

RS1 is a unit-level consumption invariant. It cannot detect that no event ever ARRIVES.
This file closes that gap at the system level: it asserts the real `EventConsumer.handle`
dispatch reaches the service, which is what "wired" actually means
(`verification-depth.md`: wired == a production consumer reads it and acts).
"""

from __future__ import annotations

import pytest

from cohezion.data_mesh.event_consumer import EventConsumer


@pytest.fixture
def consumer():
    """A consumer with no live SurrealDB — routing is what is under test, not I/O."""
    return EventConsumer(sql_fn=lambda q: [{"status": "OK", "result": []}])


class TestRS5BusDispatchesToTheGate:
    def test_DISCRIMINATING_model_needed_reaches_the_residency_handler(self, consumer):
        """Neutralising the dispatch branch makes this fail — the whole point.
        Before this wiring the event fell through to `{'action': 'tally'}`, i.e. counted
        and discarded."""
        seen: list[dict] = []
        consumer._residency = lambda ev: seen.append(ev) or type("R", (), {"ok": True})()
        out = consumer.handle({"event_type": "model_needed", "model_id": "M"})

        assert seen and seen[0]["model_id"] == "M", "event never reached the gate"
        assert out["action"] == "residency", f"routed elsewhere: {out}"

    def test_DISCRIMINATING_model_idle_also_routes(self, consumer):
        seen: list[dict] = []
        consumer._residency = lambda ev: seen.append(ev) or True
        out = consumer.handle({"event_type": "model_idle", "model_id": "M"})
        assert seen and out["action"] == "residency"

    def test_refusal_is_reported_not_swallowed(self, consumer):
        """A refusal is a NORMAL gate outcome and must surface as ok=False, not vanish."""
        consumer._residency = lambda ev: type("R", (), {"ok": False})()
        out = consumer.handle({"event_type": "model_needed", "model_id": "Huge"})
        assert out["action"] == "residency" and out["ok"] is False

    def test_residency_error_does_not_stall_the_drain(self, consumer):
        """One bad residency event must not stop every other event type being drained."""

        def boom(ev):
            raise RuntimeError("gate exploded")

        consumer._residency = boom
        out = consumer.handle({"event_type": "model_needed", "model_id": "M"})
        assert out["action"] == "residency-error" and "exploded" in out["error"]

    def test_DISCRIMINATING_model_id_is_read_from_PAYLOAD_as_the_real_bus_sends_it(
        self, consumer
    ):
        """`model_id` is NOT a column on data_product_event — SurrealDB silently rejects a
        row carrying it (verified: CREATE returned status OK and stored nothing). Real bus
        events put it inside payload JSON. An implementation reading only the top level
        passes every other test here and is INERT in production."""
        seen: list[dict] = []
        consumer._residency = lambda ev: seen.append(ev) or type("R", (), {"ok": True})()
        consumer.handle(
            {"event_type": "model_needed", "payload": '{"model_id": "FromPayload"}'}
        )
        assert seen and seen[0].get("model_id") == "FromPayload", (
            f"model_id not recovered from payload; handler saw {seen}"
        )

    def test_top_level_model_id_still_wins_for_in_process_callers(self, consumer):
        seen: list[dict] = []
        consumer._residency = lambda ev: seen.append(ev) or True
        consumer.handle(
            {"event_type": "model_needed", "model_id": "TopLevel",
             "payload": '{"model_id": "FromPayload"}'}
        )
        assert seen[0]["model_id"] == "TopLevel"

    def test_malformed_payload_does_not_raise(self, consumer):
        seen: list[dict] = []
        consumer._residency = lambda ev: seen.append(ev) or True
        consumer.handle({"event_type": "model_needed", "payload": "not json {{{"})
        assert seen, "a malformed payload must still reach the gate (which then no-ops)"

    def test_POSITIVE_CONTROL_other_event_types_are_unaffected(self, consumer):
        """Proves the new branch is selective, not a catch-all that hijacks the bus.
        Without this, a dispatch bug that swallowed everything would look like success."""
        called: list[str] = []
        consumer._residency = lambda ev: called.append("residency")
        out = consumer.handle({"event_type": "some_other_thing", "payload": "{}"})
        assert called == [], "the residency branch hijacked an unrelated event"
        assert out["action"] == "tally"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
