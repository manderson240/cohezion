"""Hybrid scoring engine — keyword matching + Ollama LLM scoring."""

import logging
import re
from typing import Any

import requests

from research.pipeline import Finding

logger = logging.getLogger(__name__)

# Keyword sets for each focus area
AREA_KEYWORDS: dict[str, list[str]] = {
    "compound_engineering": [
        "compound", "knowledge graph", "decision record", "session memory",
        "pattern extraction", "multi-session", "knowledge accumulation",
        "adr", "compound ai",
    ],
    "token_efficiency": [
        "token", "context window", "compression", "cache", "distillation",
        "efficiency", "prompt caching", "kv cache", "speculative decoding",
        "batching", "cost optimization",
    ],
    "context_awareness": [
        "context", "memory", "retrieval", "rag", "long context", "semantic",
        "cross-session", "context injection", "memory persistence",
        "augmented generation",
    ],
    "app_creation": [
        "agent", "mcp", "tool use", "framework", "code generation",
        "multi-agent", "function calling", "agentic", "orchestration",
        "model context protocol",
    ],
}

SKILL_KEYWORDS = [
    "framework", "tool", "plugin", "library", "pattern", "template",
    "workflow", "cli", "sdk", "package", "utility", "module", "extension",
]


def keyword_score(findings: list[Finding], config: dict[str, Any]) -> list[Finding]:
    """Score findings using keyword matching against focus area keywords."""
    for finding in findings:
        text = (finding.title + " " + finding.snippet).lower()
        total = 0
        for area_name, keywords in AREA_KEYWORDS.items():
            area_score = sum(1 for kw in keywords if kw in text)
            # Weight by focus area config
            weight = config.get("focus_areas", {}).get(area_name, {}).get("weight", 1.0)
            total += area_score * weight
        finding.raw_score = total
    return findings


async def ollama_score(
    findings: list[Finding],
    config: dict[str, Any],
) -> list[Finding]:
    """Score findings using local Ollama LLM for relevance assessment."""
    scoring_config = config.get("scoring", {})
    model = scoring_config.get("model", "mistral:latest")
    ollama_url = scoring_config.get("ollama_url", "http://localhost:11434")

    for finding in findings:
        prompt = (
            f"Rate the relevance (1-10) of this finding to building AI agent systems "
            f"with knowledge persistence, token efficiency, context management, and tool creation.\n\n"
            f"Title: {finding.title}\n"
            f"Snippet: {finding.snippet[:200]}\n\n"
            f"Reply with ONLY a number 1-10."
        )

        try:
            resp = requests.post(
                f"{ollama_url}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
                timeout=30,
            )
            resp.raise_for_status()
            response_text = resp.json().get("response", "0").strip()
            # Extract first number from response
            match = re.search(r"\d+", response_text)
            llm_score = int(match.group()) if match else 0
            llm_score = max(0, min(10, llm_score))
            # Blend keyword score with LLM score (LLM weighted higher)
            finding.raw_score = finding.raw_score * 0.3 + llm_score * 0.7
        except (ConnectionError, requests.RequestException) as e:
            logger.warning("Ollama scoring failed for '%s': %s", finding.title[:50], e)
            # Keep existing keyword score as-is

    return findings


def detect_skill_candidates(findings: list[Finding]) -> list[dict[str, Any]]:
    """Flag findings that describe reusable tools, patterns, or techniques."""
    results = []
    for finding in findings:
        text = (finding.title + " " + finding.snippet).lower()
        is_candidate = any(kw in text for kw in SKILL_KEYWORDS)

        # Determine skill type
        skill_type = None
        if is_candidate:
            if any(kw in text for kw in ["tool", "cli", "utility", "sdk"]):
                skill_type = "tool"
            elif any(kw in text for kw in ["pattern", "template"]):
                skill_type = "pattern"
            elif any(kw in text for kw in ["framework", "library", "package"]):
                skill_type = "framework"
            else:
                skill_type = "technique"

        results.append({
            "finding": finding,
            "skill_candidate": is_candidate,
            "skill_type": skill_type,
        })
    return results


async def score(
    findings: list[Finding],
    config: dict[str, Any],
) -> tuple[list[Finding], dict[str, Any]]:
    """Run full scoring pipeline: keyword → Ollama → skill detection → top-N."""
    scoring_config = config.get("scoring", {})
    top_n = scoring_config.get("top_n", 60)

    # Tier 1: Keyword scoring
    scored = keyword_score(findings, config)
    keyword_count = sum(1 for f in scored if f.raw_score > 0)

    # Tier 2: Ollama LLM scoring (only for keyword-positive findings)
    candidates = [f for f in scored if f.raw_score > 0]
    if candidates:
        candidates = await ollama_score(candidates, config)

    # Merge back: keep all scored findings
    all_scored = candidates + [f for f in scored if f.raw_score == 0]

    # Sort by score descending, take top-N
    all_scored.sort(key=lambda f: f.raw_score, reverse=True)
    top_findings = all_scored[:top_n]

    # Skill candidate detection
    skill_results = detect_skill_candidates(top_findings)
    skill_count = sum(1 for r in skill_results if r["skill_candidate"])

    metadata = {
        "total_findings": len(findings),
        "keyword_positive": keyword_count,
        "top_n_selected": len(top_findings),
        "skill_candidates": skill_count,
    }

    logger.info(
        "Scoring complete: %d → %d keyword-positive → %d top-N, %d skill candidates",
        len(findings), keyword_count, len(top_findings), skill_count,
    )

    return top_findings, metadata
