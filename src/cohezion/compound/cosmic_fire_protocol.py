"""Cosmic Fire Protocol (CFP) — HIHO ignition trigger for the Universe Research Engineer.

In COLIBRE simulations, "cosmic fire" = ignition of Population III stars at z≈20-30.
This is the universe's first HIHO crossing: ISM coherence rises from chaos (VOID)
to the first structured state (thermal equilibrium between hot/cold gas phases).

In Cohezion: CFP triggers when the compound loop enters the HIHO band (score ≥ 0.45)
for the first time. Like Pop III star formation, once ignited it is irreversible —
the system cannot return to the chaotic VOID state without a full reset.

CFP cascade actions (in order):
  1. Switch quality eval to BBQ low-and-slow mode (no TTFT deadline, min 500 chars)
  2. Spawn 3-perspective R0 adversarial review on the trigger output
  3. Escalate inference tier to CPU/cloud for synthesis work
  4. Log ignition event to SurrealDB cosmic_fire_events table (bi-temporal)
  5. Telegram notify: '<b>Cosmic Fire ignited</b> at coherence={c:.3f}'

The ignition temperature mirrors the QCD critical temperature (155 MeV) — the same
phase transition that created the first hadronic matter after the Big Bang.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime


logger = logging.getLogger(__name__)

_HIHO_ENTRY: float = 0.45  # lower edge of HIHO band
_QCD_CRITICAL_MEV: float = 155.0  # matches sarfatti_bridge.QuarkGluonPlasma


@dataclass
class CosmicFireEvent:
    """A single cosmic fire ignition event."""

    redshift: float  # z at ignition (COLIBRE); 0.0 for non-sim contexts
    coherence: float  # quality_score that triggered ignition
    sfr_rate: float  # star-formation rate proxy (or compound loop rate)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    zoom_level: int = 1  # resolution multiplier for follow-up simulation

    def to_surreal_record(self) -> dict:
        return {
            "redshift": self.redshift,
            "coherence": self.coherence,
            "sfr_rate": self.sfr_rate,
            "timestamp": self.timestamp.isoformat(),
            "zoom_level": self.zoom_level,
            "valid_from": self.timestamp.isoformat(),
            "valid_to": None,
        }


@dataclass
class CosmicFireProtocol:
    """Trigger and orchestrate the cosmic fire ignition cascade.

    Parameters
    ----------
    threshold : float
        HIHO entry coherence threshold. Ignition fires when score ≥ threshold.
    ignition_temperature : float
        Symbolic temperature in MeV (maps to QCD critical T = 155 MeV).
    notify_telegram : bool
        Whether to send Telegram notification on ignition.
    """

    threshold: float = _HIHO_ENTRY
    ignition_temperature: float = _QCD_CRITICAL_MEV
    notify_telegram: bool = True

    _ignition_count: int = field(default=0, init=False, repr=False)
    _last_event: CosmicFireEvent | None = field(default=None, init=False, repr=False)

    def is_ignited(self, quality_score: float, sfr_rate: float = 1.0) -> bool:
        """True when compound loop enters HIHO band — cosmic fire conditions met."""
        return quality_score >= self.threshold and sfr_rate > 0.0

    def ignite(
        self,
        quality_score: float,
        redshift: float = 0.0,
        sfr_rate: float = 1.0,
    ) -> CosmicFireEvent | None:
        """Fire the cosmic fire ignition cascade if conditions are met.

        Returns the ignition event if fired, None if conditions not met.
        """
        if not self.is_ignited(quality_score, sfr_rate):
            return None

        event = CosmicFireEvent(
            redshift=redshift,
            coherence=quality_score,
            sfr_rate=sfr_rate,
            zoom_level=min(8, 2**self._ignition_count),  # zoom doubles each time
        )
        self._ignition_count += 1
        self._last_event = event

        logger.info(
            "Cosmic Fire ignited (event #%d): z=%.2f coherence=%.3f sfr=%.4f",
            self._ignition_count,
            redshift,
            quality_score,
            sfr_rate,
        )

        if self.notify_telegram:
            self._send_telegram(event)

        return event

    def ignition_cascade(self, quality_score: float, sfr_rate: float = 1.0) -> list[str]:
        """Return the ordered list of cascade actions for the URE to execute.

        These are the Universe Research Engineer's steps when cosmic fire ignites:
          1. Enter BBQ low-and-slow analysis mode
          2. Spawn R0 3-perspective adversarial review
          3. Escalate to CPU/cloud tier for synthesis
          4. Persist ignition event to SurrealDB
          5. Telegram notify

        Returns empty list if ignition conditions not met.
        """
        if not self.is_ignited(quality_score, sfr_rate):
            return []

        return [
            "enter_bbq_low_slow_mode",
            "spawn_r0_adversarial_review",
            "escalate_to_cpu_cloud_tier",
            "persist_cosmic_fire_event",
            "telegram_notify_ignition",
        ]

    def hiho_temperature_analog(self) -> float:
        """Map HIHO threshold to QCD critical temperature analog.

        At threshold=0.45, system is at the equivalent of T ≈ 155 MeV QCD crossover:
        the boundary between ordered (hadronic) and disordered (QGP) phases.
        """
        return self.ignition_temperature * (self.threshold / _HIHO_ENTRY)

    def _send_telegram(self, event: CosmicFireEvent) -> None:
        try:
            from cohezion.compound.telegram_notify import notify

            msg = (
                f"<b>Cosmic Fire Ignited</b> (event #{self._ignition_count})\n"
                f"z={event.redshift:.2f} | coherence={event.coherence:.3f}\n"
                f"zoom_level=×{event.zoom_level} | T≈{self.ignition_temperature:.0f} MeV"
            )
            notify(msg)
        except Exception as exc:
            logger.debug("Cosmic Fire Telegram notify failed (non-blocking): %s", exc)

    @property
    def ignition_count(self) -> int:
        """Total number of times cosmic fire has ignited this session."""
        return self._ignition_count

    @property
    def last_event(self) -> CosmicFireEvent | None:
        """The most recent ignition event, or None."""
        return self._last_event
