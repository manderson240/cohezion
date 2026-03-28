"""Thread-safe singleton decorator using double-checked locking."""

from __future__ import annotations

import functools
import threading
from typing import TYPE_CHECKING, Any, TypeVar


if TYPE_CHECKING:
    from collections.abc import Callable


T = TypeVar("T")


def safe_singleton(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator that wraps a factory function with double-checked locking.

    The decorated function creates the instance on first call and returns
    the same instance on subsequent calls. A ``.reset()`` method is attached
    for testing.

    Parameters
    ----------
    func : Callable[..., T]
        Factory function to wrap.

    Returns
    -------
    Callable[..., T]
        Thread-safe singleton wrapper.

    Examples
    --------
    >>> @safe_singleton
    ... def get_executor(config=None):
    ...     return CompoundExecutor(config=config)
    ...
    >>> executor = get_executor()  # creates instance
    >>> same = get_executor()  # returns cached instance
    >>> assert executor is same
    >>> get_executor.reset()  # clear for testing
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        if wrapper._instance is None:  # type: ignore[attr-defined]
            with wrapper._lock:  # type: ignore[attr-defined]
                if wrapper._instance is None:  # type: ignore[attr-defined]
                    wrapper._instance = func(*args, **kwargs)  # type: ignore[attr-defined]
        return wrapper._instance  # type: ignore[attr-defined, return-value]

    wrapper._instance = None  # type: ignore[attr-defined]
    wrapper._lock = threading.Lock()  # type: ignore[attr-defined]

    def reset() -> None:
        """Reset the singleton instance (for testing)."""
        with wrapper._lock:  # type: ignore[attr-defined]
            wrapper._instance = None  # type: ignore[attr-defined]

    wrapper.reset = reset  # type: ignore[attr-defined]
    return wrapper
