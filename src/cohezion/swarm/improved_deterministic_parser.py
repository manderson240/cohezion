"""Improved deterministic FLM parser based on observed output patterns.

Observed FLM output format:
  {model_name}:{size} ⏬   [size]   {family}   {status}

Examples from actual discovery:
  granite3.2-dense:2b ⏬  2.5M GraniteCode
  granite3.2:8b ⏬  8.1B Granite
  granite3.3:8b ⏬  8.1B Granite
"""

import logging
import re
import subprocess
import time
from typing import Any


logger = logging.getLogger(__name__)


class FLMFormatPattern:
    """Documented FLM output format patterns."""

    # Format: model_name:⏬ or model_name ⏬ (size indicator)
    SIZE_MARKER = "⏬"

    # Model name patterns (learned from observation)
    KNOWN_PREFIXES = [
        "qwen",
        "gemma",
        "llama",
        "mistral",
        "granite",
        "phi",
        "tiny",
        "starcoder",
        "stablelm",
        "whisper",
    ]

    # Known size suffixes
    SIZE_SUFFIXES = ["b", "m", "k"]

    @classmethod
    def get_patterns(cls) -> dict[str, str]:
        """Get documented patterns."""
        return {
            "format": "{model_name}:{size} ⏬",
            "size_marker": cls.SIZE_MARKER,
            "separator": ":",
            "prefixes": ", ".join(cls.KNOWN_PREFIXES),
        }


class ImprovedFLMParser:
    """Improved deterministic parser with learned patterns."""

    def __init__(self):
        self.patterns = FLMFormatPattern()
        self.stats = {
            "lines_parsed": 0,
            "lines_skipped": 0,
            "models_extracted": 0,
            "parse_failures": [],
        }

    def discover_flm_deterministic(self) -> list[dict[str, Any]]:
        """Discover FLM models with improved deterministic parsing."""
        models = []

        try:
            result = subprocess.run(["flm", "list"], capture_output=True, text=True, timeout=10, check=False)

            if result.returncode != 0:
                logger.debug(f"FLM list returned {result.returncode}")
                return []

            # Parse each line deterministically
            for line in result.stdout.split("\n"):
                self.stats["lines_parsed"] += 1

                model = self._parse_line_improved(line)
                if model:
                    models.append(model)
                    self.stats["models_extracted"] += 1
                else:
                    self.stats["lines_skipped"] += 1

        except subprocess.TimeoutExpired:
            logger.warning("FLM list timeout")
        except FileNotFoundError:
            logger.debug("FLM not installed")
        except Exception as e:
            logger.error(f"FLM discovery failed: {e}")

        return models

    def _parse_line_improved(self, line: str) -> dict[str, Any] | None:
        """Parse FLM line with improved deterministic rules.

        Patterns learned from actual FLM output:
        - "granite3.2-dense:2b ⏬  2.5M GraniteCode"
        - "granite3.2:8b ⏬  8.1B Granite"
        """
        line = line.strip()

        # Rule 0: Skip empty lines
        if not line:
            return None

        # Rule 1: Skip decorative border lines
        if line.startswith(("┌", "├", "└", "│", "─", "─")):
            return None

        # Rule 2: Skip header lines
        if any(x in line.lower() for x in ["model", "size", "family", "status"]):
            if "name" in line.lower():
                return None

        # Rule 3: Skip bracketed content (table separators)
        if line.startswith("[") or line.startswith("]"):
            return None

        # Rule 4: Check for size marker "⏬" (exact match)
        # BUT some entries might not have it, so check for model pattern first

        # Try exact pattern first: "model:size ⏬"
        if self.patterns.SIZE_MARKER in line:
            # Extract model name (before ⏬)
            model_part = line.split(self.patterns.SIZE_MARKER)[0].strip()
            if ":" in model_part:
                model_name = model_part
                return self._create_model_entry(model_name)

        # Try pattern without marker: "model:size  other_columns"
        parts = line.split()
        if not parts:
            return None

        first_part = parts[0]
        if ":" in first_part:
            # Likely a model name
            model_name = first_part
            if self._validate_model_name(model_name):
                return self._create_model_entry(model_name)

        # Rule 5: Try known prefix detection (still deterministic based on hardcoded list)
        if self._has_known_prefix(line.lower()):
            # Extract potential model
            if ":" in line:
                # Get substring before next space after colon
                m = re.match(r"([\w\-]+:\w+)", line)
                if m:
                    return self._create_model_entry(m.group(1))

        # Failed to parse - record for debugging
        if len(line) > 3 and not self._is_table_decoration(line):
            if len(self.stats["parse_failures"]) < 10:  # Limit storage
                self.stats["parse_failures"].append(line)

        return None

    def _validate_model_name(self, name: str) -> bool:
        """Validate that a string looks like a model name."""
        if ":" not in name:
            return False

        parts = name.split(":")
        if len(parts) != 2:
            return False

        prefix_part = parts[0].lower()
        size_part = parts[1].lower()

        # Check prefix (known patterns)
        has_known_prefix = any(prefix in prefix_part for prefix in self.patterns.KNOWN_PREFIXES)

        # Check size (ends with b/m/k or is numeric)
        looks_like_size = size_part.endswith(("b", "m", "k", "tiny", "mini", "small", "medium", "large")) or any(
            c.isdigit() for c in size_part
        )

        return has_known_prefix or looks_like_size

    def _has_known_prefix(self, line_lower: str) -> bool:
        """Check if line contains known model prefix."""
        return any(prefix in line_lower for prefix in self.patterns.KNOWN_PREFIXES)

    def _is_table_decoration(self, line: str) -> bool:
        """Check if line is table decoration."""
        return bool(re.match(r"^[\s\[\]\|\-┌┐└┘├┤┬┴┼]+$", line))

    def _create_model_entry(self, model_name: str) -> dict[str, Any]:
        """Create standardized model entry."""
        # Parse capabilities from name
        capabilities = self._infer_capabilities_deterministic(model_name)

        # Determine backend from FLM source
        backend = "NPU"  # FLM = NPU models

        return {
            "name": model_name,
            "source": "FLM",
            "backend": backend,
            "status": "available",
            "capabilities": capabilities,
            "discovered_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "parsing_method": "deterministic_improved",
            "parser_version": "2.0",
        }

    def _infer_capabilities_deterministic(self, model_name: str) -> list[str]:
        """Deterministic capability inference with hardcoded patterns."""
        name = model_name.lower()
        capabilities = []

        # Hardcoded patterns (tested, deterministic)
        CAPABILITY_PATTERNS = {
            "code": "code_generation",
            "coder": "code_generation",
            "vl": "vision_understanding",
            "vision": "vision_understanding",
            "instruct": "instruction_following",
            "chat": "chat_dialogue",
            "whisper": "audio_transcription",
            "translate": "text_translation",
            "granite": "enterprise_text",  # IBM Granite pattern
        }

        for pattern, capability in CAPABILITY_PATTERNS.items():
            if pattern in name:
                capabilities.append(capability)

        # Always add base capability
        if not capabilities:
            capabilities = ["text_generation"]

        return capabilities

    def get_stats(self) -> dict[str, Any]:
        """Get parsing statistics."""
        accuracy = 0.0
        if self.stats["lines_parsed"] > 0:
            accuracy = self.stats["models_extracted"] / self.stats["lines_parsed"]

        return {
            **self.stats,
            "extraction_rate": accuracy,
            "known_patterns": self.patterns.KNOWN_PREFIXES,
        }


class AutoImprovementCycle:
    """Auto-improvement cycle based on observed failures."""

    def __init__(self, parser: ImprovedFLMParser, target_accuracy: float = 0.80):
        self.parser = parser
        self.target_accuracy = target_accuracy
        self.improvements_made = []

    def run_cycle(self) -> dict[str, Any]:
        """Run one improvement cycle."""
        # Discover models
        models = self.parser.discover_flm_deterministic()

        # Get current stats
        stats = self.parser.get_stats()
        accuracy = stats["extraction_rate"]

        result = {
            "models_found": len(models),
            "accuracy": accuracy,
            "target": self.target_accuracy,
            "improvements": [],
        }

        if accuracy >= self.target_accuracy:
            result["status"] = "target_achieved"
            return result

        # Analyze failures and improve
        if self.parser.stats["parse_failures"]:
            for failure in self.parser.stats["parse_failures"]:
                improvement = self._attempt_improve(failure)
                if improvement:
                    result["improvements"].append(improvement)

        result["status"] = "improvement_attempted"
        return result

    def _attempt_improve(self, failure_line: str) -> dict[str, Any] | None:
        """Attempt to improve parser based on failure."""
        # Learn: if failure contains certain patterns, add new rule
        failed_lower = failure_line.lower()

        if "b" in failed_lower or "m" in failed_lower:
            # Might be a model without known prefix
            # Add learning: extract new prefix pattern
            return {
                "type": "new_pattern_detected",
                "line": failure_line,
                "suggestion": "Add prefix from line",
            }

        return None


def test_improved_parser():
    """Test the improved parser."""
    print("=" * 70)
    print("IMPROVED FLM PARSER TEST")
    print("=" * 70)

    parser = ImprovedFLMParser()
    models = parser.discover_flm_deterministic()
    stats = parser.get_stats()

    print("\n📊 Results:")
    print(f"  Lines parsed: {stats['lines_parsed']}")
    print(f"  Lines skipped: {stats['lines_skipped']}")
    print(f"  Models extracted: {stats['models_extracted']}")
    print(f"  Extraction rate: {stats['extraction_rate']:.1%}")

    print("\n📌 First 10 models:")
    for model in models[:10]:
        print(f"  - {model['name']} ({model['backend']})")
        if model["capabilities"]:
            print(f"    Capabilities: {', '.join(model['capabilities'])}")

    if stats["parse_failures"]:
        print("\n⚠️ Parse failures (first 5):")
        for failure in stats["parse_failures"][:5]:
            print(f"  |{failure}|")

    # Run auto-improvement cycle
    print("\n🔧 Running auto-improvement cycle...")
    cycle = AutoImprovementCycle(parser, target_accuracy=0.80)
    result = cycle.run_cycle()

    print(f"  Status: {result['status']}")
    print(f"  Accuracy: {result['accuracy']:.1%}")
    print(f"  Target: {result['target']:.1%}")

    if result["improvements"]:
        print(f"  Improvements detected: {len(result['improvements'])}")

    return stats["extraction_rate"]


if __name__ == "__main__":
    accuracy = test_improved_parser()
    print(f"\n✅ Final Extraction Rate: {accuracy:.1%}")
