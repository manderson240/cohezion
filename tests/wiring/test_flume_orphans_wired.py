"""Discriminating identity tests: flume orphans wired in round-2 sweep."""

from cohezion.flume import gvendi_diversity_filter as pkg_gvendi
from cohezion.flume import SkillStateEncoder as pkg_sse
from cohezion.flume.diversity import gvendi_diversity_filter as src_gvendi
from cohezion.flume.skill_state_encoder import SkillStateEncoder as src_sse


def test_gvendi_diversity_filter_is_same():
    assert pkg_gvendi is src_gvendi


def test_skill_state_encoder_is_same():
    assert pkg_sse is src_sse
