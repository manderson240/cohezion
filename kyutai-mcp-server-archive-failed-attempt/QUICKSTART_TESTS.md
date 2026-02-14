# Quick Start: Running the Test Suite

## Install Dependencies

```bash
cd /home/mike-anderson/dev/cohezion/kyutai-mcp-server

# Python
pip install -r requirements-test.txt

# TypeScript/Node
npm install
```

## Run Tests Quickly

### Option 1: Just Unit Tests (5 minutes)

```bash
# Python unit tests
pytest tests/unit -v --cov=src

# TypeScript unit tests
npm run test:unit
```

### Option 2: All Tests Except Docker (15 minutes)

```bash
# Python (unit + integration)
pytest tests/ -v -m "not docker" --cov=src --cov-report=html

# TypeScript (unit only)
npm run test:coverage

# Open coverage report
open tests/htmlcov/index.html  # Python
open tests/coverage/index.html # TypeScript
```

### Option 3: Full Suite (30 minutes)

```bash
# Python - all tests
pytest tests/ -v --cov=src --cov-report=html

# TypeScript - all tests
npm run test:coverage

# CI simulation
npm run ci
```

## Common Commands

### Run Specific Test File

```bash
# Python
pytest tests/unit/test_pocket_tts_service.py -v

# TypeScript
npm test -- modals.test.ts
```

### Run Specific Test

```bash
# Python
pytest tests/unit/test_pocket_tts_service.py::TestPocketTTSService::test_speak_text_basic -v

# TypeScript
npm test -- -t "should render text input field"
```

### Watch Mode (Auto-rerun on changes)

```bash
# Python
pytest tests/ -v --watch  # Requires pytest-watch

# TypeScript
npm run test:watch
```

### Generate Coverage Report

```bash
# Python
pytest tests/ --cov=src --cov-report=html
open tests/htmlcov/index.html

# TypeScript
npm run test:coverage
open tests/coverage/index.html
```

### Run Only Fast Tests

```bash
# Skip slow tests
pytest tests/ -v -m "not slow"
```

### Run Only Docker Tests

```bash
# Docker integration tests (requires Docker)
pytest tests/integration/test_docker_compose.py -v -m docker
```

## Test Organization

### By Category

```bash
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests
pytest -m docker        # Docker tests (slow)
pytest -m slow          # Slow tests
pytest -m mock_api      # Tests with mocked APIs
```

### By Path

```bash
pytest tests/unit                    # All unit tests
pytest tests/unit/test_*.py          # Python unit tests only
pytest tests/unit/*.test.ts          # TypeScript unit tests only
pytest tests/integration             # All integration tests
```

## Debugging

### View Test Output

```bash
# Show print statements
pytest tests/unit/test_pocket_tts_service.py -v -s

# Show logs
pytest tests/ -v --log-cli-level=DEBUG
```

### Run Single Test with Debugger

```bash
# Python with pdb (interactive debugger)
pytest tests/unit/test_pocket_tts_service.py::TestPocketTTSService::test_speak_text_basic -s --pdb

# TypeScript
npm test -- --verbose modals.test.ts
```

## Success Indicators

### Successful Run

```
============ 350 passed in 12.45s, 2 warnings =============
Coverage: 82% lines, 78% branches
```

### Check Coverage Threshold

```bash
# If coverage < 80%, tests fail
# Check report: tests/htmlcov/index.html (Python) or tests/coverage/index.html (TypeScript)
```

## Troubleshooting

### Import Errors

```bash
# Add src to Python path
export PYTHONPATH=/path/to/kyutai-mcp-server/src:$PYTHONPATH
pytest tests/
```

### TypeScript Compilation Errors

```bash
# Build before testing
npm run build
npm test
```

### Async Test Timeouts

```python
# Increase timeout in pytest.ini or test:
@pytest.mark.timeout(30)  # 30 seconds
@pytest.mark.asyncio
async def test_slow_operation():
    pass
```

### Docker Tests Fail

```bash
# Skip Docker tests if Docker not running
pytest tests/ -m "not docker"
```

## Files to Know

```
pytest.ini                      # Test configuration
jest.config.js                  # Jest configuration
requirements-test.txt           # Python dependencies
package.json                    # NPM scripts

tests/conftest.py               # Shared pytest fixtures
tests/fixtures/                 # Mocks and test data
tests/unit/                     # Unit tests
tests/integration/              # Integration tests
tests/README.md                 # Full documentation
TEST_SUITE_SUMMARY.md          # Statistics and coverage
```

## Next Steps

1. **Check coverage**: `tests/htmlcov/index.html` (Python) or `tests/coverage/index.html` (TypeScript)
2. **Read full guide**: `tests/README.md`
3. **Understand mocks**: `tests/fixtures/mock_kyutai.py` and `tests/fixtures/mock-mcp.ts`
4. **View statistics**: `TEST_SUITE_SUMMARY.md`

## CI/CD Pipeline

Tests run automatically on:
- Push to `main` or `develop` branches
- All pull requests

View results: GitHub Actions → Test Suite workflow

## Support

For detailed documentation, see:
- `tests/README.md` - Comprehensive guide
- `TEST_SUITE_SUMMARY.md` - Statistics, coverage, next steps
- Architecture docs in `decisions/`

---

**Current Test Coverage**: 600+ test cases across unit and integration tests
**Target Coverage**: 80%+ lines, 78%+ branches
**Status**: ✅ Ready for Phase 4 validation
