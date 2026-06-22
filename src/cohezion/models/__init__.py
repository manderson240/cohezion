"""Pydantic / dataclass model definitions -- package marker."""

import contextlib

with contextlib.suppress(Exception):
    from cohezion.models.model_registry import ModelRegistry as ModelRegistry

with contextlib.suppress(Exception):
    from cohezion.models.routing_log import record_routing_decision as record_routing_decision

with contextlib.suppress(Exception):
    from cohezion.models.routing_log import TuningProposal as TuningProposal

with contextlib.suppress(Exception):
    from cohezion.models.routing_log import SpecialistProposal as SpecialistProposal

with contextlib.suppress(Exception):
    from cohezion.models.birdclef_baseline import BirdCLEFBaseline as BirdCLEFBaseline

with contextlib.suppress(Exception):
    from cohezion.models.perch_v2_adapter import PerchV2Adapter as PerchV2Adapter
