"""Discriminating identity test: task_classifier exports reachable via inference package."""

from cohezion.inference import RouteDecision as pkg_RouteDecision
from cohezion.inference import classify as pkg_classify
from cohezion.inference import classify_with_harness as pkg_cwh
from cohezion.inference import select_harness as pkg_select_harness
from cohezion.inference.task_classifier import RouteDecision as src_RouteDecision
from cohezion.inference.task_classifier import classify as src_classify
from cohezion.inference.task_classifier import classify_with_harness as src_cwh
from cohezion.inference.task_classifier import select_harness as src_select_harness


def test_classify_is_same_object():
    assert pkg_classify is src_classify


def test_classify_with_harness_is_same_object():
    assert pkg_cwh is src_cwh


def test_route_decision_is_same_class():
    assert pkg_RouteDecision is src_RouteDecision


def test_select_harness_is_same_object():
    assert pkg_select_harness is src_select_harness
