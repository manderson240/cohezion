"""Tests for Ouroboros Version Healing (Story 7.5)."""

from __future__ import annotations

from cohezion.registry.ouroboros_version_healer import HealingOutcome, OuroborosVersionHealer


class TestOuroborosVersionHealer:
    def test_simple_conflict_auto_healed(self):
        healer = OuroborosVersionHealer()
        event = healer.heal(
            conflict_id="c1",
            packages={"requests": "2.28.0"},
            constraints={"requests": [">=2.30.0"]},
            is_complex=False,
        )
        assert event.outcome == HealingOutcome.AUTO_HEALED
        assert event.auto_healed_flag is True

    def test_complex_conflict_triggers_vae(self):
        healer = OuroborosVersionHealer()
        event = healer.heal(
            conflict_id="c2",
            packages={"numpy": "1.21.0"},
            constraints={"numpy": [">=2.0.0"]},
            is_complex=True,
        )
        assert event.outcome == HealingOutcome.VAE_TRIGGERED

    def test_regression_triggers_rollback(self):
        healer = OuroborosVersionHealer()
        event = healer.rollback_on_regression("c3", "pytest failed after upgrade")
        assert event.outcome == HealingOutcome.ROLLED_BACK
        assert event.freeze_frame_id is not None

    def test_auto_heal_rate_meets_target(self):
        healer = OuroborosVersionHealer()
        # 4 simple, 1 complex → 80% auto-heal rate
        for i in range(4):
            healer.heal(f"simple-{i}", {"pkg": "1.0.0"}, {"pkg": [">=1.1.0"]})
        healer.heal("complex", {"pkg": "1.0.0"}, {}, is_complex=True)
        assert healer.auto_heal_rate() >= 0.8

    def test_proposal_includes_version_changes(self):
        healer = OuroborosVersionHealer()
        event = healer.heal(
            "c4",
            packages={"flask": "2.0.0"},
            constraints={"flask": [">=2.3.0"]},
        )
        assert event.proposal is not None
        assert "flask" in event.proposal.changes

    def test_events_accumulated(self):
        healer = OuroborosVersionHealer()
        healer.heal("c1", {"a": "1.0"}, {})
        healer.heal("c2", {"b": "2.0"}, {})
        assert len(healer.events()) == 2
