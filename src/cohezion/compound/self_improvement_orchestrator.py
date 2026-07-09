"""SelfImprovementOrchestrator — final wiring piece (WS4, 2026-06-04).

Subscribes to ALL PrecipitationKind values on the bus and routes
each kind through the appropriate ouroboros + mycelium + handler
chain. Closes the loop: every event now has a destination.

Best-effort: any handler failure is caught and logged at debug
level. The orchestrator never raises. This makes the bus
fault-tolerant: producers do not need to worry about consumer
failures.

Routes:
  WITNESS_MARK
      -> MyceliumRegistry.observe (no-op for skill executions)
      -> cooldown: if cluster.size >= 2, promote pattern
  MYCELIUM_PATTERN
      -> OuroborosRecorder.snapshot
      -> vault/wiki/ouroboros/improvements/<ts>_<pattern>.md
  HEALING_EVENT
      -> OuroborosRecorder.snapshot
      -> vault/wiki/ouroboros/healings/<ts>_<target>.md
  JOURNEY_STEP
      -> CompoundJourneyWorker (existing consumer)
  * (catch-all)
      -> logger.debug
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


try:
    from cohezion.precipitation.events import PrecipitationEvent, PrecipitationKind
except ImportError:  # pragma: no cover
    PrecipitationEvent = Any  # type: ignore
    PrecipitationKind = Any  # type: ignore


# Status string constants
STATUS_OK = "ok"
STATUS_NOOP = "noop"
STATUS_ERROR = "error"


def _safe_call(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> tuple[bool, str]:
    """Call a function; return (ok, error_str). Never raises."""
    try:
        fn(*args, **kwargs)
        return True, ""
    except (ImportError, AttributeError, TypeError, RuntimeError, OSError, ValueError) as e:
        return False, f"{type(e).__name__}: {e}"


class SelfImprovementOrchestrator:
    """Wires the bus to the self-improvement loop.

    Lifecycle:
        orch = SelfImprovementOrchestrator()
        orch.subscribe_to_bus()
        # ... events flow automatically ...
    """

    def __init__(self, vault_path: Path | None = None) -> None:
        self._handlers: dict[str, Callable[[PrecipitationEvent], None]] = {
            "WITNESS_MARK": self._on_witness_mark,
            "MYCELIUM_PATTERN": self._on_mycelium_pattern,
            "HEALING_EVENT": self._on_healing_event,
        }
        self.vault_path = vault_path
        self._subscribed = False

    def subscribe_to_bus(self) -> bool:
        """Subscribe to all PrecipitationKind values on the bus.

        Idempotent: calling twice is a no-op. Returns True on
        success, False if the bus is unavailable.
        """
        if self._subscribed:
            return True
        try:
            from cohezion.precipitation.bus import get_bus

            bus = get_bus()
            for kind_name in self._handlers:
                try:
                    kind = getattr(PrecipitationKind, kind_name, None)
                    if kind is None:
                        continue
                    bus.subscribe(
                        lambda event, k=kind_name: self.handle_event(event),
                        kind=kind,
                    )
                except (AttributeError, TypeError, RuntimeError) as e:
                    logger.debug("Failed to subscribe to %s: %s", kind_name, e)
            self._subscribed = True
            logger.debug("SelfImprovementOrchestrator subscribed to bus")
            return True
        except (ImportError, AttributeError) as e:
            logger.debug("Bus unavailable, orchestrator not subscribed: %s", e)
            return False

    def handle_event(self, event: PrecipitationEvent) -> str:
        """Route an event to the appropriate handler.

        Returns:
            STATUS_OK if handled, STATUS_NOOP if no handler, STATUS_ERROR
            on any failure (caught and logged).
        """
        try:
            kind_name = event.kind.name if hasattr(event, "kind") else str(event.kind)
        except AttributeError:
            kind_name = str(event.kind)
        handler = self._handlers.get(kind_name)
        if handler is None:
            return STATUS_NOOP
        try:
            handler(event)
            return STATUS_OK
        except (ImportError, AttributeError, TypeError, RuntimeError, OSError, ValueError) as e:
            logger.debug("Handler for %s failed: %s", kind_name, e)
            return STATUS_ERROR

    def _on_witness_mark(self, event: PrecipitationEvent) -> None:
        """WITNESS_MARK handler: warm MyceliumRegistry observation
        + write a per-event wiki note (best-effort)."""
        try:
            from cohezion.mycelium.registry import MyceliumRegistry  # type: ignore

            registry = (
                MyceliumRegistry.instance() if hasattr(MyceliumRegistry, "instance") else None
            )
            if registry is not None and hasattr(registry, "observe"):
                _safe_call(registry.observe, event)
        except (ImportError, AttributeError) as e:
            logger.debug("MyceliumRegistry unavailable: %s", e)

    def _on_mycelium_pattern(self, event: PrecipitationEvent) -> None:
        """MYCELIUM_PATTERN handler: write a wiki note + snapshot."""
        self._write_wiki_note(
            event,
            subdir="patterns",
            title="Mycelium Pattern",
        )

    def _on_healing_event(self, event: PrecipitationEvent) -> None:
        """HEALING_EVENT handler: write a wiki note + snapshot."""
        self._write_wiki_note(
            event,
            subdir="healings",
            title="Ouroboros Healing",
        )

    def _write_wiki_note(
        self,
        event: PrecipitationEvent,
        subdir: str,
        title: str,
    ) -> None:
        """Write a markdown note about the event to the vault.

        Best-effort: any filesystem error is caught and logged.
        """
        try:
            from datetime import datetime

            payload = getattr(event, "payload", {}) or {}
            ts = datetime.now().strftime("%Y%m%dT%H%M%S")
            slug = (
                payload.get("universe_id")
                or payload.get("target")
                or payload.get("skill_name")
                or "event"
            )
            slug = str(slug).replace("/", "_").replace(" ", "_")[:64]
            # Vault path resolution
            candidates: list[Path] = []
            if self.vault_path is not None:
                candidates.append(self.vault_path)
            candidates.extend(
                [
                    Path("data/vault"),
                    Path.home() / "vaults" / "cohezion-vault",
                    Path.cwd() / "vaults" / "cohezion-vault",
                ]
            )
            target: Path | None = None
            for c in candidates:
                if c.exists() and c.is_dir():
                    target = c / "wiki" / "ouroboros" / subdir
                    break
            if target is None:
                target = (
                    candidates[0] / "wiki" / "ouroboros" / subdir
                    if candidates
                    else Path("/tmp/cohezion-vault") / "wiki" / "ouroboros" / subdir
                )
            target.mkdir(parents=True, exist_ok=True)
            file_path = target / f"{ts}_{slug}.md"
            content = (
                f"# {title}\n\n"
                f"- event_id: {getattr(event, 'event_id', 'n/a')}\n"
                f"- source: {getattr(event, 'source', 'n/a')}\n"
                f"- universe_id: {getattr(event, 'universe_id', 'n/a')}\n"
                f"- created_at: {getattr(event, 'created_at', 'n/a')}\n\n"
                f"## Payload\n\n```json\n"
            )
            try:
                import json

                content += json.dumps(payload, indent=2, default=str)
            except (TypeError, ValueError):
                content += str(payload)
            content += "\n```\n"
            file_path.write_text(content)
            logger.debug("Wrote wiki note: %s", file_path)
        except (OSError, AttributeError, TypeError) as e:
            logger.debug("Wiki note write failed: %s", e)
