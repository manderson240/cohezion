"""Status handler — AMD silicon health via Slack Block Kit."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.cohezion_bridge import CohezionBridge

_bridge = CohezionBridge()

# Router-centric: all served by the single :13305 router (dispatches by model).
_TIER_MODELS = {
    "npu": ("13305", "llama3.2-1b-FLM", "42 TPS"),
    "igpu": ("13305", "Gemma-4-E4B-it-GGUF", "~200ms"),
    "cpu": ("13305", "Gemma-4-31B-it-GGUF", "~800ms"),
}


def handle_status() -> dict:
    """Return AMD silicon status for display in Slack.

    Returns:
        {
            "text": str,          # plain text fallback
            "blocks": list,       # Slack Block Kit blocks
            "tiers": dict,        # {"npu": bool, "igpu": bool, "cpu": bool}
            "cache_stats": dict,
        }
    """
    status = _bridge.get_status()
    cache_stats = _bridge.get_cache_stats()

    tiers = {
        "npu": status.get("lemonade_npu", False),
        "igpu": status.get("lemonade_igpu", False),
        "cpu": status.get("lemonade_cpu", False),
    }

    hit_rate = cache_stats.get("combined_hit_rate", cache_stats.get("hit_rate", 0))
    if isinstance(hit_rate, float) and hit_rate > 0:
        cache_line = f"{hit_rate:.0%} hit rate"
    else:
        cache_line = "warming up" if status.get("cohezion_package") else "unavailable"

    # ── Plain text ────────────────────────────────────────────────────
    lines = ["*Cohezion AMD Silicon Status*", ""]
    for tier, (port, model, speed) in _TIER_MODELS.items():
        icon = ":white_check_mark:" if tiers[tier] else ":x:"
        lines.append(f"{icon} *{tier.upper()}* (:{port}) `{model}` — {speed}")
    lines.append("")
    lines.append(f":brain: SemanticCache (FLUME VAE 256D): {cache_line}")
    lines.append(f":package: Cohezion package: {'available' if status.get('cohezion_package') else 'not installed'}")
    lines.append("")

    online_count = sum(1 for v in tiers.values() if v)
    if online_count == 3:
        lines.append(":rocket: All tiers online — $0.00/query")
    elif online_count > 0:
        lines.append(f":warning: {online_count}/3 tiers online — partial local inference")
    else:
        lines.append(":cloud: Falling back to Anthropic API (cloud costs apply)")

    text = "\n".join(lines)

    # ── Slack Block Kit ───────────────────────────────────────────────
    tier_fields = []
    for tier, (port, model, speed) in _TIER_MODELS.items():
        icon = "✅" if tiers[tier] else "❌"
        tier_fields.append({"type": "mrkdwn", "text": f"{icon} *{tier.upper()}* `:{port}`\n`{model}` · {speed}"})

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "🔵 Cohezion AMD Silicon Status"},
        },
        {
            "type": "section",
            "fields": tier_fields,
        },
        {"type": "divider"},
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*SemanticCache (FLUME VAE 256D)*\n{cache_line}"},
                {"type": "mrkdwn", "text": f"*Cohezion Package*\n{'✅ available' if status.get('cohezion_package') else '⚠️ not installed'}"},
            ],
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": (
                        "🚀 *All tiers online — $0.00/query*"
                        if online_count == 3
                        else f"⚠️ {online_count}/3 tiers online"
                        if online_count > 0
                        else "☁️ Cloud fallback active"
                    ),
                }
            ],
        },
    ]

    return {
        "text": text,
        "blocks": blocks,
        "tiers": tiers,
        "cache_stats": cache_stats,
    }
