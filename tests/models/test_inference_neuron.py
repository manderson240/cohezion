"""Discriminating tests for inference→neuron deposition (2026-06-06, item 15).

Makes "local inference forms new neurons" literal: a REWARDED routing decision deposits a
neuron into the EXISTING neurons table (country='inference'). Each test fails a plausible
wrong impl:
  - one that deposits a neuron for a FELL_BACK (un-rewarded) decision (neurons must form only
    on success — the Knower-only-on-accept rule, harness P5),
  - one that writes to the real graph during pytest,
  - one that mislabels the neuron's country (must be 'inference', the new region),
  - one whose deposited neuron can't be round-tripped back out of the store.
"""

from __future__ import annotations

from cohezion.models.routing_log import (
    build_inference_neuron,
    deposit_inference_neuron,
)


def test_build_neuron_is_inference_country_and_carries_model() -> None:
    n = build_inference_neuron("EXTRACTION", "LFM2.5-VL", "igpu_rocwmma", reward=1.0)
    assert n["country"] == "inference"  # the new region, not 'cerebellum'
    assert "LFM2.5-VL" in n["content"]
    assert "EXTRACTION" in n["name"]


def test_rewarded_decision_deposits_a_neuron() -> None:
    store: list[dict] = []
    rec = {
        "task_class": "EXTRACTION",
        "chosen_model": "LFM2.5-VL",
        "lane": "igpu",
        "fell_back": False,
    }
    n = deposit_inference_neuron(rec, store=store)
    assert n is not None and n["country"] == "inference"
    assert len(store) == 1 and store[0]["name"] == n["name"]


def test_fell_back_decision_deposits_nothing() -> None:
    # A fallback is NOT a reward — no neuron forms (success-only growth).
    store: list[dict] = []
    rec = {
        "task_class": "EXTRACTION",
        "chosen_model": "router-model",
        "lane": "",
        "fell_back": True,
    }
    assert deposit_inference_neuron(rec, store=store) is None
    assert store == []


def test_no_model_deposits_nothing() -> None:
    store: list[dict] = []
    rec = {"task_class": "EXTRACTION", "chosen_model": None, "lane": "", "fell_back": False}
    assert deposit_inference_neuron(rec, store=store) is None
    assert store == []


def test_pytest_run_writes_nothing_to_the_real_graph() -> None:
    # No store + under pytest → must NOT write to the real SurrealDB neurons table.
    rec = {"task_class": "EXTRACTION", "chosen_model": "m", "lane": "", "fell_back": False}
    assert deposit_inference_neuron(rec) is None


def test_deposited_neuron_round_trips_from_store() -> None:
    store: list[dict] = []
    for tc, m in [("EXTRACTION", "LFM"), ("ROUTING", "llama-1b")]:
        deposit_inference_neuron(
            {"task_class": tc, "chosen_model": m, "lane": "x", "fell_back": False}, store=store
        )
    found = [n for n in store if "ROUTING" in n["name"]]
    assert len(found) == 1 and "llama-1b" in found[0]["content"]
