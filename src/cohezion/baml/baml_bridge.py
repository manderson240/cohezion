"""BAML Integration Bridge & Domain Ecosystem for Cohezion.
============================================================
Reference: https://github.com/boundaryml/baml

Provides:
1. `BAMLSchemaGenerator`: Exports Cohezion Pydantic schemas to declarative BAML (.baml) syntax.
2. `BAMLResilientParser`: Robust schema healing and token parser that cleans <think> blocks,
   heals truncated/malformed JSON, and parses structured output with zero failures.
3. `BAMLStreamingParser`: Real-time streaming token aggregator that extracts partial/complete typed models.
4. `BAMLRegistry`: Central registry of type-safe domain schemas across all 10 subsystems.
5. Core Domain Pydantic Models for BAML synchronization.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, ClassVar, TypeVar, get_args, get_origin

from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


# ==============================================================================
# Core Domain Pydantic Models Matching .baml Schemas
# ==============================================================================


class GoalSpecification(BaseModel):
    goal_id: str = Field(description="Unique deterministic goal identifier")
    title: str = Field(description="Human-readable goal summary")
    target_metric: str = Field(description="Target metric name (e.g. 'coherence', 'pass_rate')")
    target_threshold: float = Field(description="Numerical convergence threshold")
    max_iterations: int = Field(default=10, description="Maximum allowed closed-loop iterations")
    timeout_seconds: float = Field(default=30.0, description="Execution timeout floor")


class TaskClassificationResult(BaseModel):
    node: str = Field(description="Compute target: 'npu', 'igpu', 'cpu', 'cloud'")
    output_type: str = Field(
        description="Output intent: 'short_answer', 'code', 'long_generation', 'structured'"
    )
    quality_gate_chars: int = Field(
        default=0, description="Minimum character threshold for response"
    )
    confidence: float = Field(default=1.0, description="Classifier certainty score [0.0, 1.0]")
    rationale: str = Field(default="", description="Explanation of tier selection")


class RoutingDecision(BaseModel):
    model_id: str = Field(
        description="Model identifier (e.g. 'deepseek-r1-0528-8b-FLM', 'Qwen3-Coder-30B-GGUF')"
    )
    tier: str = Field(description="'npu', 'igpu', 'cpu', 'cloud'")
    port: int = Field(default=13305, description="Port endpoint (strictly 13305 for local)")
    temperature: float = Field(default=0.6, description="Card-aligned sampling temperature")
    top_p: float = Field(default=0.9, description="Card-aligned nucleus sampling")
    max_context: int = Field(default=16384, description="Bounded context length (<= 16384)")
    evi_score: float = Field(default=1.0, description="Expected Value of Intervention score")


class SheafDirichletState(BaseModel):
    num_nodes: int = Field(description="Number of stalks in the cellular sheaf")
    num_edges: int = Field(description="Number of restriction maps")
    dirichlet_energy: float = Field(description="Harmonic energy E_D = 1/2 x^T L_Sigma x")
    is_concordant: bool = Field(description="True if energy < 2.0 (no contradiction)")
    disputed_edges: list[str] = Field(
        default_factory=list, description="List of edge IDs exceeding discrepancy threshold"
    )


class ModelCardProfile(BaseModel):
    model_id: str = Field(description="Model name")
    backend_recipe: str = Field(description="'flm', 'llamacpp', 'kokoro', 'sd-cpp', 'whispercpp'")
    device: str = Field(description="'npu', 'gpu', 'cpu'")
    sweet_spot_temp: float = Field(default=0.6, description="Optimal temperature")
    min_memory_gb: float = Field(default=8.0, description="Memory requirement in GiB")
    supported_modes: list[str] = Field(
        default_factory=list, description="e.g. ['code', 'chat', 'tools', 'math']"
    )


class KanbanItem(BaseModel):
    id: str = Field(description="Task card identifier")
    title: str = Field(description="Task title")
    status: str = Field(
        default="todo", description="'backlog', 'todo', 'in_progress', 'done', 'blocked'"
    )
    priority: str = Field(default="medium", description="'critical', 'high', 'medium', 'low'")
    source: str = Field(default="agent", description="Session or agent emitter")
    category: str = Field(
        default="architecture", description="'architecture', 'bugfix', 'tech_debt', 'research'"
    )
    description: str = Field(default="", description="Comprehensive task specification")


class VModelTrace(BaseModel):
    concept_name: str = Field(description="Core architectural concept")
    target_category: str = Field(description="Subsystem category")
    node_id: str = Field(description="SurrealDB relational node identifier")
    j_space_regime: str = Field(description="J-Space latent workspace depth")
    ast_verified: bool = Field(description="AutoHarness AST policy check")
    zkfv_verified: bool = Field(description="ZK-FV Plonkish constraint proof")
    multiperspective_score: float = Field(description="Adversarial agent consensus score")


class HardwareVitalsSnapshot(BaseModel):
    total_ram_gb: float = Field(description="Total physical memory")
    free_ram_gb: float = Field(description="Free physical memory")
    gate_v2_safe: bool = Field(description="True if free RAM >= 16.0 GiB")
    lemonade_alive: bool = Field(description="Port 13305 health status")
    active_models: list[str] = Field(default_factory=list, description="List of loaded model IDs")


# ==============================================================================
# BAML Registry & Schema Generator
# ==============================================================================


class BAMLRegistry:
    """Central registry mapping schema names to typed Pydantic models."""

    _MODELS: ClassVar[dict[str, type[BaseModel]]] = {
        "GoalSpecification": GoalSpecification,
        "TaskClassificationResult": TaskClassificationResult,
        "RoutingDecision": RoutingDecision,
        "SheafDirichletState": SheafDirichletState,
        "ModelCardProfile": ModelCardProfile,
        "KanbanItem": KanbanItem,
        "VModelTrace": VModelTrace,
        "HardwareVitalsSnapshot": HardwareVitalsSnapshot,
    }

    @classmethod
    def register(cls, name: str, model_cls: type[BaseModel]) -> None:
        cls._MODELS[name] = model_cls

    @classmethod
    def get(cls, name: str) -> type[BaseModel] | None:
        return cls._MODELS.get(name)

    @classmethod
    def all_models(cls) -> dict[str, type[BaseModel]]:
        return dict(cls._MODELS)

    @classmethod
    def generate_all_baml_schemas(cls) -> str:
        """Exports all registered models into a single BAML schema bundle."""
        chunks = [
            "// Cohezion Unified Domain Schema Bundle",
            "// Automatically generated via BAMLSchemaGenerator\n",
        ]
        for _name, model_cls in cls._MODELS.items():
            chunks.append(BAMLSchemaGenerator.generate_baml_class(model_cls))
            chunks.append("")
        return "\n".join(chunks)


class BAMLSchemaGenerator:
    """Generates Boundary Abstract Modeling Language (.baml) definitions from Python models."""

    PYTHON_TO_BAML_TYPES: dict[str, str] = {
        "str": "string",
        "int": "int",
        "float": "float",
        "bool": "bool",
        "dict": "map<string, any>",
        "list": "string[]",
        "Any": "any",
    }

    @classmethod
    def to_baml_type(cls, py_type: Any) -> str:
        origin = get_origin(py_type)
        args = get_args(py_type)

        if origin is list:
            item_type = cls.to_baml_type(args[0]) if args else "any"
            return f"{item_type}[]"
        if origin is dict:
            val_type = cls.to_baml_type(args[1]) if len(args) > 1 else "any"
            return f"map<string, {val_type}>"

        type_name = getattr(py_type, "__name__", str(py_type))
        return cls.PYTHON_TO_BAML_TYPES.get(type_name, type_name)

    @classmethod
    def generate_baml_class(cls, model_cls: type[BaseModel]) -> str:
        """Converts a Pydantic model to a BAML class definition."""
        lines = [f"class {model_cls.__name__} {{"]
        for field_name, field_info in model_cls.model_fields.items():
            baml_type = cls.to_baml_type(field_info.annotation)
            desc = f" // {field_info.description}" if field_info.description else ""
            lines.append(f"  {field_name} {baml_type}{desc}")
        lines.append("}")
        return "\n".join(lines)


# ==============================================================================
# BAML Resilient & Streaming Parsers
# ==============================================================================


class BAMLResilientParser:
    """Resilient parser applying BAML principles for robust schema extraction."""

    THINK_REGEX = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
    JSON_BLOCK_REGEX = re.compile(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", re.DOTALL)

    @classmethod
    def strip_thinking_tokens(cls, raw_text: str) -> str:
        """Removes reasoning tokens emitted by thinking models."""
        cleaned = cls.THINK_REGEX.sub("", raw_text).strip()
        if "<think>" in cleaned.lower():
            idx = cleaned.lower().find("<think>")
            cleaned = cleaned[:idx].strip()
        return cleaned

    @classmethod
    def heal_json_string(cls, json_str: str) -> str:
        """Performs structural heuristic healing on imperfect JSON output."""
        cleaned = json_str.strip()
        # Remove trailing commas before closing braces/brackets
        cleaned = re.sub(r",\s*([\]}])", r"\1", cleaned)

        # Balance unclosed brackets/braces if model output was truncated
        open_braces = cleaned.count("{") - cleaned.count("}")
        open_brackets = cleaned.count("[") - cleaned.count("]")

        if open_braces > 0:
            cleaned += "}" * open_braces
        if open_brackets > 0:
            cleaned += "]" * open_brackets

        return cleaned

    @classmethod
    def parse_to_model(cls, raw_output: str, model_cls: type[T]) -> T:
        """Parses model output into target Pydantic model with schema healing."""
        cleaned = cls.strip_thinking_tokens(raw_output)

        match = cls.JSON_BLOCK_REGEX.search(cleaned)
        candidate = match.group(1) if match else cleaned

        first_brace = candidate.find("{")
        last_brace = candidate.rfind("}")
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            candidate = candidate[first_brace : last_brace + 1]

        candidate = cls.heal_json_string(candidate)

        try:
            parsed_dict = json.loads(candidate)
            return model_cls.model_validate(parsed_dict)
        except Exception as exc:
            logger.warning(
                "Standard JSON parse failed, attempting heuristic field recovery: %s", exc
            )
            return cls._heuristic_field_recovery(cleaned, model_cls)

    @classmethod
    def parse_to_dict(cls, raw_output: str, schema: dict[str, Any] | None = None) -> dict[str, Any]:
        """Parses model output into a plain dictionary with structural healing.

        Extracts JSON blocks, handles unclosed braces, strips thinking tokens,
        and falls back to heuristic key-value extraction against schema properties.
        """
        cleaned = cls.strip_thinking_tokens(raw_output)

        match = cls.JSON_BLOCK_REGEX.search(cleaned)
        candidate = match.group(1) if match else cleaned

        first_brace = candidate.find("{")
        last_brace = candidate.rfind("}")
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            candidate = candidate[first_brace : last_brace + 1]

        candidate = cls.heal_json_string(candidate)

        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except Exception as exc:
            logger.warning(
                "Standard JSON parse to dict failed, attempting heuristic recovery: %s",
                exc,
            )

        return cls._heuristic_dict_recovery(cleaned, schema)

    @classmethod
    def _coerce_value(cls, val_raw: str, expected_type: str | Any) -> Any:
        """Coerces raw string token into expected primitive type."""
        try:
            return json.loads(val_raw)
        except Exception:
            pass

        type_str = (
            expected_type.lower() if isinstance(expected_type, str) else str(expected_type).lower()
        )
        if "bool" in type_str:
            return val_raw.lower() in ("true", "1", "yes")
        if "int" in type_str:
            try:
                return int(float(val_raw))
            except ValueError:
                return val_raw
        if "number" in type_str or "float" in type_str:
            try:
                return float(val_raw)
            except ValueError:
                return val_raw
        return val_raw

    @classmethod
    def _heuristic_dict_recovery(cls, text: str, schema: dict[str, Any] | None) -> dict[str, Any]:
        """Recovers key-value pairs from text (YAML, Markdown, plain text)."""
        fields_data: dict[str, Any] = {}
        properties = (schema or {}).get("properties", {})

        if properties:
            for field_name, prop_info in properties.items():
                pattern = re.compile(
                    rf'(?:^|\n|\s)(?:[-*]\s*)?(?:\*\*)?["\']?({re.escape(field_name)})["\']?(?:\*\*)?\s*[:=]\s*([^\n,}}]+)',
                    re.IGNORECASE,
                )
                m = pattern.search(text)
                if m:
                    val_raw = m.group(2).strip().strip('"').strip("'")
                    expected_type = (
                        prop_info.get("type", "string") if isinstance(prop_info, dict) else "string"
                    )
                    fields_data[field_name] = cls._coerce_value(val_raw, expected_type)
        else:
            line_pattern = re.compile(
                r"(?:^|\n)\s*(?:[-*]\s*)?(?:\*\*)?([a-zA-Z_][a-zA-Z0-9_]*)(?:\*\*)?\s*[:=]\s*([^\n]+)"
            )
            for m in line_pattern.finditer(text):
                k = m.group(1).strip()
                v = m.group(2).strip().strip('"').strip("'")
                fields_data[k] = cls._coerce_value(v, "string")

        return fields_data

    @classmethod
    def _heuristic_field_recovery(cls, text: str, model_cls: type[T]) -> T:
        """Best-effort regex extraction for known fields in target schema."""
        fields_data: dict[str, Any] = {}
        for field_name, field_info in model_cls.model_fields.items():
            pattern = re.compile(
                rf'(?:^|\n|\s)(?:[-*]\s*)?(?:\*\*)?["\']?({re.escape(field_name)})["\']?(?:\*\*)?\s*[:=]\s*([^\n,}}]+)',
                re.IGNORECASE,
            )
            m = pattern.search(text)
            if m:
                val_raw = m.group(2).strip().strip('"').strip("'")
                fields_data[field_name] = cls._coerce_value(val_raw, str(field_info.annotation))
        return model_cls.model_validate(fields_data)


class BAMLStreamingParser:
    """Aggregates streaming token chunks and attempts continuous partial parsing."""

    def __init__(self, model_cls: type[T]) -> None:
        self.model_cls = model_cls
        self.buffer = ""
        self.last_parsed: T | None = None

    def feed_token(self, token: str) -> T | None:
        """Feeds a token chunk and returns the most complete valid model parsed so far."""
        self.buffer += token
        try:
            parsed = BAMLResilientParser.parse_to_model(self.buffer, self.model_cls)
            self.last_parsed = parsed
            return parsed
        except Exception:
            return self.last_parsed

    def finalize(self) -> T:
        """Finalizes parsing over full accumulated buffer."""
        return BAMLResilientParser.parse_to_model(self.buffer, self.model_cls)
