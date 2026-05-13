"""Deterministic model discovery with skill-based heuristics fallback.

BALANCED APPROACH:
- Deterministic: Known formats, tested code paths, reliable execution
- Skill-based heuristics: Unknown formats, pattern matching, adaptive parsing
- Clear separation: Deterministic first, heuristic fallback when deterministic fails
"""

import logging
import subprocess
import time
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# DETERMINISTIC LAYER: Known, tested, reliable
# ═══════════════════════════════════════════════════════════════════════════════


class DeterministicDiscovery:
    """Deterministic discovery for known sources and formats."""

    def discover_flm(self) -> list[dict[str, Any]]:
        """Deterministic FLM discovery - tested code path."""
        models = []

        try:
            # Known working invocation
            result = subprocess.run(
                ["flm", "list"],
                capture_output=True,
                text=True,
                timeout=10,  # Deterministic timeout
                check=False,  # Don't raise on non-zero exit
            )

            if result.returncode != 0:
                logger.debug(f"FLM list returned {result.returncode}")
                return []

            # Deterministic parsing of known format
            for line in result.stdout.split("\n"):
                model = self._parse_flm_line_deterministic(line)
                if model:
                    models.append(model)

        except subprocess.TimeoutExpired:
            logger.warning("FLM list timeout (deterministic)")
        except FileNotFoundError:
            logger.debug("FLM not installed")
        except Exception as e:
            logger.error(f"FLM deterministic path failed: {e}")

        return models

    def _parse_flm_line_deterministic(self, line: str) -> dict[str, Any] | None:
        """Deterministic FLM line parsing - no heuristics."""
        line = line.strip()

        # Deterministic rules (exact matches)
        if not line or line.startswith("[") or line.startswith("┌"):
            return None  # Header/border lines

        if "⏬" not in line:
            return None  # Not a model line (no download indicator)

        # Exact pattern: "model:size ⏬"
        parts = line.split()
        if not parts:
            return None

        name_part = parts[0]
        if ":" not in name_part:
            return None

        return {
            "name": name_part,
            "source": "FLM",
            "backend": "NPU",
            "status": "available",
            "discovered_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "parsing_method": "deterministic",
        }

    def discover_known_models(self) -> list[dict[str, Any]]:
        """Deterministic discovery from known validated models."""
        # Hardcoded validated models - never changes
        return [
            {
                "name": "CODE_SPECIALIST",
                "model_name": "qwen3:4b",
                "backend": "NPU",
                "tps": 75.0,
                "latency_ms": 13.0,
                "context_window": 131072,
                "capabilities": ["code_generation", "code_completion"],
                "source": "validated",
                "parsing_method": "deterministic",
            },
            {
                "name": "REASONING_SPECIALIST",
                "model_name": "Gemma-4-E2B-it-GGUF",
                "backend": "GPU_VULKAN",
                "tps": 97.26,
                "latency_ms": 10.3,
                "context_window": 262144,
                "capabilities": ["reasoning", "long_context"],
                "source": "validated",
                "parsing_method": "deterministic",
            },
            {
                "name": "NOVEL_SPECIALIST",
                "model_name": "Jan-v1-4B-GGUF",
                "backend": "GPU_VULKAN",
                "tps": 76.18,
                "latency_ms": 13.1,
                "context_window": 4096,
                "capabilities": ["novel_architecture"],
                "source": "validated",
                "parsing_method": "deterministic",
            },
        ]

    def discover_local_gguf(self, max_models: int = 50) -> list[dict[str, Any]]:
        """Deterministic local file discovery."""
        models = []
        search_paths = [
            Path.home() / ".cache/flm/models",
            Path.home() / ".cache/llama.cpp",
        ]

        for path in search_paths:
            if not path.exists():
                continue

            try:
                # Deterministic glob
                gguf_files = sorted(path.rglob("*.gguf"))

                for gguf in gguf_files[:max_models]:
                    models.append(
                        {
                            "name": gguf.stem,
                            "path": str(gguf),
                            "backend": "GPU_VULKAN",
                            "format": "gguf",
                            "source": "local_cache",
                            "parsing_method": "deterministic",
                        }
                    )

            except PermissionError:
                logger.debug(f"Permission denied: {path}")
            except Exception as e:
                logger.error(f"Local discovery failed for {path}: {e}")

        return models


# ═══════════════════════════════════════════════════════════════════════════════
# HEURISTIC/SKILL LAYER: Adaptive, pattern-based fallback
# ═══════════════════════════════════════════════════════════════════════════════


class HeuristicDiscovery:
    """Heuristic/skill-based discovery for unknown formats."""

    def discover_with_skill(self, command: list[str], source: str) -> list[dict[str, Any]]:
        """Skill-based discovery when deterministic fails."""
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=10)

            return self._parse_with_heuristics(result.stdout, source)

        except Exception as e:
            logger.debug(f"Skill-based discovery failed: {e}")
            return []

    def _parse_with_heuristics(self, output: str, source: str) -> list[dict[str, Any]]:
        """Parse using skill-based heuristics."""
        models = []
        lines = output.split("\n")

        # Heuristic: Lines with colons often contain model:size
        # Skill: Pattern matching learned from FLM format
        for line in lines:
            line = line.strip()

            # Skip obvious non-model lines
            if len(line) < 3 or line.startswith("#"):
                continue

            # Heuristic: Look for model patterns
            model = self._apply_parsing_heuristics(line, source)
            if model:
                models.append(model)

        return models

    def _apply_parsing_heuristics(self, line: str, source: str) -> dict[str, Any] | None:
        """Apply learned heuristics to parse unknown line."""
        # Heuristic 1: Contains version marker (1.0, v2, etc.)
        if any(c.isdigit() for c in line) and ":" in line:
            parts = line.replace("\t", " ").split()
            for part in parts:
                if ":" in part and len(part) > 2:
                    return {
                        "name": part.split()[0] if " " in part else part,
                        "source": source,
                        "backend": "unknown",
                        "parsing_method": "heuristic",
                        "confidence": "medium",
                    }

        # Heuristic 2: Common model name patterns
        known_prefixes = ["qwen", "gemma", "llama", "mistral", "phi"]
        line_lower = line.lower()

        for prefix in known_prefixes:
            if prefix in line_lower:
                # Extract potential model name
                return {
                    "name": line.split()[0] if " " in line else line[:50],
                    "source": source,
                    "backend": "inferred",
                    "parsing_method": "heuristic",
                    "confidence": "low",
                    "note": f"Detected prefix: {prefix}",
                }

        return None

    def infer_capabilities_fallback(self, model_name: str) -> list[str]:
        """Skill-based capability inference when explicit data unavailable."""
        name = model_name.lower()
        capabilities = []

        # Pattern-based inference (skill learned from naming conventions)
        patterns = {
            "code": ["code_generation", "code_completion"],
            "coder": ["code_generation", "code_completion"],
            "vl": ["vision_understanding"],
            "vision": ["vision_understanding"],
            "instruct": ["instruction_following"],
            "chat": ["chat_conversation"],
            "whisper": ["audio_transcription"],
            "translate": ["translation"],
        }

        for pattern, caps in patterns.items():
            if pattern in name:
                capabilities.extend(caps)

        # Always assume these base capabilities
        capabilities.extend(["text_generation"])

        return list(set(capabilities))


# ═══════════════════════════════════════════════════════════════════════════════
# BALANCED ORCHESTRATOR: Deterministic first, heuristic fallback
# ═══════════════════════════════════════════════════════════════════════════════


class BalancedModelDiscovery:
    """Orchestrates deterministic and heuristic discovery."""

    def __init__(self):
        self.deterministic = DeterministicDiscovery()
        self.heuristic = HeuristicDiscovery()
        self.stats = {
            "deterministic_success": 0,
            "heuristic_fallback": 0,
            "heuristic_success": 0,
            "total_models": 0,
        }

    def discover_all(self) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Balanced discovery: deterministic first, heuristic fallback."""
        all_models = []

        # Layer 1: Deterministic (reliable, tested)
        logger.info("Phase 1: Deterministic discovery...")

        # Known validated models (always works)
        known = self.deterministic.discover_known_models()
        all_models.extend(known)
        self.stats["deterministic_success"] += len(known)

        # FLM (deterministic path)
        flm = self.deterministic.discover_flm()
        if flm:
            all_models.extend(flm)
            self.stats["deterministic_success"] += len(flm)
        else:
            # FALLBACK: Heuristic for FLM
            logger.info("FLM deterministic failed, trying heuristic fallback...")
            self.stats["heuristic_fallback"] += 1
            flm_heuristic = self.heuristic.discover_with_skill(["flm", "list"], "FLM")
            if flm_heuristic:
                all_models.extend(flm_heuristic)
                self.stats["heuristic_success"] += len(flm_heuristic)

        # Local files (deterministic)
        local = self.deterministic.discover_local_gguf()
        all_models.extend(local)
        self.stats["deterministic_success"] += len(local)

        # Layer 2: Heuristic enrichment (capability inference)
        logger.info("Phase 2: Heuristic enrichment...")
        for model in all_models:
            if "capabilities" not in model or not model["capabilities"]:
                # Fallback to skill-based inference
                model["capabilities"] = self.heuristic.infer_capabilities_fallback(model.get("name", ""))
                model["capability_method"] = "heuristic_inference"

        # Deduplicate
        unique_models = self._deduplicate(all_models)
        self.stats["total_models"] = len(unique_models)

        # Return models and stats
        report = {
            "total_models": len(unique_models),
            "by_source": self._count_by_source(unique_models),
            "by_parsing_method": self._count_by_method(unique_models),
            "stats": self.stats,
            "balance_ratio": self._calculate_balance_ratio(),
        }

        return unique_models, report

    def _deduplicate(self, models: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Remove duplicates, preferring deterministic over heuristic."""
        seen = {}

        for model in models:
            name = model.get("name", "")

            if name not in seen:
                seen[name] = model
            else:
                # Prefer deterministic over heuristic
                existing = seen[name]
                if existing.get("parsing_method") == "heuristic" and model.get("parsing_method") == "deterministic":
                    seen[name] = model

        return list(seen.values())

    def _count_by_source(self, models: list[dict[str, Any]]) -> dict[str, int]:
        """Count models by source."""
        counts = {}
        for m in models:
            src = m.get("source", "unknown")
            counts[src] = counts.get(src, 0) + 1
        return counts

    def _count_by_method(self, models: list[dict[str, Any]]) -> dict[str, int]:
        """Count by parsing method."""
        counts = {"deterministic": 0, "heuristic": 0}
        for m in models:
            method = m.get("parsing_method", "unknown")
            if "deterministic" in method:
                counts["deterministic"] += 1
            elif "heuristic" in method:
                counts["heuristic"] += 1
        return counts

    def _calculate_balance_ratio(self) -> float:
        """Calculate deterministic vs heuristic ratio."""
        total = self.stats["deterministic_success"] + self.stats["heuristic_success"]
        if total == 0:
            return 0.0
        return self.stats["deterministic_success"] / total


# ═══════════════════════════════════════════════════════════════════════════════
# USAGE
# ═══════════════════════════════════════════════════════════════════════════════


def run_balanced_discovery():
    """Run discovery with balance reporting."""
    discovery = BalancedModelDiscovery()
    models, report = discovery.discover_all()

    print("=" * 70)
    print("BALANCED MODEL DISCOVERY COMPLETE")
    print("=" * 70)

    print("\n📊 Results:")
    print(f"  Total models: {report['total_models']}")
    print(f"  Deterministic: {report['by_parsing_method'].get('deterministic', 0)}")
    print(f"  Heuristic: {report['by_parsing_method'].get('heuristic', 0)}")

    print(f"\n📈 Balance Ratio: {report['balance_ratio']:.2%}")
    print("  (Higher = more deterministic/reliable)")

    print("\n📁 By Source:")
    for source, count in report["by_source"].items():
        print(f"  {source}: {count}")

    if report["stats"]["heuristic_fallback"] > 0:
        print(f"\n⚠ Heuristic Fallbacks: {report['stats']['heuristic_fallback']}")
        print("  (Consider improving deterministic parsers)")

    return models, report


if __name__ == "__main__":
    models, report = run_balanced_discovery()
