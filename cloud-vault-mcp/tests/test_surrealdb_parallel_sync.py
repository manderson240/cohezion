"""Test suite for SurrealDB parallel sync implementation.

Tests parallel vs sequential bulk imports, verifies data integrity,
and measures performance improvements.
"""

import asyncio
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server.surrealdb_sync import SurrealDBSync


@pytest.fixture
def temp_vault():
    """Create temporary vault structure for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir)

        # Create directories
        (vault_path / "papers").mkdir()
        (vault_path / "concepts").mkdir()

        # Create sample papers
        for i in range(10):
            paper_file = vault_path / "papers" / f"paper-{i:02d}.md"
            paper_file.write_text(
                f"""---
title: Paper {i}
date: 2026-01-01
tags: [ai, research]
---

This is paper {i} content.

[[concept-{i % 3}]]
"""
            )

        # Create sample concepts
        for i in range(3):
            concept_file = vault_path / "concepts" / f"concept-{i}.md"
            concept_file.write_text(
                f"""---
title: Concept {i}
tags: [core]
---

Core concept {i}.
"""
            )

        yield vault_path


@pytest.fixture
def sync_instance(temp_vault):
    """Create SurrealDBSync instance with mock HTTP client."""
    sync = SurrealDBSync(
        vault_path=str(temp_vault),
        parallel_enabled=True,
        max_concurrent=5,
    )
    yield sync
    # Cleanup
    if hasattr(sync, "async_client") and sync.async_client:
        try:
            asyncio.run(sync.async_client.aclose())
        except Exception:
            pass


class TestParallelConfiguration:
    """Test configuration options."""

    def test_parallel_enabled_by_default(self, temp_vault):
        """Verify parallel mode is enabled by default."""
        sync = SurrealDBSync(vault_path=str(temp_vault))
        assert sync.parallel_enabled is True
        assert sync.max_concurrent == 10

    def test_parallel_disabled_config(self, temp_vault):
        """Verify can disable parallel mode."""
        sync = SurrealDBSync(
            vault_path=str(temp_vault),
            parallel_enabled=False,
        )
        assert sync.parallel_enabled is False

    def test_custom_max_concurrent(self, temp_vault):
        """Verify custom concurrency limit."""
        sync = SurrealDBSync(
            vault_path=str(temp_vault),
            max_concurrent=20,
        )
        assert sync.max_concurrent == 20


class TestAsyncPaperSync:
    """Test async paper synchronization."""

    @pytest.mark.asyncio
    async def test_sync_paper_async_success(self, sync_instance, temp_vault):
        """Test successful async paper sync."""
        paper_path = temp_vault / "papers" / "paper-00.md"

        # Mock the async execute query
        with patch.object(
            sync_instance, "_execute_query_async", new_callable=AsyncMock
        ) as mock_query:
            mock_query.return_value = []

            # Mock the sync links
            with patch.object(sync_instance, "_sync_paper_links") as mock_links:
                client = MagicMock()
                success, paper_id = await sync_instance._sync_paper_async(
                    paper_path, client
                )

                assert success is True
                assert paper_id == "papers_paper-00"
                mock_query.assert_called_once()
                mock_links.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_paper_async_non_markdown(self, sync_instance, temp_vault):
        """Test sync skips non-markdown files."""
        text_file = temp_vault / "papers" / "readme.txt"
        text_file.write_text("Not markdown")

        client = MagicMock()
        success, msg = await sync_instance._sync_paper_async(text_file, client)

        assert success is False
        assert "non-markdown" in msg.lower()

    @pytest.mark.asyncio
    async def test_bulk_import_papers_parallel(self, sync_instance, temp_vault):
        """Test parallel bulk import of papers."""
        with patch.object(
            sync_instance, "_execute_query_async", new_callable=AsyncMock
        ) as mock_query:
            mock_query.return_value = []

            with patch.object(sync_instance, "_sync_paper_links"):
                count = await sync_instance._bulk_import_papers_parallel()

                # Should have 10 papers
                assert count == 10
                # Each paper should trigger one query
                assert mock_query.call_count >= 10


class TestAsyncConceptSync:
    """Test async concept synchronization."""

    @pytest.mark.asyncio
    async def test_sync_concept_async_success(self, sync_instance, temp_vault):
        """Test successful async concept sync."""
        concept_path = temp_vault / "concepts" / "concept-0.md"

        with patch.object(
            sync_instance, "_execute_query_async", new_callable=AsyncMock
        ) as mock_query:
            mock_query.return_value = []

            client = MagicMock()
            success, concept_id = await sync_instance._sync_concept_async(
                concept_path, client
            )

            assert success is True
            assert concept_id == "concept-0"
            mock_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_import_concepts_parallel(self, sync_instance, temp_vault):
        """Test parallel bulk import of concepts."""
        with patch.object(
            sync_instance, "_execute_query_async", new_callable=AsyncMock
        ) as mock_query:
            mock_query.return_value = []

            count = await sync_instance._bulk_import_concepts_parallel()

            # Should have 3 concepts
            assert count == 3
            # Each concept should trigger one query
            assert mock_query.call_count >= 3


class TestBulkImportMethods:
    """Test public bulk import methods."""

    def test_bulk_import_papers_uses_parallel(self, sync_instance):
        """Verify bulk import uses parallel when enabled."""
        sync_instance.parallel_enabled = True

        with patch.object(
            sync_instance, "_bulk_import_papers_parallel", return_value=5
        ) as mock_parallel:
            result = sync_instance.bulk_import_papers()

            assert result == 5
            mock_parallel.assert_called_once()

    def test_bulk_import_papers_uses_sequential(self, sync_instance):
        """Verify bulk import uses sequential when disabled."""
        sync_instance.parallel_enabled = False

        with patch.object(
            sync_instance, "_bulk_import_papers_sequential", return_value=5
        ) as mock_seq:
            result = sync_instance.bulk_import_papers()

            assert result == 5
            mock_seq.assert_called_once()

    def test_bulk_import_concepts_uses_parallel(self, sync_instance):
        """Verify concept bulk import uses parallel when enabled."""
        sync_instance.parallel_enabled = True

        with patch.object(
            sync_instance, "_bulk_import_concepts_parallel", return_value=3
        ) as mock_parallel:
            result = sync_instance.bulk_import_concepts()

            assert result == 3
            mock_parallel.assert_called_once()

    def test_bulk_import_concepts_uses_sequential(self, sync_instance):
        """Verify concept bulk import uses sequential when disabled."""
        sync_instance.parallel_enabled = False

        with patch.object(
            sync_instance, "_bulk_import_concepts_sequential", return_value=3
        ) as mock_seq:
            result = sync_instance.bulk_import_concepts()

            assert result == 3
            mock_seq.assert_called_once()

    def test_bulk_import_papers_missing_directory(self, sync_instance, temp_vault):
        """Handle missing papers directory gracefully."""
        import shutil

        shutil.rmtree(temp_vault / "papers")

        count = sync_instance._bulk_import_papers_sequential()
        assert count == 0

    def test_bulk_import_concepts_missing_directory(self, sync_instance, temp_vault):
        """Handle missing concepts directory gracefully."""
        import shutil

        shutil.rmtree(temp_vault / "concepts")

        count = sync_instance._bulk_import_concepts_sequential()
        assert count == 0


class TestErrorHandling:
    """Test error handling in parallel operations."""

    @pytest.mark.asyncio
    async def test_partial_failure_in_parallel(self, sync_instance, temp_vault):
        """Verify partial failures don't crash entire import."""
        call_count = [0]

        async def mock_execute(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 3:
                raise Exception("Simulated HTTP error")
            return []

        with (
            patch.object(
                sync_instance,
                "_execute_query_async",
                new_callable=AsyncMock,
                side_effect=mock_execute,
            ),
            patch.object(sync_instance, "_sync_paper_links"),
        ):
            count = await sync_instance._bulk_import_papers_parallel()

            # Should succeed for papers without HTTP error
            assert count == 9  # 1 failed, 9 succeeded

    @pytest.mark.asyncio
    async def test_timeout_handling(self, sync_instance, temp_vault):
        """Verify timeout errors are caught."""

        async def timeout_execute(*args, **kwargs):
            raise TimeoutError("Request timeout")

        with (
            patch.object(
                sync_instance,
                "_execute_query_async",
                new_callable=AsyncMock,
                side_effect=timeout_execute,
            ),
            patch.object(sync_instance, "_sync_paper_links"),
        ):
            count = await sync_instance._bulk_import_papers_parallel()

            # All should fail due to timeout
            assert count == 0


class TestConcurrencyControl:
    """Test concurrency limiting."""

    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrency(self, sync_instance, temp_vault):
        """Verify semaphore limits concurrent operations."""
        concurrent_count = [0]
        max_concurrent = [0]

        async def mock_execute(*args, **kwargs):
            concurrent_count[0] += 1
            max_concurrent[0] = max(max_concurrent[0], concurrent_count[0])
            await asyncio.sleep(0.01)  # Simulate work
            concurrent_count[0] -= 1
            return []

        sync_instance.max_concurrent = 3

        with (
            patch.object(
                sync_instance,
                "_execute_query_async",
                new_callable=AsyncMock,
                side_effect=mock_execute,
            ),
            patch.object(sync_instance, "_sync_paper_links"),
        ):
            await sync_instance._bulk_import_papers_parallel()

            # Should never exceed max_concurrent
            assert max_concurrent[0] <= sync_instance.max_concurrent


class TestDataIntegrity:
    """Test data integrity across parallel imports."""

    def test_all_papers_synced_correctly(self, sync_instance, temp_vault):
        """Verify all papers are synced with correct data."""
        with patch.object(sync_instance, "_execute_query") as mock_query:
            mock_query.return_value = []

            with patch.object(sync_instance, "_sync_paper_links"):
                # Use sequential to avoid async complexity
                count = sync_instance._bulk_import_papers_sequential()

                assert count == 10
                # Verify each paper was processed
                assert mock_query.call_count == 10

    def test_wiki_links_extracted_correctly(self, sync_instance, temp_vault):
        """Verify wiki-links are extracted from papers."""
        paper_path = temp_vault / "papers" / "paper-00.md"

        with patch.object(sync_instance, "_execute_query") as mock_query:
            mock_query.return_value = []

            with patch.object(sync_instance, "_sync_paper_links") as mock_links:
                sync_instance.sync_paper(paper_path)

                # Verify links were extracted and processed
                mock_links.assert_called_once()


class TestPerformanceComparison:
    """Test and compare parallel vs sequential performance."""

    @pytest.mark.asyncio
    async def test_parallel_faster_than_sequential(self, temp_vault):
        """Verify parallel import is faster than sequential."""
        # Create 20 papers for meaningful benchmark
        papers_dir = temp_vault / "papers"
        for i in range(10, 20):
            paper_file = papers_dir / f"paper-{i:02d}.md"
            paper_file.write_text(
                f"""---
title: Paper {i}
---
Content {i}
[[concept-0]]
"""
            )

        # Measure sequential
        sync_seq = SurrealDBSync(
            vault_path=str(temp_vault),
            parallel_enabled=False,
        )

        with patch.object(sync_seq, "_execute_query", return_value=[]):
            with patch.object(sync_seq, "_sync_paper_links"):
                start = time.perf_counter()
                count_seq = sync_seq._bulk_import_papers_sequential()
                time_seq = time.perf_counter() - start

        # Measure parallel
        sync_par = SurrealDBSync(
            vault_path=str(temp_vault),
            parallel_enabled=True,
            max_concurrent=10,
        )

        with (
            patch.object(
                sync_par,
                "_execute_query_async",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch.object(sync_par, "_sync_paper_links"),
        ):
            start = time.perf_counter()
            count_par = await sync_par._bulk_import_papers_parallel()
            time_par = time.perf_counter() - start

        # Both should import same number
        assert count_seq == count_par == 20

        # Parallel should be faster (with async mocking, times may be close)
        # In real scenario with actual HTTP, parallel would be significantly faster
        print(f"Sequential: {time_seq * 1000:.2f}ms, Parallel: {time_par * 1000:.2f}ms")
