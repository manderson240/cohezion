"""Tests for OuroborosFailureAnalyzer pattern recognition (WS5, 2026-06-03)."""

from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from cohezion.ouroboros.failure_analyzer import OuroborosFailureAnalyzer


def _analyze(log: str) -> tuple[str, str]:
    """Helper: return (root_cause, suggested_mutation)."""
    fa = OuroborosFailureAnalyzer()
    r = fa.analyze(log, target="test")
    return r.root_cause, r.suggested_mutation


def test_short_log_returns_too_short():
    rc, _ = _analyze("traceback")
    assert rc == "Log too short to analyze"


def test_oom_pattern():
    rc, mut = _analyze(
        "RuntimeError: CUDA out of memory. Tried to allocate 2 GiB on device 0. "
        "Consider reducing the batch size, using gradient accumulation, or moving "
        "the model to a smaller precision. The training run aborted at step 1234."
    )
    assert "OOM" in rc or "VRAM" in rc
    assert "batch_size" in mut


def test_timeout_pattern():
    rc, mut = _analyze(
        "Job exceeded the timeout limit of 300s and was killed by the runner. "
        "The training script was running fine for the first 250s but the final "
        "evaluation phase never completed because the underlying service was slow."
    )
    assert "timeout" in rc.lower()
    assert "timeout" in mut.lower()


def test_bwrap_pattern_can_create_file():
    log = (
        "bwrap: Can't create file at /usr/lib/mesa-diverted/x86_64-linux-gnu: "
        "No such file or directory\n"
        "The sandbox tries to bind each LD_LIBRARY_PATH entry; the first missing "
        "entry aborts bwrap before any user command runs. This blocks all Bash "
        "tool invocations across the affected session."
    )
    rc, mut = _analyze(log)
    assert "bwrap" in rc.lower()
    assert "safe-env.sh" in mut


def test_bwrap_pattern_can_find_source_path():
    log = (
        "bwrap: Can't find source path /opt/rocm-removed: No such file or directory\n"
        "bwrap tried to bind a toolchain path that was once installed but is now "
        "deleted, causing a total Bash sandbox outage for the agent session."
    )
    rc, mut = _analyze(log)
    assert "bwrap" in rc.lower()
    assert "safe-env.sh" in mut


def test_arxiv_module_missing():
    rc, mut = _analyze(
        "ModuleNotFoundError: No module named 'arxiv' — `pip install arxiv` to fix. "
        "The arxiv Python client is not in the project's venv. Either install it via "
        "uv pip install arxiv OR fall back to the raw export.arxiv.org/api/query "
        "HTTP endpoint which requires no dependency and is what cohezion uses."
    )
    assert "arxiv" in rc.lower() or "arxiv" in mut.lower()


def test_kaggle_mamba_missing():
    rc, mut = _analyze(
        "ModuleNotFoundError: No module named 'mamba_ssm' (Kaggle Blackwell env "
        "notebook ran out of mamba_ssm pre-built wheel cache; need to pin a torch "
        "version that has matching pre-built CUDA 12.1 wheels for Blackwell G4 GPUs)"
    )
    assert "kaggle" in rc.lower() or "mamba" in rc.lower() or "torch" in mut.lower()


def test_generic_module_missing():
    rc, mut = _analyze(
        "ModuleNotFoundError: No module named 'nonexistent_pkg' at line 42. The "
        "agent tried to import this library to do X but the venv does not have it. "
        "Add it to pyproject.toml or to the Kaggle dataset wheel bundle."
    )
    assert "Missing dependency" in rc
    assert "nonexistent_pkg" in mut


def test_undefined_symbol_pattern():
    rc, mut = _analyze(
        "ImportError: /usr/lib/libfoo.so: undefined symbol: some_thing_new. The "
        "shared library was compiled against a newer C++ ABI than the runtime "
        "supports. Switch to a stable backend or pin the matching library versions."
    )
    assert "mismatch" in rc.lower() or "version" in rc.lower()


def test_cloud_5xx_pattern():
    rc, mut = _analyze(
        "openai.APIConnectionError: Cloud provider returned 524 (a timeout at the "
        "edge proxy). This is a transient 5xx. The agent should retry with "
        "exponential backoff OR fall back to local AMD silicon via lemonade."
    )
    assert "5xx" in rc or "transient" in rc.lower()
    assert "lemonade" in mut.lower() or "local" in mut.lower()


def test_mcp_tool_failure_pattern():
    log = (
        "Tool result missing due to internal error from mcp__cohezion__vault_query. "
        "The MCP server crashed mid-call. Verify VAULT_PATH env var is set and "
        "the cloud-vault-mcp subprocess is still alive in the gateway."
    )
    rc, mut = _analyze(log)
    assert "MCP" in rc or "mcp" in rc.lower()


def test_arxiv_rate_limit_429():
    log = (
        "arxiv query failed: HTTP 429 Too Many Requests. arxiv asks for ~3 seconds "
        "between requests. The request was retried twice before giving up. This "
        "is a rate-limit response from the arxiv public API, not a code bug."
    )
    rc, mut = _analyze(log)
    assert "rate" in rc.lower() or "429" in rc
    assert "back" in mut.lower() or "jitter" in mut.lower()


def test_hf_auth_required():
    log = (
        "huggingface.co API returned HTTP 401 Unauthorized. The request to "
        "https://huggingface.co/api/models did not include a valid HF_TOKEN. "
        "Set the HF_TOKEN env var to a free token from "
        "huggingface.co/settings/tokens before retrying."
    )
    rc, mut = _analyze(log)
    assert "auth" in rc.lower() or "401" in rc or "403" in rc
    assert "HF_TOKEN" in mut or "token" in mut.lower()


def test_semantic_scholar_rate_limit_429():
    log = (
        "Semantic Scholar paper lookup returned HTTP 429. The API allows "
        "approximately 100 requests per 5 minutes without an API key. "
        "Back off before retrying or use a paid API key for higher quotas."
    )
    rc, mut = _analyze(log)
    assert "rate" in rc.lower() or "429" in rc or "scholar" in rc.lower()
    assert "back" in mut.lower() or "100" in mut or "stagger" in mut.lower()


def test_unknown_long_log_falls_through():
    rc, mut = _analyze(
        "An obscure error happened somewhere with 200+ characters of "
        "unstructured content that does not match any known pattern and "
        "should fall through to the generic 'Unknown failure' bucket "
        "without matching any of the specific patterns above."
    )
    assert rc == "Unknown failure"
