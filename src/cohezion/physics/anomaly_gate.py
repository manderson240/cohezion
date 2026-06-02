"""AnomalyGate — domain-pluggable anomaly detection across cohezion's unified physics.

Generalizes ``ConservationFilter`` (which is MHD-specialized) into a domain-agnostic gate that the
whole unified-physics stack shares — MHD, spinor/SU(2), gauge (Yang-Mills), Lagrangian, the TOE /
cosmogony symmetry-breaking layer, and any future framework — by registering each domain's
invariants rather than hardcoding one set.

It is the *deterministic* half of the "perfect blend of deterministic programs and non-deterministic
inference":

  DETERMINISTIC (this gate, pure Python, runs every step):
      decides WHETHER a result is anomalous. Splits each domain's invariants into
      INTEGRITY (a valid computation must hold them — unitarity, ∇·B=0, gauge action ≥ 0, …) and
      PHYSICAL (the candidate-discovery quantities — energy, action, symmetry conservation). The
      verdict rule is universal across domains: an ANOMALY fires only when a PHYSICAL invariant is
      violated WHILE every INTEGRITY invariant holds. Any integrity failure ⇒ REJECT (artifact).

  NON-DETERMINISTIC (the Skeptic, local-inference, runs only on a surviving anomaly):
      argues about WHY. A fleet model is constrained to *falsify* the anomaly with established
      physics; it can REJECT (found a boundary/mesh/assumption flaw) but it can never *accept* —
      survival just means "not dismissable by the standard model", which routes to human review.

That asymmetry is deliberate: cheap deterministic code is the gate; expensive fallible inference
only ever *reduces* false discoveries, never manufactures them. The Skeptic falls back to
"survived — pending human" if the fleet is unreachable (never auto-reject a real anomaly because a
validator was down; never auto-accept either).
"""

from __future__ import annotations

import json
import re
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum

from cohezion.physics.conservation_filter import Verdict


__all__ = [
    "DOMAIN_INVARIANTS",
    "AnomalyGate",
    "AnomalyVerdict",
    "InvariantKind",
    "InvariantSpec",
    "LocalSkeptic",
    "SkepticVerdict",
    "adjudicate",
]

ROUTER = "http://localhost:13305/api/v1/chat/completions"


class InvariantKind(StrEnum):
    INTEGRITY = "integrity"  # a valid computation MUST hold this; violation = artifact ⇒ REJECT
    PHYSICAL = "physical"  # candidate-discovery quantity; violation w/ integrity intact ⇒ ANOMALY


@dataclass(frozen=True)
class InvariantSpec:
    """One invariant for a domain: a named tolerance with a kind. Fails if |deviation| > tolerance."""

    name: str
    kind: InvariantKind
    tolerance: float


# Per-domain invariant registry. Tolerances mirror InvariantChecker defaults where they overlap.
# Extensible: register a new domain (e.g. 'tek') by adding its conserved-quantity specs.
DOMAIN_INVARIANTS: dict[str, list[InvariantSpec]] = {
    "mhd": [
        InvariantSpec("solenoidal_div_b", InvariantKind.INTEGRITY, 1e-6),  # ∇·B = 0
        InvariantSpec("unitarity", InvariantKind.INTEGRITY, 1e-8),  # |ψ|² = 1
        InvariantSpec("energy", InvariantKind.PHYSICAL, 0.05),  # ΔE/E₀
    ],
    "spinor": [
        InvariantSpec("unitarity", InvariantKind.INTEGRITY, 1e-8),  # |α|²+|β|² = 1
        InvariantSpec(
            "coherence_band", InvariantKind.INTEGRITY, 0.0
        ),  # in [0.05,1.0] (pre-checked)
        InvariantSpec("energy", InvariantKind.PHYSICAL, 0.05),
    ],
    "gauge": [
        InvariantSpec("yang_mills_nonneg", InvariantKind.INTEGRITY, 0.0),  # S_YM ≥ 0
        InvariantSpec("energy", InvariantKind.PHYSICAL, 0.05),
    ],
    "lagrangian": [
        InvariantSpec("unitarity", InvariantKind.INTEGRITY, 1e-8),
        InvariantSpec("energy", InvariantKind.PHYSICAL, 0.05),  # E = T+V conservation
        InvariantSpec("action", InvariantKind.PHYSICAL, 0.10),  # stationary-action deviation
    ],
    "toe": [
        # Cosmogony / symmetry-breaking (Campbell My-Big-TOE layer): a broken symmetry is only
        # physics if Noether's conserved current still balances; otherwise it's a numerical artifact.
        InvariantSpec(
            "noether_current", InvariantKind.INTEGRITY, 1e-6
        ),  # conserved-current balance
        InvariantSpec(
            "symmetry_order", InvariantKind.PHYSICAL, 0.05
        ),  # spontaneous order parameter
    ],
}


@dataclass(frozen=True)
class AnomalyVerdict:
    domain: str
    verdict: Verdict
    integrity_failed: list[str] = field(default_factory=list)
    physical_failed: list[str] = field(default_factory=list)
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "domain": self.domain,
            "verdict": self.verdict.value,
            "integrity_failed": list(self.integrity_failed),
            "physical_failed": list(self.physical_failed),
            "reason": self.reason,
        }


class AnomalyGate:
    """Deterministic, domain-pluggable gate. ``evaluate`` classifies measured deviations per domain."""

    def __init__(self, registry: dict[str, list[InvariantSpec]] | None = None) -> None:
        self._registry = registry if registry is not None else DOMAIN_INVARIANTS

    def register(self, domain: str, specs: list[InvariantSpec]) -> None:
        """Add or replace a domain's invariant set (e.g. a new 'tek' framework)."""
        self._registry[domain] = specs

    def evaluate(self, domain: str, measured: dict[str, float]) -> AnomalyVerdict:
        """Classify a step's measured invariant deviations for ``domain``.

        ``measured`` maps invariant name -> |deviation| (e.g. {'energy': 0.6, 'solenoidal_div_b': 1e-9}).
        Unlisted invariants are skipped. Integrity failure dominates a physical violation.
        """
        specs = self._registry.get(domain)
        if specs is None:
            raise KeyError(
                f"unknown physics domain {domain!r}; registered: {sorted(self._registry)}"
            )
        integrity_failed, physical_failed = [], []
        for spec in specs:
            dev = measured.get(spec.name)
            if dev is None:
                continue
            if abs(dev) > spec.tolerance:
                (
                    integrity_failed if spec.kind is InvariantKind.INTEGRITY else physical_failed
                ).append(spec.name)
        if integrity_failed:
            return AnomalyVerdict(
                domain,
                Verdict.REJECT,
                integrity_failed,
                physical_failed,
                f"integrity invariant(s) failed: {', '.join(integrity_failed)} — artifact, route to retry",
            )
        if physical_failed:
            return AnomalyVerdict(
                domain,
                Verdict.ANOMALY,
                [],
                physical_failed,
                f"physical invariant(s) {', '.join(physical_failed)} violated with integrity intact "
                f"— structural candidate, escalate to Skeptic",
            )
        return AnomalyVerdict(domain, Verdict.STANDARD, [], [], "all invariants within tolerance")


# ---- non-deterministic half: the local-inference Skeptic --------------------


@dataclass(frozen=True)
class SkepticVerdict:
    survived: bool  # True = NOT dismissable by standard model -> human review
    refutation: str | None  # the falsification, if the skeptic found one
    model: str
    note: str = ""

    def to_dict(self) -> dict:
        return {
            "survived": self.survived,
            "refutation": self.refutation,
            "model": self.model,
            "note": self.note,
        }


class LocalSkeptic:
    """Fleet-backed adversarial validator. Falsify-only: can REJECT, never accept.

    Falls back to ``survived`` (pending human) on any fleet failure — a real anomaly is never
    auto-rejected because the validator was unreachable.
    """

    def __init__(
        self, model: str = "DeepSeek-Qwen3-8B-GGUF", call: Callable[[str], str] | None = None
    ):
        self.model = model
        self._call = call or self._fleet_call

    def _fleet_call(self, prompt: str) -> str:
        req = urllib.request.Request(  # noqa: S310 — fixed localhost fleet URL
            ROUTER,
            data=json.dumps(
                {
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 400,
                    "temperature": 0,
                }
            ).encode(),
            headers={"Content-Type": "application/json"},
        )
        body = json.loads(urllib.request.urlopen(req, timeout=60).read())  # noqa: S310 local fleet
        return body["choices"][0]["message"]["content"]

    def falsify(self, verdict: AnomalyVerdict, measured: dict[str, float]) -> SkepticVerdict:
        prompt = (
            "You are an adversarial physics validator. Your ONLY objective is to FALSIFY an anomaly "
            "using established physics — find a simulation boundary error, a flawed mesh/grid "
            "resolution, or an invalid assumption. Do NOT confirm it.\n"
            f"Domain: {verdict.domain}\n"
            f"Physical invariant(s) violated (integrity invariants all held): {verdict.physical_failed}\n"
            f"Measured deviations: {measured}\n"
            "If you can dismiss it with standard-model constraints, end with exactly "
            "'REFUTED: <one-sentence reason>'. If you cannot, end with exactly 'SURVIVED'."
        )
        try:
            text = self._call(prompt)
        except Exception as e:  # fleet unreachable -> conservative: survive pending human
            return SkepticVerdict(
                True, None, self.model, note=f"validator unavailable ({e}) — pending human"
            )
        m = re.search(r"REFUTED:\s*(.+)", text)
        if m:
            return SkepticVerdict(
                False, m.group(1).strip()[:300], self.model, note="refuted by standard model"
            )
        return SkepticVerdict(True, None, self.model, note="not dismissable — pending human review")


def adjudicate(
    domain: str,
    measured: dict[str, float],
    *,
    gate: AnomalyGate | None = None,
    skeptic: LocalSkeptic | None = None,
) -> dict:
    """The blend: deterministic gate first; only a surviving ANOMALY reaches the Skeptic.

    Returns ``{verdict, skeptic}``. ``skeptic`` is None unless the deterministic verdict was ANOMALY.
    A REJECT (artifact) or STANDARD run never invokes inference — the cheap path stays cheap.
    """
    av = (gate or AnomalyGate()).evaluate(domain, measured)
    out: dict = {"verdict": av.to_dict()}
    if av.verdict is Verdict.ANOMALY:
        sk = (skeptic or LocalSkeptic()).falsify(av, measured)
        out["skeptic"] = sk.to_dict()
        out["final"] = "human_review" if sk.survived else "rejected_by_skeptic"
    else:
        out["final"] = av.verdict.value
    return out
