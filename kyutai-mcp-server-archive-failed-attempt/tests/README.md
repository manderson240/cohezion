# Kyutai MCP Server & Obsidian Plugin Test Suite

Comprehensive test suite for the Kyutai MCP Server and Obsidian plugin, covering unit tests, integration tests, and performance benchmarks.

## Directory Structure

```
tests/
├── unit/                          # Unit tests
│   ├── test_pocket_tts_service.py   # PocketTTS service tests
│   ├── test_config.py               # Configuration management tests
│   ├── test_tools.py                # MCP tool tests
│   ├── test_health_monitor.py       # Health monitoring tests
│   ├── modals.test.ts               # Obsidian modal tests
│   ├── settings.test.ts             # Plugin settings tests
│   └── mcp-client.test.ts           # MCP client tests
├── integration/                   # Integration tests
│   ├── test_mcp_server.py           # MCP server integration
│   ├── test_docker_compose.py       # Docker container tests
│   ├── test_kyutai_api.py           # Kyutai API integration
│   └── plugin.test.ts               # Obsidian plugin integration
├── fixtures/                      # Test fixtures & mocks
│   ├── mock_kyutai.py               # Kyutai API mocks
│   ├── test_data.py                 # Test data & constants
│   └── mock-mcp.ts                  # MCP client mocks
├── conftest.py                    # Pytest configuration
├── setup.ts                       # Jest setup
├── coverage/                      # Coverage reports (generated)
└── README.md                      # This file
```

## Test Coverage

### MCP Server Tests

**Unit Tests (80%+ coverage target):**
- `test_pocket_tts_service.py`: TTS synthesis, voice config, audio formats
- `test_config.py`: YAML parsing, env var overrides, validation
- `test_tools.py`: All 7 MCP tools (speak_text, transcribe_audio, etc.)
- `test_health_monitor.py`: Health checks, model status, metrics

**Integration Tests:**
- `test_mcp_server.py`: Server startup, tool invocation, error handling
- `test_docker_compose.py`: Container lifecycle, networking, volumes
- `test_kyutai_api.py`: API auth, request/response, error scenarios

### Obsidian Plugin Tests

**Unit Tests:**
- `modals.test.ts`: SpeakTextModal, TranscribeAudioModal, VoiceSelectionModal, ConfigurationModal
- `settings.test.ts`: Settings loading, persistence, validation, UI
- `mcp-client.test.ts`: Client connection, tool invocation, call tracking

**Integration Tests:**
- `plugin.test.ts` (placeholder): Full plugin integration in Obsidian

## Running Tests

### Python Tests (MCP Server)

```bash
# All tests with coverage report
pytest tests/ -v --cov=src --cov-report=html

# Unit tests only
pytest tests/unit -v --cov=src

# Integration tests only
pytest tests/integration -v

# Specific test file
pytest tests/unit/test_pocket_tts_service.py -v

# Specific test function
pytest tests/unit/test_pocket_tts_service.py::TestPocketTTSService::test_speak_text_basic -v

# Markers
pytest -m "unit" -v              # Unit tests only
pytest -m "integration" -v       # Integration tests only
pytest -m "docker" -v            # Docker tests only
pytest -m "not slow" -v          # Skip slow tests
```

### TypeScript Tests (Obsidian Plugin)

```bash
# All tests with coverage
npm run test:coverage

# Watch mode
npm run test:watch

# Unit tests only
npm run test:unit

# Integration tests only
npm run test:integration

# Specific test file
npm test modals.test.ts

# Coverage report
npm run test:coverage -- --coverage
```

### Combined Testing

```bash
# Run all tests (Python + TypeScript)
npm run test:all

# CI pipeline
npm run ci  # Lint + type check + coverage
```

## Test Categories

### By Type

1. **Unit Tests** (80%+ coverage)
   - `@pytest.mark.unit` / Jest by default
   - Isolated, fast, no external dependencies
   - Mock all external services

2. **Integration Tests**
   - `@pytest.mark.integration`
   - Test component interactions
   - Use real MCP server and services

3. **Docker Tests**
   - `@pytest.mark.docker`
   - Require Docker Compose running
   - Test containerized deployment

4. **Performance Tests**
   - `@pytest.mark.benchmark` (Jest)
   - Measure response latency
   - Track throughput

5. **Slow Tests**
   - `@pytest.mark.slow`
   - Long-running scenarios
   - Excluded from quick runs

### By Feature

**TTS (Text-to-Speech)**
- Basic synthesis
- Voice selection
- Speed control
- Audio format conversion
- Long text handling

**STT (Speech-to-Text)**
- Audio transcription
- Timestamp extraction
- Language detection
- Multiple speaker handling

**Configuration**
- YAML parsing
- Environment overrides
- Validation
- Persistence

**Health Monitoring**
- Model availability
- Service status
- Metrics collection
- Alert generation

**Obsidian Plugin**
- Modal rendering
- Settings management
- MCP communication
- User workflows

## Test Data

### Fixtures

```python
# Use pytest fixtures for common test data
@pytest.mark.asyncio
async def test_with_fixtures(sample_texts, sample_voices, sample_models):
    """Example test using provided fixtures."""
    result = await tts_service.speak(
        sample_texts["short"],
        voice_id=sample_voices["character_1"]["voice_id"]
    )
    assert result["status"] == "success"
```

### Mock Objects

```python
# Mock Kyutai APIs without external calls
from tests.fixtures.mock_kyutai import MockKyutaiTTSAPI, MockKyutaiSTTAPI

tts_api = MockKyutaiTTSAPI()
response = await tts_api.speak("Hello world")
assert response["status"] == "success"
```

### TypeScript Mocks

```typescript
// Mock MCP client for plugin testing
import { setupMockMCPClient } from '../fixtures/mock-mcp';

const client = setupMockMCPClient();
const response = await client.callTool('speak_text', { text: 'Test' });
expect(response.status).toBe('success');
```

## Configuration

### pytest.ini

```ini
[pytest]
testpaths = tests
python_files = test_*.py
addopts = -v --cov=src --cov-report=html
markers =
    unit: Unit tests
    integration: Integration tests
    docker: Docker tests
    slow: Slow tests
```

### jest.config.js

```javascript
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  testMatch: ['<rootDir>/tests/**/*.test.ts'],
  collectCoverageFrom: ['src/**/*.ts'],
  coverageThreshold: { global: { lines: 80 } }
};
```

## Coverage Reports

### Python Coverage

```bash
pytest tests/ --cov=src --cov-report=html
# Open tests/htmlcov/index.html
```

### TypeScript Coverage

```bash
npm run test:coverage
# Open tests/coverage/index.html
```

### Coverage Requirements

- **Minimum:** 80% line coverage
- **Target:** 90%+ coverage for critical paths
- **Excluded:** Generated code, type definitions, test utilities

## Continuous Integration

### GitHub Actions Pipeline

```yaml
- Run lint: eslint, flake8
- Type check: mypy, tsc
- Unit tests: pytest, jest
- Integration tests: Docker Compose
- Coverage reports: HTML + LCOV
```

### Pre-commit Hooks

```bash
# Install
pre-commit install

# Runs: lint, format, type check
git commit -m "message"
```

## Debugging Tests

### Python Debugging

```bash
# Run single test with pdb
pytest tests/unit/test_pocket_tts_service.py::TestPocketTTSService::test_speak_text_basic -s --pdb

# Enable logging
pytest tests/ -v --log-cli-level=DEBUG

# Print output during tests
pytest tests/ -v -s
```

### TypeScript Debugging

```bash
# Run with verbose output
npm test -- --verbose

# Debug in IDE
# Add breakpoints, then run: node --inspect-brk node_modules/jest/bin/jest.js

# Chrome DevTools
node --inspect-brk node_modules/jest/bin/jest.js
# Open chrome://inspect
```

## Common Issues & Solutions

### Issue: Import errors in Python tests

```bash
# Solution: Ensure src is in PYTHONPATH
export PYTHONPATH=/path/to/kyutai-mcp-server/src:$PYTHONPATH
pytest tests/
```

### Issue: TypeScript compilation errors

```bash
# Solution: Build before running tests
npm run build
npm test
```

### Issue: Async test timeouts

```python
# Add timeout parameter
@pytest.mark.asyncio
async def test_async_operation(self):
    # Increase timeout for slow operations
    async with asyncio.timeout(30):
        result = await slow_operation()
```

### Issue: Docker tests fail without Docker

```bash
# Skip Docker tests
pytest tests/ -m "not docker"
```

## Performance Benchmarks

### Baseline Metrics (to capture at start of Phase B)

```
TTS Synthesis:
  - Latency: < 100ms
  - Throughput: > 10 requests/sec

STT Transcription:
  - Latency: < 200ms (short audio)
  - Throughput: > 5 requests/sec

Model Loading:
  - Time: < 5s for pocket-tts
  - Memory: < 1GB

API Communication:
  - Connection setup: < 500ms
  - Request/response: < 100ms
```

### Running Benchmarks

```bash
# Python benchmarks
pytest tests/ -m "benchmark" -v

# TypeScript benchmarks
npm test -- --testMatch="**/*.bench.ts"
```

## Test Maintenance

### Adding New Tests

1. **Identify test category** (unit, integration, docker)
2. **Use fixtures** for common data
3. **Mock external dependencies**
4. **Follow naming** conventions: `test_<feature>_<scenario>`
5. **Add docstrings** explaining test purpose
6. **Update markers** for categorization

### Updating Mocks

- Update `tests/fixtures/mock_kyutai.py` when Kyutai API changes
- Update `tests/fixtures/mock-mcp.ts` when MCP protocol changes
- Update `tests/fixtures/test_data.py` with new test scenarios

### Refactoring Tests

```bash
# Use black for Python formatting
black tests/

# Use prettier for TypeScript
prettier --write tests/**/*.ts

# Check for test duplication
# Consolidate into shared fixtures or parameterized tests
```

## References

- [pytest Documentation](https://docs.pytest.org/)
- [Jest Documentation](https://jestjs.io/)
- [Obsidian Plugin Testing](https://docs.obsidian.md/)
- [MCP Server Architecture](../decisions/kyutai-mcp-server-architecture.md)
- [Obsidian Plugin Architecture](../decisions/kyutai-obsidian-plugin-architecture.md)

## Contact

For questions or issues with the test suite, reach out to the Cohezion team.
