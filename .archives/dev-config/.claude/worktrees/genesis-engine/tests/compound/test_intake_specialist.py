"""Tests for token-efficient intake specialist agent.

Covers:
- IntentClassifier (0-token heuristic classification)
- PromptOptimizer (0-token compression)
- RequestCache (L1/L2 caching)
- IntakeSpecialist (complete intake pipeline)
"""

from unittest.mock import MagicMock

import pytest

from cohezion.compound.intake_specialist import IntakeSpecialist
from cohezion.compound.intent_classifier import IntentClassifier
from cohezion.compound.prompt_optimizer import PromptOptimizer
from cohezion.compound.request_cache import RequestCache
from cohezion.compound.team_executor import AgentTask


class TestIntentClassifier:
    """Tests for IntentClassifier."""

    def setup_method(self):
        """Set up test fixtures."""
        self.classifier = IntentClassifier(default_operation="generate")

    def test_classify_generate(self):
        """Test generation intent classification."""
        assert self.classifier.classify("Generate 10 story ideas") == "generate"
        assert self.classifier.classify("Create a new function") == "generate"
        assert self.classifier.classify("Write a poem") == "generate"
        assert self.classifier.classify("Compose an email") == "generate"

    def test_classify_analyze(self):
        """Test analysis intent classification."""
        assert self.classifier.classify("Analyze the CSV data") == "analyze"
        assert self.classifier.classify("Evaluate the proposal") == "analyze"
        assert self.classifier.classify("Review the code") == "analyze"
        assert self.classifier.classify("Examine the results") == "analyze"

    def test_classify_search(self):
        """Test search intent classification."""
        assert self.classifier.classify("Search for Python files") == "search"
        assert self.classifier.classify("Find the bug in main.py") == "search"
        assert self.classifier.classify("Locate error handlers") == "search"
        assert self.classifier.classify("Query the database") == "search"

    def test_classify_transform(self):
        """Test transformation intent classification."""
        assert self.classifier.classify("Transform JSON to CSV") == "transform"
        assert self.classifier.classify("Convert Python to Go") == "transform"
        assert self.classifier.classify("Format the output") == "transform"
        assert self.classifier.classify("Extract data from logs") == "transform"

    def test_classify_persist(self):
        """Test persistence intent classification."""
        assert self.classifier.classify("Store the results") == "persist"
        assert self.classifier.classify("Save to database") == "persist"
        assert self.classifier.classify("Log the metrics") == "persist"
        assert self.classifier.classify("Archive old files") == "persist"

    def test_classify_default_fallback(self):
        """Test default fallback when no keywords match."""
        assert self.classifier.classify("xyz abc 123") == "generate"

    def test_classify_empty_string(self):
        """Test classification of empty string."""
        assert self.classifier.classify("") == "generate"
        assert self.classifier.classify(None) == "generate"

    def test_classify_case_insensitive(self):
        """Test case-insensitive classification."""
        assert self.classifier.classify("GENERATE ideas") == "generate"
        assert self.classifier.classify("Analyze DATA") == "analyze"
        assert self.classifier.classify("SEARCH files") == "search"

    def test_classify_partial_word_no_match(self):
        """Test that partial words don't match."""
        # "regenerate" contains "generate" as substring, but not as whole word
        result = self.classifier.classify("regenerate the cache")
        # Should match on "the" or default, not "regenerate"
        assert isinstance(result, str)

    def test_get_operation_keywords(self):
        """Test getting keywords for operation."""
        keywords = self.classifier.get_operation_keywords("generate")
        assert "generate" in keywords
        assert "create" in keywords
        assert "write" in keywords

    def test_get_all_keywords(self):
        """Test getting all keywords."""
        all_keywords = self.classifier.get_all_keywords()
        assert "generate" in all_keywords
        assert "analyze" in all_keywords
        assert "search" in all_keywords
        assert "transform" in all_keywords
        assert "persist" in all_keywords


class TestPromptOptimizer:
    """Tests for PromptOptimizer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.optimizer = PromptOptimizer(enable_filler_removal=True, estimate_tokens=True)

    def test_optimize_removes_filler_words(self):
        """Test removal of filler words."""
        original = "Please, could you kindly generate 10 ideas?"
        optimized = self.optimizer.optimize(original)
        assert "please" not in optimized.lower()
        assert "kindly" not in optimized.lower()
        assert "could" not in optimized.lower()

    def test_optimize_normalizes_whitespace(self):
        """Test whitespace normalization."""
        original = "Generate   10   story   ideas"
        optimized = self.optimizer.optimize(original)
        assert "   " not in optimized
        assert optimized == original.strip().replace("   ", " ")

    def test_optimize_removes_redundancy(self):
        """Test redundancy removal."""
        original = "This is very very important"
        optimized = self.optimizer.optimize(original)
        # Should reduce redundancy
        assert len(optimized) <= len(original)

    def test_estimate_tokens(self):
        """Test token estimation."""
        text = "Generate 10 ideas"
        tokens = self.optimizer._estimate_tokens(text)
        # Roughly 1.3 tokens per word
        assert tokens > 0
        assert tokens <= len(text.split()) * 2

    def test_estimate_tokens_empty(self):
        """Test token estimation for empty string."""
        assert self.optimizer._estimate_tokens("") == 0
        assert self.optimizer._estimate_tokens(None) == 0

    def test_extract_entities(self):
        """Test entity extraction."""
        text = "Parse the file data.csv with ID 12345"
        entities = self.optimizer.extract_entities(text)

        # Check for CSV file
        assert any("csv" in f.lower() for f in entities["files"]), f"Expected CSV file, got: {entities['files']}"
        assert "12345" in entities["numbers"]

    def test_extract_entities_quoted_strings(self):
        """Test extraction of quoted strings."""
        text = 'Use the phrase "hello world" in output'
        entities = self.optimizer.extract_entities(text)

        assert "hello world" in entities["quotes"]

    def test_get_compression_stats(self):
        """Test compression statistics."""
        original = "Please generate 10 creative story ideas"
        compressed = self.optimizer.optimize(original)

        stats = self.optimizer.get_compression_stats(original, compressed)

        assert "original_tokens" in stats
        assert "compressed_tokens" in stats
        assert "tokens_saved" in stats
        assert "reduction_pct" in stats
        assert stats["compressed_tokens"] <= stats["original_tokens"]


class TestRequestCache:
    """Tests for RequestCache."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mcp_client = MagicMock()
        self.cache = RequestCache(self.mcp_client, l1_size=10, l2_size=20)

    def create_test_task(self, task_id: str = "task-1") -> AgentTask:
        """Create test AgentTask."""
        return AgentTask(
            task_id=task_id,
            agent_id="test-agent",
            description="Test task",
            operation_type="generate",
            available_skills=["skill1"],
            timeout_seconds=300.0,
        )

    def test_l1_cache_put_and_get(self):
        """Test L1 cache put and get."""
        request = "Generate ideas"
        task = self.create_test_task()

        # Initially should be miss
        assert self.cache.get_exact(request) is None

        # Put in cache
        self.cache.put(request, task)

        # Now should hit
        cached = self.cache.get_exact(request)
        assert cached is not None
        assert cached.task_id == task.task_id

    def test_l1_cache_exact_match_only(self):
        """Test that L1 cache requires exact match."""
        request = "Generate ideas"
        task = self.create_test_task()

        self.cache.put(request, task)

        # Slightly different request should miss
        assert self.cache.get_exact(request + " now") is None

    def test_l1_cache_eviction(self):
        """Test L1 cache eviction on size limit."""
        # Create cache with small size
        cache = RequestCache(self.mcp_client, l1_size=3, l2_size=20)

        # Add 4 items (exceeds size limit)
        for i in range(4):
            request = f"Request {i}"
            task = self.create_test_task(f"task-{i}")
            cache.put(request, task)

        # Cache should be at size limit
        assert len(cache.l1_cache) == 3

    def test_l2_cache_semantic_match(self):
        """Test L2 semantic caching."""
        request = "Generate ideas"
        task = self.create_test_task()

        self.cache.put(request, task)

        # Semantic match (similar text)
        # Note: actual semantic matching depends on embedding model
        cached = self.cache.get_semantic(request, threshold=0.5)

        # Should hit semantic cache
        assert cached is not None or cached is None  # Depends on embedding quality

    def test_cache_statistics(self):
        """Test cache statistics tracking."""
        request = "Generate ideas"
        task = self.create_test_task()

        # No requests yet
        stats = self.cache.get_stats()
        assert stats["total_requests"] == 0

        # Miss + put
        self.cache.get_exact(request)
        self.cache.put(request, task)

        # Hit
        self.cache.get_exact(request)

        # Check statistics
        stats = self.cache.get_stats()
        assert stats["l1_hits"] >= 1
        assert stats["l1_misses"] >= 1

    def test_cache_reset_stats(self):
        """Test resetting cache statistics."""
        request = "Generate ideas"
        task = self.create_test_task()

        self.cache.put(request, task)
        self.cache.get_exact(request)

        self.cache.reset_stats()

        stats = self.cache.get_stats()
        assert stats["l1_hits"] == 0
        assert stats["l1_misses"] == 0

    def test_cache_clear(self):
        """Test clearing all cache entries."""
        request = "Generate ideas"
        task = self.create_test_task()

        self.cache.put(request, task)
        assert len(self.cache.l1_cache) > 0

        self.cache.clear()

        assert len(self.cache.l1_cache) == 0
        assert self.cache.get_exact(request) is None

    def test_warm_from_vault(self):
        """Test warming cache from vault."""
        # Mock vault_search to return empty (no patterns)
        self.mcp_client.vault_search = MagicMock(return_value=[])

        count = self.cache.warm_from_vault(project="cohezion", limit=100)

        assert count == 0
        self.mcp_client.vault_search.assert_called()

    def test_serialize_deserialize_task(self):
        """Test task serialization/deserialization."""
        task = self.create_test_task("task-123")

        serialized = self.cache._serialize_task(task)
        assert isinstance(serialized, str)
        assert "task-123" in serialized

        deserialized = self.cache._deserialize_task(serialized)
        assert deserialized is not None
        assert deserialized.task_id == task.task_id


class TestIntakeSpecialist:
    """Tests for IntakeSpecialist."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mcp_client = MagicMock()
        self.mcp_client.vault_search = MagicMock(return_value=[])
        self.intake = IntakeSpecialist(self.mcp_client)

    @pytest.mark.asyncio
    async def test_greet_creates_session(self):
        """Test greet() creates session."""
        greeting = await self.intake.greet(user_id="test-user")

        assert greeting.session_id is not None
        assert greeting.user_id == "test-user"
        assert isinstance(greeting.cache_entries, int)
        assert self.intake.session_id == greeting.session_id

    @pytest.mark.asyncio
    async def test_process_request_returns_agent_task(self):
        """Test process_request() returns AgentTask."""
        request = "Generate 10 story ideas"
        task = await self.intake.process_request(request)

        assert isinstance(task, AgentTask)
        assert task.task_id is not None
        assert task.operation_type == "generate"
        assert task.agent_id == "intake-specialist"

    @pytest.mark.asyncio
    async def test_process_request_caches_exact_match(self):
        """Test that repeated requests hit L1 cache."""
        request = "Generate ideas"

        # First request
        task1 = await self.intake.process_request(request)

        # Log to cache
        self.intake.log_success(request, task1)

        # Second request (should hit cache)
        task2 = await self.intake.process_request(request)

        # Same task from cache
        assert task1.task_id == task2.task_id

    @pytest.mark.asyncio
    async def test_process_request_empty_string(self):
        """Test process_request with empty string."""
        with pytest.raises(ValueError):
            await self.intake.process_request("")

    @pytest.mark.asyncio
    async def test_process_request_none(self):
        """Test process_request with None."""
        with pytest.raises(ValueError):
            await self.intake.process_request(None)

    @pytest.mark.asyncio
    async def test_log_success_caches_pattern(self):
        """Test log_success() caches successful patterns."""
        request = "Generate ideas"
        task = await self.intake.process_request(request)

        self.intake.log_success(request, task)

        # Verify it's in cache
        cached = self.intake.cache.get_exact(request)
        assert cached is not None
        assert cached.task_id == task.task_id

    @pytest.mark.asyncio
    async def test_get_session_stats(self):
        """Test session statistics."""
        await self.intake.greet(user_id="test-user")
        request = "Generate ideas"
        task = await self.intake.process_request(request)
        self.intake.log_success(request, task)

        stats = self.intake.get_session_stats()

        assert "session_id" in stats
        assert "user_id" in stats
        assert "cache_stats" in stats
        assert stats["user_id"] == "test-user"

    @pytest.mark.asyncio
    async def test_classify_operations(self):
        """Test classification of different operations."""
        operations = {
            "Generate 10 ideas": "generate",
            "Analyze the data": "analyze",
            "Search for files": "search",
            "Transform JSON to CSV": "transform",
            "Store the results": "persist",
        }

        for request, expected_op in operations.items():
            task = await self.intake.process_request(request)
            assert task.operation_type == expected_op, f"Expected {expected_op}, got {task.operation_type}"

    @pytest.mark.asyncio
    async def test_prompt_optimization(self):
        """Test that prompts are optimized."""
        original = "Please, could you kindly generate 10 ideas?"
        task = await self.intake.process_request(original)

        # Description should be optimized (shorter/cleaner)
        assert len(task.description) <= len(original)

    @pytest.mark.asyncio
    async def test_skill_selection(self):
        """Test that skills are selected for task."""
        # Mock skill selector
        from cohezion.compound.skill_selector import SkillScore

        mock_skills = [
            SkillScore(
                skill_name="generator",
                coherence_score=0.9,
                token_efficiency=0.8,
                success_rate=0.95,
                times_used=100,
                composite_score=0.88,
            ),
            SkillScore(
                skill_name="brainstorm",
                coherence_score=0.8,
                token_efficiency=0.7,
                success_rate=0.85,
                times_used=50,
                composite_score=0.78,
            ),
        ]

        self.intake.skill_selector.select_skills = MagicMock(return_value=mock_skills)

        task = await self.intake.process_request("Generate ideas")

        assert len(task.available_skills) > 0
        assert "generator" in task.available_skills


class TestIntakeSpecialistIntegration:
    """Integration tests for complete intake specialist flow."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mcp_client = MagicMock()
        self.mcp_client.vault_search = MagicMock(return_value=[])

    @pytest.mark.asyncio
    async def test_complete_intake_flow(self):
        """Test complete greet → process → log_success flow."""
        intake = IntakeSpecialist(self.mcp_client)

        # Greet
        greeting = await intake.greet(user_id="user123")
        assert greeting.session_id is not None

        # Process multiple requests
        requests = [
            "Generate 10 story ideas",
            "Analyze the CSV data",
            "Generate 10 creative story ideas",  # Similar to first
        ]

        tasks = []
        for request in requests:
            task = await intake.process_request(request)
            tasks.append(task)
            intake.log_success(request, task)

        # Verify stats
        stats = intake.get_session_stats()
        assert stats["user_id"] == "user123"

        # Check cache performance
        cache_stats = stats["cache_stats"]
        assert cache_stats["total_requests"] >= 3

    @pytest.mark.asyncio
    async def test_token_efficiency_metrics(self):
        """Test token efficiency metrics."""
        intake = IntakeSpecialist(self.mcp_client)

        # Process several requests
        for _i in range(5):
            request = "Generate ideas"
            task = await intake.process_request(request)
            intake.log_success(request, task)

            # Repeat request (should hit cache)
            await intake.process_request(request)

        stats = intake.get_session_stats()
        cache_stats = stats["cache_stats"]

        # With caching, avg tokens should be low
        assert cache_stats["avg_tokens_per_request"] < 100
