"""API service models: Pydantic request/response schemas for FLUME, RL, and skills."""

from cohezion.api.services.flume import (
    FlumeDecodeRequest,
    FlumeDecodeResponse,
    FlumeEncodeRequest,
    FlumeEncodeResponse,
    FlumeInterpolateRequest,
    FlumeInterpolateResponse,
    FlumeStatusResponse,
    FlumeTrainRequest,
    FlumeTrainResponse,
)
from cohezion.api.services.rl import (
    RLPolicyResponse,
    RLTrainRequest,
    RLTrainResponse,
    RlEpisodeResponse,
    RlPolicyInfoResponse,
    RlStepRequest,
    RlStepResponse,
)
from cohezion.api.services.skills import TemplateParseRequest, TemplateParseResponse

__all__ = [
    # FLUME
    "FlumeTrainRequest",
    "FlumeTrainResponse",
    "FlumeStatusResponse",
    "FlumeEncodeRequest",
    "FlumeEncodeResponse",
    "FlumeDecodeRequest",
    "FlumeDecodeResponse",
    "FlumeInterpolateRequest",
    "FlumeInterpolateResponse",
    # RL
    "RLTrainRequest",
    "RLTrainResponse",
    "RLPolicyResponse",
    "RlStepRequest",
    "RlStepResponse",
    "RlEpisodeResponse",
    "RlPolicyInfoResponse",
    # Skills
    "TemplateParseRequest",
    "TemplateParseResponse",
]
