"""Coverage batch Z29: brand service, plasma_swarm_router, skills service, triune_engine, api_key_auth extras."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import torch


# ---------------------------------------------------------------------------
# Module 1: api/services/brand.py
# ---------------------------------------------------------------------------


class TestBrandService:
    def test_get_brand_theme_returns_brand_theme_response(self):
        from cohezion.api.services.brand import BrandThemeResponse, get_brand_theme

        result = asyncio.run(get_brand_theme())
        assert isinstance(result, BrandThemeResponse)

    def test_get_brand_theme_colors_are_strings(self):
        from cohezion.api.services.brand import get_brand_theme

        result = asyncio.run(get_brand_theme())
        assert isinstance(result.colors.nexus_green, str)
        assert result.colors.nexus_green.startswith("#")

    def test_get_brand_theme_identity_name(self):
        from cohezion.api.services.brand import get_brand_theme

        result = asyncio.run(get_brand_theme())
        assert result.identity.name == "COHEZION"

    def test_get_brand_theme_hiho_palette_colors(self):
        from cohezion.api.services.brand import get_brand_theme

        result = asyncio.run(get_brand_theme())
        # stable should map to nexus_green
        assert result.hiho_palette.stable == result.colors.nexus_green
        assert result.hiho_palette.warning == result.colors.warning_gold

    def test_brand_colors_model_fields(self):
        from cohezion.api.services.brand import BrandColors

        c = BrandColors(
            nexus_green="#00FF00",
            matte_black="#000000",
            silicon_silver="#AAAAAA",
            earth_blue="#0000FF",
            critical_red="#FF0000",
            warning_gold="#FFD700",
            plasma_blue="#0088FF",
            neon_cyan="#00FFFF",
        )
        assert c.nexus_green == "#00FF00"

    def test_hiho_palette_model_fields(self):
        from cohezion.api.services.brand import HIHOPalette

        p = HIHOPalette(
            critical_low="#FF0000",
            warning="#FFD700",
            stable="#00FF00",
            critical_high="#0000FF",
        )
        assert p.stable == "#00FF00"

    def test_brand_identity_model_fields(self):
        from cohezion.api.services.brand import BrandIdentity

        i = BrandIdentity(name="TEST", tagline="tag", philosophy="phi", sign_off="bye")
        assert i.name == "TEST"


# ---------------------------------------------------------------------------
# Module 2: swarm/plasma_swarm_router.py
# ---------------------------------------------------------------------------


class TestPlasmaSwarmRouter:
    @pytest.fixture(autouse=True)
    def _mock_dependencies(self):
        with (
            patch("cohezion.swarm.plasma_swarm_router.DynamicModelRouter") as mock_router_cls,
            patch("cohezion.swarm.plasma_swarm_router.get_circuit") as mock_circuit_fn,
        ):
            self.mock_router = MagicMock()
            self.mock_router.execute_request = AsyncMock(
                return_value={"result": {"text": "Toroidal formation at L4"}}
            )
            mock_router_cls.return_value = self.mock_router

            self.mock_circuit = MagicMock()
            self.mock_circuit.allow_request.return_value = True
            mock_circuit_fn.return_value = self.mock_circuit
            yield

    def test_evo_topology_request_model(self):
        from cohezion.swarm.plasma_swarm_router import EvoTopologyRequest

        req = EvoTopologyRequest(fohatic_impulse=0.7, swarm_size=12, plasma_viscosity=0.3)
        assert req.fohatic_impulse == pytest.approx(0.7)
        assert req.swarm_size == 12

    def test_evo_topology_request_defaults(self):
        from cohezion.swarm.plasma_swarm_router import EvoTopologyRequest

        req = EvoTopologyRequest(fohatic_impulse=0.5)
        assert req.swarm_size == 8
        assert req.plasma_viscosity == pytest.approx(0.5)

    def test_predict_topology_returns_string(self):
        from cohezion.swarm.plasma_swarm_router import EvoTopologyRequest, PlasmaSwarmRouter

        router = PlasmaSwarmRouter()
        req = EvoTopologyRequest(fohatic_impulse=0.7)
        result = asyncio.run(router.predict_topology(req))
        assert isinstance(result, str)

    def test_predict_topology_calls_execute_request(self):
        from cohezion.swarm.plasma_swarm_router import EvoTopologyRequest, PlasmaSwarmRouter

        router = PlasmaSwarmRouter()
        asyncio.run(router.predict_topology(EvoTopologyRequest(fohatic_impulse=0.5)))
        self.mock_router.execute_request.assert_awaited_once()

    def test_predict_topology_records_circuit_success(self):
        from cohezion.swarm.plasma_swarm_router import EvoTopologyRequest, PlasmaSwarmRouter

        router = PlasmaSwarmRouter()
        asyncio.run(router.predict_topology(EvoTopologyRequest(fohatic_impulse=0.5)))
        self.mock_circuit.record_success.assert_called_once()

    def test_predict_topology_circuit_open_returns_message(self):
        self.mock_circuit.allow_request.return_value = False
        from cohezion.swarm.plasma_swarm_router import EvoTopologyRequest, PlasmaSwarmRouter

        router = PlasmaSwarmRouter()
        result = asyncio.run(router.predict_topology(EvoTopologyRequest(fohatic_impulse=0.3)))
        assert "Circuit open" in result

    def test_predict_topology_exception_records_failure(self):
        self.mock_router.execute_request = AsyncMock(side_effect=RuntimeError("router down"))
        from cohezion.swarm.plasma_swarm_router import EvoTopologyRequest, PlasmaSwarmRouter

        router = PlasmaSwarmRouter()
        result = asyncio.run(router.predict_topology(EvoTopologyRequest(fohatic_impulse=0.5)))
        self.mock_circuit.record_failure.assert_called_once()
        assert "Prediction failed" in result

    def test_predict_topology_non_dict_result(self):
        self.mock_router.execute_request = AsyncMock(return_value={"result": "plain string"})
        from cohezion.swarm.plasma_swarm_router import EvoTopologyRequest, PlasmaSwarmRouter

        router = PlasmaSwarmRouter()
        result = asyncio.run(router.predict_topology(EvoTopologyRequest(fohatic_impulse=0.5)))
        assert result == "No topology generated."


# ---------------------------------------------------------------------------
# Module 3: api/services/skills.py
# ---------------------------------------------------------------------------


class TestSkillsService:
    def test_template_parse_request_model(self):
        from cohezion.api.services.skills import TemplateParseRequest

        req = TemplateParseRequest(skill_name="VAULT_KEEPER")
        assert req.skill_name == "VAULT_KEEPER"

    def test_parse_template_service_happy_path(self):
        from cohezion.api.services.skills import TemplateParseRequest, parse_template_service

        mock_spec = MagicMock()
        mock_spec.name = "vault_keeper"
        mock_spec.domain_expertise = "Memory management"
        mock_spec.concepts = {"concept": "value"}
        mock_spec.instructions = ["step 1", "step 2"]
        mock_spec.version = "v1.0"
        mock_spec.see_also = []

        mock_engine = MagicMock()
        mock_engine.get_spec_by_name.return_value = mock_spec
        mock_engine.generate_agent_stub.return_value = "class VaultKeeper: pass"
        mock_engine.generate_config_class.return_value = "class Config: pass"

        mock_manager = MagicMock()
        mock_manager.engine = mock_engine

        # ConfigTemplateManager is lazily imported inside the function
        with patch(
            "cohezion.core.config_templates.ConfigTemplateManager", return_value=mock_manager
        ):
            req = TemplateParseRequest(skill_name="VAULT_KEEPER")
            response = asyncio.run(parse_template_service(req))
        assert response.name == "vault_keeper"
        assert response.version == "v1.0"

    def test_parse_template_service_raises_404_when_not_found(self):
        from fastapi import HTTPException

        from cohezion.api.services.skills import TemplateParseRequest, parse_template_service

        mock_engine = MagicMock()
        mock_engine.get_spec_by_name.return_value = None
        mock_manager = MagicMock()
        mock_manager.engine = mock_engine

        with patch(
            "cohezion.core.config_templates.ConfigTemplateManager", return_value=mock_manager
        ):
            req = TemplateParseRequest(skill_name="NONEXISTENT")
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(parse_template_service(req))
        assert exc_info.value.status_code == 404

    def test_parse_template_service_raises_500_on_engine_error(self):
        from fastapi import HTTPException

        from cohezion.api.services.skills import TemplateParseRequest, parse_template_service

        mock_engine = MagicMock()
        mock_engine.get_spec_by_name.side_effect = RuntimeError("engine failed")
        mock_manager = MagicMock()
        mock_manager.engine = mock_engine

        with patch(
            "cohezion.core.config_templates.ConfigTemplateManager", return_value=mock_manager
        ):
            req = TemplateParseRequest(skill_name="ANY_SKILL")
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(parse_template_service(req))
        assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# Module 4: universe/triune_engine.py
# ---------------------------------------------------------------------------


def _make_engine():
    from cohezion.universe.triune_engine import TriuneSimulationEngine
    from cohezion.universe.triune_manifold import TriuneState

    state = TriuneState(doer=torch.zeros(12), thinker=torch.zeros(512), knower=torch.zeros(2048))
    mock_surreal = MagicMock()
    mock_surreal.log_trajectory = AsyncMock()
    mock_obsidian = MagicMock()
    mock_obsidian.store_state_summary = AsyncMock()
    engine = TriuneSimulationEngine(
        state=state, surreal_logger=mock_surreal, obsidian_mcp=mock_obsidian
    )
    return engine, mock_surreal, mock_obsidian


class TestTriuneSimulationEngine:
    def test_step_calls_surreal_logger(self):
        engine, mock_surreal, _ = _make_engine()
        env = torch.randn(12)
        asyncio.run(engine.step(0.01, env, "traj-1"))
        mock_surreal.log_trajectory.assert_awaited_once()

    def test_step_calls_obsidian_mcp(self):
        engine, _, mock_obsidian = _make_engine()
        env = torch.randn(12)
        asyncio.run(engine.step(0.01, env, "traj-2"))
        mock_obsidian.store_state_summary.assert_awaited_once()

    def test_step_updates_doer_state(self):
        from cohezion.universe.triune_manifold import TriuneState

        # Use non-zero doer so coherence != 0.5 → non-zero restoring force
        state = TriuneState(
            doer=torch.ones(12),
            thinker=torch.zeros(512),
            knower=torch.zeros(2048),
        )
        mock_surreal = MagicMock()
        mock_surreal.log_trajectory = AsyncMock()
        mock_obsidian = MagicMock()
        mock_obsidian.store_state_summary = AsyncMock()
        from cohezion.universe.triune_engine import TriuneSimulationEngine

        engine = TriuneSimulationEngine(
            state=state, surreal_logger=mock_surreal, obsidian_mcp=mock_obsidian
        )

        initial_doer = engine.state.doer.clone()
        # env=full(-1) → cosine_sim=-1.0 → coherence=0.0 → force=(0.5-0.0)*0.1=0.05 (non-zero)
        env = torch.full((12,), -1.0)
        asyncio.run(engine.step(0.5, env, "traj-3"))
        # Doer should have moved toward env
        assert not torch.allclose(engine.state.doer, initial_doer)

    def test_step_handles_persistence_failure_gracefully(self):
        engine, mock_surreal, _ = _make_engine()
        mock_surreal.log_trajectory = AsyncMock(side_effect=RuntimeError("DB down"))
        # Should not raise — persistence failure is non-fatal
        asyncio.run(engine.step(0.01, torch.randn(12), "traj-fail"))

    def test_inject_patch_with_number_nudges_thinker(self):
        engine, _, mock_obsidian = _make_engine()
        asyncio.run(engine.inject_patch("adjust by 0.75"))
        # thinker[0] should be set to 0.75
        assert engine.state.thinker[0].item() == pytest.approx(0.75)
        mock_obsidian.store_state_summary.assert_awaited_once()

    def test_inject_patch_without_number_does_not_modify_thinker(self):
        engine, _, mock_obsidian = _make_engine()
        initial_thinker = engine.state.thinker.clone()
        asyncio.run(engine.inject_patch("stabilize the system now"))
        # No regex match → thinker unchanged
        assert torch.allclose(engine.state.thinker, initial_thinker)
        mock_obsidian.store_state_summary.assert_awaited_once()
