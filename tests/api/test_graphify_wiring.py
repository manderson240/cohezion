"""Unit tests for the graphify wiring (Move 2) — mapping + parsing, no network."""

from __future__ import annotations

from cohezion.api.services.graphify import GraphifyService


class TestEdgeTableMapping:
    def test_exact_matches_map_to_existing_tables(self):
        for verb in ("informed_by", "led_to", "influences", "similar_to", "derived_from"):
            assert GraphifyService.edge_table_for(verb) == verb

    def test_verb_prefix_families_map(self):
        assert GraphifyService.edge_table_for("informs") == "informed_by"
        assert GraphifyService.edge_table_for("leads to") == "led_to"
        assert GraphifyService.edge_table_for("derived from") == "derived_from"

    def test_unknown_verbs_fall_back_not_spawn_tables(self):
        # Discriminating: a novel verb must NOT create a new edge table per verb
        # (that would re-sprawl the schema); it lands in relates_to.
        assert GraphifyService.edge_table_for("orchestrates") == "relates_to"
        assert GraphifyService.edge_table_for("") == "relates_to"


class TestSlug:
    def test_slug_is_record_id_safe(self):
        s = GraphifyService._slug("NPU Gauntlet (24/7) — v1.2!")
        assert s == "npu_gauntlet_24_7_v1_2"
        assert len(GraphifyService._slug("x" * 200)) <= 60
