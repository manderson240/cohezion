"""Discriminating identity tests: agent/ and agents/ orphan modules wired in round-5 sweep."""

# agent/ identity tests
from cohezion.agent import ReDispatchLedger as pkg_ledger
from cohezion.agent import ReflectiveDriver as pkg_driver
from cohezion.agent import adapt_skill as pkg_adapt_skill
from cohezion.agent.error_loop import ReDispatchLedger as src_ledger
from cohezion.agent.reflective_driver import ReflectiveDriver as src_driver
from cohezion.agent.skill_adaptor import adapt_skill as src_adapt_skill

# agents/ template_pipeline identity test
from cohezion.agents import TemplatePipeline as pkg_template_pipeline

# agents/ identity tests
from cohezion.agents import VersionTracker as pkg_version_tracker
from cohezion.agents import wrap_untrusted as pkg_wrap_untrusted
from cohezion.agents.prompt_injection_guard import wrap_untrusted as src_wrap_untrusted
from cohezion.agents.template_pipeline import TemplatePipeline as src_template_pipeline
from cohezion.agents.version_tracker import VersionTracker as src_version_tracker


def test_redispatch_ledger_is_same():
    """ReDispatchLedger from cohezion.agent surface must be identical to its source."""
    assert pkg_ledger is src_ledger


def test_reflective_driver_is_same():
    """ReflectiveDriver from cohezion.agent surface must be identical to its source."""
    assert pkg_driver is src_driver


def test_adapt_skill_is_same():
    """adapt_skill from cohezion.agent surface must be identical to its source."""
    assert pkg_adapt_skill is src_adapt_skill


def test_version_tracker_is_same():
    """VersionTracker from cohezion.agents surface must be identical to its source."""
    assert pkg_version_tracker is src_version_tracker


def test_wrap_untrusted_is_same():
    """wrap_untrusted from cohezion.agents surface must be identical to its source."""
    assert pkg_wrap_untrusted is src_wrap_untrusted


def test_template_pipeline_is_same():
    """TemplatePipeline from cohezion.agents surface must be identical to its source."""
    assert pkg_template_pipeline is src_template_pipeline
