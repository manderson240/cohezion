"""CapabilityProfile + CardParser.

A CapabilityProfile is the structured, machine-readable shape of a model
card. We never build one without having read the card; the parser enforces
this. The downstream code (recipe_guard, route_by_capability, the four
lanes) treats the profile as the source of truth for what a model is good
at and how to call it.

CardParseError is raised when the input is missing the fields the plan
requires (Strengths + Limitations sections for HF cards). We do not
silently fall back to a partial profile.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime


class CardParseError(ValueError):
    """Raised when a model card cannot be parsed into a CapabilityProfile."""


@dataclass(frozen=True)
class CapabilityProfile:
    """Structured model card. See plan: a single source of truth for a
    model's strengths, weaknesses, optimal ctx, sampling sweet spot,
    prompt template fingerprint, and known failure modes.

    Frozen so a profile cannot be mutated after construction; new cards
    produce a new profile, and the newer read_at wins.
    """

    model_id: str
    family: str
    supported_modes: frozenset[str]
    optimal_ctx: int
    min_ctx: int
    strengths: frozenset[str]
    weaknesses: frozenset[str]
    sampling_sweet_spot: dict[str, float]
    prompt_template_fingerprint: str
    thinking_mode: str  # "always" | "optional_prefix" | "never"
    known_failure_modes: tuple[str, ...] = field(default_factory=tuple)
    source_url: str = ""
    read_at: datetime = field(default_factory=lambda: datetime.utcnow())


# ── HuggingFace card parser ──────────────────────────────────────────────────


# Recognized "section heading" patterns (case-insensitive)
_HEADINGS = {
    "strengths": ("strengths", "intended uses", "intended use"),
    "limitations": ("limitations", "weaknesses", "constraints"),
    "how_to_use": ("how to use", "usage", "inference"),
}


def _split_sections(md: str) -> dict[str, list[str]]:
    """Split a markdown card into {section_name: [bullet lines]}."""
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in md.splitlines():
        m = re.match(r"^##\s+(.*)$", line.strip())
        if m:
            heading = m.group(1).strip().lower()
            # Classify
            for key, aliases in _HEADINGS.items():
                if any(heading.startswith(a) for a in aliases):
                    current = key
                    sections.setdefault(current, [])
                    break
            else:
                current = None
            continue
        if current is None:
            continue
        sections[current].append(line)
    return sections


_BULLET_RE = re.compile(r"^[\s>*\-+]+\s*(.+)$")


def _bullets(lines: list[str]) -> list[str]:
    out = []
    for line in lines:
        m = _BULLET_RE.match(line.strip())
        if m:
            out.append(m.group(1).strip().rstrip(".").lower())
    return out


def _parse_temperature(line: str) -> float | None:
    m = re.search(r"temperature\s*[=:]\s*([0-9]+(?:\.[0-9]+)?)", line, re.IGNORECASE)
    return float(m.group(1)) if m else None


def _parse_top_p(line: str) -> float | None:
    m = re.search(r"top[-_ ]?p\s*[=:]\s*([0-9]+(?:\.[0-9]+)?)", line, re.IGNORECASE)
    return float(m.group(1)) if m else None


def _detect_thinking_mode(how_to_use: list[str]) -> str:
    text = "\n".join(how_to_use).lower()
    if "/no_think" in text or "no_think prefix" in text:
        return "optional_prefix"
    if "reasoning" in text or "thinking" in text or "<think>" in text:
        return "always"
    return "never"


def _detect_prompt_template(model_id: str, how_to_use: list[str]) -> str:
    text = "\n".join(how_to_use + [model_id]).lower()
    if "chatml" in text or "qwen" in text or "deepseek-qwen" in text:
        return "chatml"
    if "llama3" in text or "llama-3" in text:
        return "llama3"
    if "granite" in text:
        return "granite"
    if "gemma" in text:
        return "gemma"
    return "unknown"


class CardParser:
    """Parses raw model card sources into CapabilityProfile objects.

    Two entry points:
    - parse_huggingface: a full README/model_card.md
    - parse_arxiv_abstract: a lightweight arXiv abstract with optional
      "Strengths:" / "Weaknesses:" lines

    Both raise CardParseError on missing required fields — the plan
    explicitly rejects building a profile from a card we haven't fully
    read.
    """

    # ── HuggingFace ──────────────────────────────────────────────────────

    @staticmethod
    def parse_huggingface(
        card_md: str,
        model_id: str,
        source_url: str = "",
        read_at: datetime | None = None,
    ) -> CapabilityProfile:
        sections = _split_sections(card_md)

        if "strengths" not in sections or not _bullets(sections["strengths"]):
            raise CardParseError(
                f"Card for {model_id} has no Strengths/Intended Uses section "
                f"with bullet points. Refusing to build a profile from a "
                f"card we haven't read."
            )
        if "limitations" not in sections or not _bullets(sections["limitations"]):
            raise CardParseError(
                f"Card for {model_id} has no Limitations/Weaknesses section. "
                f"Refusing to build a profile from a card we haven't read."
            )

        how_to_use = sections.get("how_to_use", [])

        # Sampling sweet spot: scan the "How to Use" section for
        # temperature / top_p. Empty dict is fine — many cards don't
        # publish a sweet spot.
        sweet: dict[str, float] = {}
        for line in how_to_use:
            t = _parse_temperature(line)
            if t is not None:
                sweet["temperature"] = t
            p = _parse_top_p(line)
            if p is not None:
                sweet["top_p"] = p

        # Family: derive from the model_id prefix. HF models are
        # "org/Model-Name"; family is the leading org or the model stem.
        family = model_id.split("/")[-1].split("-")[0].lower() if "/" in model_id else model_id.lower()

        # Supported modes: chat is the default; tool_use is set if the
        # card mentions "tool" or "function calling".
        text = card_md.lower()
        modes = {"chat"}
        if "tool" in text or "function calling" in text:
            modes.add("tool_use")
        if "fill-in-the-middle" in text or "fim" in text or "<fim-prefix>" in text:
            modes.add("fim")
        if "embedding" in text or "embed " in text:
            modes.add("embedding")
        if "vision" in text or "image" in text or "multimodal" in text:
            modes.add("vision")

        # Known failure modes: capture the Limitations bullets as a tuple
        # of strings (these are the things the card says it does badly).
        known_failures = tuple(_bullets(sections["limitations"]))

        return CapabilityProfile(
            model_id=model_id,
            family=family,
            supported_modes=frozenset(modes),
            optimal_ctx=32768,  # conservative default; refine when the
                                # card says otherwise. We don't read ctx
                                # from the card here — the runtime will
                                # check ResourceGuard.can_load_model with
                                # the recipe's own ctx_size.
            min_ctx=512,
            strengths=frozenset(_bullets(sections["strengths"])),
            weaknesses=frozenset(_bullets(sections["limitations"])),
            sampling_sweet_spot=sweet,
            prompt_template_fingerprint=_detect_prompt_template(model_id, how_to_use),
            thinking_mode=_detect_thinking_mode(how_to_use),
            known_failure_modes=known_failures,
            source_url=source_url or f"https://huggingface.co/{model_id}",
            read_at=read_at or datetime.utcnow(),
        )

    # ── arXiv abstract (lighter) ────────────────────────────────────────

    @staticmethod
    def parse_arxiv_abstract(
        abstract: str,
        model_id: str,
        source_url: str = "",
        read_at: datetime | None = None,
    ) -> CapabilityProfile:
        text = abstract.lower()
        # arXiv abstracts rarely have structured "Strengths:" fields.
        # We look for explicit "Strengths:" and "Weaknesses:" prefixes
        # in the abstract; if absent, raise — we don't guess.
        strengths_match = re.search(r"strengths?\s*:\s*([^\n.]+)", text)
        weaknesses_match = re.search(r"weaknesses?\s*:\s*([^\n.]+)", text)
        if not strengths_match or not weaknesses_match:
            raise CardParseError(
                f"arXiv abstract for {model_id} lacks explicit Strengths:/"
                f"Weaknesses: lines. Refusing to fabricate a profile from "
                f"an abstract that doesn't claim its own strengths."
            )

        strengths = frozenset(
            s.strip() for s in re.split(r"[,;]", strengths_match.group(1)) if s.strip()
        )
        weaknesses = frozenset(
            s.strip() for s in re.split(r"[,;]", weaknesses_match.group(1)) if s.strip()
        )

        return CapabilityProfile(
            model_id=model_id,
            family=model_id.split(":")[-1].lower(),
            supported_modes=frozenset({"chat"}),
            optimal_ctx=8192,
            min_ctx=512,
            strengths=strengths,
            weaknesses=weaknesses,
            sampling_sweet_spot={},  # arXiv abstracts don't publish this
            prompt_template_fingerprint="unknown",
            thinking_mode="never",
            known_failure_modes=tuple(weaknesses),
            source_url=source_url or f"https://arxiv.org/abs/{model_id.split(':')[-1]}",
            read_at=read_at or datetime.utcnow(),
        )
