"""Tests for vibe types — VibeIntent and VibeWorkflowSpec."""

import pytest

from cohezion.vibe.types import (
    EdgeDescription,
    NodeDescription,
    OperationType,
    VibeIntent,
    VibeWorkflowSpec,
)


class TestVibeIntent:
    def test_basic_construction(self):
        intent = VibeIntent(
            raw_text="research and implement auth",
            keywords=["research", "implement", "auth"],
            operation_type=OperationType.IMPLEMENT,
            complexity=3,
            confidence=0.85,
        )
        assert intent.raw_text == "research and implement auth"
        assert intent.keywords == ["research", "implement", "auth"]
        assert intent.operation_type == OperationType.IMPLEMENT
        assert intent.complexity == 3
        assert intent.confidence == 0.85
        assert intent.sub_intents == []

    def test_sub_intents_default_empty(self):
        intent = VibeIntent(
            raw_text="do things",
            keywords=[],
            operation_type=OperationType.UNKNOWN,
            complexity=1,
            confidence=0.5,
        )
        assert intent.sub_intents == []

    def test_sub_intents_populated(self):
        intent = VibeIntent(
            raw_text="complex task",
            keywords=["complex"],
            operation_type=OperationType.ORCHESTRATE,
            complexity=5,
            confidence=0.7,
            sub_intents=["fetch data", "transform data", "save results"],
        )
        assert len(intent.sub_intents) == 3

    def test_complexity_must_be_1_to_5(self):
        with pytest.raises(ValueError, match="complexity"):
            VibeIntent(
                raw_text="x",
                keywords=[],
                operation_type=OperationType.UNKNOWN,
                complexity=0,
                confidence=0.5,
            )

    def test_complexity_upper_bound(self):
        with pytest.raises(ValueError, match="complexity"):
            VibeIntent(
                raw_text="x",
                keywords=[],
                operation_type=OperationType.UNKNOWN,
                complexity=6,
                confidence=0.5,
            )

    def test_confidence_must_be_0_to_1(self):
        with pytest.raises(ValueError, match="confidence"):
            VibeIntent(
                raw_text="x",
                keywords=[],
                operation_type=OperationType.UNKNOWN,
                complexity=1,
                confidence=1.5,
            )

    def test_operation_type_enum_values(self):
        assert OperationType.RESEARCH.value == "research"
        assert OperationType.IMPLEMENT.value == "implement"
        assert OperationType.UNKNOWN.value == "unknown"


class TestNodeDescription:
    def test_basic_construction(self):
        node = NodeDescription(
            name="researcher",
            role="Gather background information",
            agent_role="researcher",
        )
        assert node.name == "researcher"
        assert node.inputs == []
        assert node.outputs == []

    def test_with_io_keys(self):
        node = NodeDescription(
            name="coder",
            role="Write implementation",
            agent_role="coder",
            inputs=["research_summary"],
            outputs=["code", "tests"],
        )
        assert node.inputs == ["research_summary"]
        assert node.outputs == ["code", "tests"]


class TestEdgeDescription:
    def test_basic_construction(self):
        edge = EdgeDescription(from_name="A", to_name="B")
        assert edge.from_name == "A"
        assert edge.to_name == "B"
        assert edge.keys == []
        assert edge.condition is None

    def test_with_condition(self):
        edge = EdgeDescription(from_name="gate", to_name="impl", keys=["signal"], condition="signal=='go'")
        assert edge.condition == "signal=='go'"


class TestVibeWorkflowSpec:
    def _make_intent(self):
        return VibeIntent(
            raw_text="research then implement",
            keywords=["research", "implement"],
            operation_type=OperationType.IMPLEMENT,
            complexity=2,
            confidence=0.9,
        )

    def test_basic_construction(self):
        intent = self._make_intent()
        spec = VibeWorkflowSpec(
            intent=intent,
            node_descriptions=[
                NodeDescription("A", "first", "researcher"),
                NodeDescription("B", "second", "coder"),
            ],
            edge_descriptions=[EdgeDescription("A", "B")],
        )
        assert spec.node_count == 2
        assert spec.edge_count == 1
        assert spec.parameters == {}
        assert spec.similar_past_workflows == []
        assert spec.template_used is None

    def test_empty_spec(self):
        intent = self._make_intent()
        spec = VibeWorkflowSpec(intent=intent, node_descriptions=[], edge_descriptions=[])
        assert spec.node_count == 0
        assert spec.edge_count == 0

    def test_with_metadata(self):
        intent = self._make_intent()
        spec = VibeWorkflowSpec(
            intent=intent,
            node_descriptions=[],
            edge_descriptions=[],
            parameters={"max_retries": 3},
            similar_past_workflows=["wf-abc", "wf-def"],
            template_used="research-implement-v1",
        )
        assert spec.parameters["max_retries"] == 3
        assert len(spec.similar_past_workflows) == 2
        assert spec.template_used == "research-implement-v1"
