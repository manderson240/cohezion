"""Coverage batch Z59: kaggle_curation, bmad_tools."""

from __future__ import annotations

import asyncio
import csv
import json
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Module 1: integrations/kaggle_curation.py
# ---------------------------------------------------------------------------


class TestKaggleCurator:
    def _make_mock_encoder(self):
        mock_enc = MagicMock()
        mock_enc.encode.return_value = np.zeros(256)
        return mock_enc

    def _make_curator(self, mock_encoder=None):
        with patch(
            "cohezion.integrations.kaggle_curation.get_encoder",
            return_value=mock_encoder or self._make_mock_encoder(),
        ):
            from cohezion.integrations.kaggle_curation import KaggleCurator

            return KaggleCurator()

    def test_process_jsonl_dataset(self, tmp_path):
        curator = self._make_curator()
        curator.encoder.encode = MagicMock(return_value=np.zeros(256))

        input_file = tmp_path / "data.jsonl"
        records = [
            {"prompt": "What is 2+2?", "answer": "4"},
            {"prompt": "Capital of France?", "answer": "Paris"},
        ]
        with input_file.open("w") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

        output_file = tmp_path / "output.jsonl"
        asyncio.run(curator.process_dataset(input_file, output_file))
        assert output_file.exists()

        lines = [json.loads(l) for l in output_file.read_text().strip().splitlines()]
        assert len(lines) == 2
        assert "embedding" in lines[0]

    def test_process_csv_dataset(self, tmp_path):
        curator = self._make_curator()
        curator.encoder.encode = MagicMock(return_value=np.zeros(256))

        input_file = tmp_path / "data.csv"
        with input_file.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["prompt", "answer"])
            writer.writeheader()
            writer.writerow({"prompt": "What is ML?", "answer": "Machine Learning"})

        output_file = tmp_path / "output.jsonl"
        asyncio.run(curator.process_dataset(input_file, output_file))
        assert output_file.exists()

    def test_process_missing_file_raises(self, tmp_path):
        curator = self._make_curator()
        with pytest.raises(FileNotFoundError):
            asyncio.run(curator.process_dataset(tmp_path / "missing.jsonl", tmp_path / "out.jsonl"))

    def test_process_jsonl_empty_lines_skipped(self, tmp_path):
        curator = self._make_curator()
        curator.encoder.encode = MagicMock(return_value=np.zeros(256))

        input_file = tmp_path / "data.jsonl"
        input_file.write_text('{"prompt": "q", "answer": "a"}\n\n\n')

        output_file = tmp_path / "out.jsonl"
        asyncio.run(curator.process_dataset(input_file, output_file))
        lines = [l for l in output_file.read_text().strip().splitlines() if l.strip()]
        assert len(lines) == 1

    def test_process_jsonl_question_key_fallback(self, tmp_path):
        curator = self._make_curator()
        curator.encoder.encode = MagicMock(return_value=np.zeros(256))

        input_file = tmp_path / "data.jsonl"
        input_file.write_text(json.dumps({"question": "What?", "answer": "Yes"}) + "\n")

        output_file = tmp_path / "out.jsonl"
        asyncio.run(curator.process_dataset(input_file, output_file))
        assert output_file.exists()


# ---------------------------------------------------------------------------
# Module 2: mcp/bmad_tools.py
# ---------------------------------------------------------------------------


class TestBmadTools:
    def _make_mock_engine(self):
        engine = MagicMock()
        engine.analyze_context.return_value = {"context_type": "general"}
        engine.get_next_steps.return_value = {
            "suggestions": ["Use bmad-help"],
            "suggested_commands": ["help"],
            "suggested_skills": [],
        }
        engine.list_modules.return_value = ["cis", "tea"]
        engine.load_skill.return_value = {"skill_name": "test_skill", "content": "..."}
        engine.list_skills.return_value = [{"name": "bmad-help"}]
        engine.execute_workflow = AsyncMock(return_value={"result": "ok"})
        return engine

    def _make_mock_session_manager(self):
        sm = MagicMock()
        sm.get_session = AsyncMock(return_value=None)
        return sm

    def test_bmad_help_returns_response(self):
        from cohezion.mcp.bmad_tools import bmad_help

        mock_engine = self._make_mock_engine()
        with (
            patch("cohezion.mcp.bmad_tools.get_engine", return_value=mock_engine),
            patch(
                "cohezion.mcp.bmad_tools.get_session_manager",
                return_value=self._make_mock_session_manager(),
            ),
        ):
            result = asyncio.run(bmad_help(query="what should I do?", context="", session_id=""))
        assert "help_response" in result
        assert "available_modules" in result

    def test_bmad_load_skill_returns_content(self):
        from cohezion.mcp.bmad_tools import bmad_load_skill

        mock_engine = self._make_mock_engine()
        with patch("cohezion.mcp.bmad_tools.get_engine", return_value=mock_engine):
            result = asyncio.run(bmad_load_skill(skill_name="bmad-help"))
        assert "available_skills" in result

    def test_bmad_gds_game_architecture(self):
        from cohezion.mcp.bmad_tools import bmad_gds_game_architecture

        mock_engine = self._make_mock_engine()
        mock_engine.load_workflow.return_value = {"workflow": "game-arch"}
        mock_engine.execute_workflow = AsyncMock(
            return_value={"result": "arch", "systems": ["rendering", "physics"]}
        )

        with patch("cohezion.mcp.bmad_tools.get_engine", return_value=mock_engine):
            result = asyncio.run(
                bmad_gds_game_architecture(game_brief_id="brief-001", engine_choice="Unity")
            )
        assert "architecture" in result
        assert "systems" in result
