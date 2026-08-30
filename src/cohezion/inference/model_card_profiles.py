"""Model Card Profiles & Aligned Hyperparameters per Model Architecture.

Enforces Card-Aligned Recipes:
1. No model is called with generic blanket params.
2. Distinct Context Window, Max Output Tokens, Timeout, and Sampling Sweet-Spots per model.
"""

from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class ModelProfile:
    model_id: str
    tier: str  # local_npu, local_igpu, local_cpu, ollama_cloud, premium_api
    context_window: int
    max_output_tokens: int
    timeout_seconds: float
    temperature: float
    top_p: float
    thinking_model: bool
    purpose: str

MODEL_CARD_REGISTRY: dict[str, ModelProfile] = {
    # --- Local NPU Models (Strix Halo XDNA2) ---
    "deepseek-r1-0528-8b-FLM": ModelProfile(
        model_id="deepseek-r1-0528-8b-FLM",
        tier="local_npu",
        context_window=131072,  # Full 128K context with MLA compression
        max_output_tokens=8192,
        timeout_seconds=300.0,  # 5 min for deep reasoning
        temperature=0.6,
        top_p=0.95,
        thinking_model=True,
        purpose="Deep mathematical reasoning, logic puzzle solving, Sheaf cohomology"
    ),
    "qwen3.6-moe-35b-a3b-FLM": ModelProfile(
        model_id="qwen3.6-moe-35b-a3b-FLM",
        tier="local_npu",
        context_window=65536,  # 64K MoE context
        max_output_tokens=2048,
        timeout_seconds=120.0,  # 2 min
        temperature=0.2,
        top_p=0.9,
        thinking_model=False,
        purpose="Fast tokenized macro planning, literature extraction"
    ),
    "qwen3-4b-FLM": ModelProfile(
        model_id="qwen3-4b-FLM",
        tier="local_npu",
        context_window=32768,
        max_output_tokens=1024,
        timeout_seconds=60.0,
        temperature=0.1,
        top_p=0.9,
        thinking_model=False,
        purpose="Small tool calling, format validation"
    ),

    # --- Local iGPU Models (Radeon 8060S / Vulkan) ---
    "Qwen3-Coder-30B": ModelProfile(
        model_id="Qwen3-Coder-30B",
        tier="local_igpu",
        context_window=131072,  # Full 128K context for multi-file repo refactoring
        max_output_tokens=4096,
        timeout_seconds=180.0,  # 3 min
        temperature=0.1,  # Low temp for deterministic coding
        top_p=0.9,
        thinking_model=False,
        purpose="Python AST code generation, multi-file refactoring"
    ),
    "gpt-oss-20b": ModelProfile(
        model_id="gpt-oss-20b",
        tier="local_igpu",
        context_window=131072,  # Full 128K context with MXFP4 KV-cache
        max_output_tokens=4096,
        timeout_seconds=180.0,
        temperature=0.2,
        top_p=0.9,
        thinking_model=True,
        purpose="Adversarial red-team review, edge case identification"
    ),

    # --- Frontier Ollama Cloud Models ---
    "deepseek-v4-pro:cloud": ModelProfile(
        model_id="deepseek-v4-pro:cloud",
        tier="ollama_cloud",
        context_window=128000,
        max_output_tokens=16384,
        timeout_seconds=600.0,  # 10 min for 1.6T frontier math
        temperature=0.6,
        top_p=0.95,
        thinking_model=True,
        purpose="Frontier mathematical proofs, non-equilibrium thermodynamic systems"
    ),
    "qwen3.5:397b-cloud": ModelProfile(
        model_id="qwen3.5:397b-cloud",
        tier="ollama_cloud",
        context_window=64000,
        max_output_tokens=8192,
        timeout_seconds=420.0,  # 7 min
        temperature=0.2,
        top_p=0.9,
        thinking_model=True,
        purpose="Frontier competitive ML architecture, high-dimensional Hungarian solvers"
    ),
    "glm-5.2:cloud": ModelProfile(
        model_id="glm-5.2:cloud",
        tier="ollama_cloud",
        context_window=64000,
        max_output_tokens=8192,
        timeout_seconds=360.0,  # 6 min
        temperature=0.3,
        top_p=0.9,
        thinking_model=True,
        purpose="Medical imaging (3D DICOM) and physical field simulation"
    )
}

def get_aligned_profile(model_id: str) -> ModelProfile:
    """Returns the card-aligned profile or a safe calibrated fallback."""
    if model_id in MODEL_CARD_REGISTRY:
        return MODEL_CARD_REGISTRY[model_id]
    # Default calibrated profile
    return ModelProfile(
        model_id=model_id,
        tier="generic",
        context_window=16384,
        max_output_tokens=2048,
        timeout_seconds=120.0,
        temperature=0.2,
        top_p=0.9,
        thinking_model=False,
        purpose="Standard inference"
    )
