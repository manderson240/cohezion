"""Unit tests for the Google Research SLEEP Continual Learning Framework."""

import pytest
from cohezion.agi.sleep_framework import (
    ConsolidationReport,
    DreamCurriculumGenerator,
    DreamReport,
    EpisodicExperienceBuffer,
    KnowledgeSeeder,
    SleepCycleSummary,
    SleepFramework,
    WakeExperience,
)


def test_wake_experience_td_error() -> None:
    """Verify TD-error calculation for prioritized experience replay."""
    exp1 = WakeExperience(
        experience_id="exp1",
        session_id="s1",
        task_description="task 1",
        action_sequence=("step1", "step2"),
        state_vector=(0.1, 0.2, 0.3),
        reward=1.0,
        loss=0.05,
        entropy=0.2,
    )
    # td_error = |loss| + |reward - 0.5| + (entropy * 0.1)
    # = 0.05 + 0.5 + 0.02 = 0.57
    assert pytest.approx(exp1.td_error, abs=1e-4) == 0.57

    exp_high_loss = WakeExperience(
        experience_id="exp2",
        session_id="s1",
        task_description="failed task",
        action_sequence=("step1",),
        state_vector=(0.5, 0.5),
        reward=0.0,
        loss=2.5,
        entropy=0.8,
    )
    assert exp_high_loss.td_error > exp1.td_error


def test_episodic_buffer_prioritized_sampling() -> None:
    """Verify episodic buffer capacity, append, and prioritized sampling."""
    buffer = EpisodicExperienceBuffer(capacity=10)
    for i in range(15):
        buffer.append(
            WakeExperience(
                experience_id=f"exp_{i}",
                session_id="test",
                task_description=f"task {i}",
                action_sequence=("action",),
                state_vector=(float(i),),
                reward=float(i) / 15.0,
                loss=1.0 / (float(i) + 1.0),
                entropy=0.1,
            )
        )

    # Capacity bounded
    assert len(buffer) == 10

    # Prioritized sample
    sampled = buffer.sample_prioritized(batch_size=5)
    assert len(sampled) == 5
    assert all(isinstance(x, WakeExperience) for x in sampled)

    # Buffer clear
    buffer.clear()
    assert len(buffer) == 0
    assert buffer.sample_prioritized(batch_size=5) == []


def test_knowledge_seeder_consolidation_and_ewc() -> None:
    """Verify knowledge seeding with EWC penalty and Fisher updates."""
    seeder = KnowledgeSeeder(dimension=4, ewc_lambda=50.0, learning_rate=0.1)
    assert seeder.theta == [0.0, 0.0, 0.0, 0.0]

    exps = [
        WakeExperience(
            experience_id="e1",
            session_id="s1",
            task_description="t1",
            action_sequence=("a",),
            state_vector=(1.0, 0.5, 0.0, 0.2),
            reward=0.9,
            loss=0.1,
            entropy=0.1,
        )
    ]

    report = seeder.consolidate(exps)
    assert isinstance(report, ConsolidationReport)
    assert report.experiences_consolidated == 1
    assert report.knowledge_retention_score > 0.0
    assert report.duration_ms >= 0.0

    # Parameters moved toward target vector
    assert seeder.theta[0] > 0.0
    assert seeder.theta[1] > 0.0

    # Freeze prior baseline
    seeder.freeze_as_prior()
    assert seeder.theta_prior == seeder.theta


def test_dream_curriculum_generation() -> None:
    """Verify synthetic dream curriculum generation and invariant verification."""
    dreamer = DreamCurriculumGenerator(dimension=6)
    base_state = [0.2, 0.1, 0.05, 0.0, 0.1, 0.2]

    report = dreamer.generate_and_rehearse(base_state=base_state, num_dreams=10)
    assert isinstance(report, DreamReport)
    assert report.dreams_generated == 10
    assert report.dreams_verified > 0
    assert 0.0 <= report.verification_rate <= 1.0
    assert report.mean_synthetic_reward >= 0.0
    assert report.duration_ms >= 0.0


def test_sleep_framework_full_lifecycle() -> None:
    """Verify end-to-end SleepFramework: Wake -> Sleep -> Reset -> Retain."""
    framework = SleepFramework(dimension=4, buffer_capacity=100, ewc_lambda=20.0)

    # 1. Wake Phase: Record experiences
    for i in range(5):
        framework.record_experience(
            task_description=f"Execution task {i}",
            action_sequence=[f"action_{i}"],
            state_vector=[0.2 * i, 0.1 * i, 0.05 * i, 0.1],
            reward=0.8,
            loss=0.2,
            entropy=0.15,
        )

    assert len(framework.buffer) == 5
    assert framework.cycle_count == 0

    # 2. Sleep Phase: Run consolidation, dreaming, and buffer reset
    summary = framework.sleep(batch_size=4, num_dreams=6)
    assert isinstance(summary, SleepCycleSummary)
    assert summary.wake_experiences_processed == 5
    assert summary.consolidation.experiences_consolidated == 4
    assert summary.dreaming.dreams_generated == 6
    assert summary.overall_retention_score > 0.5
    assert summary.parameter_drift_norm > 0.0
    assert framework.cycle_count == 1

    # Buffer must be cleared after sleep
    assert len(framework.buffer) == 0

    # History stored
    history = framework.get_cycle_history()
    assert len(history) == 1
    assert history[0].cycle_id == "sleep_cycle_0001"


def test_continual_learning_anti_forgetting_multi_cycle() -> None:
    """Verify that EWC prevents catastrophic forgetting across sequential tasks."""
    framework = SleepFramework(dimension=4, ewc_lambda=100.0)

    # Task A: High activation on dimension 0
    for _ in range(4):
        framework.record_experience(
            task_description="Task A (Dimension 0 emphasis)",
            action_sequence=["stepA"],
            state_vector=[1.0, 0.0, 0.0, 0.0],
            reward=1.0,
            loss=0.05,
        )
    summary_a = framework.sleep(batch_size=4, num_dreams=4)
    dim0_after_a = framework.seeder.theta[0]
    assert dim0_after_a > 0.0

    # Task B: High activation on dimension 3
    for _ in range(4):
        framework.record_experience(
            task_description="Task B (Dimension 3 emphasis)",
            action_sequence=["stepB"],
            state_vector=[0.0, 0.0, 0.0, 1.0],
            reward=1.0,
            loss=0.05,
        )
    summary_b = framework.sleep(batch_size=4, num_dreams=4)
    dim0_after_b = framework.seeder.theta[0]
    dim3_after_b = framework.seeder.theta[3]

    # Critical continual learning check: Dimension 0 must NOT be zeroed out
    # (Catastrophic forgetting prevented by EWC penalty and Fisher importance)
    assert dim0_after_b > 0.0
    assert dim3_after_b > 0.0
    assert summary_b.overall_retention_score > 0.0
