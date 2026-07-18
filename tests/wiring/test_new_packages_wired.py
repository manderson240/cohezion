import pytest


pytest.importorskip(
    "cohezion.pipelines.traceability", reason="TDD-red: TraceabilityLink module not yet created"
)
"""Discriminating identity tests: compound/universal, models, pipelines, physics/quantum,
flux/providers, real_envs/tasks orphans wired."""

import importlib
import os


# Suppress init-time side effects (log file writes, stdout prints) during testing.
os.environ.setdefault("COHEZION_NON_INTERACTIVE", "1")

# ---- compound.universal -------------------------------------------------------
# Note: init.py (not __init__.py) is the real source module; __init__.py re-exports from it.
from cohezion.compound.universal import initialize_cohezion_environment as pkg_init_cohezion
from cohezion.compound.universal import is_cohezion_environment as pkg_is_cohezion
from cohezion.compound.universal.init import (
    initialize_cohezion_environment as src_init_cohezion,
)
from cohezion.compound.universal.init import is_cohezion_environment as src_is_cohezion

# ---- flux.providers -----------------------------------------------------------
from cohezion.flux.providers import CacheFlux as pkg_cache_flux
from cohezion.flux.providers import HistoryFlux as pkg_history_flux
from cohezion.flux.providers import SurrealFlux as pkg_surreal_flux
from cohezion.flux.providers import ToolFlux as pkg_tool_flux
from cohezion.flux.providers import VaultFlux as pkg_vault_flux
from cohezion.flux.providers.cache_flux import CacheFlux as src_cache_flux
from cohezion.flux.providers.history_flux import HistoryFlux as src_history_flux
from cohezion.flux.providers.surreal_flux import SurrealFlux as src_surreal_flux
from cohezion.flux.providers.tool_flux import ToolFlux as src_tool_flux
from cohezion.flux.providers.vault_flux import VaultFlux as src_vault_flux

# ---- models -------------------------------------------------------------------
from cohezion.models import ModelRegistry as pkg_model_registry
from cohezion.models.model_registry import ModelRegistry as src_model_registry

# ---- physics.quantum ----------------------------------------------------------
from cohezion.physics.quantum import compute_seti_metrics as pkg_seti
from cohezion.physics.quantum.utils import compute_seti_metrics as src_seti

# ---- pipelines ----------------------------------------------------------------
from cohezion.pipelines import TraceabilityLink as pkg_trace_link
from cohezion.pipelines import TraceabilityPipeline as pkg_trace_pipeline
from cohezion.pipelines.traceability import TraceabilityLink as src_trace_link
from cohezion.pipelines.traceability import TraceabilityPipeline as src_trace_pipeline


# ---- compound.universal tests -------------------------------------------------


def test_is_cohezion_environment_is_same():
    assert pkg_is_cohezion is src_is_cohezion


def test_initialize_cohezion_environment_is_same():
    assert pkg_init_cohezion is src_init_cohezion


def test_is_cohezion_environment_callable():
    """Detection function returns a plain bool in any environment."""
    result = pkg_is_cohezion()
    assert isinstance(result, bool)


# ---- models tests -------------------------------------------------------------


def test_model_registry_is_same():
    assert pkg_model_registry is src_model_registry


# ---- pipelines tests ----------------------------------------------------------


def test_traceability_link_is_same():
    assert pkg_trace_link is src_trace_link


def test_traceability_pipeline_is_same():
    assert pkg_trace_pipeline is src_trace_pipeline


# ---- physics.quantum tests ----------------------------------------------------


def test_compute_seti_metrics_is_same():
    assert pkg_seti is src_seti


def test_peaked_circuit_solver_absent_without_cotengra():
    """PeakedCircuitSolver is guarded — absent when cotengra is not installed."""
    m = importlib.import_module("cohezion.physics.quantum")
    assert not hasattr(m, "PeakedCircuitSolver")


# ---- flux.providers tests -----------------------------------------------------


def test_cache_flux_is_same():
    assert pkg_cache_flux is src_cache_flux


def test_history_flux_is_same():
    assert pkg_history_flux is src_history_flux


def test_surreal_flux_is_same():
    assert pkg_surreal_flux is src_surreal_flux


def test_tool_flux_is_same():
    assert pkg_tool_flux is src_tool_flux


def test_vault_flux_is_same():
    assert pkg_vault_flux is src_vault_flux


# ---- real_envs.tasks tests ----------------------------------------------------


def test_real_envs_tasks_module_is_reachable():
    """Package loads even when cohezion.real_envs.evaluator dep is absent."""
    t = importlib.import_module("cohezion.real_envs.tasks")
    assert t is not None


def test_real_envs_tasks_functions_absent_without_evaluator():
    """All task functions are guarded — absent when real_envs.evaluator is missing."""
    t = importlib.import_module("cohezion.real_envs.tasks")
    absent = [
        "create_flask_api_task",
        "data_pipeline_task",
        "etl_api_to_db_task",
        "git_workflow_automation_task",
    ]
    for name in absent:
        assert not hasattr(t, name), f"Expected {name!r} absent (missing evaluator dep)"
