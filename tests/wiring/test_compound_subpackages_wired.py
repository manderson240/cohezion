"""Identity tests for compound/ sub-package orphan wiring.

Each assertion proves the name re-exported from the sub-package __init__ is
the same object as the name imported directly from the source module.
"""

# analytics
from cohezion.compound.analytics import AnalysisConfig as pkg_analysis_cfg
from cohezion.compound.analytics import ExecutionAnalyzer as pkg_exec_analyzer
from cohezion.compound.analytics import MetricsCollector as pkg_metrics_collector
from cohezion.compound.analytics import MetricsSnapshot as pkg_metrics_snapshot
from cohezion.compound.analytics import SimpleAnalyzer as pkg_simple_analyzer
from cohezion.compound.analytics import SimpleMetrics as pkg_simple_metrics
from cohezion.compound.analytics.engine import AnalysisConfig as src_analysis_cfg
from cohezion.compound.analytics.engine import ExecutionAnalyzer as src_exec_analyzer
from cohezion.compound.analytics.engine import SimpleAnalyzer as src_simple_analyzer
from cohezion.compound.analytics.metrics import MetricsCollector as src_metrics_collector
from cohezion.compound.analytics.metrics import MetricsSnapshot as src_metrics_snapshot
from cohezion.compound.analytics.metrics import SimpleMetrics as src_simple_metrics

# autonomous_loop
from cohezion.compound.autonomous_loop import ChallengerAgent as pkg_challenger
from cohezion.compound.autonomous_loop import EpisodeResult as pkg_episode
from cohezion.compound.autonomous_loop import ImprovementExecutor as pkg_imp_exec
from cohezion.compound.autonomous_loop import LocalImprovementExecutor as pkg_local_exec
from cohezion.compound.autonomous_loop import LoopConfig as pkg_loop_cfg
from cohezion.compound.autonomous_loop import LoopCoordinator as pkg_loop_coord
from cohezion.compound.autonomous_loop import LoopTask as pkg_loop_task
from cohezion.compound.autonomous_loop import LoopTickSweeper as pkg_tick_sweeper
from cohezion.compound.autonomous_loop import MarkovQualityTracker as pkg_markov
from cohezion.compound.autonomous_loop import RZeroChallengerExecutor as pkg_rzero
from cohezion.compound.autonomous_loop import RunReport as pkg_run_report
from cohezion.compound.autonomous_loop import SolverAgent as pkg_solver
from cohezion.compound.autonomous_loop import SprintResult as pkg_sprint
from cohezion.compound.autonomous_loop import TaskAttempt as pkg_task_attempt
from cohezion.compound.autonomous_loop.coordinator import LoopConfig as src_loop_cfg
from cohezion.compound.autonomous_loop.coordinator import LoopCoordinator as src_loop_coord
from cohezion.compound.autonomous_loop.coordinator import LoopTask as src_loop_task
from cohezion.compound.autonomous_loop.coordinator import RunReport as src_run_report
from cohezion.compound.autonomous_loop.coordinator import SprintResult as src_sprint
from cohezion.compound.autonomous_loop.executor import ImprovementExecutor as src_imp_exec
from cohezion.compound.autonomous_loop.local_executor import (
    LocalImprovementExecutor as src_local_exec,
)
from cohezion.compound.autonomous_loop.local_executor import LoopTickSweeper as src_tick_sweeper
from cohezion.compound.autonomous_loop.quality_tracker import (
    MarkovQualityTracker as src_markov,
)
from cohezion.compound.autonomous_loop.rzero_challenger import ChallengerAgent as src_challenger
from cohezion.compound.autonomous_loop.rzero_challenger import EpisodeResult as src_episode
from cohezion.compound.autonomous_loop.rzero_challenger import (
    RZeroChallengerExecutor as src_rzero,
)
from cohezion.compound.autonomous_loop.rzero_challenger import SolverAgent as src_solver
from cohezion.compound.autonomous_loop.rzero_challenger import TaskAttempt as src_task_attempt

# core
from cohezion.compound.core import BatchProcessor as pkg_batch_proc
from cohezion.compound.core import BatchResult as pkg_batch_result
from cohezion.compound.core import CompoundExecutor as pkg_core_executor
from cohezion.compound.core import ExecutionConfig as pkg_exec_cfg
from cohezion.compound.core import SimpleBatch as pkg_simple_batch
from cohezion.compound.core import execute_simple as pkg_execute_simple
from cohezion.compound.core.batch_processor import BatchProcessor as src_batch_proc
from cohezion.compound.core.batch_processor import BatchResult as src_batch_result
from cohezion.compound.core.batch_processor import SimpleBatch as src_simple_batch
from cohezion.compound.core.executor import CompoundExecutor as src_core_executor
from cohezion.compound.core.executor import ExecutionConfig as src_exec_cfg
from cohezion.compound.core.executor import execute_simple as src_execute_simple

# executor_helpers
from cohezion.compound.executor_helpers import fetch_experience_guidance as pkg_fetch_exp
from cohezion.compound.executor_helpers import run_async_guardrail as pkg_run_guardrail
from cohezion.compound.executor_helpers import try_template_match as pkg_try_template
from cohezion.compound.executor_helpers.guardrail_runner import (
    run_async_guardrail as src_run_guardrail,
)
from cohezion.compound.executor_helpers.template_matcher import (
    try_template_match as src_try_template,
)
from cohezion.compound.executor_helpers.vault_integration import (
    fetch_experience_guidance as src_fetch_exp,
)

# exp_persistence
from cohezion.compound.exp_persistence import ExecutionContext as pkg_exec_ctx
from cohezion.compound.exp_persistence import JourneyPersistence as pkg_journey_pers
from cohezion.compound.exp_persistence import PersistenceAccumulator as pkg_pers_acc
from cohezion.compound.exp_persistence import VaultLogger as pkg_vault_logger
from cohezion.compound.exp_persistence import get_accumulator as pkg_get_acc
from cohezion.compound.exp_persistence import get_journey_persistence as pkg_get_journey
from cohezion.compound.exp_persistence import get_vault_logger as pkg_get_vault_logger
from cohezion.compound.exp_persistence.accumulator import (
    PersistenceAccumulator as src_pers_acc,
)
from cohezion.compound.exp_persistence.accumulator import get_accumulator as src_get_acc
from cohezion.compound.exp_persistence.journey import JourneyPersistence as src_journey_pers
from cohezion.compound.exp_persistence.journey import (
    get_journey_persistence as src_get_journey,
)
from cohezion.compound.exp_persistence.vault import ExecutionContext as src_exec_ctx
from cohezion.compound.exp_persistence.vault import VaultLogger as src_vault_logger
from cohezion.compound.exp_persistence.vault import get_vault_logger as src_get_vault_logger

# tdd_adversarial
from cohezion.compound.tdd_adversarial import AdversarialCritique as pkg_adv_critique
from cohezion.compound.tdd_adversarial import AdversarialRedTeamAgent as pkg_redteam
from cohezion.compound.tdd_adversarial import AdversarialReviewSystem as pkg_adv_review
from cohezion.compound.tdd_adversarial import PerspectiveState as pkg_perspective_state
from cohezion.compound.tdd_adversarial import ReviewFinding as pkg_review_finding
from cohezion.compound.tdd_adversarial import ReviewPerspective as pkg_review_perspective
from cohezion.compound.tdd_adversarial import ReviewSession as pkg_review_session
from cohezion.compound.tdd_adversarial import TDDAdversarialCoordinator as pkg_tdd_coord
from cohezion.compound.tdd_adversarial import TDDAdversarialState as pkg_tdd_state
from cohezion.compound.tdd_adversarial import TDDIntegration as pkg_tdd_integration
from cohezion.compound.tdd_adversarial import TDDState as pkg_tdd_state2
from cohezion.compound.tdd_adversarial import TestResult as pkg_test_result
from cohezion.compound.tdd_adversarial import TestStatus as pkg_test_status
from cohezion.compound.tdd_adversarial import TestType as pkg_test_type
from cohezion.compound.tdd_adversarial import (
    get_adversarial_review_system as pkg_get_adv_review,
)
from cohezion.compound.tdd_adversarial import (
    get_tdd_adversarial_coordinator as pkg_get_tdd_coord,
)
from cohezion.compound.tdd_adversarial import get_tdd_integration as pkg_get_tdd_int
from cohezion.compound.tdd_adversarial.adversarial_review import (
    AdversarialReviewSystem as src_adv_review,
)
from cohezion.compound.tdd_adversarial.adversarial_review import (
    PerspectiveState as src_perspective_state,
)
from cohezion.compound.tdd_adversarial.adversarial_review import (
    ReviewFinding as src_review_finding,
)
from cohezion.compound.tdd_adversarial.adversarial_review import (
    ReviewPerspective as src_review_perspective,
)
from cohezion.compound.tdd_adversarial.adversarial_review import (
    ReviewSession as src_review_session,
)
from cohezion.compound.tdd_adversarial.adversarial_review import (
    get_adversarial_review_system as src_get_adv_review,
)
from cohezion.compound.tdd_adversarial.adversarial_reviewer import (
    AdversarialCritique as src_adv_critique,
)
from cohezion.compound.tdd_adversarial.adversarial_reviewer import (
    AdversarialRedTeamAgent as src_redteam,
)
from cohezion.compound.tdd_adversarial.coordinator import (
    TDDAdversarialCoordinator as src_tdd_coord,
)
from cohezion.compound.tdd_adversarial.coordinator import (
    TDDAdversarialState as src_tdd_state,
)
from cohezion.compound.tdd_adversarial.coordinator import (
    get_tdd_adversarial_coordinator as src_get_tdd_coord,
)
from cohezion.compound.tdd_adversarial.tdd_integration import TDDIntegration as src_tdd_int
from cohezion.compound.tdd_adversarial.tdd_integration import TDDState as src_tdd_state2
from cohezion.compound.tdd_adversarial.tdd_integration import TestResult as src_test_result
from cohezion.compound.tdd_adversarial.tdd_integration import TestStatus as src_test_status
from cohezion.compound.tdd_adversarial.tdd_integration import TestType as src_test_type
from cohezion.compound.tdd_adversarial.tdd_integration import (
    get_tdd_integration as src_get_tdd_int,
)

# persistence
from cohezion.compound.persistence import PersistenceConfig as pkg_pers_cfg
from cohezion.compound.persistence import SessionPersister as pkg_session_pers
from cohezion.compound.persistence import SimplePersistence as pkg_simple_pers
from cohezion.compound.persistence import VaultPersister as pkg_vault_pers
from cohezion.compound.persistence.vault import PersistenceConfig as src_pers_cfg
from cohezion.compound.persistence.vault import SessionPersister as src_session_pers
from cohezion.compound.persistence.vault import SimplePersistence as src_simple_pers
from cohezion.compound.persistence.vault import VaultPersister as src_vault_pers

# skills
from cohezion.compound.skills import SelectorFeedbackRefiner as pkg_sel_refiner
from cohezion.compound.skills import SimpleSkills as pkg_simple_skills
from cohezion.compound.skills import SkillMatch as pkg_skill_match
from cohezion.compound.skills import SkillSelector as pkg_skill_selector
from cohezion.compound.skills.selector import SelectorFeedbackRefiner as src_sel_refiner
from cohezion.compound.skills.selector import SimpleSkills as src_simple_skills
from cohezion.compound.skills.selector import SkillMatch as src_skill_match
from cohezion.compound.skills.selector import SkillSelector as src_skill_selector


# ── analytics ────────────────────────────────────────────────────────────────


def test_analysis_config_is_same():
    assert pkg_analysis_cfg is src_analysis_cfg


def test_execution_analyzer_is_same():
    assert pkg_exec_analyzer is src_exec_analyzer


def test_simple_analyzer_is_same():
    assert pkg_simple_analyzer is src_simple_analyzer


def test_metrics_collector_is_same():
    assert pkg_metrics_collector is src_metrics_collector


def test_metrics_snapshot_is_same():
    assert pkg_metrics_snapshot is src_metrics_snapshot


def test_simple_metrics_is_same():
    assert pkg_simple_metrics is src_simple_metrics


# ── autonomous_loop ───────────────────────────────────────────────────────────


def test_loop_config_is_same():
    assert pkg_loop_cfg is src_loop_cfg


def test_loop_coordinator_is_same():
    assert pkg_loop_coord is src_loop_coord


def test_loop_task_is_same():
    assert pkg_loop_task is src_loop_task


def test_run_report_is_same():
    assert pkg_run_report is src_run_report


def test_sprint_result_is_same():
    assert pkg_sprint is src_sprint


def test_improvement_executor_is_same():
    assert pkg_imp_exec is src_imp_exec


def test_local_improvement_executor_is_same():
    assert pkg_local_exec is src_local_exec


def test_loop_tick_sweeper_is_same():
    assert pkg_tick_sweeper is src_tick_sweeper


def test_markov_quality_tracker_is_same():
    assert pkg_markov is src_markov


def test_challenger_agent_is_same():
    assert pkg_challenger is src_challenger


def test_episode_result_is_same():
    assert pkg_episode is src_episode


def test_rzero_challenger_executor_is_same():
    assert pkg_rzero is src_rzero


def test_solver_agent_is_same():
    assert pkg_solver is src_solver


def test_task_attempt_is_same():
    assert pkg_task_attempt is src_task_attempt


# ── core ─────────────────────────────────────────────────────────────────────


def test_batch_result_is_same():
    assert pkg_batch_result is src_batch_result


def test_batch_processor_is_same():
    assert pkg_batch_proc is src_batch_proc


def test_simple_batch_is_same():
    assert pkg_simple_batch is src_simple_batch


def test_execution_config_is_same():
    assert pkg_exec_cfg is src_exec_cfg


def test_core_compound_executor_is_same():
    assert pkg_core_executor is src_core_executor


def test_execute_simple_is_same():
    assert pkg_execute_simple is src_execute_simple


# ── executor_helpers ─────────────────────────────────────────────────────────


def test_run_async_guardrail_is_same():
    assert pkg_run_guardrail is src_run_guardrail


def test_try_template_match_is_same():
    assert pkg_try_template is src_try_template


def test_fetch_experience_guidance_is_same():
    assert pkg_fetch_exp is src_fetch_exp


# ── exp_persistence ───────────────────────────────────────────────────────────


def test_persistence_accumulator_is_same():
    assert pkg_pers_acc is src_pers_acc


def test_get_accumulator_is_same():
    assert pkg_get_acc is src_get_acc


def test_journey_persistence_is_same():
    assert pkg_journey_pers is src_journey_pers


def test_get_journey_persistence_is_same():
    assert pkg_get_journey is src_get_journey


def test_execution_context_is_same():
    assert pkg_exec_ctx is src_exec_ctx


def test_vault_logger_is_same():
    assert pkg_vault_logger is src_vault_logger


def test_get_vault_logger_is_same():
    assert pkg_get_vault_logger is src_get_vault_logger


# ── tdd_adversarial ───────────────────────────────────────────────────────────


def test_adversarial_review_system_is_same():
    assert pkg_adv_review is src_adv_review


def test_perspective_state_is_same():
    assert pkg_perspective_state is src_perspective_state


def test_review_finding_is_same():
    assert pkg_review_finding is src_review_finding


def test_review_perspective_is_same():
    assert pkg_review_perspective is src_review_perspective


def test_review_session_is_same():
    assert pkg_review_session is src_review_session


def test_get_adversarial_review_system_is_same():
    assert pkg_get_adv_review is src_get_adv_review


def test_adversarial_critique_is_same():
    assert pkg_adv_critique is src_adv_critique


def test_adversarial_red_team_agent_is_same():
    assert pkg_redteam is src_redteam


def test_tdd_adversarial_coordinator_is_same():
    assert pkg_tdd_coord is src_tdd_coord


def test_tdd_adversarial_state_is_same():
    assert pkg_tdd_state is src_tdd_state


def test_get_tdd_adversarial_coordinator_is_same():
    assert pkg_get_tdd_coord is src_get_tdd_coord


def test_tdd_integration_is_same():
    assert pkg_tdd_integration is src_tdd_int


def test_tdd_state_is_same():
    assert pkg_tdd_state2 is src_tdd_state2


def test_test_result_is_same():
    assert pkg_test_result is src_test_result


def test_test_status_is_same():
    assert pkg_test_status is src_test_status


def test_test_type_is_same():
    assert pkg_test_type is src_test_type


def test_get_tdd_integration_is_same():
    assert pkg_get_tdd_int is src_get_tdd_int


# ── persistence ───────────────────────────────────────────────────────────────


def test_persistence_config_is_same():
    assert pkg_pers_cfg is src_pers_cfg


def test_session_persister_is_same():
    assert pkg_session_pers is src_session_pers


def test_vault_persister_is_same():
    assert pkg_vault_pers is src_vault_pers


def test_simple_persistence_is_same():
    assert pkg_simple_pers is src_simple_pers


# ── skills ────────────────────────────────────────────────────────────────────


def test_skill_match_is_same():
    assert pkg_skill_match is src_skill_match


def test_skill_selector_is_same():
    assert pkg_skill_selector is src_skill_selector


def test_selector_feedback_refiner_is_same():
    assert pkg_sel_refiner is src_sel_refiner


def test_simple_skills_is_same():
    assert pkg_simple_skills is src_simple_skills
