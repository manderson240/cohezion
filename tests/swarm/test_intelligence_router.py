"""Tests for intelligence routing."""

from __future__ import annotations

import pytest

from cohezion.swarm.intelligence_router import (
    IntelligenceRouter,
    TaskType,
    TaskTypeClassifier,
)


def test_task_type_classifier_planning():
    """Test classification of planning tasks."""
    classifier = TaskTypeClassifier()

    assert classifier.classify("design a new system architecture") == TaskType.PLANNING
    assert (
        classifier.classify("plan the implementation approach")
        == TaskType.PLANNING
    )
    assert (
        classifier.classify("outline the project structure")
        == TaskType.PLANNING
    )


def test_task_type_classifier_verification():
    """Test classification of verification tasks."""
    classifier = TaskTypeClassifier()

    assert (
        classifier.classify("review this code for bugs")
        == TaskType.VERIFICATION
    )
    assert (
        classifier.classify("validate the implementation")
        == TaskType.VERIFICATION
    )
    assert (
        classifier.classify("test the authentication flow")
        == TaskType.VERIFICATION
    )


def test_task_type_classifier_implementation():
    """Test classification of implementation tasks."""
    classifier = TaskTypeClassifier()

    assert (
        classifier.classify("implement the login function")
        == TaskType.IMPLEMENTATION
    )
    assert (
        classifier.classify("build a REST API endpoint")
        == TaskType.IMPLEMENTATION
    )
    assert (
        classifier.classify("write code to parse JSON")
        == TaskType.IMPLEMENTATION
    )


def test_task_type_classifier_query():
    """Test classification of query tasks."""
    classifier = TaskTypeClassifier()

    assert classifier.classify("what is the current status") == TaskType.QUERY
    assert classifier.classify("how does this function work") == TaskType.QUERY
    assert classifier.classify("explain the algorithm") == TaskType.QUERY


def test_intelligence_router_planning_override():
    """Test that planning tasks route to premium model."""
    router = IntelligenceRouter()

    decision = router.route("design a scalable architecture for this system")

    assert decision.task_type == TaskType.PLANNING
    # Should override to premium model for planning
    assert decision.override_model is not None
    assert "deepseek" in decision.override_model.lower()


def test_intelligence_router_verification_override():
    """Test that verification tasks route to premium model."""
    router = IntelligenceRouter()

    decision = router.route("review this code and check for security issues")

    assert decision.task_type == TaskType.VERIFICATION
    # Should override to premium model for verification
    assert decision.override_model is not None
    assert "deepseek" in decision.override_model.lower()


def test_intelligence_router_query_override():
    """Test that simple queries route to economy model."""
    router = IntelligenceRouter()

    decision = router.route("what is the current version")

    assert decision.task_type == TaskType.QUERY
    # Query routing should either override OR base decision should be economy
    final_model = router.get_final_model(decision)
    assert "phi3" in final_model.lower()


def test_intelligence_router_implementation_no_override():
    """Test that implementation uses complexity-based routing."""
    router = IntelligenceRouter()

    decision = router.route("implement this simple function")

    assert decision.task_type == TaskType.IMPLEMENTATION
    # Implementation should use base complexity routing (no override)
    # unless complexity analysis suggests otherwise
    assert decision.base_decision is not None


def test_get_final_model():
    """Test getting final model from decision."""
    router = IntelligenceRouter()

    decision = router.route("plan the project architecture")
    final_model = router.get_final_model(decision)

    # Planning should use override model
    if decision.override_model:
        assert final_model == decision.override_model
    else:
        assert final_model == decision.base_decision.model


def test_routing_stats():
    """Test routing statistics tracking."""
    router = IntelligenceRouter()

    router.route("design a system")
    router.route("implement a feature")
    router.route("review the code")
    router.route("what is the status")

    stats = router.get_routing_stats()

    assert stats["total_routes"] == 4
    assert "task_type_distribution" in stats
    assert stats["task_type_distribution"]["planning"] >= 1
    assert stats["task_type_distribution"]["verification"] >= 1


def test_force_task_type():
    """Test forcing a specific task type."""
    router = IntelligenceRouter()

    # Force planning even though query looks like query
    decision = router.route(
        "what is this", force_task_type=TaskType.PLANNING
    )

    assert decision.task_type == TaskType.PLANNING


def test_disable_override():
    """Test disabling task type override."""
    router = IntelligenceRouter(enable_override=False)

    decision = router.route("design a complex system architecture")

    # Even though it's planning, override should be disabled
    assert decision.override_model is None
    assert decision.task_type == TaskType.PLANNING
