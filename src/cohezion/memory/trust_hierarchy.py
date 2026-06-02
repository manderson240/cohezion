"""Trust-scored ground-truth hierarchy — Memory OS Layers 3 + 7, on cohezion's stack.

Memory OS (github.com/ClaudioDrews/memory-os) is a 7-layer memory system for the Hermes agent.
Cohezion already covers most of it (mem0 + SurrealDB vector + provenance graph). The one piece
it lacks — and the most compositional one — is the pairing of:

  * Layer 3: **structured facts with trust scoring + entity resolution**
  * Layer 7: **ground-truth hierarchy** — injected memory is treated as *authoritative* and
    conflicts resolve by authority tier before the agent re-derives anything.

This module adds exactly that, as a dependency-light layer over plain fact data (no Qdrant/Redis,
no new infra) so it composes everywhere:

  * with mem0: wrap extracted fact dicts as TrustedFacts.
  * with the active-inference Observer: a high-surprise observation that contradicts a high-trust
    fact is a decision point — explore (fact stale) or discount the observation. Trust is the
    counterpart to surprise.
  * with the QuadratureNexus: voice consensus is a corroboration source (agreement reinforces a
    fact's trust; dissent records a contradiction).

Trust is a **Beta-Bernoulli posterior mean**, not a linear tally — corroborations and
contradictions update a Beta(α, β) and trust = (α+c)/(α+β+c+x). This is a proper, bounded,
calibration-respecting score (per the metacognitive-calibration rule: never linear scoring),
so a fact corroborated 1/1 is not as trusted as one corroborated 50/50.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


__all__ = ["GroundTruthHierarchy", "TrustTier", "TrustedFact"]


class TrustTier(IntEnum):
    """Authority tiers (Layer 7). Higher tier wins conflicts before trust is consulted."""

    GROUND_TRUTH = 4  # SOUL/rulebook/constitution — authoritative, never overridden by recall
    STRUCTURED_FACT = 3  # verified extracted facts
    SESSION = 2  # this-session statements
    VECTOR_RECALL = 1  # semantic recall (lossy)
    UNVERIFIED = 0  # provisional / model-asserted


def _norm(text: str) -> str:
    """Cheap entity-resolution key: case/space-insensitive content identity."""
    return " ".join(text.lower().split())


@dataclass
class TrustedFact:
    """A fact with an authority tier and a Beta-Bernoulli trust posterior."""

    content: str
    tier: TrustTier = TrustTier.UNVERIFIED
    entity: str | None = None
    corroborations: int = 0  # Bernoulli successes
    contradictions: int = 0  # Bernoulli failures
    alpha: float = 1.0  # Beta prior (Laplace)
    beta: float = 1.0

    @property
    def trust(self) -> float:
        """Posterior mean of Beta(alpha+corroborations, beta+contradictions) in (0, 1)."""
        a = self.alpha + self.corroborations
        b = self.beta + self.contradictions
        return a / (a + b)

    def reinforce(self, agree: bool) -> None:
        """Record one corroboration (agree) or contradiction (disagree)."""
        if agree:
            self.corroborations += 1
        else:
            self.contradictions += 1

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "tier": int(self.tier),
            "entity": self.entity,
            "trust": round(self.trust, 4),
            "corroborations": self.corroborations,
            "contradictions": self.contradictions,
        }


@dataclass
class GroundTruthHierarchy:
    """Trust-scored fact store with tiered authority + conflict resolution + context injection.

    Facts are keyed by normalized content for entity resolution (re-adding a fact corroborates
    it rather than duplicating). Authority is (tier, trust): ground-truth tier outranks any amount
    of recall trust — the Layer-7 guarantee that injected authoritative context is not re-litigated.
    """

    _facts: dict[str, TrustedFact] = field(default_factory=dict)

    def add(
        self,
        content: str,
        tier: TrustTier = TrustTier.UNVERIFIED,
        *,
        entity: str | None = None,
    ) -> TrustedFact:
        """Add or corroborate a fact (entity resolution by normalized content).

        Re-adding existing content corroborates it and upgrades its tier if the new claim is more
        authoritative — so a session statement later confirmed as ground-truth is promoted.
        """
        key = _norm(content)
        fact = self._facts.get(key)
        if fact is None:
            fact = TrustedFact(content=content, tier=tier, entity=entity)
            self._facts[key] = fact
        else:
            fact.reinforce(True)  # seeing it again is corroboration
            if tier > fact.tier:
                fact.tier = tier
            if entity and not fact.entity:
                fact.entity = entity
        return fact

    def corroborate(self, content: str, agree: bool) -> TrustedFact | None:
        """Reinforce an existing fact with external evidence (e.g. Nexus consensus). None if absent."""
        fact = self._facts.get(_norm(content))
        if fact is not None:
            fact.reinforce(agree)
        return fact

    def rank(self, facts: list[TrustedFact] | None = None) -> list[TrustedFact]:
        """Order by authority: tier descending, then trust descending."""
        items = facts if facts is not None else list(self._facts.values())
        return sorted(items, key=lambda f: (int(f.tier), f.trust), reverse=True)

    def resolve(self, candidates: list[TrustedFact]) -> TrustedFact | None:
        """Pick the authoritative fact among (possibly conflicting) candidates: highest (tier, trust)."""
        if not candidates:
            return None
        return self.rank(candidates)[0]

    def authoritative_for(self, entity: str) -> TrustedFact | None:
        """The single most-authoritative fact about an entity (Layer-7 resolution)."""
        matches = [f for f in self._facts.values() if f.entity == entity]
        return self.resolve(matches)

    def inject_context(self, max_facts: int = 10, min_trust: float = 0.0) -> str:
        """Render an authoritative memory block (Layer 7), highest authority first.

        The header instructs the consumer to treat these as authoritative — the directive that
        stops the agent re-querying what it already reliably knows.
        """
        chosen = [f for f in self.rank() if f.trust >= min_trust][:max_facts]
        if not chosen:
            return ""
        lines = [
            "## Authoritative memory (treat as ground truth; do not re-derive)",
        ]
        for f in chosen:
            lines.append(f"- [{f.tier.name} trust={f.trust:.2f}] {f.content}")
        return "\n".join(lines)

    def ingest_mem0(self, facts: list[dict], tier: TrustTier = TrustTier.STRUCTURED_FACT) -> int:
        """Wrap mem0-style fact dicts ({'memory'|'content'|'text': str, 'entity'?}) as TrustedFacts."""
        n = 0
        for d in facts:
            content = d.get("memory") or d.get("content") or d.get("text")
            if not content:
                continue
            self.add(str(content), tier, entity=d.get("entity"))
            n += 1
        return n

    def __len__(self) -> int:
        return len(self._facts)
