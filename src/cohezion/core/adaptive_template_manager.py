#!/usr/bin/env python3
"""
COHEZION ADAPTIVE TEMPLATE MANAGEMENT SYSTEM v1.1.48

This system enables seamless cross-model family compatibility by automatically
detecting and converting between different prompt template formats.
Supports ChatML, Microsoft, Llama3, and custom formats.

Compound engineering through template evolution and learning.
"""

import json
import re
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TemplateFormat(Enum):
    """Supported template formats"""

    CHATML = "chatml"
    MICROSOFT = "microsoft"
    LLAMA3 = "llama3"
    ALPACA = "alpaca"
    VICUNA = "vicuna"
    CUSTOM = "custom"


@dataclass
class TemplateConfig:
    """Template configuration with conversion rules"""

    format_name: str
    prefix: str
    suffix: str
    system_token: str
    user_token: str
    assistant_token: str
    separator: Optional[str] = None
    thinking_prefix: Optional[str] = None
    thinking_suffix: Optional[str] = None


class AdaptiveTemplateManager:
    """Dynamic template adaptation and conversion engine"""

    def __init__(self):
        self.templates = self._load_template_library()
        self.conversion_matrix = self._build_conversion_matrix()
        self.template_history = []  # For learning and optimization
        self.performance_cache = {}

    def _load_template_library(self) -> Dict[TemplateFormat, TemplateConfig]:
        """Load comprehensive template library"""
        return {
            TemplateFormat.CHATML: TemplateConfig(
                format_name="chatml",
                prefix="<<|im_start|>>",
                suffix="<<|im_end|>>",
                system_token="system",
                user_token="user",
                assistant_token="assistant",
                thinking_prefix="<<|im_start|>>thinking\n",
                thinking_suffix="<<|im_end|>>\n",
            ),
            TemplateFormat.MICROSOFT: TemplateConfig(
                format_name="microsoft",
                prefix="<<|im_start|>>",
                suffix="<<|im_end|>>",
                separator="<<|im_sep|>>",
                system_token="system",
                user_token="user",
                assistant_token="assistant",
            ),
            TemplateFormat.LLAMA3: TemplateConfig(
                format_name="llama3",
                prefix="<|begin_of_text|>",
                suffix="<|eot_id|>",
                system_token="<|start_header_id|>system<|end_header_id|>\n\n",
                user_token="<|start_header_id|>user<|end_header_id|>\n\n",
                assistant_token="<|start_header_id|>assistant<|end_header_id|>\n\n",
            ),
            TemplateFormat.ALPACA: TemplateConfig(
                format_name="alpaca",
                prefix="",
                suffix="",
                system_token="### Instruction:\n",
                user_token="### Input:\n",
                assistant_token="### Response:\n",
            ),
            TemplateFormat.VICUNA: TemplateConfig(
                format_name="vicuna",
                prefix="",
                suffix="",
                system_token="SYSTEM: ",
                user_token="USER: ",
                assistant_token="ASSISTANT: ",
                separator="\n\n",
            ),
        }

    def _build_conversion_matrix(
        self,
    ) -> Dict[Tuple[TemplateFormat, TemplateFormat], str]:
        """Build conversion rule matrix"""
        return {
            # Direct conversions (lossless or minimal loss)
            (TemplateFormat.CHATML, TemplateFormat.MICROSOFT): "separator_injection",
            (TemplateFormat.MICROSOFT, TemplateFormat.CHATML): "separator_removal",
            (TemplateFormat.LLAMA3, TemplateFormat.CHATML): "header_replacement",
            (TemplateFormat.CHATML, TemplateFormat.LLAMA3): "header_conversion",
            # Semi-compatible conversions
            (TemplateFormat.ALPACA, TemplateFormat.CHATML): "wrap_chatml",
            (TemplateFormat.VICUNA, TemplateFormat.CHATML): "wrap_chatml",
            (TemplateFormat.CHATML, TemplateFormat.ALPACA): "unwrap_alpaca",
            (TemplateFormat.CHATML, TemplateFormat.VICUNA): "unwrap_vicuna",
            # Complex conversions (higher potential for loss)
            (TemplateFormat.ALPACA, TemplateFormat.LLAMA3): "convert_llama3",
            (TemplateFormat.LLAMA3, TemplateFormat.ALPACA): "convert_alpaca",
            (TemplateFormat.VICUNA, TemplateFormat.LLAMA3): "convert_llama3",
            (TemplateFormat.LLAMA3, TemplateFormat.VICUNA): "convert_vicuna",
        }

    def detect_model_template(self, model_name: str) -> TemplateFormat:
        """Auto-detect template format based on model family"""
        model_name_lower = model_name.lower()

        # Primary model family detection
        if any(x in model_name_lower for x in ["qwen3", "qwen2.5", "qwen2"]):
            logger.debug(f"Detected ChatML template for {model_name}")
            return TemplateFormat.CHATML

        elif any(x in model_name_lower for x in ["phi", "mistral-small"]):
            logger.debug(f"Detected Microsoft template for {model_name}")
            return TemplateFormat.MICROSOFT

        elif any(x in model_name_lower for x in ["llama", "gemma", "tinyllama"]):
            logger.debug(f"Detected Llama3 template for {model_name}")
            return TemplateFormat.LLAMA3

        elif any(x in model_name_lower for x in ["vicuna", "koala"]):
            logger.debug(f"Detected Vicuna template for {model_name}")
            return TemplateFormat.VICUNA

        elif any(x in model_name_lower for x in ["alpaca", "guanaco"]):
            logger.debug(f"Detected Alpaca template for {model_name}")
            return TemplateFormat.ALPACA

        # Fallback detection based on model characteristics
        elif "8b" in model_name_lower or "7b" in model_name_lower:
            logger.debug(f"Falling back to ChatML for small model {model_name}")
            return TemplateFormat.CHATML

        else:
            logger.debug(
                f"Using default ChatML template for unknown model {model_name}"
            )
            return TemplateFormat.CHATML

    def convert_message_format(
        self,
        messages: List[Dict],
        source_format: TemplateFormat,
        target_format: TemplateFormat,
    ) -> Tuple[List[Dict], float]:
        """
        Convert message format between different template types

        Returns:
            Tuple of (converted_messages, conversion_confidence)
        """
        if source_format == target_format:
            return messages, 1.0

        conversion_key = (source_format, target_format)

        if conversion_key not in self.conversion_matrix:
            logger.warning(
                f"No direct conversion from {source_format.value} to {target_format.value}"
            )
            return self._generic_conversion(messages, source_format, target_format)

        conversion_method = self.conversion_matrix[conversion_key]
        converted_messages, confidence = self._apply_conversion_method(
            messages, conversion_method, source_format, target_format
        )

        # Record conversion for learning
        self._record_conversion(
            source_format, target_format, conversion_method, confidence
        )

        return converted_messages, confidence

    def _apply_conversion_method(
        self,
        messages: List[Dict],
        method: str,
        source: TemplateFormat,
        target: TemplateFormat,
    ) -> Tuple[List[Dict], float]:
        """Apply specific conversion method"""

        if method == "separator_injection":
            return self._inject_separator(messages, source, target)
        elif method == "separator_removal":
            return self._remove_separator(messages, source, target)
        elif method == "header_replacement":
            return self._replace_headers(messages, source, target)
        elif method == "header_conversion":
            return self._convert_headers(messages, source, target)
        elif method == "wrap_chatml":
            return self._wrap_in_chatml(messages, source, target)
        elif method == "unwrap_alpaca":
            return self._unwrap_from_chatml(messages, target)
        elif method == "unwrap_vicuna":
            return self._unwrap_from_chatml(messages, target)
        elif method == "convert_llama3":
            return self._convert_to_llama3(messages, source, target)
        elif method == "convert_alpaca":
            return self._convert_to_alpaca(messages, source, target)
        else:
            return self._generic_conversion(messages, source, target)

    def _inject_separator(
        self, messages: List[Dict], source: TemplateFormat, target: TemplateFormat
    ) -> Tuple[List[Dict], float]:
        """Inject Microsoft separator into ChatML messages"""
        target_template = self.templates[target]
        converted_messages = []

        for message in messages:
            converted_message = message.copy()

            # Add separator for multi-part content
            if "\n\n" in message.get("content", ""):
                parts = message["content"].split("\n\n")
                if len(parts) > 1:
                    converted_message["content"] = (
                        f" {target_template.separator} ".join(parts)
                    )

            converted_messages.append(converted_message)

        return converted_messages, 0.95  # High confidence conversion

    def _remove_separator(
        self, messages: List[Dict], source: TemplateFormat, target: TemplateFormat
    ) -> Tuple[List[Dict], float]:
        """Remove Microsoft separator when converting to ChatML"""
        source_template = self.templates[source]
        converted_messages = []

        for message in messages:
            converted_message = message.copy()

            if source_template.separator in message.get("content", ""):
                converted_message["content"] = message["content"].replace(
                    f" {source_template.separator} ", "\n\n"
                )

            converted_messages.append(converted_message)

        return converted_messages, 0.95

    def _replace_headers(
        self, messages: List[Dict], source: TemplateFormat, target: TemplateFormat
    ) -> Tuple[List[Dict], float]:
        """Replace Llama3 headers with ChatML tokens"""
        target_template = self.templates[target]
        converted_messages = []

        for message in messages:
            converted_message = message.copy()
            role = message.get("role", "user")

            if role == "system":
                converted_message["role"] = "system"
                converted_message["content"] = (
                    target_template.system_token + message.get("content", "")
                )
            elif role == "user":
                converted_message["role"] = "user"
                converted_message["content"] = target_template.user_token + message.get(
                    "content", ""
                )
            elif role == "assistant":
                converted_message["role"] = "assistant"
                converted_message["content"] = (
                    target_template.assistant_token + message.get("content", "")
                )

            converted_messages.append(converted_message)

        return converted_messages, 0.90

    def _convert_headers(
        self, messages: List[Dict], source: TemplateFormat, target: TemplateFormat
    ) -> Tuple[List[Dict], float]:
        """Convert ChatML to Llama3 headers"""
        target_template = self.templates[target]
        converted_messages = []

        for message in messages:
            converted_message = message.copy()
            role = message.get("role", "user")

            # Extract content from ChatML-wrapped messages
            content = message.get("content", "")

            # Remove ChatML prefixes if present
            for token in [
                "<<|im_start|>>system\n",
                "<<|im_start|>>user\n",
                "<<|im_start|>>assistant\n",
            ]:
                content = content.replace(token, "")
            content = content.replace("<<|im_end|>>", "").strip()

            # Add Llama3 headers
            if role == "system":
                converted_message["role"] = "system"
                converted_message["content"] = target_template.system_token + content
            elif role == "user":
                converted_message["role"] = "user"
                converted_message["content"] = target_template.user_token + content
            elif role == "assistant":
                converted_message["role"] = "assistant"
                converted_message["content"] = target_template.assistant_token + content

            converted_messages.append(converted_message)

        return converted_messages, 0.90

    def _wrap_in_chatml(
        self, messages: List[Dict], source: TemplateFormat, target: TemplateFormat
    ) -> Tuple[List[Dict], float]:
        """Wrap simple format messages in ChatML structure"""
        target_template = self.templates[target]
        converted_messages = []

        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")

            # Determine ChatML role
            if role == "system" or target_template.system_token in content[:50]:
                chatml_role = "system"
                # Extract content from Alpaca/Vicuna format
                if target_template.system_token in content[:50]:
                    content = content.replace(target_template.system_token, "")
            elif role == "user":
                chatml_role = "user"
                if target_template.user_token in content[:50]:
                    content = content.replace(target_template.user_token, "")
            else:
                chatml_role = "assistant"
                if target_template.assistant_token in content[:50]:
                    content = content.replace(target_template.assistant_token, "")

            converted_messages.append({"role": chatml_role, "content": content.strip()})

        return converted_messages, 0.85

    def _unwrap_from_chatml(
        self, messages: List[Dict], target: TemplateFormat
    ) -> Tuple[List[Dict], float]:
        """Convert ChatML messages to simpler formats"""
        target_template = self.templates[target]
        converted_messages = []

        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")

            if role == "system":
                converted_content = target_template.system_token + content
            elif role == "user":
                converted_content = target_template.user_token + content
            else:
                converted_content = target_template.assistant_token + content

            converted_messages.append({"role": role, "content": converted_content})

        return converted_messages, 0.85

    def _convert_to_llama3(
        self, messages: List[Dict], source: TemplateFormat, target: TemplateFormat
    ) -> Tuple[List[Dict], float]:
        """Generic conversion to Llama3 format"""
        return self._replace_headers(messages, source, target)

    def _convert_to_alpaca(
        self, messages: List[Dict], source: TemplateFormat, target: TemplateFormat
    ) -> Tuple[List[Dict], float]:
        """Generic conversion to Alpaca format"""
        return self._wrap_in_chatml(messages, source, target)

    def _generic_conversion(
        self, messages: List[Dict], source: TemplateFormat, target: TemplateFormat
    ) -> Tuple[List[Dict], float]:
        """Generic conversion with minimal confidence"""
        logger.warning(
            f"Using generic conversion from {source.value} to {target.value}"
        )

        # Try to preserve structure but change delimiters
        target_template = self.templates[target]
        converted_messages = []

        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")

            # Generic role mapping
            if role == "system":
                formatted_content = target_template.system_token + content
            elif role == "user":
                formatted_content = target_template.user_token + content
            else:
                formatted_content = target_template.assistant_token + content

            converted_messages.append({"role": role, "content": formatted_content})

        return converted_messages, 0.70  # Lower confidence for generic conversion

    def _record_conversion(
        self,
        source: TemplateFormat,
        target: TemplateFormat,
        method: str,
        confidence: float,
    ):
        """Record conversion for learning and optimization"""
        conversion_record = {
            "timestamp": time.time(),
            "source_format": source.value,
            "target_format": target.value,
            "conversion_method": method,
            "confidence": confidence,
        }

        self.template_history.append(conversion_record)

        # Keep history manageable
        if len(self.template_history) > 1000:
            self.template_history = self.template_history[-1000:]

    def optimize_template_selection(
        self, model_name: str, messages: List[Dict]
    ) -> TemplateFormat:
        """Optimize template selection based on historical performance"""

        detected_format = self.detect_model_template(model_name)

        # Check if we have performance data for this model
        cache_key = f"{model_name}_{detected_format.value}"

        if cache_key in self.performance_cache:
            performance_data = self.performance_cache[cache_key]

            # If performance is poor, try alternative formats
            if performance_data["success_rate"] < 0.8:
                logger.info(
                    f"Trying alternative templates for {model_name} due to poor performance"
                )

                # Try similar formats
                alternatives = self._get_similar_templates(detected_format)
                for alt_format in alternatives:
                    if self._test_template_compatibility(
                        model_name, alt_format, messages
                    ):
                        logger.info(
                            f"Switching to {alt_format.value} template for {model_name}"
                        )
                        return alt_format

        return detected_format

    def _get_similar_templates(
        self, template_format: TemplateFormat
    ) -> List[TemplateFormat]:
        """Get similar template formats for fallback"""
        similarity_map = {
            TemplateFormat.CHATML: [TemplateFormat.MICROSOFT, TemplateFormat.LLAMA3],
            TemplateFormat.MICROSOFT: [TemplateFormat.CHATML, TemplateFormat.LLAMA3],
            TemplateFormat.LLAMA3: [TemplateFormat.CHATML, TemplateFormat.MICROSOFT],
            TemplateFormat.ALPACA: [TemplateFormat.VICUNA],
            TemplateFormat.VICUNA: [TemplateFormat.ALPACA],
        }

        return similarity_map.get(template_format, [TemplateFormat.CHATML])

    def _test_template_compatibility(
        self, model_name: str, template_format: TemplateFormat, messages: List[Dict]
    ) -> bool:
        """Test if a template is compatible with a model"""

        # For now, return True (future: implement quick compatibility test)
        # Could involve small test prompt and response validation
        return True

    def update_performance_data(
        self,
        model_name: str,
        template_format: TemplateFormat,
        success: bool,
        response_quality: float = None,
    ):
        """Update performance data for template learning"""

        cache_key = f"{model_name}_{template_format.value}"

        if cache_key not in self.performance_cache:
            self.performance_cache[cache_key] = {
                "success_count": 0,
                "total_attempts": 0,
                "success_rate": 0.0,
                "quality_scores": [],
            }

        data = self.performance_cache[cache_key]
        data["total_attempts"] += 1

        if success:
            data["success_count"] += 1

            if response_quality is not None:
                data["quality_scores"].append(response_quality)
                # Keep only last 20 quality scores
                data["quality_scores"] = data["quality_scores"][-20:]

        data["success_rate"] = data["success_count"] / data["total_attempts"]

        logger.debug(
            f"Updated performance for {cache_key}: {data['success_rate']:.2f} success rate"
        )

    def get_template_statistics(self) -> Dict:
        """Get template usage and performance statistics"""
        stats = {
            "total_conversions": len(self.template_history),
            "performance_cache_size": len(self.performance_cache),
            "template_success_rates": {},
            "most_used_conversions": [],
        }

        # Calculate conversion frequencies
        conversion_counts = {}
        for record in self.template_history:
            conversion_key = f"{record['source_format']}-> {record['target_format']}"
            conversion_counts[conversion_key] = (
                conversion_counts.get(conversion_key, 0) + 1
            )

        # Get most used conversions
        stats["most_used_conversions"] = sorted(
            conversion_counts.items(), key=lambda x: x[1], reverse=True
        )[:10]

        # Get success rates by model-template combination
        for key, data in self.performance_cache.items():
            stats["template_success_rates"][key] = data["success_rate"]

        return stats


# Initialize global template manager
template_manager = AdaptiveTemplateManager()

if __name__ == "__main__":
    # Test template management system
    test_messages = [
        {"role": "system", "content": "You are a helpful AI assistant"},
        {"role": "user", "content": "Explain template conversion"},
        {"role": "assistant", "content": "Template conversion adapts formats"},
    ]

    # Test various conversions
    source_format = TemplateFormat.CHATML
    target_format = TemplateFormat.MICROSOFT

    converted, confidence = template_manager.convert_message_format(
        test_messages, source_format, target_format
    )

    print(f"Conversion {source_format.value} -> {target_format.value}")
    print(f"Confidence: {confidence:.2f}")
    print(f"Converted messages: {json.dumps(converted, indent=2)}")

    # Show statistics
    stats = template_manager.get_template_statistics()
    print(f"\nTemplate Statistics: {json.dumps(stats, indent=2)}")
