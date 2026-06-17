---
name: cohezion-shadow-portfolio-loop
description: |
  Full architecture for running a Cohezion shadow portfolio research loop with
  evidence-based trade gating. Use when:
  (1) User asks to start, resume, or extend portfolio monitoring
  (2) RSI signals need to be tracked with historical evidence
  (3) BetaBeliefLedger needs to be populated or consulted
  (4) New thesis docs need to be created for watchlist signals
  (5) portfolio_proposal.html dashboard needs updating
  Key insight: Python cannot call Robinhood directly (OAuth lives in MCP layer).
  Data hub pattern: Claude Code writes cache; Python loop reads it.
author: Claude Code
version: 1.0.0
tags: [portfolio, shadow-trading, robinhood, rsi, yfinance, betabelief]
---

# Cohezion Shadow Portfolio Loop

## Architecture

```
Claude Code session (MCP-enabled)
  → get_equity_positions / get_equity_quotes  (Robinhood MCP)
  → get_price_history / get_ticker_info       (yfinance MCP)
  → write ~/.cohezion/portfolio_cache.json    (via scripts/refresh_portfolio_cache.py)
  → create/update docs/portfolio/theses/<date>-<symbol>-<signal>.md

Shadow Loop (scripts/run_portfolio_loop.py)
  → read portfolio_cache.json (snapshot_fn)
  → fetch yfinance RSI (rsi_fn)
  → ShadowTradingLoop.fast_npu_check() → hard gates + RSI signal detection
  → log_rsi_hypothesis() → BetaBeliefLedger
  → update_html_dashboard(portfolio_proposal.html)
  → log_cycle_to_vault()
```

**HARD CONSTRAINT**: shadow_mode=True always. No purchases until BetaBeliefLedger
shows ≥5 resolved observations at >55% hit rate per thesis tag.

## Key Files

| File | Purpose |
|------|---------|
| `scripts/run_portfolio_loop.py` | Main loop driver |
| `scripts/refresh_portfolio_cache.py` | Cache writer (run from MCP-enabled session) |
| `scripts/portfolio_backtest.py` | 2-year RSI backtest; `--update-theses` patches thesis docs |
| `src/cohezion/integrations/robinhood_analysis.py` | ShadowTradingLoop, BetaBeliefLedger, all analysis classes |
| `docs/portfolio/theses/` | Per-thesis evidence documents |
| `~/.cohezion/portfolio_cache.json` | Live portfolio snapshot cache |
| `portfolio_proposal.html` | HTML dashboard (GOAL_LOOP_STATUS_START/END markers) |

## Critical Field Names (avoid relearning)

```python
# Position dataclass — NOT shares/current_price
Position(
    symbol="NVDA",
    quantity=0.09765,      # NOT .shares
    market_value=20.40,    # NOT .current_price * .shares
    cost_basis=15.0,
)

# PortfolioSnapshot — NOT total_equity
PortfolioSnapshot(
    positions=[...],
    total_value=25.16,     # NOT total_equity
    cash=0.76,
)
```

## RSI Signal Thresholds (matches ShadowTradingLoop)

| RSI | Zone | Signal type | Predicted |
|-----|------|-------------|-----------|
| > 65 | Overbought | `overbought` | DOWN |
| 60–65 | Near-overbought | `overbought_exit` | DOWN |
| 40–50 | Recovering | `oversold_exit` | UP |
| < 40 | Oversold | `oversold` | UP |

**Entry-on-first-crossing only** — only log signal when RSI first enters zone,
not on each subsequent day. Prevents inflated signal counts in backtest.

## BetaBeliefLedger API

```python
from cohezion.integrations.robinhood_analysis import BetaBeliefLedger

ledger = BetaBeliefLedger()
tag = "rsi_overbought_bnd"   # format: rsi_{signal_type}_{symbol.lower()}

# Update after thesis resolves
ledger.update(tag, correct=True)   # or correct=False

# Gate check (must be True before live trading)
ledger.has_proven_edge(tag)        # α/(α+β) > 0.55 AND count ≥ 5

# Inspect
ledger.observation_count(tag)      # number of resolved observations
ledger.format_ledger()             # human-readable string
```

Initial priors: α=1.0, β=1.0 (uninformative). Each correct observation adds to α,
each incorrect adds to β. Hit rate = α/(α+β).

## Hard Gate Goal IDs (code-enforced, never LLM)

```python
HARD_GATE_GOAL_IDS = frozenset({
    "max_concentration",  # ≤35% of portfolio in any single position
    "cash_floor",         # ≥10% cash at all times
    "max_positions",      # ≤4 open positions
    "drawdown_gate",      # portfolio drawdown < 20%
})
```

All 4 must be CLEAR before any signal triggers a recommendation.

## Thesis Doc Structure

File: `docs/portfolio/theses/<YYYY-MM-DD>-<SYMBOL>-<signal-type>.md`

```yaml
---
thesis_tag: rsi_overbought_bnd
symbol: BND
signal_type: overbought
rsi_at_detection: 69.3
threshold: 65.0
predicted_direction: DOWN
horizon_days: 7
logged_at: 2026-06-16
status: OPEN
evidence_quality: PRELIMINARY
---
```

Resolution criteria (standard):
- DOWN thesis CORRECT: price < entry - 0% (any decline counts)
- DOWN thesis INCORRECT: price > entry + 0.5%
- UP thesis CORRECT: price > entry
- UP thesis INCORRECT: price < entry - 2%

## HTML Dashboard Marker Pattern

The `portfolio_proposal.html` uses marker-based idempotent replacement:

```html
<!-- GOAL_LOOP_STATUS_START -->
  ... generated content ...
<!-- GOAL_LOOP_STATUS_END -->
```

`run_portfolio_loop.py::update_html_dashboard()` reads the file, finds the markers,
replaces the entire block, writes back. Safe to run repeatedly — no stale block
accumulation.

## Running the System

```bash
# 1. Refresh cache with live Robinhood data (from Claude Code MCP session)
uv run python scripts/refresh_portfolio_cache.py

# 2. Run RSI backtest and patch thesis docs with historical hit rates
uv run python scripts/portfolio_backtest.py --update-theses

# 3. Run one monitoring cycle
uv run python scripts/run_portfolio_loop.py --once

# 4. Run continuously (5-min fast tier, optional 30-min OmniTier)
uv run python scripts/run_portfolio_loop.py [--omni]

# 5. Get JSON output for scripting
uv run python scripts/portfolio_backtest.py --json
```

## Bond ETF RSI Interpretation (non-obvious)

BND RSI overbought signals are often driven by YIELD MATH, not speculation:
- BND duration ~6.5 years
- Every 10 bps yield decline ≈ +$0.48 BND price appreciation
- RSI >65 on BND usually means 10Y yields have fallen fast (e.g., 20-30 bps)
- Check ^TNX trend FIRST before interpreting BND RSI as a reversal signal
- If ^TNX MACD is still positive (yields still falling), BND RSI may extend further
- The reversal thesis requires a yield BOUNCE, not just RSI reaching 65+

## MCP Tool Limits

| Tool | Limit | Workaround |
|------|-------|------------|
| Alpha Vantage free | 25 req/day | Space calls; use yfinance for OHLCV |
| Alpha Vantage MACD | Premium only | Compute from yfinance price history |
| Alpha Vantage NEWS_SENTIMENT | Free tier | Use sparingly (high value/call) |
| yfinance ticker_info fast=True | ETF returns mostly null | Use get_price_history instead |

## Dependencies

`yfinance>=0.2.50` must be in `pyproject.toml` (was missing initially — caused
`ModuleNotFoundError: No module named 'yfinance'` when running portfolio scripts).

```bash
uv add yfinance
```

## Thesis Resolution Workflow (due 7 days after signal)

```python
# At horizon (7 trading days after signal):
from cohezion.integrations.robinhood_analysis import BetaBeliefLedger
ledger = BetaBeliefLedger()

# BND overbought: entry $73.38, resolve by 2026-06-23
bnd_correct = current_bnd_price < 73.38
ledger.update("rsi_overbought_bnd", correct=bnd_correct)

# NVDA oversold_exit: entry $208.72, resolve by 2026-06-23
nvda_correct = current_nvda_price > 208.72
ledger.update("rsi_oversold_exit_nvda", correct=nvda_correct)

print(ledger.format_ledger())
print("Edge unlocked:", ledger.has_proven_edge("rsi_overbought_bnd"))
```
