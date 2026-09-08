from pydantic import BaseModel, Field

from cohezion.baml.baml_bridge import BAMLResilientParser, BAMLSchemaGenerator


class SampleGoalSpec(BaseModel):
    goal_id: str = Field(description="Unique goal identifier")
    target_metric: str
    target_threshold: float
    max_iterations: int = 10


def test_baml_schema_generator():
    baml_code = BAMLSchemaGenerator.generate_baml_class(SampleGoalSpec)
    assert "class SampleGoalSpec {" in baml_code
    assert "goal_id string // Unique goal identifier" in baml_code
    assert "target_threshold float" in baml_code
    assert "max_iterations int" in baml_code


def test_baml_resilient_parser_with_thinking_and_markdown():
    raw_llm_response = """
    <think>
    The user wants a goal spec. Let's create an identifier and set target to 0.5.
    We need to make sure the JSON format matches.
    </think>
    Here is your structured goal:
    ```json
    {
        "goal_id": "goal_hiho_001",
        "target_metric": "coherence",
        "target_threshold": 0.50,
        "max_iterations": 15,
    }
    ```
    Hope this helps!
    """
    spec = BAMLResilientParser.parse_to_model(raw_llm_response, SampleGoalSpec)
    assert spec.goal_id == "goal_hiho_001"
    assert spec.target_metric == "coherence"
    assert spec.target_threshold == 0.50
    assert spec.max_iterations == 15


def test_baml_resilient_parser_healing_unclosed_braces():
    truncated_response = (
        '{"goal_id": "goal_trunc", "target_metric": "snr", "target_threshold": 20.0'
    )
    spec = BAMLResilientParser.parse_to_model(truncated_response, SampleGoalSpec)
    assert spec.goal_id == "goal_trunc"
    assert spec.target_metric == "snr"
    assert spec.target_threshold == 20.0
    assert spec.max_iterations == 10
