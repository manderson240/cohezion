---
title: "09 Rust Flume Python313 Incompatibility"
date: 2026-02-19
tags: [concept]
aspect: knower
neural:
  activation: 0.82
  stage: mature
  synapse_in: 6
  synapse_out: 10
---
## Definition

The Rust FLUME / Python 3.13 incompatibility is a dependency conflict where the `flume` crate (a Rust-based multi-producer multi-consumer channel library) used by certain Python packages via PyO3 bindings fails to compile or link against Python 3.13 due to changes in the Python C API and the GIL (Global Interpreter Lock) handling introduced in the free-threaded Python 3.13 builds. This manifests as build failures during `pip install` or `uv pip install` for packages that depend on Rust extensions using `flume`.

## Background: Python 3.13 Free-Threading (PEP 703)

Python 3.13 shipped an experimental free-threaded build (sometimes called "no-GIL" mode) per PEP 703 -- Making the Global Interpreter Lock Optional in CPython. The free-threaded build is installed as `python3.13t` and removes the GIL that historically serialized all Python thread execution. This change has cascading implications for C and Rust extension modules:

- **C API surface changes**: The free-threaded build alters the C API surface that PyO3 (Rust-to-Python bindings) depends on. Extensions must now explicitly declare thread-safety guarantees.
- **`#[pyclass]` requires `Sync`**: PyO3 0.23+ requires that Rust types exposed to Python implement `Sync` when targeting free-threaded builds, since multiple Python threads can access Rust data simultaneously.
- **`GILProtected` removed**: The `GILProtected` type (used to make interior mutability thread-safe via the GIL) is unavailable in free-threaded builds. Extensions must migrate to `Mutex` or other synchronization primitives.
- **Performance gap**: As of Python 3.14, the single-threaded performance gap between free-threaded and GIL builds has been reduced from 40% to under 10% on most platforms.

The `flume` crate itself is a pure Rust multi-producer multi-consumer channel library. The incompatibility arises not from `flume` directly, but from how PyO3-wrapped code that uses `flume` interacts with the changed Python C API -- particularly around thread synchronization, GIL acquisition patterns, and the `Sync` requirement.

## Key Properties

- **Root cause**: Python 3.13's free-threading changes altered the C API surface that PyO3 Rust bindings depend on. Extensions using `flume` channels for internal concurrency may not meet the new `Sync` requirements or may deadlock on GIL acquisition patterns.
- **Symptom**: Compilation failures during wheel building for Rust-extension packages (e.g., `tokenizers`, `pydantic-core`), or runtime deadlocks when `flume`'s blocking operations interact with Python's threading model.
- **Workaround**: Pin to Python 3.12 or use pre-built wheels where available; avoid source builds on 3.13. Set `PYTHON_GIL=1` or `-X gil` to re-enable the GIL at runtime as a fallback.
- **Scope**: Affects any Python package with Rust extensions that transitively depend on `flume` or similar concurrency primitives not yet updated for free-threading.
- **CI impact**: CI pipelines targeting Python 3.13 must account for this incompatibility in dependency resolution. Pre-commit hooks are a common trigger because they build isolated environments from source.
- **Ecosystem status**: Work is underway across PyO3, Cython, pybind11, and nanobind to update for free-threaded Python. As of 2025, pip 24.1+ is required for C extension installation in free-threaded builds.

## Examples

- `pip install tokenizers` failing on Python 3.13 with Rust compilation errors referencing `flume`
- Pre-commit hooks failing because hook environments build from source against incompatible Python versions
- Runtime deadlocks in PyO3 extensions where `flume`'s blocking `recv()` interacts with Python's GIL acquisition

## Primary Sources

- PEP 703. *Making the Global Interpreter Lock Optional in CPython*. [https://peps.python.org/pep-0703/](https://peps.python.org/pep-0703/)
- PyO3 User Guide. *Supporting Free-Threaded Python*. [https://pyo3.rs/v0.27.2/free-threading.html](https://pyo3.rs/v0.27.2/free-threading.html)
- Python Free-Threading Guide. *Compatibility and migration information*. [https://py-free-threading.github.io/](https://py-free-threading.github.io/)
- Python 3.13 What's New. *Free-threaded CPython*. [https://docs.python.org/3/whatsnew/3.13.html](https://docs.python.org/3/whatsnew/3.13.html)
- Python 3.14 Release Notes. *Free-threading no longer experimental*. [https://docs.python.org/3/whatsnew/3.14.html](https://docs.python.org/3/whatsnew/3.14.html)

## Related Papers

- [[lesson-16-pre-commit-hooks-stage-override]]
- [[lesson-17-stale-branch-mining]]
- [[lesson-20-ci-scope-discipline]]
- [[python-314-free-threaded-gil-removal]]

## Related Concepts

- [[concept-isolation]] -- isolating test and CI environments to avoid version conflicts
- [[data-governance-prevention-through-pre-commit-enforcement]] -- pre-commit hooks are a common trigger for this incompatibility
- [[runbook-ci-cd-pipeline]] -- CI pipelines must handle Python version matrix testing to avoid this class of failure
- [[api-design]] -- the PyO3 C API boundary is where the incompatibility manifests

## Relevance to Cohezion

This incompatibility was encountered during the Cohezion development pipeline when CI environments and pre-commit hooks attempted to build Rust-backed Python dependencies against Python 3.13. The resolution (pinning Python version and managing pre-commit environments) became a lesson in CI scope discipline and dependency management.

The incident exemplifies a broader principle in the Cohezion framework: dependency version management is not just a DevOps concern -- it directly impacts agent productivity. A broken CI pipeline or failing pre-commit hook wastes context tokens on debugging infrastructure rather than building features. The [[concept-isolation]] principle was strengthened as a result, mandating isolated environments per CI job and explicit Python version pinning.

## Session References

- [[session-49-retrospective]] -- root cause discovery that pivoted FLUME optimization from Rust to Python
- [[SESSION-50-QUICKSTART]] -- why Python optimization was chosen over Rust rebuild
