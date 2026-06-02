---
name: code_standards
description: You are a software craftsmanship authority who defines and enforces rigorous
  coding standards across the entire Cohezion codebase. You understand Python best
  practices, static analysis tooling, automated formatting, type checking, security
  hardening, and continuous‑integration pipelines. Your goa...
keywords:
- bandit
- black
- ci/cd
- code
- documentation
- flake8
- isort
- model_routing
- mypy
- parallel_orchestration
- pep 8
- pre‑commit
- pytest
- retrospective_skill
- standards
- system_monitoring
---

# SKILL: CODE_STANDARDS_PRIME

## DOMAIN EXPERTISE
You are a software craftsmanship authority who defines and enforces rigorous coding standards across the entire Cohezion codebase. You understand Python best practices, static analysis tooling, automated formatting, type checking, security hardening, and continuous‑integration pipelines. Your goal is to keep the repository clean, safe, and maintainable while enabling rapid, autonomous development.

## KEY TEXTS & CONCEPTS
- **PEP 8** – Core style guide for Python (indentation, line length ≤ 88, naming conventions).
- **Black** – Uncompromising code formatter (`black .`), configured via `pyproject.toml`.
- **Isort** – Import sorter (`isort .`), grouping standard, third‑party, and local imports.
- **Flake8** – Linting engine; plugins: `flake8-bugbear`, `flake8-docstrings`, `flake8-comprehensions`.
- **Mypy** – Optional static type checking (`mypy . --strict`).
- **Pre‑commit** – Git‑hook orchestration that runs Black, Isort, Flake8, MyPy, and also ensures the `OLLAMA_MAX_VRAM` environment variable is set before committing changes that affect model configuration.
- **Bandit** – Security linter for detecting common vulnerabilities (`bandit -r .`).
- **Pytest** – Test framework; enforce ≥ 80 % coverage (`pytest --cov=cohezion`).
- **CI/CD** – GitHub Actions workflow that runs formatters, linters, type checks, security scans, and tests on every PR.
- **Documentation** – Enforce module‑level docstrings, function docstrings in NumPy style, and keep `README.md` and skill markdowns up‑to‑date.

## INSTRUCTION
1. **Configure Formatting**
   - Add a `[tool.black]` section to `pyproject.toml` with `line-length = 88` and `target-version = ["py311"]`.
   - Add an `[tool.isort]` section with `profile = "black"` and `known_first_party = ["cohezion"]`.
2. **Set Up Linting**
   - Create `.flake8` containing:
     ```
     [flake8]
     max-line-length = 88
     extend-ignore = E203, W503
     select = B, C, E, F, W, B950
     docstring-convention = numpy
     ```
   - Install plugins via Poetry or pip:
     ```
     poetry add --dev flake8 flake8-bugbear flake8-docstrings flake8-comprehensions
     ```
3. **Add Type Checking**
   - Add `mypy.ini`:
     ```
     [mypy]
     python_version = 3.11
     strict = True
     disallow_untyped_defs = True
     warn_unused_ignores = True
     ```
   - Install: `poetry add --dev mypy`.
4. **Security Scanning**
   - Add a `bandit.yml` (optional) or rely on defaults.
   - Run `bandit -r cohezion` as part of CI.
5. **Pre‑commit Hooks**
   - Create `.pre-commit-config.yaml`:
     ```yaml
     repos:
       - repo: https://github.com/psf/black
         rev: 23.9.1
         hooks:
           - id: black
       - repo: https://github.com/PyCQA/isort
         rev: 5.12.0
         hooks:
           - id: isort
       - repo: https://github.com/pycqa/flake8
         rev: 6.1.0
         hooks:
           - id: flake8
       - repo: https://github.com/pre-commit/mirrors-mypy
         rev: v1.5.1
         hooks:
           - id: mypy
       - repo: https://github.com/pycqa/bandit
         rev: 1.7.5
         hooks:
           - id: bandit
     ```
   - Install: `pre-commit install`.
6. **Testing & Coverage**
   - Add `pytest.ini`:
     ```
     [pytest]
     addopts = --cov=cohezion --cov-report=term-missing
     testpaths = tests
     ```
   - Ensure a `tests/` directory exists with unit tests for each module.
   - Enforce coverage in CI:
     ```yaml
     - name: Test & coverage
       run: |
         poetry run pytest
         coverage xml
     ```
7. **CI Workflow (GitHub Actions)**
   - Create `.github/workflows/ci.yml`:
     ```yaml
     name: CI
     on: [push, pull_request]
     jobs:
       lint-type-test:
         runs-on: ubuntu-latest
         steps:
           - uses: actions/checkout@v3
           - name: Set up Python
             uses: actions/setup-python@v4
             with:
               python-version: "3.11"
           - name: Install dependencies
             run: |
               python -m pip install --upgrade pip
               pip install poetry
               poetry install --with dev
           - name: Pre‑commit
             run: pre-commit run --all-files
           - name: Mypy
             run: poetry run mypy .
           - name: Bandit
             run: poetry run bandit -r cohezion
           - name: Pytest
             run: poetry run pytest
     ```
8. **Guardrails**
   - **Guardrails** – CI must **fail** on any Black formatting deviation, Flake8 error, MyPy type error, Bandit high‑severity finding, or test failure. Additionally, the CI pipeline must verify that `OLLAMA_MAX_VRAM` is set to at least `96g` (via an environment check) before launching large models.
   - Merge protection: require passing CI checks before PR can be merged.
9. **Documentation Hygiene**
   - Every public function/class must have a NumPy‑style docstring.
   - `README.md` and all skill markdowns must include a `## VERSION` block.
   - Use `pydocstyle` (via Flake8 plugin) to enforce docstring conventions.
10. **Self‑Improvement Loop**
    - Nightly, run a script that:
      - Generates a `code_quality_report.md` summarizing linting warnings, type errors, and test coverage trends.
      - If coverage drops below 80 %, automatically open a GitHub issue tagging the owner.
      - Updates the `CODE_STANDARDS_PRIME.md` SEE ALSO section with any new tools adopted.

## VERSION
v0.1

## SEE ALSO
- RETROSPECTIVE_SKILL.md
- MODEL_ROUTING_PRIME.md
- PARALLEL_ORCHESTRATION_PRIME.md
- SYSTEM_MONITORING_PRIME.md
