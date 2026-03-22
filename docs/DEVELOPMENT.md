# Development Guide

Complete guide for contributors and developers extending Kyutai MCP Server and Obsidian Plugin.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Project Structure](#project-structure)
3. [Development Environment](#development-environment)
4. [Code Standards](#code-standards)
5. [Running Tests](#running-tests)
6. [Building & Packaging](#building--packaging)
7. [Adding New Tools](#adding-new-tools)
8. [Debugging](#debugging)
9. [Pull Request Process](#pull-request-process)
10. [Performance Optimization](#performance-optimization)

---

## Getting Started

### Prerequisites

- Python 3.9+ (MCP Server)
- Node.js 18+ (Obsidian Plugin)
- Git 2.20+
- Docker (optional, for isolated environments)

### Clone Repository

```bash
git clone https://github.com/kyutai-labs/kyutai-mcp-obsidian
cd kyutai-mcp-obsidian
```

### Setup Development Environment

**MCP Server:**
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# or
.\venv\Scripts\activate   # Windows

# Install dev dependencies
pip install -e ".[dev]"
pip install pytest pytest-cov pytest-asyncio black flake8 mypy
```

**Obsidian Plugin:**
```bash
cd obsidian-plugin
npm install

# Install dev tools
npm install --save-dev typescript @types/obsidian @types/node esbuild
```

### Verify Setup

```bash
# MCP Server
python -m pytest tests/unit/test_models.py -v

# Obsidian Plugin
npm run test
```

---

## Project Structure

### MCP Server Layout

```
kyutai-mcp/
├── src/
│   ├── kyutai_mcp/
│   │   ├── __init__.py           # Package init
│   │   ├── server.py             # FastAPI app
│   │   ├── tools.py              # MCP tool definitions
│   │   ├── config.py             # Configuration
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── base.py           # Base model class
│   │   │   ├── tts.py            # TTS wrappers
│   │   │   ├── stt.py            # STT wrappers
│   │   │   ├── manager.py        # Model lifecycle
│   │   │   └── registry.py       # Model registry
│   │   ├── audio/
│   │   │   ├── __init__.py
│   │   │   ├── pipeline.py       # Audio processing
│   │   │   ├── codecs.py         # Format conversion
│   │   │   └── streaming.py      # WebSocket handling
│   │   ├── resources/
│   │   │   ├── __init__.py
│   │   │   ├── gpu.py            # GPU management
│   │   │   ├── memory.py         # Memory allocation
│   │   │   └── pooling.py        # Thread pooling
│   │   ├── monitoring/
│   │   │   ├── __init__.py
│   │   │   ├── health.py         # Health checks
│   │   │   ├── metrics.py        # Prometheus
│   │   │   └── logging.py        # Structured logging
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── helpers.py        # Utility functions
│   └── __main__.py               # Entry point
├── tests/
│   ├── unit/
│   │   ├── test_models.py
│   │   ├── test_audio_pipeline.py
│   │   └── test_config.py
│   ├── integration/
│   │   ├── test_server.py
│   │   ├── test_tts.py
│   │   └── test_stt.py
│   ├── fixtures/
│   │   ├── audio_samples/
│   │   └── mock_models.py
│   └── conftest.py
├── requirements.txt
├── setup.py
├── pytest.ini
├── .flake8
├── mypy.ini
└── README.md
```

### Obsidian Plugin Layout

```
obsidian-plugin/
├── src/
│   ├── main.ts                  # Plugin entry
│   ├── manifest.json            # Plugin metadata
│   ├── styles.css               # Styling
│   ├── client.ts                # MCP client
│   ├── settings.ts              # Settings pane
│   ├── ribbon.ts                # Ribbon commands
│   ├── modals/
│   │   ├── SynthesizeModal.ts
│   │   ├── TranscribeModal.ts
│   │   ├── VoiceModal.ts
│   │   └── BaseModal.ts
│   ├── components/
│   │   ├── VoiceSelector.ts
│   │   ├── AudioUploader.ts
│   │   └── ResultsDisplay.ts
│   └── utils/
│       ├── http.ts
│       ├── audio.ts
│       └── validation.ts
├── tests/
│   ├── unit/
│   │   ├── client.test.ts
│   │   └── modals.test.ts
│   ├── integration/
│   │   └── e2e.test.ts
│   └── fixtures/
│       └── mock-server.ts
├── esbuild.config.js            # Build config
├── tsconfig.json                # TS config
├── package.json
├── jest.config.js
└── README.md
```

---

## Development Environment

### VS Code Setup

**Recommended Extensions:**
- Python (Microsoft)
- Pylance
- Prettier - Code formatter
- ESLint
- TypeScript Vue Plugin

**.vscode/settings.json:**
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.formatting.provider": "black",
  "[python]": {
    "editor.defaultFormatter": "ms-python.python",
    "editor.formatOnSave": true
  },
  "[typescript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
    "editor.formatOnSave": true
  }
}
```

### IDE Debugging

**Python (in VS Code):**

Create `.vscode/launch.json`:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "MCP Server",
      "type": "python",
      "request": "launch",
      "module": "kyutai_mcp.server",
      "console": "integratedTerminal",
      "cwd": "${workspaceFolder}",
      "env": {
        "MCP_LOG_LEVEL": "DEBUG"
      }
    },
    {
      "name": "Tests",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": ["tests/", "-v"],
      "console": "integratedTerminal"
    }
  ]
}
```

**TypeScript (Node debugging):**

Build and test plugin:
```bash
npm run dev          # Continuous build
npm run test:watch   # Continuous testing
```

---

## Code Standards

### Python (Server)

**Style Guide:** PEP 8 via Black

```bash
# Format code
black src/

# Lint
flake8 src/ tests/

# Type checking
mypy src/
```

**Code Template:**
```python
"""Module docstring describing purpose."""

from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

class MyModel:
    """Class docstring with purpose and usage."""

    def __init__(self, config: dict):
        """Initialize with configuration.

        Args:
            config: Configuration dictionary

        Raises:
            ValueError: If config invalid
        """
        self.config = config

    async def process(self, data: bytes) -> str:
        """Process input data asynchronously.

        Args:
            data: Input binary data

        Returns:
            Processed result string

        Raises:
            RuntimeError: If processing fails
        """
        logger.info("Processing %d bytes", len(data))
        return await self._run_inference(data)
```

**Type Hints Required:**
```python
# Good
def synthesize(text: str, voice_id: str) -> bytes:
    pass

async def transcribe(audio: bytes) -> dict[str, Any]:
    pass

# Bad - avoid
def synthesize(text, voice_id):
    pass
```

### TypeScript (Plugin)

**Style Guide:** ESLint + Prettier

```bash
# Format
npx prettier --write src/

# Lint
npx eslint src/

# Type check
npx tsc --noEmit
```

**Code Template:**
```typescript
/**
 * Module description for Obsidian plugin.
 */

import { Plugin, Modal, Setting, App } from 'obsidian';

export class MyModal extends Modal {
  /**
   * Constructor with Obsidian app reference.
   * @param app - Obsidian app instance
   */
  constructor(app: App) {
    super(app);
  }

  /**
   * Render modal content.
   */
  onOpen(): void {
    const { contentEl } = this;
    contentEl.createEl('h1', { text: 'My Modal' });

    new Setting(contentEl)
      .setName('Setting name')
      .setDesc('Setting description')
      .addText((text) =>
        text
          .setPlaceholder('Enter text...')
          .onChange((value) => {
            console.log('Value:', value);
          })
      );
  }

  /**
   * Clean up when modal closes.
   */
  onClose(): void {
    const { contentEl } = this;
    contentEl.empty();
  }
}
```

### Git Commit Messages

**Format:**
```
<type>: <subject>

<body>

Fixes #<issue_number>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `test`: Test additions
- `refactor`: Code refactoring
- `perf`: Performance improvement
- `chore`: Build, deps, etc.

**Example:**
```
feat: Add Moshi full-duplex support

Implement WebSocket streaming for Moshi 7B model.
Includes real-time audio handling and echo cancellation.

Fixes #123
```

---

## Running Tests

### MCP Server Tests

**Unit Tests:**
```bash
pytest tests/unit/ -v
pytest tests/unit/test_models.py -v  # Specific file
pytest tests/unit/ -k "test_tts"     # By pattern
```

**Integration Tests:**
```bash
pytest tests/integration/ -v
pytest tests/integration/test_server.py::test_synthesize_text -v
```

**With Coverage:**
```bash
pytest --cov=src --cov-report=html

# Open htmlcov/index.html
```

**Test Template:**
```python
import pytest
from kyutai_mcp.models import TTSModel

@pytest.fixture
def tts_model():
    """Fixture providing TTS model."""
    return TTSModel.load_model()

def test_synthesize_basic(tts_model):
    """Test basic text synthesis."""
    audio = tts_model.synthesize("Hello world")
    assert isinstance(audio, bytes)
    assert len(audio) > 0

@pytest.mark.asyncio
async def test_synthesize_async(tts_model):
    """Test async synthesis."""
    audio = await tts_model.synthesize_async("Hello async")
    assert isinstance(audio, bytes)

def test_synthesize_empty_text(tts_model):
    """Test synthesis with empty text."""
    with pytest.raises(ValueError):
        tts_model.synthesize("")

@pytest.mark.parametrize("text", ["hello", "世界", "Привет"])
def test_synthesize_multilingual(tts_model, text):
    """Test multilingual synthesis."""
    audio = tts_model.synthesize(text)
    assert isinstance(audio, bytes)
```

### Obsidian Plugin Tests

**Unit Tests:**
```bash
npm run test
npm run test -- --watch        # Watch mode
npm run test -- --coverage     # With coverage
```

**Test Template:**
```typescript
import { describe, it, expect, beforeEach } from '@jest/globals';
import { MCPClient } from '../client';

describe('MCPClient', () => {
  let client: MCPClient;

  beforeEach(() => {
    client = new MCPClient('http://localhost:8000');
  });

  it('should connect to server', async () => {
    const status = await client.getStatus();
    expect(status.status).toBe('healthy');
  });

  it('should synthesize text', async () => {
    const audio = await client.synthesizeText('Hello');
    expect(audio).toBeInstanceOf(Blob);
  });

  it('should handle errors gracefully', async () => {
    await expect(
      client.synthesizeText(''.repeat(5000))
    ).rejects.toThrow('Text too long');
  });
});
```

---

## Building & Packaging

### MCP Server Package

**Build wheel:**
```bash
pip install build
python -m build

# Output: dist/kyutai_mcp-0.1.0-py3-none-any.whl
```

**Install from wheel:**
```bash
pip install dist/kyutai_mcp-0.1.0-py3-none-any.whl
```

**setup.py:**
```python
from setuptools import setup, find_packages

setup(
    name='kyutai-mcp',
    version='0.1.0',
    description='Kyutai MCP Server for Obsidian',
    author='Kyutai Labs',
    package_dir={'': 'src'},
    packages=find_packages('src'),
    python_requires='>=3.9',
    install_requires=[
        'fastapi>=0.104.0',
        'uvicorn>=0.24.0',
        'torch>=2.0.0',
        'transformers>=4.30.0',
        'pocket-tts>=1.0.0',
    ],
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-asyncio>=0.21.0',
            'black>=23.0.0',
            'flake8>=6.0.0',
            'mypy>=1.0.0',
        ],
    },
)
```

### Obsidian Plugin Package

**Build plugin:**
```bash
npm run build

# Output: esbuild.js, manifest.json, styles.css
```

**Package for distribution:**
```bash
npm run build
zip kyutai-mcp-plugin-0.1.0.zip manifest.json styles.css esbuild.js

# Upload to releases
```

**package.json:**
```json
{
  "name": "kyutai-mcp",
  "version": "0.1.0",
  "description": "Kyutai MCP Plugin for Obsidian",
  "scripts": {
    "dev": "esbuild src/main.ts --bundle --external:obsidian --outfile=esbuild.js --watch",
    "build": "esbuild src/main.ts --bundle --external:obsidian --outfile=esbuild.js",
    "test": "jest",
    "test:watch": "jest --watch"
  },
  "dependencies": {
    "obsidian": "latest",
    "tslib": "2.4.0"
  },
  "devDependencies": {
    "@types/node": "^16.0.0",
    "@typescript-eslint/eslint-plugin": "5.29.0",
    "@typescript-eslint/parser": "5.29.0",
    "esbuild": "0.13.12",
    "obsidian": "latest",
    "tslib": "2.4.0",
    "typescript": "4.7.4"
  }
}
```

---

## Adding New Tools

### Example: Adding a New MCP Tool

**Step 1: Define Tool Specification**

```python
# src/kyutai_mcp/tools.py

from pydantic import BaseModel

class GetLanguagesRequest(BaseModel):
    """Request to list supported languages."""
    pass

class LanguageInfo(BaseModel):
    """Language information."""
    code: str
    name: str
    models: list[str]

class GetLanguagesResponse(BaseModel):
    """List of supported languages."""
    languages: list[LanguageInfo]
```

**Step 2: Implement Tool Handler**

```python
# src/kyutai_mcp/tools.py

async def get_languages(request: GetLanguagesRequest) -> GetLanguagesResponse:
    """Get list of supported languages.

    Returns:
        List of language objects with models
    """
    languages = [
        LanguageInfo(
            code="en",
            name="English",
            models=["stt-1b-en_fr", "stt-2.6b"]
        ),
        LanguageInfo(
            code="fr",
            name="French",
            models=["stt-1b-en_fr"]
        ),
    ]
    return GetLanguagesResponse(languages=languages)
```

**Step 3: Register Tool in Server**

```python
# src/kyutai_mcp/server.py

@app.post("/get-languages")
async def handle_get_languages(request: GetLanguagesRequest) -> GetLanguagesResponse:
    """MCP endpoint for get_languages tool."""
    return await get_languages(request)
```

**Step 4: Update Tool Registry**

```python
# src/kyutai_mcp/server.py

REGISTERED_TOOLS = {
    "synthesize_text": {
        "description": "Convert text to speech",
        "input_schema": SynthesizeTextRequest.schema(),
        "output_schema": bytes,
    },
    # ... other tools ...
    "get_languages": {
        "description": "Get list of supported languages",
        "input_schema": GetLanguagesRequest.schema(),
        "output_schema": GetLanguagesResponse.schema(),
    },
}
```

**Step 5: Test Tool**

```python
# tests/unit/test_languages.py

import pytest
from kyutai_mcp.tools import get_languages, GetLanguagesRequest

@pytest.mark.asyncio
async def test_get_languages():
    """Test language listing."""
    request = GetLanguagesRequest()
    response = await get_languages(request)

    assert len(response.languages) >= 2
    assert any(lang.code == "en" for lang in response.languages)
    assert any(lang.code == "fr" for lang in response.languages)

@pytest.mark.asyncio
async def test_language_has_models():
    """Test that languages have associated models."""
    request = GetLanguagesRequest()
    response = await get_languages(request)

    for lang in response.languages:
        assert len(lang.models) > 0
```

---

## Debugging

### Debug MCP Server

**Enable Debug Logging:**
```bash
MCP_LOG_LEVEL=DEBUG python -m kyutai_mcp.server
```

**Attach Debugger (VS Code):**

1. Set breakpoint in code
2. Run debug config: "MCP Server"
3. Step through execution

**Print Debugging:**
```python
import logging
logger = logging.getLogger(__name__)

logger.debug("Debug message: %s", variable)
logger.info("Info: %s", result)
logger.warning("Warning: %s", issue)
logger.error("Error: %s", exception)
```

### Debug Obsidian Plugin

**Obsidian Console:**
- Ctrl+Shift+I (Windows/Linux) or Cmd+Shift+I (macOS)
- View → Toggle Developer Tools
- Console tab shows plugin output

**Print Debugging:**
```typescript
console.log('Debug:', variable);
console.warn('Warning:', issue);
console.error('Error:', error);
```

**Network Debugging:**
- DevTools → Network tab
- See all MCP requests/responses
- Check headers, timing, payload

### Performance Profiling

**Python (cProfile):**
```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Code to profile...
result = model.synthesize("Hello")

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)  # Top 20
```

**JavaScript (DevTools):**
1. DevTools → Performance tab
2. Click record
3. Perform action
4. Stop and analyze

---

## Pull Request Process

### Before Submitting PR

1. **Format Code:**
   ```bash
   # Python
   black src/ tests/
   flake8 src/
   mypy src/

   # TypeScript
   npm run lint
   npm run format
   ```

2. **Run Tests:**
   ```bash
   pytest tests/ -v
   npm run test
   ```

3. **Update Docs:**
   - Add/update docstrings
   - Update CHANGELOG.md
   - Update README if API changes

4. **Commit:**
   ```bash
   git add .
   git commit -m "feat: your feature description"
   ```

5. **Push:**
   ```bash
   git push origin your-branch
   ```

### PR Template

```markdown
## Description
Brief description of changes.

## Type of Change
- [ ] New feature
- [ ] Bug fix
- [ ] Documentation
- [ ] Performance

## Testing
- [ ] Unit tests added
- [ ] Integration tests pass
- [ ] Manual testing done

## Checklist
- [ ] Code formatted
- [ ] Tests passing
- [ ] Docs updated
- [ ] No breaking changes
```

### Code Review

Reviewers will check:
- Code quality and style
- Test coverage
- Documentation completeness
- Performance impact
- Security considerations

---

## Performance Optimization

### Profiling Tools

**Python:**
```bash
# Memory profiling
pip install memory-profiler
python -m memory_profiler script.py

# GPU profiling
pip install py-spy
py-spy record -o profile.svg python script.py
```

**JavaScript:**
```bash
npm install --save-dev webpack-bundle-analyzer
webpack-bundle-analyzer dist/stats.json
```

### Common Optimizations

**Python (Server):**
- Cache model weights
- Use async/await for I/O
- Batch inference when possible
- Profile before optimizing

**TypeScript (Plugin):**
- Lazy load modals
- Debounce event handlers
- Use virtual scrolling for lists
- Minimize bundle size

---

**Last Updated**: 2026-02-10
**Version**: 0.1.0-alpha
