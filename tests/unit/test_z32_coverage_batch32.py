"""Coverage batch Z32: quadrature_nexus, cert_generator, knowledge_mcp, swarm_mcp, mycelium_loop."""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Module 1: governance/quadrature_nexus.py
# ---------------------------------------------------------------------------


class TestQuadratureNexus:
    def test_initial_state_defaults(self):
        from cohezion.governance.quadrature_nexus import QuadratureNexus

        nexus = QuadratureNexus()
        assert nexus.state.coherence == pytest.approx(0.5)
        assert nexus.state.awareness == pytest.approx(0.5)

    def test_update_state_maps_metrics(self):
        from cohezion.governance.quadrature_nexus import QuadratureNexus

        nexus = QuadratureNexus()
        nexus.update_state({"active_agents": 5, "verification_rate": 0.9, "hiho_coherence": 0.8})
        assert nexus.state.awareness == pytest.approx(0.5)  # 5 / 10
        assert nexus.state.precision == pytest.approx(0.9)
        assert nexus.state.coherence == pytest.approx(0.8)

    def test_update_state_calculates_stability(self):
        from cohezion.governance.quadrature_nexus import QuadratureNexus

        nexus = QuadratureNexus()
        nexus.update_state({"verification_rate": 0.6, "hiho_coherence": 0.4})
        assert nexus.state.stability == pytest.approx(0.5)  # (0.6 + 0.4) / 2

    def test_update_state_calculates_synthesis(self):
        from cohezion.governance.quadrature_nexus import QuadratureNexus

        nexus = QuadratureNexus()
        nexus.update_state({"active_agents": 10, "verification_rate": 0.8, "hiho_coherence": 0.8})
        # awareness = 10/10 = 1.0, stability = (0.8+0.8)/2 = 0.8
        assert nexus.state.synthesis == pytest.approx(0.8)  # 1.0 * 0.8

    def test_update_state_appends_to_history(self):
        from cohezion.governance.quadrature_nexus import QuadratureNexus

        nexus = QuadratureNexus()
        nexus.update_state({"verification_rate": 0.5})
        nexus.update_state({"verification_rate": 0.7})
        assert len(nexus.history) == 2

    def test_get_reality_gate_true_when_stable(self):
        from cohezion.governance.quadrature_nexus import QuadratureNexus

        nexus = QuadratureNexus()
        nexus.update_state({"verification_rate": 0.6, "hiho_coherence": 0.6})
        assert nexus.get_reality_gate() is True

    def test_get_reality_gate_false_when_unstable(self):
        from cohezion.governance.quadrature_nexus import QuadratureNexus

        nexus = QuadratureNexus()
        nexus.update_state({"verification_rate": 0.2, "hiho_coherence": 0.2})
        assert nexus.get_reality_gate() is False

    def test_get_dilation_factor_default(self):
        from cohezion.governance.quadrature_nexus import QuadratureNexus

        nexus = QuadratureNexus()
        # Default dilation = 0.0 → factor = 1.0
        assert nexus.get_dilation_factor() == pytest.approx(1.0)

    def test_get_dilation_factor_with_viscosity(self):
        from cohezion.governance.quadrature_nexus import QuadratureNexus

        nexus = QuadratureNexus()
        nexus.update_state({"system_viscosity": 0.5})
        assert nexus.get_dilation_factor() == pytest.approx(1.5)

    def test_quadrature_state_dataclass(self):
        from cohezion.governance.quadrature_nexus import QuadratureState

        state = QuadratureState(awareness=0.9)
        assert state.awareness == pytest.approx(0.9)
        assert state.coherence == pytest.approx(0.5)  # default


# ---------------------------------------------------------------------------
# Module 2: security/cert_generator.py
# ---------------------------------------------------------------------------


class TestCertificateGenerator:
    def test_returns_true_when_files_exist_no_force(self, tmp_path):
        from cohezion.security.cert_generator import CertificateGenerator

        cert = tmp_path / "cert.crt"
        key = tmp_path / "key.key"
        cert.write_text("cert")
        key.write_text("key")
        result = CertificateGenerator.generate_self_signed_cert(str(cert), str(key), force=False)
        assert result is True

    def test_generates_cert_when_files_missing(self, tmp_path):
        from cohezion.security.cert_generator import CertificateGenerator

        cert = tmp_path / "new.crt"
        key = tmp_path / "new.key"
        with patch("cohezion.security.cert_generator.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            with patch.object(Path, "chmod"):
                result = CertificateGenerator.generate_self_signed_cert(str(cert), str(key))
        assert result is True

    def test_returns_false_on_subprocess_failure(self, tmp_path):
        from cohezion.security.cert_generator import CertificateGenerator

        cert = tmp_path / "fail.crt"
        key = tmp_path / "fail.key"
        with patch("cohezion.security.cert_generator.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "openssl", stderr="error")
            result = CertificateGenerator.generate_self_signed_cert(str(cert), str(key))
        assert result is False

    def test_returns_false_when_openssl_missing(self, tmp_path):
        from cohezion.security.cert_generator import CertificateGenerator

        cert = tmp_path / "miss.crt"
        key = tmp_path / "miss.key"
        with patch("cohezion.security.cert_generator.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("openssl not found")
            result = CertificateGenerator.generate_self_signed_cert(str(cert), str(key))
        assert result is False

    def test_returns_false_on_unexpected_exception(self, tmp_path):
        from cohezion.security.cert_generator import CertificateGenerator

        cert = tmp_path / "exc.crt"
        key = tmp_path / "exc.key"
        with patch("cohezion.security.cert_generator.subprocess.run") as mock_run:
            mock_run.side_effect = RuntimeError("unexpected")
            result = CertificateGenerator.generate_self_signed_cert(str(cert), str(key))
        assert result is False

    def test_ensure_dev_certificates_returns_paths_on_success(self, tmp_path):
        from cohezion.security.cert_generator import CertificateGenerator

        with patch.object(CertificateGenerator, "generate_self_signed_cert", return_value=True):
            cert, key = CertificateGenerator.ensure_dev_certificates(cert_dir=str(tmp_path))
        assert cert is not None
        assert key is not None

    def test_ensure_dev_certificates_returns_none_on_failure(self, tmp_path):
        from cohezion.security.cert_generator import CertificateGenerator

        with patch.object(CertificateGenerator, "generate_self_signed_cert", return_value=False):
            cert, key = CertificateGenerator.ensure_dev_certificates(cert_dir=str(tmp_path))
        assert cert is None
        assert key is None


# ---------------------------------------------------------------------------
# Module 3: mcp/knowledge_server_mcp.py
# ---------------------------------------------------------------------------


class TestKnowledgeServerMcp:
    @pytest.fixture(autouse=True)
    def _mock_server(self):
        self.mock_server = MagicMock()
        self.mock_server.search_knowledge = MagicMock(return_value=[{"title": "doc1"}])
        self.mock_server.get_skill = MagicMock(
            return_value={"name": "vault_keeper", "content": "..."}
        )
        self.mock_server.list_skills = MagicMock(return_value=["skill_a", "skill_b"])

        with patch("cohezion.mcp.knowledge_server_mcp.get_server", return_value=self.mock_server):
            yield

    def test_search_knowledge_calls_server(self):
        from cohezion.mcp.knowledge_server_mcp import search_knowledge

        result = asyncio.run(search_knowledge("vault operations", limit=3))
        self.mock_server.search_knowledge.assert_called_once_with("vault operations", 3)
        assert result[0]["title"] == "doc1"

    def test_get_skill_calls_server(self):
        from cohezion.mcp.knowledge_server_mcp import get_skill

        result = asyncio.run(get_skill("vault_keeper"))
        self.mock_server.get_skill.assert_called_once_with("vault_keeper")
        assert result["name"] == "vault_keeper"

    def test_list_skills_calls_server(self):
        from cohezion.mcp.knowledge_server_mcp import list_skills

        result = asyncio.run(list_skills())
        self.mock_server.list_skills.assert_called_once()
        assert "skill_a" in result


# ---------------------------------------------------------------------------
# Module 4: mcp/swarm_server_mcp.py
# ---------------------------------------------------------------------------


class TestSwarmServerMcp:
    @pytest.fixture(autouse=True)
    def _mock_server(self):
        self.mock_server = MagicMock()
        self.mock_server.run_debate = AsyncMock(return_value={"consensus": "decision text"})
        self.mock_server.get_perspectives = MagicMock(return_value=[{"name": "ARCHITECT"}])
        self.mock_server.get_metrics = MagicMock(return_value={"debates_run": 5})

        with patch("cohezion.mcp.swarm_server_mcp.get_server", return_value=self.mock_server):
            yield

    def test_run_debate_calls_server(self):
        from cohezion.mcp.swarm_server_mcp import run_debate

        result = asyncio.run(run_debate("should we scale?", ["ARCHITECT", "CRITIC"]))
        self.mock_server.run_debate.assert_awaited_once_with(
            "should we scale?", ["ARCHITECT", "CRITIC"]
        )
        assert "consensus" in result

    def test_run_debate_no_perspectives(self):
        from cohezion.mcp.swarm_server_mcp import run_debate

        asyncio.run(run_debate("test query"))
        self.mock_server.run_debate.assert_awaited_once_with("test query", None)

    def test_get_perspectives_calls_server(self):
        from cohezion.mcp.swarm_server_mcp import get_perspectives

        result = asyncio.run(get_perspectives())
        self.mock_server.get_perspectives.assert_called_once()
        assert result[0]["name"] == "ARCHITECT"

    def test_get_swarm_metrics_calls_server(self):
        from cohezion.mcp.swarm_server_mcp import get_swarm_metrics

        result = asyncio.run(get_swarm_metrics())
        self.mock_server.get_metrics.assert_called_once()
        assert result["debates_run"] == 5


# ---------------------------------------------------------------------------
# Module 5: mycelium/loop.py
# ---------------------------------------------------------------------------


class TestCoverageLoop:
    def _make_loop(self):
        from cohezion.mycelium.loop import CoverageLoop

        mock_scripter = MagicMock()
        return CoverageLoop(
            mock_scripter, root_dir=".", test_output_dir="/tmp/tests_z32"
        ), mock_scripter

    def test_run_tests_returns_float(self):
        loop, _ = self._make_loop()
        with patch("cohezion.mycelium.loop.subprocess.check_output") as mock_co:
            mock_co.return_value = b"src/cohezion/x.py    10    2    80%\n"
            result = loop.run_tests_and_get_coverage("src/cohezion/x.py")
        assert result == pytest.approx(80.0)

    def test_run_tests_returns_zero_on_no_match(self):
        loop, _ = self._make_loop()
        with patch("cohezion.mycelium.loop.subprocess.check_output") as mock_co:
            mock_co.return_value = b"no coverage output here\n"
            result = loop.run_tests_and_get_coverage("src/cohezion/x.py")
        assert result == pytest.approx(0.0)

    def test_run_tests_returns_zero_on_process_error(self):
        loop, _ = self._make_loop()
        with patch("cohezion.mycelium.loop.subprocess.check_output") as mock_co:
            mock_co.side_effect = subprocess.CalledProcessError(
                1, "pytest", output=b"test failed\n"
            )
            result = loop.run_tests_and_get_coverage("src/cohezion/x.py")
        assert result == pytest.approx(0.0)

    def test_execute_returns_coverage_when_already_at_target(self):
        loop, _ = self._make_loop()
        with patch("cohezion.mycelium.loop.subprocess.check_output") as mock_co:
            mock_co.return_value = b"src/cohezion/x.py    10    0   100%\n"
            result = asyncio.run(
                loop.execute("src/cohezion/x.py", "def foo(): pass", target_coverage=100.0)
            )
        assert result == pytest.approx(100.0)

    def test_execute_runs_synthesis_loop_when_coverage_low(self, tmp_path):
        from cohezion.mycelium.loop import CoverageLoop

        mock_scripter = MagicMock()
        mock_scripter.synthesize_test_suite = AsyncMock(return_value="def test_foo(): pass")

        loop = CoverageLoop(mock_scripter, root_dir=".", test_output_dir=str(tmp_path / "tests"))

        call_count = 0

        def mock_coverage(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return b"src/cohezion/x.py    10    5    50%\n"
            return b"src/cohezion/x.py    10    0   100%\n"

        with patch("cohezion.mycelium.loop.subprocess.check_output", side_effect=mock_coverage):
            result = asyncio.run(
                loop.execute(
                    "src/cohezion/x.py", "code context", target_coverage=100.0, max_iterations=3
                )
            )

        mock_scripter.synthesize_test_suite.assert_awaited_once()
        assert result == pytest.approx(100.0)
