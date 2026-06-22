import contextlib


with contextlib.suppress(Exception):
    from cohezion.api.routes.a2a import a2a_router as a2a_router

with contextlib.suppress(Exception):
    from cohezion.api.routes.agentjet import agentjet_router as agentjet_router

with contextlib.suppress(Exception):
    from cohezion.api.routes.agui import agui_router as agui_router

with contextlib.suppress(Exception):
    from cohezion.api.routes.compound import compound_router as compound_router

with contextlib.suppress(Exception):
    from cohezion.api.routes.eigent import router as eigent_router  # noqa: F401

with contextlib.suppress(Exception):
    from cohezion.api.routes.fleet import router as fleet_router  # noqa: F401

with contextlib.suppress(Exception):
    from cohezion.api.routes.flume import flume_router as flume_router

with contextlib.suppress(Exception):
    from cohezion.api.routes.flume_inline import flume_inline_router as flume_inline_router

with contextlib.suppress(Exception):
    from cohezion.api.routes.journeys_legacy import (
        journeys_legacy_router as journeys_legacy_router,
    )

with contextlib.suppress(Exception):
    from cohezion.api.routes.knowledge import knowledge_router as knowledge_router

with contextlib.suppress(Exception):
    from cohezion.api.routes.mcp import mcp_router as mcp_router

with contextlib.suppress(Exception):
    from cohezion.api.routes.metrics import metrics_router as metrics_router

with contextlib.suppress(Exception):
    from cohezion.api.routes.notebooks import notebooks_router as notebooks_router

with contextlib.suppress(Exception):
    from cohezion.api.routes.rl import rl_router as rl_router

with contextlib.suppress(Exception):
    from cohezion.api.routes.skills import skills_router as skills_router

with contextlib.suppress(Exception):
    from cohezion.api.routes.swarm import swarm_router as swarm_router

with contextlib.suppress(Exception):
    from cohezion.api.routes.templates import templates_router as templates_router

with contextlib.suppress(Exception):
    from cohezion.api.routes.training import training_router as training_router
