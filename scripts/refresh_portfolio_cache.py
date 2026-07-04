"""
Portfolio Cache Refresher
==========================
Writes current Robinhood portfolio data to ~/.cohezion/portfolio_cache.json.

Run this from Claude Code (which has MCP auth) to feed the portfolio loop driver:
  uv run python scripts/refresh_portfolio_cache.py --from-json '<json_string>'

Or in-session: paste the Robinhood MCP output directly as stdin:
  echo '<json>' | uv run python scripts/refresh_portfolio_cache.py --stdin

The cache file is read by scripts/run_portfolio_loop.py for the shadow loop.

Format of portfolio_cache.json:
{
  "fetched_at": "2026-06-16T20:00:00+00:00",
  "account_id": "****0567",
  "total_equity": 25.14,
  "cash": 0.00,
  "positions": [
    {"symbol": "NVDA", "shares": 0.09765, "current_price": 208.72, "cost_basis": 15.00}
  ],
  "agentic_account": {
    "account_id": "****0477",
    "cash": 75.00,
    "positions": []
  }
}
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

CACHE_DIR = Path.home() / ".cohezion"
CACHE_FILE = CACHE_DIR / "portfolio_cache.json"

# ── Current snapshot (June 16, 2026 ~15:50 ET) ────────────────────────────────
# Sourced from Robinhood MCP: get_equity_positions + get_equity_quotes + get_accounts

CURRENT_SNAPSHOT: dict = {
    "fetched_at": "2026-06-16T21:38:00+00:00",
    "source": "robinhood_mcp + yfinance",
    "main_account": {
        "account_id": "****0567",
        "account_type": "margin",
        "agentic_allowed": False,
        "total_equity": 25.16,
        "cash": 0.76,
        "positions": [
            {
                "symbol": "NVDA",
                "shares": 0.09765,
                "current_price": 209.065,
                "cost_basis": 15.0,
                "market_value": 20.40,
            }
        ],
        # NOTE: VTI/VWO/VEA/BND positions returned $0 market value from MCP —
        # likely fractional shares below the API threshold or recently closed.
    },
    "agentic_account": {
        "account_id": "****0477",
        "account_type": "cash",
        "agentic_allowed": True,
        "total_equity": 0.0,
        "cash": 75.0,
        "positions": [],
    },
    "combined_total": 125.16,
    "watchlist_quotes": {
        "BND": {"last_price": 73.455, "prev_close": 73.300, "change_pct": 0.21},
        "NVDA": {"last_price": 209.065, "prev_close": 212.450, "change_pct": -1.59},
        "VTI": {"last_price": 371.135, "prev_close": 372.530, "change_pct": -0.37},
        "VWO": {"last_price": 60.255, "prev_close": 60.840, "change_pct": -0.96},
        "VEA": {"last_price": 72.475, "prev_close": 72.390, "change_pct": 0.12},
    },
    "macro_context": {
        "treasury_10y_yield_pct": 4.426,
        "treasury_10y_trend": "falling",
        "treasury_10y_3mo_peak": 4.670,
        "note": "^TNX from yfinance. Falling yields = BND price pressure UP (headwind for BND overbought thesis).",
        "market_regime_today": "mild_risk_off",
    },
    "rsi_14": {
        # Computed 2026-06-16 via yfinance Wilder's RSI, 1-month daily
        "NVDA": 43.8,  # oversold_exit — recovering
        "VTI": 61.1,  # neutral
        "VWO": 60.2,  # neutral
        "VEA": 63.2,  # near-overbought
        "BND": 69.3,  # OVERBOUGHT — signal active
    },
    "active_signals": [
        {
            "symbol": "BND",
            "signal_type": "overbought",
            "rsi": 69.3,
            "thesis_tag": "rsi_overbought_bnd",
            "entry_price": 73.38,
            "action": "trim_candidate",
            "horizon_days": 7,
            "resolve_by": "2026-06-23",
            "logged_at": "2026-06-16T20:50:00+00:00",
        },
        {
            "symbol": "NVDA",
            "signal_type": "oversold_exit",
            "rsi": 43.8,
            "thesis_tag": "rsi_oversold_exit_nvda",
            "entry_price": 208.72,
            "action": "hold_recovering",
            "horizon_days": 7,
            "resolve_by": "2026-06-23",
            "logged_at": "2026-06-16T20:50:00+00:00",
            "notes": "Grant-locked at Schwab — cannot sell regardless of signal",
        },
    ],
}


def write_cache(data: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    data["cache_written_at"] = datetime.now(timezone.utc).isoformat()
    with CACHE_FILE.open("w") as f:
        json.dump(data, f, indent=2)
    print(f"Portfolio cache written to {CACHE_FILE}")
    print(f"  Main account equity: ${data['main_account']['total_equity']:.2f}")
    print(f"  Agentic account cash: ${data['agentic_account']['cash']:.2f}")
    print(f"  Active signals: {len(data.get('active_signals', []))}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-json", help="Inline JSON string")
    parser.add_argument("--stdin", action="store_true", help="Read JSON from stdin")
    parser.add_argument(
        "--use-embedded",
        action="store_true",
        default=True,
        help="Write the embedded June 16 snapshot (default)",
    )
    args = parser.parse_args()

    if args.from_json:
        data = json.loads(args.from_json)
        data["fetched_at"] = datetime.now(timezone.utc).isoformat()
        write_cache(data)
    elif args.stdin:
        data = json.load(sys.stdin)
        data["fetched_at"] = datetime.now(timezone.utc).isoformat()
        write_cache(data)
    else:
        write_cache(CURRENT_SNAPSHOT)


if __name__ == "__main__":
    main()
