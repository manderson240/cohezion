"""Discriminating identity tests: knowledge, patterns, learning orphans wired."""

from cohezion.knowledge import LLMWiki as pkg_wiki
from cohezion.knowledge import WikiEntry as pkg_entry
from cohezion.knowledge.llm_wiki import LLMWiki as src_wiki
from cohezion.knowledge.llm_wiki import WikiEntry as src_entry
from cohezion.learning import VaultNeuronWriter as pkg_writer
from cohezion.learning.vault_neuron_reader import VaultNeuronWriter as src_writer
from cohezion.patterns import CorrespondencePattern as pkg_corr
from cohezion.patterns import MentalismPattern as pkg_mental
from cohezion.patterns.hermetic_design_patterns import CorrespondencePattern as src_corr
from cohezion.patterns.hermetic_design_patterns import MentalismPattern as src_mental


def test_llm_wiki_is_same():
    assert pkg_wiki is src_wiki


def test_wiki_entry_is_same():
    assert pkg_entry is src_entry


def test_vault_neuron_writer_is_same():
    assert pkg_writer is src_writer


def test_correspondence_pattern_is_same():
    assert pkg_corr is src_corr


def test_mentalism_pattern_is_same():
    assert pkg_mental is src_mental
