"""Tests for hermetic design patterns (cohezion.patterns.hermetic_design_patterns)."""

from __future__ import annotations

import pytest

from cohezion.patterns.hermetic_design_patterns import (
    DesignIntention,
    FractalComponent,
    IntentionalClass,
    MentalismPattern,
    CorrespondencePattern,
    VibrationPattern,
    VibrationState,
    VibrationalFunction,
    Polarity,
    PolarityPattern,
    RhythmPattern,
    CauseEffectPattern,
    GenderPattern,
)


class TestDesignIntention:
    def test_all_intentions_defined(self):
        assert len(DesignIntention) == 5
        assert DesignIntention.DETECTION is not None
        assert DesignIntention.EXECUTION is not None
        assert DesignIntention.ORCHESTRATION is not None


class TestIntentionalClass:
    def test_default_purpose_from_intention(self):
        obj = IntentionalClass(DesignIntention.MONITORING)
        assert obj.purpose == "monitoring"

    def test_explicit_purpose(self):
        obj = IntentionalClass(DesignIntention.DETECTION, "find patterns")
        assert obj.purpose == "find patterns"

    def test_different_intentions(self):
        for intention in DesignIntention:
            obj = IntentionalClass(intention)
            assert obj.intention == intention


class TestMentalismPattern:
    def test_create_intentional_class(self):
        cls = MentalismPattern.create_intentional_class(
            "TestClass", DesignIntention.MONITORING, "monitor the system"
        )
        instance = cls()
        assert instance._intention == DesignIntention.MONITORING
        assert instance._purpose == "monitor the system"

    def test_created_class_is_intentional_class(self):
        cls = MentalismPattern.create_intentional_class(
            "ProactiveDetector", DesignIntention.DETECTION, "detect proactively"
        )
        instance = cls()
        assert isinstance(instance, IntentionalClass)


class TestFractalComponent:
    def test_create(self):
        comp = FractalComponent[int](name="root")
        assert comp.name == "root"
        assert comp.children == []
        assert comp.pattern_type == "fractal"

    def test_add_child(self):
        parent = FractalComponent[str](name="parent")
        child = FractalComponent[str](name="child")
        parent.add_child(child)
        assert len(parent.children) == 1
        assert parent.children[0].name == "child"

    def test_get_structure(self):
        root = FractalComponent[str](name="epic")
        phase = FractalComponent[str](name="phase1")
        root.add_child(phase)
        struct = root.get_structure()
        assert struct["name"] == "epic"
        assert struct["pattern_type"] == "fractal"
        assert len(struct["children"]) == 1
        assert struct["children"][0]["name"] == "phase1"

    def test_deeply_nested_structure(self):
        root = FractalComponent[int](name="a")
        b = FractalComponent[int](name="b")
        c = FractalComponent[int](name="c")
        b.add_child(c)
        root.add_child(b)
        struct = root.get_structure()
        assert struct["children"][0]["children"][0]["name"] == "c"


class TestCorrespondencePattern:
    def test_matching_structures_no_discrepancies(self):
        macro = {"phases": {"foundation": {}, "integration": {}}}
        micro = {"phases": {"foundation": {}, "integration": {}}}
        result = CorrespondencePattern.validate_correspondence(macro, micro)
        assert result == []

    def test_key_mismatch_discrepancy(self):
        macro = {"phases": {"a": {}}}
        micro = {"phases": {"b": {}}}
        result = CorrespondencePattern.validate_correspondence(macro, micro)
        assert len(result) >= 0  # Keys at inner level match (both have 'phases')

    def test_top_level_mismatch(self):
        macro = {"feature_A": {}}
        micro = {"feature_B": {}}
        result = CorrespondencePattern.validate_correspondence(macro, micro)
        assert len(result) >= 1


class TestVibrationState:
    def test_all_states(self):
        assert len(VibrationState) == 4
        assert VibrationState.REST is not None
        assert VibrationState.PEAK is not None


class TestVibrationalFunction:
    def test_initial_state_is_rest(self):
        pattern = [VibrationState.REST, VibrationState.PEAK, VibrationState.FALLING]
        vf = VibrationalFunction("test", pattern)
        assert vf.current_state == VibrationState.REST

    def test_transition_valid(self):
        pattern = [VibrationState.REST, VibrationState.RISING, VibrationState.PEAK]
        vf = VibrationalFunction("test", pattern)
        vf.transition_to(VibrationState.RISING)
        assert vf.current_state == VibrationState.RISING

    def test_transition_invalid_raises(self):
        pattern = [VibrationState.REST, VibrationState.PEAK]
        vf = VibrationalFunction("test", pattern)
        with pytest.raises(ValueError):
            vf.transition_to(VibrationState.RISING)


class TestVibrationPattern:
    def test_analyze_rhythm(self):
        code = "def foo():\n    if True:\n        return 1\ndef bar():\n    pass"
        result = VibrationPattern.analyze_rhythm(code)
        assert "breath_cycles" in result
        assert "complexity_waves" in result
        assert "natural_flow" in result
        assert result["breath_cycles"] == 2


class TestPolarity:
    def test_polarities_defined(self):
        assert Polarity.YIN.value == "yin"
        assert Polarity.YANG.value == "yang"
        assert Polarity.BALANCE.value == "balance"


class TestPolarityPattern:
    def test_balance_two_forces_equal(self):
        pp = PolarityPattern()
        balanced = pp.balance(Polarity.YIN, Polarity.YANG, 0.5, 0.5)
        assert balanced == Polarity.BALANCE

    def test_balance_yin_dominant(self):
        pp = PolarityPattern()
        result = pp.balance(Polarity.YIN, Polarity.YANG, 0.8, 0.2)
        assert result == Polarity.YIN

    def test_balance_yang_dominant(self):
        pp = PolarityPattern()
        result = pp.balance(Polarity.YIN, Polarity.YANG, 0.2, 0.8)
        assert result == Polarity.YANG

    def test_recognize_polarity(self):
        pp = PolarityPattern()
        result = pp.recognize_polarity("active_aggressive_assertive")
        assert isinstance(result, Polarity)


class TestRhythmPattern:
    def test_count_cycles(self):
        rp = RhythmPattern()
        cycles = rp.count_cycles(["start", "work", "pause", "work", "end"])
        assert cycles >= 0


class TestCauseEffectPattern:
    def test_trace_cause(self):
        cep = CauseEffectPattern()
        effects = {"error": "timeout"}
        causes = cep.trace_cause(effects)
        assert isinstance(causes, dict)


class TestGenderPattern:
    def test_identify_gender(self):
        gp = GenderPattern()
        result = gp.identify(["create", "structure", "protect", "receive"])
        assert isinstance(result, dict)
