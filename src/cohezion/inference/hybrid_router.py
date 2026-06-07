"""Hybrid local-first / cloud-supplement routing decision (backlog item 137, 2026-06-07).

User directive: "leverage hybrid local-first inference supplemented with cloud." Hybrid already
exists (`fleet.extend_claude` local→cloud on a quality gate; CostAwareRouter Lemonade-first; the
triune NPU→iGPU→CPU→cloud chain). This composes that decision with the TWO safeguards built this
session so the cloud supplement is capacity- AND quota-aware:

  - **capacity** — `resource_aware_route` (items 122/131): can the LOCAL fleet serve right now,
    or is it OOM/saturated? (``"route"`` | ``"defer"``)
  - **quota** — `usage_guard` (item 134): is there Claude-Code plan headroom? (``"proceed"`` |
    ``"throttle"`` | ``"halt"``)
  - **quality** — the extend_claude gate: is the local output good enough? (``local_quality`` vs
    ``quality_threshold``)

Rule (local-first; never run out of Claude — doctrine bullet 5):
  - local can serve AND quality OK            → **local**
  - local insufficient AND quota == proceed   → **cloud** (supplement)
  - local insufficient AND quota != proceed   → **local** if it can serve at all, else **defer**

So cloud is used ONLY when local genuinely can't deliver AND there is Claude headroom; when the
quota is throttled/halted we stay local even at lower quality rather than exhaust it. Pure:
depends only on the injected signals.
"""

from __future__ import annotations

from typing import Literal


def hybrid_route_decision(
    *,
    local_capacity: Literal["route", "defer"],
    claude_quota: Literal["proceed", "throttle", "halt"],
    local_quality: float,
    quality_threshold: float,
) -> Literal["local", "cloud", "defer"]:
    """Decide local vs cloud-supplement vs defer. Pure; see module docstring for the rule."""
    local_can_serve = local_capacity == "route"
    quality_ok = local_quality >= quality_threshold

    if local_can_serve and quality_ok:
        return "local"  # local-first happy path
    # local is insufficient (can't serve OR low quality) — consider the cloud supplement
    if claude_quota == "proceed":
        return "cloud"
    # quota throttled/halted → conserve Claude: stay local if we can, else defer
    return "local" if local_can_serve else "defer"
