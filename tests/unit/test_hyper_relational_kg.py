"""Unit tests for Hyper-Relational Knowledge Graph & SHACL Validation.
========================================================================
Tests hyper-relational statements, qualifier tracking, and SHACL constraint enforcement.
"""

import pytest
from cohezion.knowledge_graph.hyper_relational_kg import (
    ConstraintViolation,
    HyperQualifier,
    HyperRelationalGraph,
    NodeShape,
    PropertyShape,
    StatementLifecycle,
)


class TestHyperRelationalKG:
    def test_hyper_graph_statement_creation(self):
        kg = HyperRelationalGraph()
        n1 = kg.add_node("req_kaggle_001", "Requirement", properties={"title": "Harvest Allotments", "active": True})
        n2 = kg.add_node("comp_allotment_engine", "Component", properties={"status": "running"})

        qualifier = HyperQualifier(
            confidence=0.98,
            provenance_uri="git://cohezion/commit/78b99b2d7",
            ivv_token="sha256_mock_7000e5ca",
            lifecycle=StatementLifecycle.VERIFIED,
        )

        stmt = kg.add_statement("comp_allotment_engine", "IMPLEMENTS", "req_kaggle_001", qualifier=qualifier)

        assert stmt.head_id == "comp_allotment_engine"
        assert stmt.relation == "IMPLEMENTS"
        assert stmt.tail_id == "req_kaggle_001"
        assert stmt.qualifier.confidence == 0.98
        assert stmt.qualifier.lifecycle == StatementLifecycle.VERIFIED
        assert len(stmt.statement_id) == 16

    def test_shacl_validation_conforms(self):
        kg = HyperRelationalGraph()
        kg.add_node("goal_1", "Goal", properties={"name": "Saturate RSNA", "priority": 1})
        kg.add_node("proof_1", "Proof", properties={"hash": "abc123"})

        kg.add_statement("goal_1", "VERIFIED_BY", "proof_1")

        # Define SHACL shape
        shape = NodeShape(
            target_type="Goal",
            property_shapes=[
                PropertyShape(path="name", min_count=1, datatype=str),
                PropertyShape(path="priority", min_count=1, datatype=int),
            ],
            required_outgoing_relations={"VERIFIED_BY": 1},
        )
        kg.add_shape(shape)

        report = kg.validate_shacl()
        assert report.conforms is True
        assert len(report.violations) == 0

    def test_shacl_validation_catches_missing_property_and_relation(self):
        kg = HyperRelationalGraph()
        # Missing priority property and missing VERIFIED_BY relation
        kg.add_node("goal_incomplete", "Goal", properties={"name": "Unverified Goal"})

        shape = NodeShape(
            target_type="Goal",
            property_shapes=[
                PropertyShape(path="name", min_count=1, datatype=str),
                PropertyShape(path="priority", min_count=1, datatype=int),
            ],
            required_outgoing_relations={"VERIFIED_BY": 1},
        )
        kg.add_shape(shape)

        report = kg.validate_shacl()
        assert report.conforms is False
        assert len(report.violations) == 2

        paths = {v.path for v in report.violations}
        assert "priority" in paths
        assert "VERIFIED_BY" in paths

    def test_to_surrealql_serialization(self):
        kg = HyperRelationalGraph()
        kg.add_node("agent_1", "Agent", properties={"name": "Architect"})
        kg.add_node("artifact_1", "Artifact", properties={"title": "V-Model Plan"})
        kg.add_statement("agent_1", "PRODUCES", "artifact_1", HyperQualifier(confidence=0.99))

        surql = kg.to_surrealql()
        assert len(surql) == 3
        assert any("UPSERT Agent:agent_1" in s for s in surql)
        assert any("RELATE Agent:agent_1->PRODUCES->Artifact:artifact_1" in s for s in surql)
