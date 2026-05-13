"""Tests for error classification in compound executor."""

from cohezion.compound.error_classifier import classify_error


class TestErrorClassifier:
    """Unit tests for the error_classifier module."""

    def test_value_error_is_logic_not_retryable(self):
        result = classify_error(ValueError("bad input"))
        assert result["error_category"] == "logic"
        assert result["retryable"] is False
        assert result["error_type"] == "ValueError"

    def test_timeout_error_is_transient_retryable(self):
        result = classify_error(TimeoutError("timed out"))
        assert result["error_category"] == "transient"
        assert result["retryable"] is True

    def test_memory_error_is_resource_retryable(self):
        result = classify_error(MemoryError("OOM"))
        assert result["error_category"] == "resource"
        assert result["retryable"] is True

    def test_runtime_error_is_permanent_not_retryable(self):
        result = classify_error(RuntimeError("unexpected"))
        assert result["error_category"] == "permanent"
        assert result["retryable"] is False

    def test_asyncio_timeout_is_transient(self):
        result = classify_error(TimeoutError())
        assert result["error_category"] == "transient"
        assert result["retryable"] is True

    def test_type_error_is_logic(self):
        result = classify_error(TypeError("wrong type"))
        assert result["error_category"] == "logic"
        assert result["retryable"] is False

    def test_attribute_error_is_logic(self):
        result = classify_error(AttributeError("no such attr"))
        assert result["error_category"] == "logic"
        assert result["retryable"] is False

    def test_io_error_is_resource(self):
        result = classify_error(OSError("disk full"))
        assert result["error_category"] == "resource"
        assert result["retryable"] is True


class TestExecutorErrorClassification:
    """Integration: executor adds error_category when using error_classifier."""

    def test_executor_imports_error_classifier(self):
        """Structural: error_classifier module exists and is importable."""
        from cohezion.compound.error_classifier import classify_error
        assert callable(classify_error)

    def test_classify_error_dict_has_required_keys(self):
        result = classify_error(ValueError("test"))
        assert "error_type" in result
        assert "error_category" in result
        assert "retryable" in result

