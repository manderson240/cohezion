"""Unit tests for Janelia Male CNS Connectome integration.

Validates the Janelia neuPrint API client, Drosophila CNS connectome topology,
SurrealDB graph seeding, and closed-loop reflex arc steering dynamics.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.neuro.drosophila_cns import (
    DrosophilaCircuitTier,
    DrosophilaCNSConnectome,
    DrosophilaSensoryMotorCircuit,
)
from cohezion.neuro.janelia_neuprint_client import (
    JaneliaNeuPrintClient,
    NeuPrintNeuron,
    NeuPrintSynapse,
)


# Sample fixture data imitating Janelia neuPrint custom Cypher JSON output
SAMPLE_CX_NEUPRINT_RESPONSE = {
    "columns": [
        "source_id",
        "source_type",
        "source_instance",
        "target_id",
        "target_type",
        "target_instance",
        "weight",
    ],
    "data": [
        [519941, "EPG", "EPG_R1", 10099, "ExR6", "ExR6_R", 171],
        [84758, "EPG", "EPG_L1", 10099, "ExR6", "ExR6_R", 176],
        [203301, "PFL3", "PFL3_L1", 10550, "DNg13", "DNg13_L", 42],
        [11989, "PEG", "PEG_R", 519941, "EPG", "EPG_R1", 92],
    ],
}

SAMPLE_DN_NEUPRINT_RESPONSE = {
    "columns": [
        "source_id",
        "source_type",
        "source_instance",
        "target_id",
        "target_type",
        "target_instance",
        "weight",
    ],
    "data": [
        [10550, "DNg13", "DNg13_L", 21001, "vnc_motor_leg", "LegMotor_T1", 85],
        [10551, "DNp01", "DNp01_R", 21002, "vnc_motor_wing", "WingMotor_Direct", 64],
    ],
}


class TestJaneliaNeuPrintClient:
    """Test suite for Janelia neuPrint HTTP API client."""

    def test_client_init_defaults(self) -> None:
        client = JaneliaNeuPrintClient()
        assert client.base_url == "https://neuprint.janelia.org/api"
        assert client.dataset == "male-cns:v1.0"
        assert client.timeout == 15.0
        assert client.auth_token is None

    def test_client_headers_without_auth(self) -> None:
        client = JaneliaNeuPrintClient()
        headers = client._headers()
        assert headers["Content-Type"] == "application/json"
        assert "Authorization" not in headers

    def test_client_headers_with_auth(self) -> None:
        client = JaneliaNeuPrintClient(auth_token="test-secret-token")
        headers = client._headers()
        assert headers["Authorization"] == "Bearer test-secret-token"

    @patch("urllib.request.urlopen")
    def test_fetch_central_complex_subgraph(self, mock_urlopen: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(SAMPLE_CX_NEUPRINT_RESPONSE).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        client = JaneliaNeuPrintClient()
        neurons, synapses = client.fetch_central_complex_subgraph(limit=10, min_weight=10)

        assert len(neurons) == 6  # 519941, 10099, 84758, 203301, 10550, 11989 (unique bodies)
        assert len(synapses) == 4
        # Verify first synapse
        syn0 = synapses[0]
        assert syn0.source_id == 519941
        assert syn0.source_type == "EPG"
        assert syn0.target_id == 10099
        assert syn0.target_type == "ExR6"
        assert syn0.weight == 171

    @patch("urllib.request.urlopen")
    def test_fetch_descending_motor_subgraph(self, mock_urlopen: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(SAMPLE_DN_NEUPRINT_RESPONSE).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        client = JaneliaNeuPrintClient()
        neurons, synapses = client.fetch_descending_motor_subgraph(limit=5, min_weight=5)

        assert len(neurons) == 4
        assert len(synapses) == 2
        assert synapses[0].source_type == "DNg13"
        assert synapses[0].weight == 85


class TestDrosophilaCNSConnectome:
    """Test suite for connectome generation and SurrealDB persistence."""

    def test_canonical_archetypes_exist(self) -> None:
        connectome = DrosophilaCNSConnectome()
        types = [a.type_id for a in connectome.CANONICAL_TYPES]
        assert "vis_R1_R6_photoreceptor" in types
        assert "cx_EB_EPG_compass" in types
        assert "cx_FB_PFL3_steering" in types
        assert "desc_DNg13_motor_turn" in types
        assert "vnc_motor_leg_steering" in types

    def test_generate_connectome_population(self) -> None:
        connectome = DrosophilaCNSConnectome()
        neurons, synapses = connectome.generate_connectome_population(target_count=50)
        assert len(neurons) == 50
        assert len(synapses) > 0

        # Verify all tiers represented
        tiers = {n["tier"] for n in neurons}
        assert DrosophilaCircuitTier.SENSORY_INPUT.value in tiers
        assert DrosophilaCircuitTier.CENTRAL_COMPLEX.value in tiers
        assert DrosophilaCircuitTier.DESCENDING_PATHWAY.value in tiers
        assert DrosophilaCircuitTier.MOTOR_ACTUATION.value in tiers

    @pytest.mark.asyncio
    async def test_seed_from_neuprint_mocked(self) -> None:
        mock_neuprint = MagicMock(spec=JaneliaNeuPrintClient)
        mock_neurons = [
            NeuPrintNeuron(
                body_id=519941, cell_type="EPG", instance="EPG_R1", region="brain", status="Traced"
            ),
            NeuPrintNeuron(
                body_id=10550,
                cell_type="DNg13",
                instance="DNg13_L",
                region="brain",
                status="Traced",
            ),
        ]
        mock_synapses = [
            NeuPrintSynapse(
                source_id=519941, source_type="EPG", target_id=10550, target_type="DNg13", weight=42
            ),
        ]
        mock_neuprint.fetch_central_complex_subgraph.return_value = (mock_neurons, mock_synapses)
        mock_neuprint.fetch_descending_motor_subgraph.return_value = ([], [])

        mock_surreal = AsyncMock()
        connectome = DrosophilaCNSConnectome(surreal_client=mock_surreal)

        result = await connectome.seed_from_neuprint(neuprint_client=mock_neuprint)
        assert result["neurons_seeded"] == 2
        assert result["synapses_seeded"] == 1
        assert mock_surreal.query.call_count >= 3  # define statements + upserts + relates


class TestDrosophilaSensoryMotorCircuit:
    """Test suite for closed-loop biological reflex arc dynamics."""

    def test_compass_ring_attractor_rotation(self) -> None:
        circuit = DrosophilaSensoryMotorCircuit(num_compass_wedges=16)
        assert circuit.compass_state[0] == 1.0

        # Turn 90 degrees right
        heading = circuit.update_compass(angular_velocity_dps=900.0, dt_seconds=0.1)
        assert heading >= 0.0
        assert heading <= 360.0
        assert circuit.compass_state.sum() == 1.0  # Normalized single bump

    def test_compute_reflex_action_yaw_right(self) -> None:
        circuit = DrosophilaSensoryMotorCircuit()
        # High optical flow on the left half -> should trigger yaw right
        error_vec = [1.0, 1.0, 1.0, 0.0, 0.0, 0.0]
        res = circuit.compute_reflex_action(error_vec, coherence=0.50)

        assert res["action"] == "YAW_RIGHT_TRIPOD"
        assert res["steering_torque"] > 0.15
        assert res["latency_ms"] <= 0.1
        assert "R1_R6" in res["circuit"]

    def test_compute_reflex_action_yaw_left(self) -> None:
        circuit = DrosophilaSensoryMotorCircuit()
        # High optical flow on the right half -> should trigger yaw left
        error_vec = [0.0, 0.0, 0.0, 1.0, 1.0, 1.0]
        res = circuit.compute_reflex_action(error_vec, coherence=0.50)

        assert res["action"] == "YAW_LEFT_TRIPOD"
        assert res["steering_torque"] < -0.15

    def test_compute_reflex_action_forward_thrust(self) -> None:
        circuit = DrosophilaSensoryMotorCircuit()
        # Balanced flow -> straight forward thrust
        error_vec = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
        res = circuit.compute_reflex_action(error_vec, coherence=0.50)

        assert res["action"] == "FORWARD_THRUST"
        assert abs(res["steering_torque"]) <= 0.15

    def test_calibrate_from_connectome(self) -> None:
        circuit = DrosophilaSensoryMotorCircuit()
        circuit.calibrate_from_connectome(pfl3_weight=150.0, dng13_weight=75.0)

        assert circuit.pfl3_gain == pytest.approx(3.0)
        assert circuit.dng13_gain == pytest.approx(3.0)

        error_vec = [1.0, 1.0, 0.0, 0.0]
        res = circuit.compute_reflex_action(error_vec, coherence=0.50)
        assert res["pfl3_gain"] == pytest.approx(3.0)
        assert res["dng13_gain"] == pytest.approx(3.0)
