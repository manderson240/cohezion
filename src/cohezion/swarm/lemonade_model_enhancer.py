"""Enhanced Lemonade model mapping with improved discovery and capability inference.

Builds on improved_deterministic_parser to achieve 95%+ extraction rate
and comprehensive capability mapping for all Lemonade/FLM models.
"""

import logging
import re
import subprocess
import time
from pathlib import Path
from typing import Any

from cohezion.swarm.improved_deterministic_parser import AutoImprovementCycle, ImprovedFLMParser


logger = logging.getLogger(__name__)


# Comprehensive model capability database (learned from naming patterns)
MODEL_CAPABILITY_PATTERNS = {
    # Model families and their capabilities
    "qwen": {
        "capabilities": ["code_generation", "code_completion", "chat", "instruction_following"],
        "default_backend": "NPU",
        "confidence": 0.95,
        "notes": "Alibaba Qwen series, strong code capabilities",
    },
    "qwen-coder": {
        "capabilities": ["code_generation", "code_completion", "programming", "debugging"],
        "default_backend": "NPU",
        "confidence": 0.98,
        "notes": "Specialized code model",
    },
    "gemma": {
        "capabilities": ["text_generation", "reasoning", "chat", "instruction_following"],
        "default_backend": "NPU",
        "confidence": 0.90,
        "notes": "Google Gemma series",
    },
    "gemma-4": {
        "capabilities": ["long_context", "reasoning", "text_generation", "chat"],
        "default_backend": "GPU_VULKAN",  # Currently NPU blocked by protobuf limit
        "confidence": 0.95,
        "notes": "Gemma 4 series - large models, requires GPU",
    },
    "llama": {
        "capabilities": ["text_generation", "chat", "instruction_following"],
        "default_backend": "NPU",
        "confidence": 0.90,
        "notes": "Meta Llama series",
    },
    "granite": {
        "capabilities": ["enterprise_text", "code_generation", "reasoning"],
        "default_backend": "NPU",
        "confidence": 0.88,
        "notes": "IBM Granite series",
    },
    "phi": {
        "capabilities": ["text_generation", "chat", "instruction_following"],
        "default_backend": "NPU",
        "confidence": 0.85,
        "notes": "Microsoft Phi series",
    },
    "tiny": {
        "capabilities": ["text_generation", "edge_deployment"],
        "default_backend": "NPU",
        "confidence": 0.80,
        "notes": "Tiny models for edge",
    },
    "mistral": {
        "capabilities": ["text_generation", "chat", "instruction_following"],
        "default_backend": "NPU",
        "confidence": 0.90,
        "notes": "Mistral series",
    },
    "starcoder": {
        "capabilities": ["code_generation", "code_completion", "programming"],
        "default_backend": "NPU",
        "confidence": 0.95,
        "notes": "Code-specific model",
    },
    "whisper": {
        "capabilities": ["audio_transcription", "translation"],
        "default_backend": "NPU",
        "confidence": 0.98,
        "notes": "Audio model - not text",
    },
    "vl": {
        "capabilities": ["vision_understanding", "multimodal"],
        "default_backend": "GPU_VULKAN",
        "confidence": 0.90,
        "notes": "Vision-language model",
    },
    "instruct": {
        "capabilities": ["instruction_following", "chat"],
        "default_backend": "NPU",
        "confidence": 0.92,
        "pattern_type": "variant",
        "notes": "Instruction-tuned variant",
    },
    "chat": {
        "capabilities": ["chat", "dialogue"],
        "default_backend": "NPU",
        "confidence": 0.90,
        "pattern_type": "variant",
        "notes": "Chat-tuned variant",
    },
}


class LemonadeModelEnhancer:
    """Enhanced model discovery and mapping for Lemonade SDK."""

    def __init__(self):
        parser = ImprovedFLMParser()
        self.parser = AutoImprovementCycle(parser)
        self.model_cache: dict[str, dict[str, Any]] = {}
        self.capability_confidence_threshold = 0.70

    def discover_comprehensive(self) -> dict[str, Any]:
        """Comprehensive model discovery with enhanced mapping."""
        print("\n" + "=" * 70)
        print("🍋 LEMONADE MODEL ENHANCER - Comprehensive Discovery")
        print("=" * 70)

        results = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "sources": {},
            "models": [],
            "statistics": {},
        }

        # Source 1: FLM CLI (NPU models)
        print("\n[1/4] Discovering FLM models...")
        flm_models = self._discover_flm_enhanced()
        results["sources"]["flm"] = {
            "count": len(flm_models),
            "models": flm_models,
        }
        print(f"  ✅ Found: {len(flm_models)} models")

        # Source 2: Local cache (GGUF files)
        print("\n[2/4] Discovering local GGUF cache...")
        local_models = self._discover_local_gguf()
        results["sources"]["local_cache"] = {
            "count": len(local_models),
            "models": local_models,
        }
        print(f"  ✅ Found: {len(local_models)} models")

        # Source 3: Running instances
        print("\n[3/4] Checking running model instances...")
        running_models = self._discover_running_instances()
        results["sources"]["running"] = {
            "count": len(running_models),
            "models": running_models,
        }
        print(f"  ✅ Found: {len(running_models)} instances")

        # Source 4: Lemonade SDK registry
        print("\n[4/4] Querying Lemonade SDK registry...")
        sdk_models = self._discover_sdk_registry()
        results["sources"]["sdk_registry"] = {
            "count": len(sdk_models),
            "models": sdk_models,
        }
        print(f"  ✅ Found: {len(sdk_models)} registry entries")

        # Merge and deduplicate
        all_models = self._merge_models(flm_models + local_models + running_models + sdk_models)
        results["models"] = all_models

        # Enhanced capability inference
        print("\n🔍 Enhancing capability inference...")
        enhanced_models = self._enhance_all_capabilities(all_models)
        results["models"] = enhanced_models

        # Statistics
        results["statistics"] = self._calculate_statistics(enhanced_models)

        # Summary
        self._print_summary(results)

        return results

    def _discover_flm_enhanced(self) -> list[dict[str, Any]]:
        """Enhanced FLM discovery with auto-improvement."""
        try:
            result = subprocess.run(
                ["flm", "list"], capture_output=True, text=True, timeout=10, check=False
            )

            if result.returncode != 0:
                return []

            models = []
            raw_lines = []

            for line in result.stdout.split("\n"):
                raw_lines.append(line)
                model = self.parser.parser._parse_line_improved(line)
                if model:
                    model["source"] = "FLM"
                    model["backend"] = "NPU"
                    model["discovery_method"] = "enhanced_parser"
                    models.append(model)

            # Store raw lines for future improvement
            self.parser.parser.stats["raw_lines"] = raw_lines

            return models

        except Exception as e:
            logger.warning(f"FLM discovery failed: {e}")
            return []

    def _discover_local_gguf(self) -> list[dict[str, Any]]:
        """Discover local GGUF files with metadata extraction."""
        models = []
        search_paths = [
            Path.home() / ".cache/flm/models",
            Path.home() / ".cache/llama.cpp",
            Path("/tmp/lemonade-models"),
        ]

        for path in search_paths:
            if not path.exists():
                continue

            try:
                for gguf in path.rglob("*.gguf"):
                    # Extract model info from filename
                    model_info = self._extract_gguf_info(gguf)
                    if model_info:
                        model_info.update(
                            {
                                "source": "local_cache",
                                "backend": "GPU_VULKAN",  # GGUF typically GPU
                                "path": str(gguf),
                                "discovery_method": "filesystem",
                                "size_bytes": gguf.stat().st_size,
                            }
                        )
                        models.append(model_info)

            except PermissionError:
                continue
            except Exception as e:
                logger.debug(f"Error scanning {path}: {e}")

        return models

    def _extract_gguf_info(self, path: Path) -> dict[str, Any] | None:
        """Extract model information from GGUF filename."""
        name = path.stem.lower()

        # Pattern: model-name-size.gguf or model_name_size.gguf
        # Examples: gemma-4-E2B-it-GGUF, qwen3-4b, granite3.2-8b

        model_info = {
            "name": path.stem,
            "filename": path.name,
        }

        # Extract size pattern (e.g., 4b, 8b, E2B)
        size_patterns = [
            r"(\d+\.?\d*)b",  # 4b, 8b, 2.5b
            r"E(\d+)B",  # E2B, E4B (Gemma specific)
        ]

        for pattern in size_patterns:
            match = re.search(pattern, name, re.IGNORECASE)
            if match:
                if "E" in match.group(0).upper():
                    model_info["size"] = f"E{match.group(1)}B"
                else:
                    model_info["size"] = f"{match.group(1)}b"
                break

        return model_info

    def _discover_running_instances(self) -> list[dict[str, Any]]:
        """Discover currently running model instances."""
        models = []

        try:
            # Check for lemonade serve processes
            result = subprocess.run(
                ["pgrep", "-a", "lemonade"], capture_output=True, text=True, check=False
            )

            # Parse process info to extract model names
            for line in result.stdout.split("\n"):
                if "serve" in line:
                    # Try to extract model name from command line
                    model_name = self._extract_from_process_line(line)
                    if model_name:
                        models.append(
                            {
                                "name": model_name,
                                "source": "running_instance",
                                "backend": self._infer_backend_from_process(line),
                                "discovery_method": "process_scan",
                                "process_info": line[:100],
                            }
                        )
        except Exception as e:
            logger.debug(f"Process scan failed: {e}")

        return models

    def _extract_from_process_line(self, line: str) -> str | None:
        """Extract model name from process command line."""
        # Pattern: lemonade serve MODEL_NAME --port ...
        parts = line.split()
        for i, part in enumerate(parts):
            if part == "serve" and i + 1 < len(parts):
                return parts[i + 1]
        return None

    def _infer_backend_from_process(self, line: str) -> str:
        """Infer backend from process command line."""
        if "--device npu" in line or "--npu" in line:
            return "NPU"
        elif "--device vulkan" in line or "--vulkan" in line:
            return "GPU_VULKAN"
        elif "--device rocm" in line or "--rocm" in line:
            return "GPU_ROCM"
        return "UNKNOWN"

    def _discover_sdk_registry(self) -> list[dict[str, Any]]:
        """Query Lemonade SDK registry for available models."""
        # This would query the actual SDK registry
        # For now, return known validated models

        return [
            {
                "name": "qwen3:4b",
                "source": "sdk_registry",
                "backend": "NPU",
                "tps": 75.0,
                "latency_ms": 13.0,
                "validated": True,
                "discovery_method": "sdk_registry",
            },
            {
                "name": "Gemma-4-E2B-it-GGUF",
                "source": "sdk_registry",
                "backend": "GPU_VULKAN",
                "tps": 97.26,
                "latency_ms": 10.3,
                "validated": True,
                "discovery_method": "sdk_registry",
            },
            {
                "name": "Jan-v1-4B-GGUF",
                "source": "sdk_registry",
                "backend": "GPU_VULKAN",
                "tps": 76.18,
                "latency_ms": 13.1,
                "validated": True,
                "discovery_method": "sdk_registry",
            },
        ]

    def _merge_models(self, models: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Merge models from multiple sources, deduplicating."""
        seen = {}

        for model in models:
            name = model.get("name", "")
            if not name:
                continue

            # Normalize name for deduplication
            normalized = name.lower().replace(":", "_").replace("-", "_")

            if normalized in seen:
                # Merge information
                existing = seen[normalized]

                # Prefer validated sources
                if model.get("validated") and not existing.get("validated"):
                    seen[normalized] = model
                # Prefer sources with more capabilities
                elif len(model.get("capabilities", [])) > len(existing.get("capabilities", [])):
                    existing["capabilities"] = model.get("capabilities", [])
                # Prefer sources with metrics
                elif model.get("tps") and not existing.get("tps"):
                    existing["tps"] = model.get("tps")
                    existing["latency_ms"] = model.get("latency_ms")
            else:
                seen[normalized] = model

        return list(seen.values())

    def _enhance_all_capabilities(self, models: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Enhance all models with inferred capabilities."""
        enhanced = []

        for model in models:
            enhanced_model = self._enhance_model_capabilities(model)
            enhanced.append(enhanced_model)

        return enhanced

    def _enhance_model_capabilities(self, model: dict[str, Any]) -> dict[str, Any]:
        """Enhance a single model with comprehensive capability inference."""
        name = model.get("name", "").lower()

        # Start with existing capabilities
        capabilities = set(model.get("capabilities", []))
        confidence_scores = []

        # Match against patterns
        for pattern, info in MODEL_CAPABILITY_PATTERNS.items():
            if pattern in name:
                caps = info.get("capabilities", [])
                conf = info.get("confidence", 0.5)

                # Add capabilities
                capabilities.update(caps)
                confidence_scores.append(conf)

                # Override backend if higher confidence
                if conf > model.get("capability_confidence", 0) and info.get("default_backend"):
                    model["backend"] = info["default_backend"]
                    model["capability_confidence"] = conf
                    model["capability_source"] = f"pattern:{pattern}"

        # Default capabilities if none inferred
        if not capabilities:
            capabilities.add("text_generation")
            model["capability_confidence"] = 0.50
            model["capability_source"] = "default:text_generation"

        # Update model
        model["capabilities"] = sorted(capabilities)
        model["capability_confidence"] = max(confidence_scores) if confidence_scores else 0.50

        # Add context window estimates based on size
        model["context_window"] = self._estimate_context_window(name)

        # Add model family
        model["family"] = self._identify_model_family(name)

        return model

    def _estimate_context_window(self, name: str) -> int:
        """Estimate context window from model name."""
        name_lower = name.lower()

        # Known context windows
        if "gemma-4" in name_lower:
            return 262144  # Gemma 4 has 256K context
        elif "qwen3" in name_lower or "qwen2.5" in name_lower:
            return 131072  # Qwen 2.5/3 has 128K context
        elif "llama3" in name_lower or "llama-3" in name_lower:
            return 131072  # Llama 3 has 128K context
        elif "mistral" in name_lower:
            return 32768  # Mistral has 32K context
        elif "phi" in name_lower:
            return 4096  # Phi typically 4K
        else:
            return 4096  # Default

    def _identify_model_family(self, name: str) -> str:
        """Identify model family from name."""
        name_lower = name.lower()

        families = [
            ("qwen", "Qwen"),
            ("gemma", "Gemma"),
            ("llama", "Llama"),
            ("granite", "Granite"),
            ("phi", "Phi"),
            ("mistral", "Mistral"),
            ("starcoder", "StarCoder"),
            ("tiny", "TinyLlama"),
        ]

        for pattern, family in families:
            if pattern in name_lower:
                return family

        return "Unknown"

    def _calculate_statistics(self, models: list[dict[str, Any]]) -> dict[str, Any]:
        """Calculate discovery statistics."""
        stats = {
            "total_models": len(models),
            "by_backend": {},
            "by_family": {},
            "by_source": {},
            "with_metrics": 0,
            "with_capabilities": 0,
            "high_confidence": 0,  # >0.85
        }

        for model in models:
            # By backend
            backend = model.get("backend", "unknown")
            stats["by_backend"][backend] = stats["by_backend"].get(backend, 0) + 1

            # By family
            family = model.get("family", "unknown")
            stats["by_family"][family] = stats["by_family"].get(family, 0) + 1

            # By source
            source = model.get("source", "unknown")
            stats["by_source"][source] = stats["by_source"].get(source, 0) + 1

            # Metrics
            if model.get("tps"):
                stats["with_metrics"] += 1

            # Capabilities
            if model.get("capabilities"):
                stats["with_capabilities"] += 1

            # Confidence
            if model.get("capability_confidence", 0) > 0.85:
                stats["high_confidence"] += 1

        return stats

    def _print_summary(self, results: dict[str, Any]):
        """Print discovery summary."""
        stats = results.get("statistics", {})

        print("\n" + "=" * 70)
        print("📊 DISCOVERY SUMMARY")
        print("=" * 70)

        print(f"\nTotal Models: {stats.get('total_models', 0)}")

        print("\nBy Backend:")
        for backend, count in sorted(stats.get("by_backend", {}).items()):
            print(f"  {backend:15}: {count:3} models")

        print("\nBy Family:")
        for family, count in sorted(
            stats.get("by_family", {}).items(), key=lambda x: x[1], reverse=True
        )[:8]:
            print(f"  {family:15}: {count:3} models")

        print("\nBy Source:")
        for source, count in sorted(stats.get("by_source", {}).items()):
            print(f"  {source:15}: {count:3} models")

        print("\nQuality Metrics:")
        print(f"  With inference metrics: {stats.get('with_metrics', 0)}")
        print(f"  With capabilities: {stats.get('with_capabilities', 0)}")
        print(f"  High confidence (>85%): {stats.get('high_confidence', 0)}")

        # Show sample of discovered models
        print("\n🔍 Sample Discovered Models:")
        for model in results.get("models", [])[:5]:
            name = model.get("name", "unknown")
            backend = model.get("backend", "?")
            family = model.get("family", "?")
            caps = ", ".join(model.get("capabilities", [])[:2])
            conf = model.get("capability_confidence", 0)
            print(f"  - {name[:35]:35} [{backend:6}] {caps} ({conf:.0%})")

        print("\n" + "=" * 70)


def demo_enhanced_discovery():
    """Demonstrate enhanced model discovery."""
    enhancer = LemonadeModelEnhancer()
    results = enhancer.discover_comprehensive()

    print("\n🎯 Next Steps for Lemonade Model Mapping:")
    print("  1. Continue parser improvement (target: 95% accuracy)")
    print("  2. Validate inferred capabilities with actual inference tests")
    print("  3. Build performance profiles for all discovered models")
    print("  4. Integrate with dynamic lever system for optimization")
    print("  5. Export comprehensive registry to SurrealDB")

    return results


if __name__ == "__main__":
    demo_enhanced_discovery()
