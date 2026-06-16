"""Tests for cohezion.inference.oom_guard — N3 OOM regression protection.

Uses only stdlib mocks — no live Lemonade connection required.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_model(name: str, size_gb: float, ctx_size: int | None) -> dict:
    """Build a catalog model entry as returned by /api/v1/models."""
    return {
        "model_name": name,
        "size": size_gb,
        "recipe_options": {"ctx_size": ctx_size} if ctx_size is not None else {},
    }


# ── check_ram ─────────────────────────────────────────────────────────────────


def test_check_ram_safe():
    from cohezion.inference.oom_guard import check_ram

    with patch("psutil.virtual_memory") as mock_vm:
        mock_vm.return_value = MagicMock(available=50_000_000_000)  # 50 GB
        safe, free_gb = check_ram(min_free_gb=20.0)
    assert safe is True
    assert abs(free_gb - 50.0) < 0.1


def test_check_ram_unsafe():
    from cohezion.inference.oom_guard import check_ram

    with patch("psutil.virtual_memory") as mock_vm:
        mock_vm.return_value = MagicMock(available=10_000_000_000)  # 10 GB
        safe, free_gb = check_ram(min_free_gb=20.0)
    assert safe is False
    assert free_gb < 20.0


def test_check_ram_no_psutil():

    with patch.dict("sys.modules", {"psutil": None}):
        import importlib
        import cohezion.inference.oom_guard as g

        importlib.reload(g)
        safe, free_gb = g.check_ram(min_free_gb=20.0)
    assert safe is True
    assert free_gb == float("inf")


# ── _is_heavy ─────────────────────────────────────────────────────────────────


def test_is_heavy_above_threshold():
    from cohezion.inference.oom_guard import _is_heavy

    assert _is_heavy({"size": 23.0}) is True


def test_is_heavy_below_threshold():
    from cohezion.inference.oom_guard import _is_heavy

    assert _is_heavy({"size": 1.3}) is False


def test_is_heavy_missing_size():
    from cohezion.inference.oom_guard import _is_heavy

    # Unknown size → treat as heavy (err on side of caution)
    assert _is_heavy({}) is True


def test_is_heavy_exactly_at_threshold():
    from cohezion.inference.oom_guard import _is_heavy, HEAVY_MODEL_GB_THRESHOLD

    assert _is_heavy({"size": HEAVY_MODEL_GB_THRESHOLD}) is True


# ── _ctx_is_unsafe ────────────────────────────────────────────────────────────


def test_ctx_unsafe_zero():
    from cohezion.inference.oom_guard import _ctx_is_unsafe

    assert _ctx_is_unsafe({"ctx_size": 0}) is True


def test_ctx_safe_bounded():
    from cohezion.inference.oom_guard import _ctx_is_unsafe

    assert _ctx_is_unsafe({"ctx_size": 16384}) is False


def test_ctx_safe_na():
    from cohezion.inference.oom_guard import _ctx_is_unsafe

    # None means N/A (FLM/GGUF models) — not a crash vector
    assert _ctx_is_unsafe({"ctx_size": None}) is False


def test_ctx_safe_missing():
    from cohezion.inference.oom_guard import _ctx_is_unsafe

    assert _ctx_is_unsafe({}) is False


# ── scan_and_harden ───────────────────────────────────────────────────────────


def test_scan_router_offline():
    from cohezion.inference.oom_guard import scan_and_harden

    with patch("cohezion.inference.oom_guard._get_catalog", return_value=[]):
        report = scan_and_harden()
    assert report["router_offline"] is True
    assert report["hardened"] == []


def test_scan_all_already_safe():
    from cohezion.inference.oom_guard import scan_and_harden

    catalog = [
        _make_model("Qwen3.6-35B-A3B-MTP-GGUF", 23.8, 16384),
        _make_model("Gemma-4-31B-it-GGUF", 19.5, 16384),
    ]
    with patch("cohezion.inference.oom_guard._get_catalog", return_value=catalog):
        report = scan_and_harden()
    assert report["router_offline"] is False
    assert report["hardened"] == []
    assert len(report["already_safe"]) == 2


def test_scan_hardens_unsafe_heavy_model():
    from cohezion.inference.oom_guard import scan_and_harden

    catalog = [_make_model("Qwen3.6-35B-A3B-NoThinking", 21.7, 0)]
    with (
        patch("cohezion.inference.oom_guard._get_catalog", return_value=catalog),
        patch("cohezion.inference.oom_guard._harden_model", return_value=True) as mock_harden,
    ):
        report = scan_and_harden()
    mock_harden.assert_called_once_with(
        "http://localhost:13305", "Qwen3.6-35B-A3B-NoThinking", ctx_size=16384
    )
    assert report["hardened"] == ["Qwen3.6-35B-A3B-NoThinking"]
    assert report["failed"] == []


def test_scan_skips_small_models():
    from cohezion.inference.oom_guard import scan_and_harden

    catalog = [_make_model("llama3.2-1b-FLM", 1.3, 0)]  # small + ctx=0 → skip
    with (
        patch("cohezion.inference.oom_guard._get_catalog", return_value=catalog),
        patch("cohezion.inference.oom_guard._harden_model") as mock_harden,
    ):
        report = scan_and_harden()
    mock_harden.assert_not_called()
    assert report["skipped"] == ["llama3.2-1b-FLM"]


def test_scan_records_failed_harden():
    from cohezion.inference.oom_guard import scan_and_harden

    catalog = [_make_model("Gemma-4-26B-A4B-it-GGUF", 18.1, 0)]
    with (
        patch("cohezion.inference.oom_guard._get_catalog", return_value=catalog),
        patch("cohezion.inference.oom_guard._harden_model", return_value=False),
    ):
        report = scan_and_harden()
    assert report["failed"] == ["Gemma-4-26B-A4B-it-GGUF"]
    assert report["hardened"] == []


# ── verify_all_bounded ────────────────────────────────────────────────────────


def test_verify_all_bounded_clean():
    from cohezion.inference.oom_guard import verify_all_bounded

    catalog = [
        _make_model("Qwen3.6-35B-A3B-MTP-GGUF", 23.8, 16384),
        _make_model("llama3.2-1b-FLM", 1.3, 16384),
    ]
    with patch("cohezion.inference.oom_guard._get_catalog", return_value=catalog):
        safe, violations = verify_all_bounded()
    assert safe is True
    assert violations == []


def test_verify_all_bounded_finds_violation():
    from cohezion.inference.oom_guard import verify_all_bounded

    catalog = [
        _make_model("Qwen3.6-35B-A3B-ThinkingCoder", 21.7, 0),
        _make_model("Gemma-4-E4B-it-GGUF", 5.97, 16384),
    ]
    with patch("cohezion.inference.oom_guard._get_catalog", return_value=catalog):
        safe, violations = verify_all_bounded()
    assert safe is False
    assert "Qwen3.6-35B-A3B-ThinkingCoder" in violations


def test_verify_router_offline():
    from cohezion.inference.oom_guard import verify_all_bounded

    with patch("cohezion.inference.oom_guard._get_catalog", return_value=[]):
        safe, violations = verify_all_bounded()
    assert safe is True  # offline → no violations to report
    assert violations == []
