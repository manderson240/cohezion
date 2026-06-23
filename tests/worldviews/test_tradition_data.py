"""Tests for the Worldview Explorer tradition data and API service."""

from __future__ import annotations

import pytest

from cohezion.worldviews.tradition_data import (
    TOE_STEPS,
    get_convergences,
    get_step_across_traditions,
    get_tradition,
    get_traditions,
)


class TestTraditionRegistry:
    """Verify the 17-tradition registry is complete and well-formed."""

    def test_exactly_17_traditions(self):
        assert len(get_traditions()) == 17

    def test_all_slugs_unique(self):
        slugs = [t.slug for t in get_traditions()]
        assert len(slugs) == len(set(slugs))

    def test_all_traditions_have_10_steps(self):
        for t in get_traditions():
            assert len(t.step_mappings) == 10, f"{t.name} has {len(t.step_mappings)} steps"

    def test_step_indices_sequential(self):
        for t in get_traditions():
            for i, step in enumerate(t.step_mappings):
                assert step.step_index == i, f"{t.name} step {i} has index {step.step_index}"

    def test_all_traditions_have_unique_contributions(self):
        for t in get_traditions():
            assert len(t.unique_contributions) > 0, f"{t.name} has no unique contributions"


class TestTraditionLookup:
    """Test slug-based lookup."""

    def test_lookup_by_slug(self):
        t = get_tradition("lakota")
        assert t is not None
        assert t.name == "Lakota"

    def test_lookup_nonexistent_returns_none(self):
        assert get_tradition("nonexistent") is None

    @pytest.mark.parametrize(
        "slug,expected_name",
        [
            ("vedic", "Vedic"),
            ("daoist", "Daoist"),
            ("yoruba", "Yoruba"),
            ("haudenosaunee", "Haudenosaunee"),
            ("hopi", "Hopi"),
            ("dine", "Dine (Navajo)"),
            ("maori", "Maori"),
            ("inuit", "Inuit"),
            ("norse", "Norse"),
            ("celtic", "Celtic"),
            ("shinto", "Shinto"),
            ("andean", "Andean"),
            ("amazonian", "Amazonian"),
            ("dogon", "Dogon"),
            ("aboriginal", "Aboriginal Australian"),
        ],
    )
    def test_all_slugs_resolve(self, slug: str, expected_name: str):
        t = get_tradition(slug)
        assert t is not None
        assert t.name == expected_name


class TestTraditionProperties:
    """Test convenience properties from the table in the task spec."""

    def test_lakota_properties(self):
        t = get_tradition("lakota")
        assert t is not None
        assert t.ground_state_name == "Wakan Tanka"
        assert t.hiho_name == "Vision Quest"
        assert t.cohesion_name == "Mitakuye Oyasin"
        assert t.witness_mark_type == "Petroglyphs"

    def test_vedic_properties(self):
        t = get_tradition("vedic")
        assert t is not None
        assert t.ground_state_name == "Brahman"
        assert t.hiho_name == "Yoga"
        assert t.cohesion_name == "Dharma / Karma"

    def test_daoist_ground_state(self):
        t = get_tradition("daoist")
        assert t is not None
        assert "Wuji" in t.ground_state_name


class TestStepComparison:
    """Test cross-tradition step view."""

    def test_step_0_returns_17_entries(self):
        result = get_step_across_traditions(0)
        assert len(result) == 17

    def test_step_entries_have_required_fields(self):
        result = get_step_across_traditions(0)
        for entry in result:
            assert "tradition" in entry
            assert "slug" in entry
            assert "indigenous_term" in entry
            assert "physics_parallel" in entry

    def test_invalid_step_raises(self):
        with pytest.raises(ValueError, match="0-9"):
            get_step_across_traditions(10)

        with pytest.raises(ValueError, match="0-9"):
            get_step_across_traditions(-1)


class TestConvergences:
    """Test convergence data."""

    def test_convergences_non_empty(self):
        convergences = get_convergences()
        assert len(convergences) >= 6

    def test_convergence_categories(self):
        categories = {c.category for c in get_convergences()}
        assert "Universal Void" in categories
        assert "Relational Binding" in categories
        assert "Fourfold Structure" in categories

    def test_convergence_has_traditions(self):
        for c in get_convergences():
            assert len(c.traditions_involved) >= 2, f"{c.category} has < 2 traditions"


class TestSerialization:
    """Test to_dict / to_summary serialization."""

    def test_tradition_to_dict(self):
        t = get_tradition("lakota")
        assert t is not None
        d = t.to_dict()
        assert d["name"] == "Lakota"
        assert d["slug"] == "lakota"
        assert len(d["step_mappings"]) == 10
        assert len(d["unique_contributions"]) > 0

    def test_tradition_to_summary(self):
        t = get_tradition("lakota")
        assert t is not None
        s = t.to_summary()
        assert "step_mappings" not in s
        assert s["name"] == "Lakota"
        assert "ground_state_name" in s

    def test_convergence_to_dict(self):
        c = get_convergences()[0]
        d = c.to_dict()
        assert isinstance(d["traditions_involved"], list)
        assert isinstance(d["toe_steps"], list)

    def test_step_mapping_to_dict(self):
        t = get_tradition("lakota")
        assert t is not None
        d = t.step_mappings[0].to_dict()
        assert d["step_index"] == 0
        assert d["indigenous_term"] == "Wakan Tanka"


class TestTOESteps:
    """Test the ToE step constants."""

    def test_10_steps_defined(self):
        assert len(TOE_STEPS) == 10

    def test_first_step_is_nothing(self):
        assert "Nothing" in TOE_STEPS[0]

    def test_last_step_is_precipitates(self):
        assert "Precipitates" in TOE_STEPS[9]
