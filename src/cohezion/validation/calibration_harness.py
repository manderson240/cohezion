"""Unified Calibration Harness for Cohezion.

Provides:
- Secure local log parsing with PromptGuard threat detection and PII redaction.
- Atomic configuration profile writes.
- Sequential parameter sweeps gated by ResourceGuard to prevent OOM.
"""

from __future__ import annotations

import asyncio
import contextlib
import gc
import json
import logging
import os
import re
import tempfile
from collections.abc import Callable, Generator
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)

# Try importing PromptGuard
try:
    from cohezion.security.prompt_guard import PromptGuard, ThreatLevel
except ImportError:
    PromptGuard = None
    ThreatLevel = None

# Try importing SystemConfig
try:
    from cohezion.config.unified import get_config
except ImportError:
    get_config = None

# Try importing ResourceGuard
try:
    from cohezion.reliability.resource_guard import ResourceGuard
except ImportError:
    ResourceGuard = None


def get_project_root() -> Path:
    """Resolve project root directory securely using unified SystemConfig."""
    if get_config is not None:
        try:
            return Path(get_config().root_dir)
        except Exception:
            pass
    return Path(__file__).resolve().parent.parent.parent.parent


def redact_pii(text: str) -> str:
    """Redact potential credentials and IP addresses from logs."""
    text = re.sub(
        r"(?i)(key|password|secret|token)['\"]?\s*[:=]\s*['\"]?[a-zA-Z0-9_\-]{16,}['\"]?",
        r"\1=REDACTED",
        text,
    )
    text = re.sub(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "IP.REDACTED", text)
    return text


def load_local_logs(
    log_dir: str | Path | None = None,
    min_len: int = 50,
) -> Generator[dict[str, Any], None, None]:
    """Securely load and yield sanitized user prompts from local projects logs.

    Traverses log_dir recursively, filters using PromptGuard, and redacts PII.
    """
    root = get_project_root()
    log_dir = Path.home() / ".claude" / "projects" if log_dir is None else Path(log_dir)

    # Initialize PromptGuard
    guard = PromptGuard() if PromptGuard is not None else None

    # Search for jsonl files
    jsonl_files = []
    if log_dir.exists():
        jsonl_files = list(log_dir.glob("**/*.jsonl"))

    # Fallback to cache log if projects directory is empty
    if not jsonl_files:
        cache_log = root / "data" / "compound" / "cache" / "token_cache.jsonl"
        if cache_log.exists():
            jsonl_files = [cache_log]

    for path in jsonl_files:
        try:
            with open(path, encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        prompt = ""
                        response = ""

                        # 1. Check for Claude Project Log schema
                        if data.get("type") == "user":
                            msg = data.get("message", {})
                            if isinstance(msg, dict) and msg.get("role") == "user":
                                prompt = msg.get("content", "")
                        # 2. Check for token_cache.jsonl schema
                        elif "prompt" in data:
                            prompt = data.get("prompt", "")
                            response = data.get("response", "")

                        if not isinstance(prompt, str) or len(prompt.strip()) <= min_len:
                            continue

                        prompt_clean = prompt.strip()

                        # Security Gating: Scan using PromptGuard
                        if guard is not None and ThreatLevel is not None:
                            analysis = guard.analyze(prompt_clean)
                            if analysis.threat_level == ThreatLevel.MALICIOUS:
                                logger.debug(
                                    "Calibration: Skipping malicious prompt in %s:%d",
                                    path.name,
                                    line_num,
                                )
                                continue

                        # Hardening: Redact credentials/IPs
                        prompt_sanitized = redact_pii(prompt_clean)
                        response_sanitized = redact_pii(str(response))

                        yield {
                            "prompt": prompt_sanitized,
                            "response": response_sanitized,
                            "file": str(
                                path.relative_to(root) if path.is_relative_to(root) else path.name
                            ),
                            "line": line_num,
                        }
                    except (json.JSONDecodeError, TypeError, KeyError):
                        continue
        except Exception as e:
            logger.debug("Failed to read log file %s: %s", path, e)


def save_calibration_profile(component_name: str, parameters: dict[str, Any]) -> None:
    """Atomic write of calibrated parameters to config/calibration_profiles.json.

    Uses os.replace to prevent race conditions or half-written file reads.
    """
    root = get_project_root()
    config_dir = root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    profile_path = config_dir / "calibration_profiles.json"

    # 1. Load existing profile data
    profile_data = {}
    if profile_path.exists():
        try:
            with open(profile_path, encoding="utf-8") as f:
                profile_data = json.load(f)
        except Exception as e:
            logger.warning("Failed to parse existing profile, resetting: %s", e)

    # 2. Update with metadata envelope
    import datetime

    profile_data[component_name] = {
        "parameters": parameters,
        "metadata": {
            "calibrated_at": datetime.datetime.utcnow().isoformat() + "Z",
            "cohezion_version": "v1.0.0",
        },
    }

    # 3. Atomic Write
    fd, temp_path_str = tempfile.mkstemp(dir=str(config_dir), prefix="calibration_", suffix=".tmp")
    temp_path = Path(temp_path_str)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as temp_file:
            json.dump(profile_data, temp_file, indent=2)
        # Atomically rename/replace target file
        os.replace(temp_path, profile_path)
    except Exception as e:
        if temp_path.exists():
            with contextlib.suppress(OSError):
                os.unlink(temp_path)
        raise OSError(f"Atomic write to {profile_path} failed: {e}") from e


async def run_parameter_sweep(
    samples: list[dict[str, Any]],
    evaluate_fn: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]],
    param_grid: list[dict[str, Any]],
    min_ram_mb: int = 24576,
) -> list[dict[str, Any]]:
    """Runs a sequential parameter sweep guarded by ResourceGuard to prevent OOM.

    Args:
        samples: Sanitized log samples.
        evaluate_fn: Callback function to run evaluation on samples given a candidate config.
        param_grid: List of candidate parameter dictionaries to evaluate.
        min_ram_mb: Safety buffer threshold (in MB) for available RAM.

    Returns:
        List of result dictionaries containing evaluation metrics per candidate.
    """
    # Enforce strict sequential execution via a semaphore (1)
    semaphore = asyncio.Semaphore(1)
    results = []

    # Initialize ResourceGuard with safety buffer
    res_guard = (
        ResourceGuard(min_ram_available_mb=min_ram_mb) if ResourceGuard is not None else None
    )

    for i, candidate in enumerate(param_grid, 1):
        async with semaphore:
            # Check OOM Guardrails
            if res_guard is not None:
                healthy, reason = res_guard.is_healthy()
                if not healthy:
                    logger.warning(
                        "OOM Guardrail check failed: %s. Initiating cooling sleep...", reason
                    )
                    # Let the system stabilize for 10 seconds
                    await asyncio.sleep(10)
                    healthy, reason = res_guard.is_healthy()
                    if not healthy:
                        raise MemoryError(f"ResourceGuard aborted sweep to prevent OOM: {reason}")

            logger.info("Evaluating candidate %d/%d: %s", i, len(param_grid), candidate)

            # Execute evaluation callback
            try:
                import inspect

                if inspect.iscoroutinefunction(evaluate_fn):
                    metrics = await evaluate_fn(samples, candidate)
                else:
                    metrics = evaluate_fn(samples, candidate)
                results.append({"candidate": candidate, "metrics": metrics})
            except Exception as e:
                logger.error("Failed to evaluate candidate %s: %s", candidate, e, exc_info=True)
                results.append({"candidate": candidate, "metrics": {"error": str(e)}})

            # Proactive memory cleanup
            gc.collect()

    # Sort results or print them (caller can render the markdown table)
    return results
