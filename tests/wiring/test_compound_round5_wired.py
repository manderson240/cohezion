"""Discriminating identity tests: compound orphans wired in round-5 sweep (2026-06-22).

Modules confirmed as genuine import-graph orphans (0 production importers) before wiring:
behavioral_eval, eco_symphony, evolution_training_bridge, experiment_correlator,
harness, health, holographic_projection, intake_specialist, long_horizon_task,
plasma_theosophy_synthesizer, post_execution, recursive_challenger,
retrospection_summary, retrospection_validator, routing_feedback_loop,
skill_consensus_voter, skill_refinement_validator, tape_logger, task_queue,
thermal_predictor, universe_bridge, vault_search_executor, vector_pruning,
workflow_manager.
"""

from cohezion.compound import AgentVote as pkg_agent_vote
from cohezion.compound import BehaviorProperty as pkg_bp
from cohezion.compound import BehaviorTestResult as pkg_btr
from cohezion.compound import CompoundHealthReport as pkg_health_report
from cohezion.compound import CycleMetrics as pkg_cycle_metrics
from cohezion.compound import EvolutionTrainingConfig as pkg_etc
from cohezion.compound import GapReport as pkg_gap
from cohezion.compound import HarnessSynthesizer as pkg_harness
from cohezion.compound import ImprovementOpportunity as pkg_opp
from cohezion.compound import IntakeSpecialist as pkg_intake
from cohezion.compound import LongHorizonTask as pkg_lht
from cohezion.compound import OnboardingResult as pkg_onboard
from cohezion.compound import PlasmaTheosophySynthesizer as pkg_plasma
from cohezion.compound import PostExecutionOrchestrator as pkg_post_exec
from cohezion.compound import PruningReport as pkg_pruning
from cohezion.compound import QueuedTask as pkg_queued
from cohezion.compound import RecursiveChallenger as pkg_rc
from cohezion.compound import RefinementMetrics as pkg_ref_metrics
from cohezion.compound import RetrospectionSummary as pkg_retro_summary
from cohezion.compound import RetrospectionValidator as pkg_retro_val
from cohezion.compound import RoutingDecision as pkg_routing_dec
from cohezion.compound import RoutingDecisionType as pkg_routing_type
from cohezion.compound import RoutingMetrics as pkg_routing_metrics
from cohezion.compound import SearchQuery as pkg_sq
from cohezion.compound import SearchResult as pkg_sr
from cohezion.compound import SemanticVector as pkg_sv
from cohezion.compound import SkillHistoryResponse as pkg_skill_hist
from cohezion.compound import SkillRefinementValidator as pkg_srval
from cohezion.compound import TapeEntry as pkg_tape_entry
from cohezion.compound import TapeLogger as pkg_tape
from cohezion.compound import TaskPriority as pkg_task_prio
from cohezion.compound import ThermalMetrics as pkg_thermal_metrics
from cohezion.compound import UniverseBridge as pkg_ub
from cohezion.compound import VotingStrategy as pkg_vs
from cohezion.compound import WorkflowManager as pkg_wf
from cohezion.compound.behavioral_eval import BehaviorProperty as src_bp
from cohezion.compound.behavioral_eval import BehaviorTestResult as src_btr
from cohezion.compound.evolution_training_bridge import (
    EvolutionTrainingConfig as src_etc,
)
from cohezion.compound.harness import HarnessSynthesizer as src_harness
from cohezion.compound.health import CompoundHealthReport as src_health_report
from cohezion.compound.health import SkillHistoryResponse as src_skill_hist
from cohezion.compound.intake_specialist import IntakeSpecialist as src_intake
from cohezion.compound.long_horizon_task import LongHorizonTask as src_lht
from cohezion.compound.plasma_theosophy_synthesizer import (
    PlasmaTheosophySynthesizer as src_plasma,
)
from cohezion.compound.post_execution import PostExecutionOrchestrator as src_post_exec
from cohezion.compound.recursive_challenger import (
    ImprovementOpportunity as src_opp,
)
from cohezion.compound.recursive_challenger import RecursiveChallenger as src_rc
from cohezion.compound.retrospection_summary import CycleMetrics as src_cycle_metrics
from cohezion.compound.retrospection_summary import (
    RetrospectionSummary as src_retro_summary,
)
from cohezion.compound.retrospection_validator import (
    RetrospectionValidator as src_retro_val,
)
from cohezion.compound.routing_feedback_loop import RoutingDecision as src_routing_dec
from cohezion.compound.routing_feedback_loop import (
    RoutingDecisionType as src_routing_type,
)
from cohezion.compound.routing_feedback_loop import RoutingMetrics as src_routing_metrics
from cohezion.compound.skill_consensus_voter import AgentVote as src_agent_vote
from cohezion.compound.skill_consensus_voter import VotingStrategy as src_vs
from cohezion.compound.skill_refinement_validator import (
    RefinementMetrics as src_ref_metrics,
)
from cohezion.compound.skill_refinement_validator import (
    SkillRefinementValidator as src_srval,
)
from cohezion.compound.tape_logger import TapeEntry as src_tape_entry
from cohezion.compound.tape_logger import TapeLogger as src_tape
from cohezion.compound.task_queue import QueuedTask as src_queued
from cohezion.compound.task_queue import TaskPriority as src_task_prio
from cohezion.compound.thermal_predictor import ThermalMetrics as src_thermal_metrics
from cohezion.compound.universe_bridge import UniverseBridge as src_ub
from cohezion.compound.vault_search_executor import SearchQuery as src_sq
from cohezion.compound.vault_search_executor import SearchResult as src_sr
from cohezion.compound.vector_pruning import PruningReport as src_pruning
from cohezion.compound.vector_pruning import SemanticVector as src_sv
from cohezion.compound.workflow_manager import GapReport as src_gap
from cohezion.compound.workflow_manager import OnboardingResult as src_onboard
from cohezion.compound.workflow_manager import WorkflowManager as src_wf


# --- behavioral_eval ---


def test_behavior_property_is_same():
    assert pkg_bp is src_bp


def test_behavior_test_result_is_same():
    assert pkg_btr is src_btr


# --- health ---


def test_compound_health_report_is_same():
    assert pkg_health_report is src_health_report


def test_skill_history_response_is_same():
    assert pkg_skill_hist is src_skill_hist


# --- tape_logger ---


def test_tape_entry_is_same():
    assert pkg_tape_entry is src_tape_entry


def test_tape_logger_is_same():
    assert pkg_tape is src_tape


# --- recursive_challenger ---


def test_improvement_opportunity_is_same():
    assert pkg_opp is src_opp


def test_recursive_challenger_is_same():
    assert pkg_rc is src_rc


# --- workflow_manager ---


def test_workflow_manager_is_same():
    assert pkg_wf is src_wf


def test_gap_report_is_same():
    assert pkg_gap is src_gap


def test_onboarding_result_is_same():
    assert pkg_onboard is src_onboard


# --- routing_feedback_loop ---


def test_routing_decision_is_same():
    assert pkg_routing_dec is src_routing_dec


def test_routing_decision_type_is_same():
    assert pkg_routing_type is src_routing_type


def test_routing_metrics_is_same():
    assert pkg_routing_metrics is src_routing_metrics


# --- skill_consensus_voter ---


def test_voting_strategy_is_same():
    assert pkg_vs is src_vs


def test_agent_vote_is_same():
    assert pkg_agent_vote is src_agent_vote


# --- skill_refinement_validator ---


def test_refinement_metrics_is_same():
    assert pkg_ref_metrics is src_ref_metrics


def test_skill_refinement_validator_is_same():
    assert pkg_srval is src_srval


# --- task_queue ---


def test_task_priority_is_same():
    assert pkg_task_prio is src_task_prio


def test_queued_task_is_same():
    assert pkg_queued is src_queued


# --- universe_bridge ---


def test_universe_bridge_is_same():
    assert pkg_ub is src_ub


# --- vault_search_executor ---


def test_search_query_is_same():
    assert pkg_sq is src_sq


def test_search_result_is_same():
    assert pkg_sr is src_sr


# --- vector_pruning ---


def test_semantic_vector_is_same():
    assert pkg_sv is src_sv


def test_pruning_report_is_same():
    assert pkg_pruning is src_pruning


# --- thermal_predictor ---


def test_thermal_metrics_is_same():
    assert pkg_thermal_metrics is src_thermal_metrics


# --- retrospection_summary ---


def test_cycle_metrics_is_same():
    assert pkg_cycle_metrics is src_cycle_metrics


def test_retrospection_summary_is_same():
    assert pkg_retro_summary is src_retro_summary


# --- retrospection_validator ---


def test_retrospection_validator_is_same():
    assert pkg_retro_val is src_retro_val


# --- post_execution ---


def test_post_execution_orchestrator_is_same():
    assert pkg_post_exec is src_post_exec


# --- plasma_theosophy_synthesizer ---


def test_plasma_theosophy_synthesizer_is_same():
    assert pkg_plasma is src_plasma


# --- long_horizon_task ---


def test_long_horizon_task_is_same():
    assert pkg_lht is src_lht


# --- intake_specialist ---


def test_intake_specialist_is_same():
    assert pkg_intake is src_intake


# --- harness ---


def test_harness_synthesizer_is_same():
    assert pkg_harness is src_harness


# --- evolution_training_bridge ---


def test_evolution_training_config_is_same():
    assert pkg_etc is src_etc
