""" "Cohezion third-party integrations."""

from __future__ import annotations

import contextlib

from .obsidian_wiki import ObsidianWiki, WikiPage
from .ulogme_bridge import ActivityEntry, FocusSession, UlogmeBridge
from .wiki_mirix_bridge import MemoryMapping, WikiMirixBridge


# Wiring-sweep 2026-06-22: competition_rate_limiter.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.integrations.competition_rate_limiter import (
        CompetitionRateLimiter as CompetitionRateLimiter,
    )

# Wiring-sweep 2026-06-22: flume_wiki_bridge.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.integrations.flume_wiki_bridge import (
        FlumeOuroborosBridge as FlumeOuroborosBridge,
    )
    from cohezion.integrations.flume_wiki_bridge import (
        FlumeWikiBridge as FlumeWikiBridge,
    )

# Wiring-sweep 2026-06-22: hermes_mcp_bridge.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.integrations.hermes_mcp_bridge import (
        run_mcp_stdio as run_mcp_stdio,
    )

# Wiring-sweep 2026-06-22: kaggle_api.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.integrations.kaggle_api import KaggleAPI as KaggleAPI

# Wiring-sweep 2026-06-22: kaggle_curation.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.integrations.kaggle_curation import KaggleCurator as KaggleCurator

# Wiring-sweep 2026-06-22: kaggle_eval.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.integrations.kaggle_eval import KaggleEvaluator as KaggleEvaluator

# Wiring-sweep 2026-06-22: kaggle_submission.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.integrations.kaggle_submission import (
        KaggleSubmissionOrchestrator as KaggleSubmissionOrchestrator,
    )

# Wiring-sweep 2026-06-22: kaggle_submission_improved.py was a genuine import-graph orphan.
# Alias disambiguated to avoid F811 collision with KaggleSubmissionOrchestrator above.
with contextlib.suppress(Exception):
    from cohezion.integrations.kaggle_submission_improved import (
        KaggleSubmissionOrchestrator as KaggleSubmissionOrchestratorImproved,
    )

# Wiring-sweep 2026-06-22: kaggle_training.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.integrations.kaggle_training import (
        KaggleTrainingManager as KaggleTrainingManager,
    )

# Wiring-sweep 2026-06-22: kaggle_training_improved.py was a genuine import-graph orphan.
# Alias disambiguated to avoid F811 collision with KaggleTrainingManager above.
with contextlib.suppress(Exception):
    from cohezion.integrations.kaggle_training_improved import (
        KaggleTrainingManager as KaggleTrainingManagerImproved,
    )

# Wiring-sweep 2026-06-22: telegram_bot.py was a genuine import-graph orphan.
with contextlib.suppress(Exception):
    from cohezion.integrations.telegram_bot import (
        TelegramCommunicationHub as TelegramCommunicationHub,
    )


__all__ = [
    "ActivityEntry",
    "CompetitionRateLimiter",
    "FlumeOuroborosBridge",
    "FlumeWikiBridge",
    "FocusSession",
    "KaggleAPI",
    "KaggleCurator",
    "KaggleEvaluator",
    "KaggleSubmissionOrchestrator",
    "KaggleSubmissionOrchestratorImproved",
    "KaggleTrainingManager",
    "KaggleTrainingManagerImproved",
    "MemoryMapping",
    "ObsidianWiki",
    "TelegramCommunicationHub",
    "UlogmeBridge",
    "WikiMirixBridge",
    "WikiPage",
    "run_mcp_stdio",
]
