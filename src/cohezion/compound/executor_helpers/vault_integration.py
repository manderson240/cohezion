"""Vault experience-guidance enrichment helper for CompoundExecutor (Wave 2D extract).

Fetches base guidance from the vault logger, then enriches it with
trajectory search results (FLUME experience) and recent SurrealDB
retrospection decisions. All enrichment steps are non-blocking — the
function always returns at minimum the base guidance.
"""

from __future__ import annotations

import logging
from typing import Any


logger = logging.getLogger(__name__)


def fetch_experience_guidance(
    vault_logger: Any,
    task_description: str,
    project: str = "cohezion",
    operation_type: str = "generate",
    skill_name: str = "",
) -> dict[str, Any]:
    """Fetch experience guidance from vault before execution.

    Enhanced with trajectory search: finds similar past executions and
    provides recommendations based on their outcomes. Then queries
    SurrealDB for recent retrospection decisions to close the feedback
    loop between RetrospectionEngine and the next execution.

    Args:
        vault_logger: VaultLogger instance (typically ``CompoundExecutor.logger``).
        task_description: Description of the task to execute.
        project: Project name for scoped search.
        operation_type: Type of operation (for trajectory search).
        skill_name: Skill whose PRIME-file learned refinements should be
            merged in (empty string skips the refinement read).

    Returns:
        Dict with relevant_context (decisions, experiments, patterns)
        plus trajectory-based recommendations, warnings, and confidence.
    """
    logger.info("Fetching experience guidance for: %s", task_description)

    # Step 1: Get base guidance from vault
    base_guidance: dict[str, Any] = vault_logger.get_experience_guidance(
        task_description=task_description, project=project
    )

    # Step 2: Enhance with trajectory search (if available)
    try:
        from cohezion.compound.guidance_enhancer import GuidanceEnhancer
        from cohezion.compound.trajectory_search import TrajectorySearchEngine
        from cohezion.flume.experience_collector import ExperienceCollector
        from cohezion.flume.experience_encoder import ExperienceEncoder

        # Initialize search components (lazy)
        collector = ExperienceCollector()
        encoder = ExperienceEncoder()
        search = TrajectorySearchEngine(collector, encoder)
        enhancer = GuidanceEnhancer()

        # Find similar trajectories
        trajectory_results = search.find_similar_trajectories(
            task_description=task_description,
            operation_type=operation_type,
            top_k=5,
            min_coherence=0.4,  # HIHO threshold
        )

        # Enhance guidance
        enhanced = enhancer.enhance_guidance(base_guidance, trajectory_results)
        result = enhancer.to_dict(enhanced)

        logger.info(
            "Guidance enhanced with %d similar trajectories (confidence=%.2f)",
            enhanced.similar_task_count,
            enhanced.confidence,
        )

    except (ImportError, AttributeError, RuntimeError, ValueError, KeyError) as e:
        logger.debug(
            "Trajectory search failed (non-blocking): %s. Using base guidance only.",
            e,
            exc_info=True,
        )
        result = base_guidance

    # Step 3: Query SurrealDB for recent retrospection decisions (closes feedback loop)
    try:
        import json
        import urllib.request
        from base64 import b64encode

        req = urllib.request.Request(
            "http://localhost:8001/sql",
            data=b"SELECT skill, should_refine, compound_score, recommendation FROM retrospection ORDER BY created DESC LIMIT 3;",
            headers={
                "Accept": "application/json",
                "surreal-ns": "cohezion",
                "surreal-db": "cohezion",
                "Authorization": "Basic " + b64encode(b"root:root").decode(),
            },
            method="POST",
        )
        resp = urllib.request.urlopen(req, timeout=2)
        data = json.loads(resp.read())
        if data and data[0].get("status") == "OK" and data[0]["result"]:
            result["recent_retrospections"] = data[0]["result"]
            logger.debug("Guidance enriched with %d recent retrospections", len(data[0]["result"]))
    except (OSError, ValueError, KeyError) as e:
        logger.debug("SurrealDB retrospection query failed (non-blocking): %s", e)

    # Step 4: Merge learned refinements from the skill's PRIME file (closes
    # the SkillRefiner._append_refinement → next-execution feedback loop)
    if skill_name:
        try:
            from cohezion.compound.executor_helpers.refinement_reader import (
                load_refined_guidance,
            )

            result["learned_refinements"] = load_refined_guidance(skill_name)
            logger.debug(
                "Guidance enriched with %d learned refinements for %s",
                len(result["learned_refinements"]),
                skill_name,
            )
        except (ImportError, OSError, ValueError, KeyError) as e:
            logger.debug("Learned-refinement read failed (non-blocking): %s", e)

    return result
