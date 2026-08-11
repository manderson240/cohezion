```markdown
# cohezion Development Patterns

> Auto-generated skill from repository analysis

## Overview

This skill teaches you how to contribute effectively to the `cohezion` Python codebase. You'll learn the project's coding conventions, commit patterns, and the main development workflows, including how to add new inference features, update model profiles and routing, and follow test-driven development practices. The guide covers file organization, code style, and how to ensure your changes are robustly tested.

## Coding Conventions

- **File Naming:** Use `snake_case` for all Python files.
  - Example: `capability_profile.py`, `route_by_capability.py`
- **Import Style:** Use relative imports within the package.
  - Example:
    ```python
    from .registry import ModelRegistry
    from .default_profiles import DEFAULT_PROFILES
    ```
- **Export Style:** Use named exports; avoid wildcard imports.
  - Example:
    ```python
    # In src/cohezion/inference/registry.py
    class ModelRegistry:
        ...
    ```
- **Commit Messages:** Follow the [Conventional Commits](https://www.conventionalcommits.org/) standard, using the `feat` prefix for new features.
  - Example:
    ```
    feat: add capability profile for new transformer model
    ```

## Workflows

### Add New Inference Feature with Tests
**Trigger:** When you want to add a new inference capability, router, or profile to the system.  
**Command:** `/new-inference-feature`

1. Create or modify core inference logic in `src/cohezion/inference/` (e.g., `capability_profile.py`, `route_by_capability.py`, `default_profiles.py`).
    ```python
    # src/cohezion/inference/capability_profile.py
    class NewCapabilityProfile:
        ...
    ```
2. Update or extend registry/model harness logic (e.g., `registry.py`, `model_card_harness.py`, `fleet.py`) to integrate the new feature.
    ```python
    # src/cohezion/inference/registry.py
    from .capability_profile import NewCapabilityProfile
    registry.register(NewCapabilityProfile())
    ```
3. Write new tests in `tests/inference/` for the new feature, covering both positive and negative cases.
    ```python
    # tests/inference/test_capability_profile.py
    def test_new_capability_profile_behavior():
        ...
    ```
4. Run and verify tests (e.g., with `pytest` or `make test-fast`) and lint checks.
5. Document or note follow-up integration points if the feature is foundational.

---

### Add or Update Model Profiles and Routing
**Trigger:** When you want to introduce new model profiles or improve routing based on model capabilities.  
**Command:** `/update-model-profiles`

1. Create or update profile data in `src/cohezion/inference/default_profiles.py`.
    ```python
    NEW_PROFILE = {
        "name": "advanced-transformer",
        "capabilities": ["summarization", "translation"]
    }
    ```
2. Integrate profiles into registry entries (`src/cohezion/inference/registry.py`).
    ```python
    from .default_profiles import NEW_PROFILE
    registry.add_profile(NEW_PROFILE)
    ```
3. Update or add routing logic (`src/cohezion/inference/route_by_capability.py`) to utilize new profiles.
    ```python
    def route_by_capability(request):
        # Use NEW_PROFILE in routing logic
        ...
    ```
4. Write or update tests in `tests/inference/` to validate profile correctness and routing behavior.
    ```python
    # tests/inference/test_route_by_capability.py
    def test_routing_with_new_profile():
        ...
    ```
5. Verify all tests and lint checks pass.

---

### Feature Development with Test-First (TDD)
**Trigger:** When you want to ensure robust, test-driven feature development.  
**Command:** `/feature-tdd`

1. Write new test cases in `tests/inference/` for the intended feature (RED).
    ```python
    # tests/inference/test_new_feature.py
    def test_new_feature_behavior():
        assert new_feature() == expected_result  # This should fail initially
    ```
2. Implement or modify feature logic in `src/cohezion/inference/` or related modules.
    ```python
    # src/cohezion/inference/new_feature.py
    def new_feature():
        return expected_result
    ```
3. Iterate until all new tests pass (GREEN).
4. Verify no regressions in existing tests.
5. Document follow-up work if the feature is foundational.

## Testing Patterns

- **Framework:** The specific test framework is unknown, but Python tests are placed in `tests/inference/` and follow the `test_*.py` naming convention.
- **Test Structure:** Tests cover both positive and negative cases for new features and routing logic.
- **Running Tests:** Use `pytest` or `make test-fast` to run tests.
- **Example Test:**
    ```python
    # tests/inference/test_default_profiles.py
    def test_default_profile_exists():
        from cohezion.inference.default_profiles import DEFAULT_PROFILES
        assert "basic-transformer" in DEFAULT_PROFILES
    ```

## Commands

| Command                | Purpose                                                      |
|------------------------|--------------------------------------------------------------|
| /new-inference-feature | Add a new inference capability with tests                    |
| /update-model-profiles | Add or update model profiles and routing logic               |
| /feature-tdd           | Start a new feature using test-driven development (TDD)      |
```