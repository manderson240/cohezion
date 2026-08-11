import pytest
from cohezion.inference.deep_cooking import DeepCookingEngine, DeepCookingResult

def test_deep_cooking_engine_initialization_and_execution():
    cooker = DeepCookingEngine(default_timeout_seconds=300.0, max_tokens=16384)
    assert cooker.default_timeout_seconds == 300.0
    assert cooker.max_tokens == 16384

    res = cooker.cook_inference_task("Synthesize deep Poincaré geodesic proof.", model="deepseek-r1-0528-8b-FLM", timeout_seconds=0.5)
    assert isinstance(res, DeepCookingResult)
    assert res.model == "deepseek-r1-0528-8b-FLM"
    assert res.cooking_time_seconds >= 0.0
    assert isinstance(res.timed_out, bool)
