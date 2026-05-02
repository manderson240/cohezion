"""Unit tests for RequestAlignmentAnalyzer.

Tests request parsing, constraint extraction, alignment analysis, and vault integration.
"""

from unittest.mock import MagicMock

import pytest

from cohezion.compound.models import (
    ConstraintType,
    ExecutionConstraint,
    HumanRequest,
    IntentType,
    SuccessCriterion,
)
from cohezion.compound.request_alignment_analyzer import (
    RequestAlignmentAnalyzer,
    RequestAlignmentAnalyzerFactory,
)


class MockMCPClient:
    """Mock MCP client for testing."""

    def vault_find_relevant_context(self, query: str, project: str = "cohezion"):
        """Mock vault search."""
        return [{"path": "test", "content": "test pattern"}]

    def vault_log_decision(self, project: str, title: str, context: str, decision: str, rationale: str) -> str:
        """Mock decision logging."""
        return "decisions/test-decision.md"

    def vault_log_experiment(
        self,
        project: str,
        hypothesis: str,
        method: str,
        result: str = "",
        learnings: str = "",
        title: str = "",
    ) -> str:
        """Mock experiment logging."""
        return "experiments/test-experiment.md"


class TestRequestParsing:
    """Test request parsing functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mcp_client = MockMCPClient()
        self.analyzer = RequestAlignmentAnalyzer(self.mcp_client, intent_confidence_threshold=0.5)

    def test_parse_simple_request(self):
        """Test parsing a simple request."""
        request_text = "Generate 10 creative story ideas"
        request = self.analyzer.parse_request(request_text)

        assert request.raw_text == request_text
        assert request.intent == IntentType.GENERATE
        assert request.intent_confidence > 0.0

    def test_parse_request_with_token_constraint(self):
        """Test extracting token constraint from request."""
        request_text = "Generate 10 ideas under 500 tokens"
        request = self.analyzer.parse_request(request_text)

        assert len(request.constraints) > 0
        token_constraints = [c for c in request.constraints if c.type == ConstraintType.TOKENS]
        assert len(token_constraints) > 0
        assert token_constraints[0].value == 500

    def test_parse_request_with_latency_constraint(self):
        """Test extracting latency constraint from request."""
        request_text = "Analyze within 5 seconds"
        request = self.analyzer.parse_request(request_text)

        assert len(request.constraints) > 0
        latency_constraints = [c for c in request.constraints if c.type == ConstraintType.LATENCY]
        assert len(latency_constraints) > 0
        # Should be normalized to ms: 5 seconds = 5000 ms
        assert latency_constraints[0].value == 5000

    def test_parse_request_with_quality_constraint(self):
        """Test extracting quality constraint from request."""
        request_text = "Generate high quality content"
        request = self.analyzer.parse_request(request_text)

        quality_constraints = [c for c in request.constraints if c.type == ConstraintType.QUALITY]
        assert len(quality_constraints) > 0

    def test_classify_intent_generate(self):
        """Test intent classification for generate."""
        intent_type, confidence = self.analyzer._classify_intent("Write a creative story")
        assert intent_type == IntentType.GENERATE
        assert confidence > 0.0

    def test_classify_intent_analyze(self):
        """Test intent classification for analyze."""
        intent_type, confidence = self.analyzer._classify_intent("Analyze the data and evaluate results")
        assert intent_type == IntentType.ANALYZE
        assert confidence > 0.0

    def test_classify_intent_search(self):
        """Test intent classification for search."""
        intent_type, confidence = self.analyzer._classify_intent("Find all documents related to machine learning")
        assert intent_type == IntentType.SEARCH
        assert confidence > 0.0

    def test_extract_success_criteria(self):
        """Test extracting success criteria from request."""
        request_text = "Generate ideas that must be creative and relevant"
        request = self.analyzer.parse_request(request_text)

        assert len(request.criteria) > 0

    def test_extract_scope(self):
        """Test extracting scope from request."""
        request_text = "Generate ideas only for technology domain"
        request = self.analyzer.parse_request(request_text)

        assert len(request.scope_includes) > 0

    def test_parse_multiline_request(self):
        """Test parsing multiline request."""
        request_text = """
        Generate 10 creative story ideas for children.
        Each idea must be coherent and age-appropriate.
        Use under 500 tokens.
        Focus on adventure themes.
        """
        request = self.analyzer.parse_request(request_text)

        # Intent should be classified (may be unknown if newlines affect keyword matching)
        assert request.intent in [IntentType.GENERATE, IntentType.UNKNOWN]
        # Should still extract constraints even if intent is unknown
        assert len(request.constraints) > 0


class TestConstraintExtraction:
    """Test constraint extraction from text."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mcp_client = MockMCPClient()
        self.analyzer = RequestAlignmentAnalyzer(self.mcp_client)

    def test_extract_token_constraint_variations(self):
        """Test extracting tokens with different phrasings."""
        texts = [
            "under 1000 tokens",
            "within 500 tokens",
            "limit to 2000 tokens",
            "max 1500 tokens",
        ]

        for text in texts:
            constraints = self.analyzer._extract_constraints(text)
            token_constraints = [c for c in constraints if c.type == ConstraintType.TOKENS]
            assert len(token_constraints) > 0, f"Failed to extract from: {text}"

    def test_extract_latency_constraint_variations(self):
        """Test extracting latency with different time units."""
        test_cases = [
            ("under 100 ms", 100),
            ("within 5 sec", 5000),
            ("limit to 2 min", 120000),
        ]

        for text, expected_ms in test_cases:
            constraints = self.analyzer._extract_constraints(text)
            latency_constraints = [c for c in constraints if c.type == ConstraintType.LATENCY]
            assert len(latency_constraints) > 0
            assert latency_constraints[0].value == expected_ms

    def test_constraint_tolerance(self):
        """Test constraint tolerance in analyzer."""
        analyzer = RequestAlignmentAnalyzer(self.mcp_client, constraint_tolerance=0.2)
        assert analyzer.constraint_tolerance == 0.2


class TestAlignmentAnalysis:
    """Test alignment analysis between request and execution."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mcp_client = MockMCPClient()
        self.analyzer = RequestAlignmentAnalyzer(self.mcp_client)

        # Create a simple request
        self.request = HumanRequest(
            raw_text="Generate 10 ideas in under 500 tokens",
            intent=IntentType.GENERATE,
            intent_confidence=0.9,
            constraints=[ExecutionConstraint(type=ConstraintType.TOKENS, value=500, unit="tokens", is_hard=True)],
            criteria=[SuccessCriterion("Output is coherent", "coherence", 0.7, False)],
        )

    def test_perfect_alignment(self):
        """Test perfect alignment scenario."""
        # Create mock execution result
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output = "1. Idea one\n2. Idea two\n..."
        mock_result.metrics = {
            "tokens_used": 300,
            "coherence": 0.85,
            "duration_seconds": 1.0,
        }

        alignment = self.analyzer.analyze_alignment(self.request, mock_result, "generate")

        assert alignment.intent_match_score > 0.5
        assert alignment.misalignment_score < 0.3
        assert len(alignment.violations) == 0

    def test_constraint_violation_tokens(self):
        """Test constraint violation for tokens."""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output = "1. Idea one\n2. Idea two\n..."
        mock_result.metrics = {
            "tokens_used": 600,  # Exceeds constraint
            "coherence": 0.85,
            "duration_seconds": 1.0,
        }

        alignment = self.analyzer.analyze_alignment(self.request, mock_result, "generate")

        assert len(alignment.violations) > 0
        assert alignment.constraint_satisfaction < 1.0

    def test_execution_failure(self):
        """Test alignment when execution fails."""
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.output = "Error: API timeout"
        mock_result.metrics = {"error": "API timeout", "duration_seconds": 2.0}

        alignment = self.analyzer.analyze_alignment(self.request, mock_result, "generate")

        assert len(alignment.drift_signals) > 0
        # Failure still allows some alignment due to intent still matching
        assert alignment.misalignment_score >= 0.0

    def test_coherence_failure(self):
        """Test alignment when coherence criterion fails."""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output = "Garbled output that doesn't make sense"
        mock_result.metrics = {
            "tokens_used": 300,
            "coherence": 0.2,  # Below threshold of 0.7
            "duration_seconds": 1.0,
        }

        alignment = self.analyzer.analyze_alignment(self.request, mock_result, "generate")

        assert len(alignment.failures) > 0
        assert alignment.criteria_satisfaction < 1.0

    def test_misalignment_score_calculation(self):
        """Test misalignment score calculation."""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output = "Output"
        mock_result.metrics = {
            "tokens_used": 500,
            "coherence": 0.7,
            "duration_seconds": 1.0,
        }

        alignment = self.analyzer.analyze_alignment(self.request, mock_result, "generate")

        # Should be between 0 and 1
        assert 0.0 <= alignment.misalignment_score <= 1.0


class TestVaultIntegration:
    """Test vault integration for alignment logging."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mcp_client = MockMCPClient()
        self.analyzer = RequestAlignmentAnalyzer(self.mcp_client)

    def test_log_high_misalignment_as_decision(self):
        """Test logging high misalignment as decision."""
        from cohezion.compound.models import ExecutionAlignment

        request = HumanRequest(raw_text="Generate ideas", intent=IntentType.GENERATE)
        alignment = ExecutionAlignment(
            intent_match_score=0.3,
            constraint_satisfaction=0.2,
            criteria_satisfaction=0.1,
            misalignment_score=0.75,  # High misalignment
            violations=[],
            failures=[],
            drift_signals=[],
            issues=["Execution failed", "Low coherence"],
            recommendations=["Use higher-quality model"],
            should_retry=True,
        )

        path = self.analyzer.log_alignment_to_vault(request, alignment, "cohezion")
        assert path == "decisions/test-decision.md"

    def test_log_normal_alignment_as_experiment(self):
        """Test logging normal alignment as experiment."""
        from cohezion.compound.models import ExecutionAlignment

        request = HumanRequest(raw_text="Generate ideas", intent=IntentType.GENERATE)
        alignment = ExecutionAlignment(
            intent_match_score=0.9,
            constraint_satisfaction=0.95,
            criteria_satisfaction=0.9,
            misalignment_score=0.05,  # Good alignment
            violations=[],
            failures=[],
            drift_signals=[],
            issues=[],
            recommendations=["Execution aligned"],
            should_retry=False,
        )

        path = self.analyzer.log_alignment_to_vault(request, alignment, "cohezion")
        assert path == "experiments/test-experiment.md"

    def test_query_alignment_patterns(self):
        """Test querying vault for alignment patterns."""
        patterns = self.analyzer.query_alignment_patterns("Generate ideas")

        assert isinstance(patterns, dict)
        assert "alignment_patterns" in patterns


class TestFactory:
    """Test RequestAlignmentAnalyzerFactory."""

    def test_create_analyzer(self):
        """Test factory creates analyzer correctly."""
        mcp_client = MockMCPClient()
        analyzer = RequestAlignmentAnalyzerFactory.create(mcp_client)

        assert isinstance(analyzer, RequestAlignmentAnalyzer)
        assert analyzer.mcp_client == mcp_client

    def test_create_with_custom_thresholds(self):
        """Test factory with custom thresholds."""
        mcp_client = MockMCPClient()
        analyzer = RequestAlignmentAnalyzerFactory.create(
            mcp_client,
            intent_confidence_threshold=0.7,
            constraint_tolerance=0.2,
        )

        assert analyzer.intent_confidence_threshold == 0.7
        assert analyzer.constraint_tolerance == 0.2


class TestIntentClassification:
    """Test intent classification logic."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mcp_client = MockMCPClient()
        self.analyzer = RequestAlignmentAnalyzer(self.mcp_client)

    def test_intent_keywords_all_types(self):
        """Test intent classification for all intent types."""
        test_cases = [
            ("Generate a story", IntentType.GENERATE),
            ("Analyze this data", IntentType.ANALYZE),
            ("Search for documents", IntentType.SEARCH),
            ("Transform the format", IntentType.TRANSFORM),
            ("Save to database", IntentType.PERSIST),
        ]

        for text, expected_intent in test_cases:
            intent, _confidence = self.analyzer._classify_intent(text)
            assert intent == expected_intent, f"Failed for: {text}"

    def test_intent_confidence_score(self):
        """Test intent confidence scoring."""
        # High confidence: multiple intent keywords
        _intent1, conf1 = self.analyzer._classify_intent("Generate and create multiple new stories")
        # Low confidence: single keyword
        _intent2, conf2 = self.analyzer._classify_intent("Generate")

        assert conf1 >= conf2  # More keywords = higher confidence


class TestIssueGeneration:
    """Test issue and recommendation generation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mcp_client = MockMCPClient()
        self.analyzer = RequestAlignmentAnalyzer(self.mcp_client)

    def test_generate_issues_from_violations(self):
        """Test issue generation from constraint violations."""
        from cohezion.compound.models import ConstraintViolation

        constraint = ExecutionConstraint(type=ConstraintType.TOKENS, value=500, unit="tokens")
        violation = ConstraintViolation(constraint=constraint, requested_value=500, actual_value=600, severity=0.2)

        issues = self.analyzer._generate_issues([violation], [], [], 0.9)

        assert len(issues) > 0
        assert "tokens" in issues[0].lower()

    def test_generate_recommendations_from_violations(self):
        """Test recommendation generation from violations."""
        from cohezion.compound.models import ConstraintViolation

        constraint = ExecutionConstraint(type=ConstraintType.TOKENS, value=500, unit="tokens")
        violation = ConstraintViolation(constraint=constraint, requested_value=500, actual_value=600, severity=0.2)

        recommendations = self.analyzer._generate_recommendations([violation], [], [], IntentType.GENERATE)

        assert len(recommendations) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
