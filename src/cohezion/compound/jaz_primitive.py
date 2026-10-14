"""JAZ: Harness as a Language (arXiv:2609.26891).

Minimalist agent framework with maximal expressivity:
1. Axiom 1 (Recursive Sub-Invokes): The LLM writes executable code in an environment
   where `invoke(...)` is a callable language primitive, enabling arbitrary recursion.
2. Axiom 2 (Everything is a REPL Variable): All inputs to `invoke` and the execution
   history `__history__` are first-class variables inside the environment.
3. Dynamic Scoping (`with scope(...)`): Context manager propagating tools and configs
   down recursive sub-invokes.
4. Hooks: Observability, validation, budget enforcement, and context window warnings.
"""

from __future__ import annotations

import contextvars
import inspect
import logging
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Generator, Generic, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Dynamic scoping context variable: holds stack of active scope dictionaries
_ACTIVE_SCOPES: contextvars.ContextVar[list[dict[str, Any]]] = contextvars.ContextVar(
    "_ACTIVE_SCOPES", default=[]
)
_ACTIVE_HOOKS: contextvars.ContextVar[list[list[Any]]] = contextvars.ContextVar(
    "_ACTIVE_HOOKS", default=[]
)


# =========================================================================
# Hooks
# =========================================================================
class BaseHook:
    """Base class for JAZ execution hooks."""

    def on_invoke_start(self, kwargs: dict[str, Any]) -> None:
        """Called before an invoke body is executed."""
        pass

    def on_invoke_end(self, result: Any, history: list[dict[str, Any]]) -> Any:
        """Called after an invoke body is executed; can inspect or mutate return value."""
        return result


@dataclass(frozen=True, slots=True)
class ReturnType(BaseHook, Generic[T]):
    """Hook enforcing expected return type on invoke output."""

    expected_type: type[T]

    def on_invoke_end(self, result: Any, history: list[dict[str, Any]]) -> Any:
        if not isinstance(result, self.expected_type):
            try:
                # Attempt graceful coercion if compatible
                return self.expected_type(result)  # type: ignore[call-arg]
            except Exception as exc:
                raise TypeError(
                    f"JAZ ReturnType violation: Expected {self.expected_type.__name__}, "
                    f"got {type(result).__name__} (value={result!r})"
                ) from exc
        return result


@dataclass(frozen=True, slots=True)
class ValidateReturn(BaseHook):
    """Hook validating return value against a custom predicate."""

    predicate: Callable[[Any], bool]
    error_message: str = "Return validation predicate failed"

    def on_invoke_end(self, result: Any, history: list[dict[str, Any]]) -> Any:
        if not self.predicate(result):
            raise ValueError(f"JAZ ValidateReturn error: {self.error_message} (value={result!r})")
        return result


@dataclass
class BudgetPool(BaseHook):
    """Scoped or local budget hook tracking maximum execution cost or iterations."""

    max_cost: float = 10.0
    current_cost: float = 0.0

    def charge(self, amount: float) -> None:
        if self.current_cost + amount > self.max_cost:
            raise RuntimeError(
                f"JAZ BudgetPool exhausted: cost {self.current_cost + amount:.2f} > limit {self.max_cost:.2f}"
            )
        self.current_cost += amount

    def on_invoke_start(self, kwargs: dict[str, Any]) -> None:
        self.charge(0.01)  # Nominal base invocation charge


@dataclass(frozen=True, slots=True)
class ContextWindowWarning(BaseHook):
    """Hook warning or signaling when conversation history exceeds threshold."""

    max_history_turns: int = 50

    def on_invoke_start(self, kwargs: dict[str, Any]) -> None:
        history = kwargs.get("__history__", [])
        prev = kwargs.get("prev_history", [])
        total_turns = len(history) + len(prev)
        if total_turns >= self.max_history_turns:
            logger.warning(
                "JAZ ContextWindowWarning: %d turns accumulated (limit %d). "
                "Triggering tail-recursive delegation.",
                total_turns,
                self.max_history_turns,
            )
            kwargs["__context_warning__"] = True


# =========================================================================
# Dynamic Scoping Context Manager
# =========================================================================
@contextmanager
def scope(*hooks: BaseHook, **variables: Any) -> Generator[dict[str, Any], None, None]:
    """Dynamically scoped context manager.

    Variables and hooks passed to `with scope(...)` are inherited by all
    top-level and recursive `invoke(...)` calls within the block.
    """
    scopes = list(_ACTIVE_SCOPES.get())
    scopes.append(variables)
    token_scopes = _ACTIVE_SCOPES.set(scopes)

    hook_list = list(_ACTIVE_HOOKS.get())
    hook_list.append(list(hooks))
    token_hooks = _ACTIVE_HOOKS.set(hook_list)
    try:
        yield variables
    finally:
        _ACTIVE_SCOPES.reset(token_scopes)
        _ACTIVE_HOOKS.reset(token_hooks)


# =========================================================================
# The Core Primitive: invoke(...)
# =========================================================================
def invoke(*local_hooks: BaseHook, **inputs: Any) -> Any:
    """Execute the JAZ LLM-based language primitive.

    Parameters
    ----------
    *local_hooks : BaseHook
        Hooks applied only to this immediate invoke call.
    **inputs : Any
        Named inputs to the execution environment. Everything visible to the
        agent (prompts, data, tools, code) is a first-class variable in the environment.

    Returns
    -------
    Any
        The result of evaluating the code body.
    """
    # 1. Resolve dynamic scopes (outermost to innermost)
    merged_env: dict[str, Any] = {}
    for scope_dict in _ACTIVE_SCOPES.get():
        merged_env.update(scope_dict)
    merged_env.update(inputs)

    # 2. Resolve active hooks (scoped + local)
    all_hooks: list[BaseHook] = []
    for scoped_hooks in _ACTIVE_HOOKS.get():
        all_hooks.extend(scoped_hooks)
    all_hooks.extend(local_hooks)

    # 3. Setup first-class variables in REPL environment
    if "__history__" not in merged_env:
        merged_env["__history__"] = []
    history: list[dict[str, Any]] = merged_env["__history__"]

    # Self-reference: invoke and scope are available inside the REPL
    merged_env["invoke"] = invoke
    merged_env["scope"] = scope

    # 4. Trigger on_invoke_start hooks
    for h in all_hooks:
        h.on_invoke_start(merged_env)

    # 5. Execute invocation body
    # If explicit 'func' or 'code' passed, execute directly;
    # otherwise invoke the function/callable provided in inputs or execute code string.
    result: Any = None
    if "code" in merged_env and isinstance(merged_env["code"], str):
        # Execute code in REPL scope
        exec_namespace = dict(merged_env)
        exec_globals = {"__builtins__": __builtins__}
        exec(merged_env["code"], exec_globals, exec_namespace)
        result = exec_namespace.get("result", exec_namespace.get("answer", None))
        history.append({"type": "code_exec", "code": merged_env["code"], "result": result})
    elif "func" in merged_env and callable(merged_env["func"]):
        fn = merged_env["func"]
        sig = inspect.signature(fn)
        call_kwargs = {k: v for k, v in merged_env.items() if k in sig.parameters}
        result = fn(**call_kwargs)
        history.append({"type": "func_call", "name": getattr(fn, "__name__", "anonymous"), "result": result})
    elif "action" in merged_env and callable(merged_env["action"]):
        result = merged_env["action"](**{k: v for k, v in merged_env.items() if k != "action"})
        history.append({"type": "action_call", "result": result})
    else:
        # Default pass-through or structured payload reflection
        task = merged_env.get("task", "default_task")
        result = merged_env.get("answer", f"Executed task: {task}")
        history.append({"type": "direct_eval", "task": task, "result": result})

    # 6. Trigger on_invoke_end hooks
    for h in all_hooks:
        result = h.on_invoke_end(result, history)

    return result
