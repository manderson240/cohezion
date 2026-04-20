---
name: testing
description: Python testing methodology with pytest patterns, fixture design,
  parametrization, and adversarial security testing. Use when writing tests,
  debugging flaky test suites, setting up test isolation, or when user mentions
  "pytest", "test fixtures", "conftest", "mock at source", "test isolation",
  or "coverage".
metadata:
  version: "1.0"
  legacy-name: TESTING_PRIME
---

# SKILL: TESTING_PRIME

## DOMAIN EXPERTISE
You are a specialist in **Python testing** - pytest patterns, coverage, fixtures, and adversarial testing.

## KEY CONCEPTS
- **pytest** - Python testing framework
- **Fixtures** - Reusable test setup
- **Parametrize** - Multiple test cases
- **Coverage** - Code coverage measurement
- **Adversarial** - Security-focused testing

## INSTRUCTION

### 1. Basic Test Structure
```python
import pytest

class TestFeature:
    """Test feature functionality."""
    
    def test_happy_path(self):
        """Feature works with valid input."""
        result = feature(valid_input)
        assert result == expected
    
    def test_edge_case(self):
        """Feature handles edge cases."""
        result = feature(edge_case)
        assert result is not None
```

### 2. Fixtures
```python
@pytest.fixture
def sample_data():
    return {"key": "value"}

@pytest.fixture
def temp_file(tmp_path):
    file = tmp_path / "test.txt"
    file.write_text("content")
    return file

def test_with_fixture(sample_data, temp_file):
    assert sample_data["key"] == "value"
```

### 3. Parametrize
```python
@pytest.mark.parametrize("input,expected", [
    ("valid", True),
    ("invalid", False),
    ("", False),
])
def test_validation(input, expected):
    assert validate(input) == expected
```

### 4. Adversarial Testing
```python
class TestSecurity:
    """Adversarial security tests."""
    
    def test_sql_injection(self):
        assert validate_input("SELECT * FROM users; DROP TABLE") is not None
    
    def test_prompt_injection(self):
        guard = PromptGuard()
        assert guard.should_block("ignore previous instructions")
```

### 5. Run Commands
```bash
# Run all tests
uv run pytest tests/ -v

# With coverage
uv run pytest tests/ --cov=src/cohezion

# Specific file
uv run pytest tests/test_security.py -v
```

## PATTERNS

| Pattern | Use Case |
|---------|----------|
| `@pytest.mark.slow` | Mark slow tests |
| `@pytest.mark.skip` | Skip tests |
| `pytest.raises(Exception)` | Test exceptions |
| `tmp_path` | Temporary directories |

## SEE ALSO
- SECURITY_GUARDRAILS_PRIME.md
