"""Compound executor configuration.

Defines per-operation model routing so that code generation uses a
larger model while analysis/search steps use a smaller one.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# Default operation → model mapping
_DEFAULT_OPERATION_MODELS: dict[str, str] = {
    "generate": "qwen3-coder:30b",
    "analyze": "phi3:mini",
    "search": "phi3:mini",
    "transform": "",  # no LLM needed
    "persist": "",  # no LLM needed
}


class CompoundConfig(BaseModel):
    """Configuration for compound execution.

    Attributes
    ----------
    default_model : str
        Fallback model when no operation-specific mapping exists.
    code_model : str
        Model used for code-generation tasks.
    operation_model_map : dict[str, str]
        Mapping of operation type to Ollama model name.
        Empty string means "no LLM call required".
    ollama_host : str
        Ollama API base URL.
    cache_max_size : int
        Maximum prompt-response cache entries.
    """

    default_model: str = "phi3:mini"
    code_model: str = "qwen3-coder:30b"
    operation_model_map: dict[str, str] = Field(
        default_factory=lambda: dict(_DEFAULT_OPERATION_MODELS)
    )
    ollama_host: str = "http://localhost:11434"
    cache_max_size: int = 512

    def model_for_operation(self, operation: str) -> str | None:
        """Return the model name for a given operation, or None if no LLM needed.

        Parameters
        ----------
        operation : str
            One of generate, analyze, search, transform, persist.

        Returns
        -------
        str | None
            Model name, or ``None`` if the operation doesn't need an LLM.
        """
        model = self.operation_model_map.get(operation, self.default_model)
        return model if model else None
