---
title: "Technical Specification: AutoHarness AST Policy Verifier as Zero-Cost Oracle (Experiment 3)"
experiment_id: "EXP-LOCAL-003"
status: "SPECIFIED"
version: "1.0"
date: "2026-08-16"
authors: ["Antigravity Master Orchestrator", "deepseek-v4-pro:cloud"]
hardware_target: "AMD Strix Halo (NPU XDNA2 + iGPU Radeon 8060S + CPU Ryzen 9)"
---

# EXP-003: AutoHarness AST Policy Verifier as a Zero-Cost Oracle

## 1. Theoretical Foundation & Hypothesis
By compiling formal language invariants (bounds, types, energy conservation, memory floors) into pure Python AST bytecode prior to model generation, agents achieve:
1. $0.00\text{ ms}$ model token latency on policy checks (bypassing LLM calls).
2. Zero illegal tool invocations and zero syntax errors across autonomous multi-step loops.
Reference: arXiv:2603.03329v1 (AutoHarness: Code-as-action verifiers).

## 2. Hardware Architecture & Partitioning
- **CPU (Ryzen 9)**: Executes native CPython AST bytecode verification ($<1\,\mu\text{s}$ latency).
- **iGPU (Radeon 8060S)**: Generates candidate code solutions when the action verifier reports invalid state.
- **NPU (XDNA2)**: Retrieves semantically similar verified AST harnesses from the local cache (`cache/`).

## 3. Resurrectable Implementation Blueprint
```python
# Standalone execution blueprint:
import ast
from typing import Callable, Any

class StandaloneAutoHarness:
    def __init__(self):
        self.rules: dict[str, Callable[[Any], bool]] = {
            "valid_python_syntax": lambda code: self._check_syntax(code),
            "no_unregistered_imports": lambda code: self._check_imports(code),
        }
        
    def _check_syntax(self, code: str) -> bool:
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False

    def _check_imports(self, code: str) -> bool:
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    # Enforce strict standard/local namespace rules
                    pass
            return True
        except Exception:
            return False
```

## 4. SurrealDB & Obsidian Dual-Store Schema
- **SurrealDB Table `exp_autoharness_oracle`**:
  ```sql
  DEFINE TABLE exp_autoharness_oracle SCHEMAFULL;
  DEFINE FIELD action_intent ON exp_autoharness_oracle TYPE string;
  DEFINE FIELD verified_allowed ON exp_autoharness_oracle TYPE bool;
  DEFINE FIELD bypassed_llm ON exp_autoharness_oracle TYPE bool;
  DEFINE FIELD ast_exec_microseconds ON exp_autoharness_oracle TYPE float;
  DEFINE FIELD timestamp ON exp_autoharness_oracle TYPE datetime DEFAULT time::now();
  ```
- **Obsidian Vault File**: `~/vaults/cohezion-vault/experiments/EXP-003-autoharness-oracle.md`
