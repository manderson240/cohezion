"""Discriminating tests for the lemond admission gate (2026-09-01).

The 08-31 double-freeze trigger was lemond AUTO-LOADING a 35B model into 10.4 GB of
headroom — no admission control exists in the router, its own config caps counts (not
bytes) and is ephemeral. The gate is a thin proxy that takes :13305 (clients unchanged),
forwards to lemond on an internal port, and refuses requests that would trigger a load
the box cannot afford.

The three anchor tests came from a 3-lane ollama-cloud council (2026-09-01, logged in
vault research/20260831-ollama-cloud-council-oom-next-steps.md):
  1. Uncapped-Window / TOCTOU (glm): the gate must enforce from the FIRST request —
     a wrong impl with lazy warm-up (pass-through until state is initialized) fails.
  2. Cold-Boot Cap Persistence (deepseek): gate parameters come from persisted config
     re-read at every construction — a wrong impl carrying caps in mutable runtime
     state loses them on restart.
  3. Direct-to-Backend Bypass (gemma4): lemond's spawned backends (:8002...) are
     reachable around the proxy — an impl claiming full enforcement lies; the gate must
     AUDIT and surface bypass paths explicitly.

Plus the incident-derived rule the council could not know: the 08-31 killer was an
FLM/NPU model, so 'NPU is always safe' is falsified AS A GATE RULE — below the hard
floor, ALL non-resident loads are refused regardless of tier.
"""

from __future__ import annotations

from unittest.mock import patch

from cohezion.platform.admission_gate import (
    AdmissionGate,
    GateConfig,
    audit_bypass_paths,
)


def _entries(names: list[str]) -> list[dict[str, object]]:
    return [{"model_name": n, "checkpoint": ""} for n in names]


def _gate(
    floor_gb: float = 16.0,
    available_gb: float = 50.0,
    resident: list[str] | None = None,
    enforce: bool = True,
) -> AdmissionGate:
    cfg = GateConfig(floor_gb=floor_gb, enforce=enforce)
    return AdmissionGate(
        config=cfg,
        read_available_gb=lambda: available_gb,
        read_resident=lambda: _entries(resident) if resident is not None else None,
    )


class TestHardFloor:
    def test_below_floor_refuses_any_nonresident_load_even_npu(self) -> None:
        # THE 08-31 crash in one test: 10.4 GB available, an FLM/NPU 35B requested.
        # check_oom_risk clears NPU models (SRAM reasoning) — the box died anyway.
        # Below the floor the gate refuses EVERYTHING non-resident, tier-blind.
        g = _gate(available_gb=10.4, resident=[])
        d = g.decide("qwen3.6-moe-35b-a3b-FLM")
        assert d.allow is False
        assert "floor" in d.reason.lower()

    def test_above_floor_npu_model_budget_checked_not_waved(self) -> None:
        # Post-08-31 the gate budget-checks FLM/NPU models against a REAL footprint
        # (npu_exempt=False): a small FLM passes with ample headroom...
        with patch("cohezion.compound.oom_guard._catalog_size_gb", return_value=1.3):
            g = _gate(available_gb=50.0, resident=[])
            assert g.decide("deepseek-r1-0528-8b-FLM").allow is True
        # ...and a large FLM MoE is REFUSED when its resolved footprint busts the
        # budget — the wrong impl (unconditional NPU pass) forwards it, which is
        # literally the 08-31 crash above the floor.
        with patch("cohezion.compound.oom_guard._catalog_size_gb", return_value=20.0):
            g = _gate(available_gb=18.0, resident=[])
            assert g.decide("qwen3.6-moe-35b-a3b-FLM").allow is False

    def test_resident_model_allowed_even_below_floor(self) -> None:
        # Reuse needs no new memory — blocking a resident model deadlocks the queue
        # (the 2026-07-19 lesson already encoded in check_oom_risk).
        g = _gate(available_gb=10.4, resident=["Bonsai-8B-gguf"])
        assert g.decide("Bonsai-8B-gguf").allow is True


class TestByteBudget:
    def test_heavy_model_refused_when_budget_insufficient(self) -> None:
        # Above the floor but the 23.3 GB model + 8 GB buffer exceeds 20 GB available.
        g = _gate(available_gb=20.0, resident=[])
        d = g.decide("Qwen3.6-35B-A3B-GGUF")
        assert d.allow is False

    def test_heavy_model_allowed_with_ample_headroom(self) -> None:
        g = _gate(available_gb=60.0, resident=[])
        assert g.decide("Qwen3.6-35B-A3B-GGUF").allow is True

    def test_unknown_model_gated_conservatively(self) -> None:
        # Unknown never reads as 0 GB — the .get(name, 0.0) class stays dead.
        with patch("cohezion.compound.oom_guard._catalog_size_gb", return_value=None):
            g = _gate(available_gb=12.0, resident=[])
            assert g.decide("brand-new-mystery-70b").allow is False


class TestResidencyMatching:
    def test_checkpoint_style_name_matches_resident_entry(self) -> None:
        # HIGH-2 regression (adversarial review 2026-09-01): health reports checkpoint
        # 'unsloth/Bonsai-8B-gguf:Q4_K_M' while the client sends 'Bonsai-8B-gguf'.
        # An exact-string residency check reads it non-resident and REFUSES it below
        # floor — a 503 on a request needing zero new memory, during pressure.
        entries = [{"model_name": "bonsai-8b", "checkpoint": "unsloth/Bonsai-8B-gguf:Q4_K_M"}]
        g = AdmissionGate(
            config=GateConfig(floor_gb=16.0),
            read_available_gb=lambda: 10.4,
            read_resident=lambda: entries,
        )
        assert g.decide("Bonsai-8B-gguf").allow is True

    def test_case_variant_of_resident_id_matches(self) -> None:
        entries = [{"model_name": "Bonsai-8B-gguf", "checkpoint": ""}]
        g = AdmissionGate(
            config=GateConfig(floor_gb=16.0),
            read_available_gb=lambda: 10.4,
            read_resident=lambda: entries,
        )
        assert g.decide("bonsai-8b-GGUF").allow is True

    def test_available_gb_is_passed_not_reread(self) -> None:
        # An impl dropping the kwarg lets check_oom_risk re-read real /proc — tests
        # would then pass or fail with the HOST's memory. Pin the plumbing.
        with patch("cohezion.platform.admission_gate.check_oom_risk") as m:
            m.return_value = type("R", (), {"safe": True, "reason": "ok"})()
            g = _gate(available_gb=33.3, resident=[])
            g.decide("Qwen3.6-35B-A3B-GGUF")
        assert m.call_args.kwargs["available_gb"] == 33.3
        assert m.call_args.kwargs["npu_exempt"] is False


class TestCouncilTest1UncappedWindow:
    def test_gate_enforces_from_the_first_request(self) -> None:
        # glm's TOCTOU test: no warm-up gap. A wrong impl that passes through until
        # some lazy state initializes admits the over-cap load in the listen->cap gap.
        # A FRESHLY constructed gate must refuse immediately — no prior calls needed.
        g = _gate(available_gb=10.4, resident=[])
        assert g.decide("Qwen3.6-35B-A3B-GGUF").allow is False  # request #1, no warm-up

    def test_residency_unreadable_is_not_a_pass(self) -> None:
        # During a real emergency the health endpoint blocks (residency unknowable).
        # 'Cannot see' must mean 'assume non-resident', never 'wave through'.
        g = _gate(available_gb=10.4, resident=None)  # None = health blocked
        assert g.decide("Bonsai-8B-gguf").allow is False


class TestCouncilTest2ColdBootPersistence:
    def test_config_rereads_environment_on_every_construction(self) -> None:
        # deepseek's persistence test, unit-scale: caps come from the environment
        # (persisted by the systemd unit), re-read at each construction — never from
        # state mutated at runtime.
        with patch.dict("os.environ", {"COHEZION_ADMISSION_FLOOR_GB": "24.0"}):
            assert GateConfig.from_env().floor_gb == 24.0
        with patch.dict("os.environ", {}, clear=False):
            import os

            os.environ.pop("COHEZION_ADMISSION_FLOOR_GB", None)
            assert GateConfig.from_env().floor_gb == 16.0  # default restored

    def test_runtime_mutation_cannot_survive_reconstruction(self) -> None:
        # GateConfig is frozen: the wrong impl (mutable cap twiddled via an admin
        # endpoint, lost or half-kept on restart) cannot exist.
        import dataclasses

        cfg = GateConfig(floor_gb=16.0)
        try:
            cfg.floor_gb = 0.0  # type: ignore[misc]
            mutated = True
        except dataclasses.FrozenInstanceError:
            mutated = False
        assert mutated is False


class TestCouncilTest3BypassAudit:
    def test_audit_surfaces_backend_ports_as_bypass_paths(self) -> None:
        # gemma4's test: lemond spawns per-model llama-servers whose ports are
        # reachable AROUND the proxy. An implementation claiming full enforcement
        # lies; the gate must name its bypass paths.
        health = [
            {"model_name": "Bonsai-8B-gguf", "backend_url": "http://127.0.0.1:8002/v1"},
            {
                "model_name": "nomic-embed-text-v2-moe-GGUF",
                "backend_url": "http://127.0.0.1:8003/v1",
            },
            {"model_name": "kokoro-v1", "backend_url": ""},
        ]
        paths = audit_bypass_paths(loaded=health)
        assert "http://127.0.0.1:8002/v1" in paths
        assert "http://127.0.0.1:8003/v1" in paths
        assert len(paths) == 2  # empty backend_url is not a path

    def test_audit_unreadable_health_reports_unknown_not_empty(self) -> None:
        # 'No bypass paths found' and 'could not look' are different answers.
        assert audit_bypass_paths(loaded=None) is None


class TestEnforceKillSwitch:
    def test_enforce_false_logs_but_allows(self) -> None:
        # Shadow mode for the cutover: decisions computed (observable) but not applied.
        g = _gate(available_gb=10.4, resident=[], enforce=False)
        d = g.decide("Qwen3.6-35B-A3B-GGUF")
        assert d.allow is True
        assert d.would_refuse is True  # the decision is still visible for telemetry

    def test_enforcing_gate_marks_would_refuse_consistently(self) -> None:
        g = _gate(available_gb=10.4, resident=[])
        d = g.decide("Qwen3.6-35B-A3B-GGUF")
        assert d.allow is False and d.would_refuse is True


class TestRequestClassification:
    def test_no_model_in_request_is_allowed(self) -> None:
        # GETs, health checks, and bodies without a model field never gate.
        g = _gate(available_gb=5.0, resident=[])
        assert g.decide(None).allow is True

    def test_meminfo_read_failure_fails_open_with_flag(self) -> None:
        # If /proc/meminfo itself is unreadable we cannot reason about memory at all;
        # refuse-everything would take the whole fleet down on a proc hiccup. Fail
        # open but mark it, so telemetry can see the gate flying blind.
        cfg = GateConfig(floor_gb=16.0)

        def boom() -> float:
            raise OSError("meminfo unreadable")

        g = AdmissionGate(config=cfg, read_available_gb=boom, read_resident=lambda: [])
        d = g.decide("Qwen3.6-35B-A3B-GGUF")
        assert d.allow is True
        assert "blind" in d.reason.lower() or "unreadable" in d.reason.lower()

    def test_blind_path_reachable_with_production_reader(self) -> None:
        # HIGH-1 regression (adversarial review 2026-09-01): the DEFAULT reader must
        # RAISE on /proc failure. oom_guard's MemorySnapshot.capture fabricates 20 GB
        # on any exception — above the floor — so wiring it as the default made the
        # blind path dead code and silently approved loads on zero information. This
        # test constructs the gate with NO injected reader and breaks /proc.
        g = AdmissionGate(config=GateConfig(floor_gb=16.0), read_resident=lambda: [])
        with patch(
            "cohezion.platform.admission_gate.pathlib.Path.read_text",
            side_effect=OSError("proc gone"),
        ):
            d = g.decide("Qwen3.6-35B-A3B-GGUF")
        assert d.allow is True
        assert "blind" in d.reason.lower()
