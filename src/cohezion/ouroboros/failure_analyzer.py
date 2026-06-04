"""Ouroboros Failure Analyzer — Recursive retrospective for agentic failures.

Pattern set (extend by adding `elif` branches; keep the keyword combinations
tight to avoid false positives):

| Pattern keywords                                          | Root cause                                | Mutation                                  |
|-----------------------------------------------------------|-------------------------------------------|-------------------------------------------|
| OutOfMemoryError, CUDA out of memory                      | GPU VRAM exhaustion (OOM)                 | Reduce batch_size or increase VRAM reset  |
| Timeout, exceeded the timeout                              | Execution timeout                         | Increase timeout budget                   |
| ModuleNotFoundError                                       | Missing dependency                        | Inject wheel into Kaggle dataset          |
| undefined symbol                                          | Binary/library version mismatch           | Switch backend or match versions          |
| bwrap + Can't create file at + PATH-like env              | bwrap sandbox bind failure                | source ~/.config/cohezion/safe-env.sh     |
| bwrap + Can't find source path + LD_LIBRARY_PATH         | (same as above; more specific)            | (same as above)                            |
| ModuleNotFoundError + arxiv                               | arxiv Python lib not installed            | Use raw export.arxiv.org/api/query         |
| ModuleNotFoundError + mamba_ssm / cutlass                 | Kaggle Blackwell missing ML kernel       | Pin torch==2.4.0+cu121 in notebook        |
| APIConnectionError + OpenAI + 524 / 503                   | Cloud LLM provider transient failure      | Switch to local AMD silicon (lemonade)     |
| Tool result missing due to internal error                 | MCP tool transport failure                | Restart MCP server / check vault path     |

Last extended: 2026-06-03 (session harness-bash-unification). Trigger
to add a new branch: the failure pattern has been seen 2+ times
in different sessions without a matching pattern already.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any


logger = logging.getLogger(__name__)


@dataclass
class FailureAnalysis:
    root_cause: str
    suggested_mutation: str
    learning_id: str
    is_recoverable: bool


class OuroborosFailureAnalyzer:
    """Analyzes execution logs to extract learnings and suggest self-healing mutations."""

    def __init__(self, model_provider: Any = None):
        self.model_provider = model_provider

    def analyze(self, logs: str, target: str) -> FailureAnalysis:
        """Analyze logs and return actionable insights."""
        # Heuristic-based analysis fallback if no model provider
        root_cause = "Unknown failure"
        suggested_mutation = "Investigate log context"
        is_recoverable = True

        # Guard: trivially short logs are usually wrappers / banners, not failures.
        if len(logs) < 100:
            return FailureAnalysis(
                root_cause="Log too short to analyze",
                suggested_mutation="Capture more context (full stderr)",
                learning_id=f"ouro_{target}_{int(time.time())}",
                is_recoverable=True,
            )

        if "OutOfMemoryError" in logs or "CUDA out of memory" in logs:
            root_cause = "GPU VRAM exhaustion (OOM)"
            suggested_mutation = "Reduce batch_size or increase VRAM reset frequency"
        elif "Timeout" in logs or "exceeded the timeout" in logs:
            root_cause = "Execution timeout"
            suggested_mutation = "Increase timeout budget or simplify model routing"
        elif "bwrap" in logs and "Can't create file at" in logs:
            root_cause = "bwrap sandbox bind failure (stale PATH-like env var)"
            suggested_mutation = (
                "source ~/.config/cohezion/safe-env.sh before launching claude "
                "(strips missing LD_LIBRARY_PATH / ROCM_PATH entries)"
            )
        elif "bwrap" in logs and "Can't find source path" in logs:
            root_cause = "bwrap sandbox bind failure (stale PATH-like env var)"
            suggested_mutation = (
                "source ~/.config/cohezion/safe-env.sh before launching claude"
            )
        elif "ModuleNotFoundError" in logs and "arxiv" in logs.lower():
            root_cause = "arxiv Python lib not installed in venv"
            suggested_mutation = (
                "Use raw export.arxiv.org/api/query (no dep) OR `uv pip install arxiv`"
            )
        elif "ModuleNotFoundError" in logs and ("mamba_ssm" in logs or "cutlass" in logs):
            root_cause = "Kaggle Blackwell notebook missing ML kernel module"
            suggested_mutation = (
                "Pin torch==2.4.0+cu121 in notebook; add mamba_ssm via pre-built wheel"
            )
        elif "ModuleNotFoundError" in logs:
            module = re.search(r"No module named '([^']+)'", logs)
            module_name = module.group(1) if module else "unknown"
            root_cause = f"Missing dependency: {module_name}"
            suggested_mutation = f"Inject {module_name} wheel into Kaggle dataset"
        elif "undefined symbol" in logs:
            root_cause = "Binary/Library version mismatch"
            suggested_mutation = "Switch to stable Transformers backend or match PyTorch versions"
        elif "APIConnectionError" in logs and ("524" in logs or "503" in logs):
            root_cause = "Cloud LLM provider transient failure (5xx)"
            suggested_mutation = (
                "Switch to local AMD silicon (lemonade) via cohezion.inference.fleet.extend_claude()"
            )
        elif "Tool result missing due to internal error" in logs:
            root_cause = "MCP tool transport failure (vault path / mcp server crash)"
            suggested_mutation = (
                "Restart mcp server; verify VAULT_PATH / cloud-vault-mcp env vars"
            )

        logger.info(f"[Ouroboros] Failure analyzed: {root_cause}")

        return FailureAnalysis(
            root_cause=root_cause,
            suggested_mutation=suggested_mutation,
            learning_id=f"ouro_{target}_{int(time.time())}",
            is_recoverable=is_recoverable,
        )


import time  # noqa: E402
