"""Discriminating identity tests: compound orphans wired in round-2 sweep."""

from cohezion.compound import CLRQualityGate as pkg_clr
from cohezion.compound import HealthObservabilityMixin as pkg_health
from cohezion.compound import LoopDaemon as pkg_daemon
from cohezion.compound import RubricMiddleware as pkg_rubric
from cohezion.compound import VModelHarness as pkg_vmodel
from cohezion.compound.clr_quality_gate import CLRQualityGate as src_clr
from cohezion.compound.degradation_health import HealthObservabilityMixin as src_health
from cohezion.compound.loop_daemon import LoopDaemon as src_daemon
from cohezion.compound.rubric_middleware import RubricMiddleware as src_rubric
from cohezion.compound.vmodel_harness import VModelHarness as src_vmodel


def test_clr_quality_gate_is_same():
    assert pkg_clr is src_clr


def test_health_observability_mixin_is_same():
    assert pkg_health is src_health


def test_loop_daemon_is_same():
    assert pkg_daemon is src_daemon


def test_rubric_middleware_is_same():
    assert pkg_rubric is src_rubric


def test_vmodel_harness_is_same():
    assert pkg_vmodel is src_vmodel
