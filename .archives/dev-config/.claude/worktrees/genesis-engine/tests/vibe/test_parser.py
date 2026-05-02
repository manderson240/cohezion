"""Tests for VibeParser — NL text → VibeIntent."""

from __future__ import annotations

import pytest

from cohezion.vibe.types import OperationType


@pytest.fixture
def parser():
    from cohezion.vibe.parser import VibeParser

    return VibeParser()


class TestVibeParserBasic:
    def test_parse_returns_vibe_intent(self, parser):
        import asyncio

        from cohezion.vibe.types import VibeIntent

        result = asyncio.run(parser.parse("research machine learning papers"))
        assert isinstance(result, VibeIntent)

    def test_parse_captures_raw_text(self, parser):
        import asyncio

        text = "implement a REST API with authentication"
        result = asyncio.run(parser.parse(text))
        assert result.raw_text == text

    def test_parse_extracts_keywords(self, parser):
        import asyncio

        result = asyncio.run(parser.parse("implement a REST API with authentication"))
        # Should extract meaningful signal words
        assert len(result.keywords) > 0
        # Should not include stopwords like "a", "with"
        assert "a" not in result.keywords
        assert "with" not in result.keywords

    def test_parse_empty_string_returns_unknown(self, parser):
        import asyncio

        result = asyncio.run(parser.parse(""))
        assert result.operation_type == OperationType.UNKNOWN
        assert result.confidence < 0.5

    def test_parse_complexity_in_range(self, parser):
        import asyncio

        result = asyncio.run(parser.parse("do something"))
        assert 1 <= result.complexity <= 5

    def test_parse_confidence_in_range(self, parser):
        import asyncio

        result = asyncio.run(parser.parse("analyze data and produce report"))
        assert 0.0 <= result.confidence <= 1.0


class TestVibeParserOperationTypes:
    @pytest.mark.parametrize(
        "text,expected_op",
        [
            ("research recent papers on transformers", OperationType.RESEARCH),
            ("implement a login page", OperationType.IMPLEMENT),
            ("analyze sales data for Q4", OperationType.ANALYZE),
            ("transform raw CSV into structured JSON", OperationType.TRANSFORM),
            ("validate the API responses against the schema", OperationType.VALIDATE),
        ],
    )
    def test_operation_type_detection(self, parser, text, expected_op):
        import asyncio

        result = asyncio.run(parser.parse(text))
        assert result.operation_type == expected_op

    def test_mixed_intent_picks_dominant(self, parser):
        import asyncio

        # "research and implement" — both present, should pick one
        result = asyncio.run(parser.parse("research the problem and implement a fix"))
        assert result.operation_type in (OperationType.RESEARCH, OperationType.IMPLEMENT)

    def test_unknown_for_gibberish(self, parser):
        import asyncio

        result = asyncio.run(parser.parse("zzz aaa bbb xyz"))
        # Either UNKNOWN or low confidence
        assert result.operation_type == OperationType.UNKNOWN or result.confidence < 0.4


class TestVibeParserComplexity:
    def test_simple_task_low_complexity(self, parser):
        import asyncio

        result = asyncio.run(parser.parse("fetch data"))
        assert result.complexity <= 2

    def test_complex_task_high_complexity(self, parser):
        import asyncio

        text = (
            "research the problem, design a solution, implement it with tests, "
            "validate the output, and deploy to production"
        )
        result = asyncio.run(parser.parse(text))
        assert result.complexity >= 3

    def test_medium_task_mid_complexity(self, parser):
        import asyncio

        result = asyncio.run(parser.parse("analyze data and generate a report"))
        assert 1 <= result.complexity <= 4  # Broad range acceptable


class TestVibeParserWithFlux:
    @pytest.mark.asyncio
    async def test_parser_works_without_flux(self):
        from cohezion.vibe.parser import VibeParser

        parser = VibeParser(flux_aggregator=None)
        result = await parser.parse("implement something")
        assert result.raw_text == "implement something"

    @pytest.mark.asyncio
    async def test_parser_accepts_flux_aggregator(self):
        from unittest.mock import AsyncMock, MagicMock

        from cohezion.flux.types import FluxContext
        from cohezion.vibe.parser import VibeParser

        mock_flux = MagicMock()
        mock_flux.get_context = AsyncMock(
            return_value=FluxContext(blocks=[], total_tokens_estimated=0, query="", sources_queried=[])
        )
        parser = VibeParser(flux_aggregator=mock_flux)
        result = await parser.parse("research transformers")
        # Flux was called (non-blocking; result ignored if no blocks)
        assert result.raw_text == "research transformers"
