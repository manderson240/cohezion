"""Test generation tools for Cohezion."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cohezion.tools.test_generator import CodeTestGenerator, main
    TestGenerator = CodeTestGenerator
else:
    def __getattr__(name: str) -> Any:
        if name in ("CodeTestGenerator", "TestGenerator"):
            from cohezion.tools.test_generator import CodeTestGenerator
            return CodeTestGenerator
        if name == "main":
            from cohezion.tools.test_generator import main
            return main
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["CodeTestGenerator", "TestGenerator", "main"]
