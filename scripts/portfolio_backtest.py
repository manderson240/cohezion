"""
Portfolio RSI Signal Backtest
==============================
Fetches 2-year daily history via yfinance for all watchlist symbols,
computes RSI-14 at each point (Wilder's smoothing), finds all historical
signal occurrences, and reports predictive hit rates for each thesis type.

Usage:
  uv run python scripts/portfolio_backtest.py
  uv run python scripts/portfolio_backtest.py --symbol BND --horizon 7
  uv run python scripts/portfolio_backtest.py --update-theses   # patch thesis docs

Output:
  Prints backtest summary table per symbol × signal type.
  Optionally pre-populates BetaBeliefLedger with historical observations.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Literal

import yfinance as yf  # type: ignore[import-untyped]

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

# ── RSI (Wilder's smoothing) ───────────────────────────────────────────────────


def wilder_rsi_series(closes: list[float], period: int = 14) -> list[float | None]:
    """Return RSI-14 for every close price; first `period` entries are None."""
    result: list[float | None] = [None] * period
    if len(closes) <= period:
        return result + [None] * (len(closes) - period)

    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(d, 0.0) for d in deltas]
    losses = [max(-d, 0.0) for d in deltas]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    result.append(100.0 - 100.0 / (1 + avg_gain / avg_loss) if avg_loss else 100.0)

    for g, lo in zip(gains[period:], losses[period:]):
        avg_gain = (avg_gain * (period - 1) + g) / period
        avg_loss = (avg_loss * (period - 1) + lo) / period
        result.append(100.0 - 100.0 / (1 + avg_gain / avg_loss) if avg_loss else 100.0)

    return result


# ── Signal classification ──────────────────────────────────────────────────────

SignalType = Literal["overbought", "oversold", "oversold_exit", "overbought_exit"]


def classify_signal(rsi: float) -> SignalType | None:
    """Classify RSI into signal type (matches ShadowTradingLoop thresholds)."""
    if rsi > 65:
        return "overbought"
    if rsi < 40:
        return "oversold"
    if 40 <= rsi <= 50:
        return "oversold_exit"
    if 60 < rsi <= 65:
        return "overbought_exit"
    return None


PREDICTED_DIRECTION: dict[SignalType, str] = {
    "overbought": "DOWN",
    "oversold": "UP",
    "oversold_exit": "UP",
    "overbought_exit": "DOWN",
}


# ── Backtest engine ────────────────────────────────────────────────────────────


@dataclass
class SignalObs:
    signal_date: date
    signal_rsi: float
    signal_type: SignalType
    predicted: str  # "UP" or "DOWN"
    entry_price: float
    exit_price: float | None = None  # price at horizon_days later
    actual: str | None = None  # "UP" or "DOWN"
    correct: bool | None = None
    return_pct: float | None = None


@dataclass
class BacktestResult:
    symbol: str
    signal_type: SignalType
    observations: list[SignalObs] = field(default_factory=list)

    @property
    def resolved(self) -> list[SignalObs]:
        return [o for o in self.observations if o.correct is not None]

    @property
    def hit_rate(self) -> float | None:
        r = self.resolved
        if not r:
            return None
        return sum(1 for o in r if o.correct) / len(r)

    @property
    def mean_return(self) -> float | None:
        r = [o.return_pct for o in self.resolved if o.return_pct is not None]
        return sum(r) / len(r) if r else None

    @property
    def max_adverse_return(self) -> float | None:
        predicted = PREDICTED_DIRECTION[self.signal_type]
        if predicted == "DOWN":
            adverse = [
                o.return_pct for o in self.resolved if o.return_pct is not None and o.return_pct > 0
            ]
        else:
            adverse = [
                o.return_pct for o in self.resolved if o.return_pct is not None and o.return_pct < 0
            ]
        if not adverse:
            return None
        return max(adverse, key=abs)


def run_backtest(
    symbol: str, horizon_days: int = 7, period: str = "2y"
) -> dict[SignalType, BacktestResult]:
    """Fetch history, compute RSI series, find all signals, resolve outcomes."""
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period=period, interval="1d")
    if hist.empty:
        print(f"  [WARN] No data for {symbol}")
        return {}

    dates = [d.date() for d in hist.index]
    closes = hist["Close"].tolist()

    rsi_series = wilder_rsi_series(closes)
    results: dict[SignalType, BacktestResult] = {}

    # Detect entry signals (first day RSI crosses into zone)
    prev_sig: SignalType | None = None
    for i, (d, close, rsi) in enumerate(zip(dates, closes, rsi_series)):
        if rsi is None:
            continue
        sig = classify_signal(rsi)
        # Only log signal on ENTRY (first day in the zone), not each subsequent day
        if sig is not None and sig != prev_sig:
            if sig not in results:
                results[sig] = BacktestResult(symbol=symbol, signal_type=sig)
            # Find exit price at horizon_days trading days later
            exit_idx = i + horizon_days
            exit_price = closes[exit_idx] if exit_idx < len(closes) else None
            return_pct = (exit_price - close) / close * 100 if exit_price is not None else None
            predicted = PREDICTED_DIRECTION[sig]
            if return_pct is not None:
                actual = "DOWN" if return_pct < 0 else "UP"
                correct = actual == predicted
            else:
                actual = None
                correct = None
            obs = SignalObs(
                signal_date=d,
                signal_rsi=round(rsi, 1),
                signal_type=sig,
                predicted=predicted,
                entry_price=round(close, 4),
                exit_price=round(exit_price, 4) if exit_price is not None else None,
                actual=actual,
                correct=correct,
                return_pct=round(return_pct, 2) if return_pct is not None else None,
            )
            results[sig].observations.append(obs)
        prev_sig = sig

    return results


# ── Report ─────────────────────────────────────────────────────────────────────


def print_report(
    all_results: dict[str, dict[SignalType, BacktestResult]],
    horizon_days: int,
    proven_only: bool = False,
) -> None:
    print(f"\n{'=' * 70}")
    print(f"  RSI-14 Signal Backtest — {horizon_days}-Day Forward Return")
    if proven_only:
        print("  ★ Showing PROVEN EDGE signals only (hit_rate>55%, n>=5)")
    print(f"{'=' * 70}\n")

    proven_edges: list[tuple[str, SignalType, BacktestResult]] = []

    for symbol, sig_map in sorted(all_results.items()):
        rows = []
        for sig_type in ("overbought", "overbought_exit", "oversold_exit", "oversold"):
            if sig_type not in sig_map:
                continue
            r = sig_map[sig_type]
            n = len(r.resolved)
            total = len(r.observations)
            hr = r.hit_rate
            mr = r.mean_return
            predicted = PREDICTED_DIRECTION[sig_type]
            has_edge = hr is not None and hr > 0.55 and n >= 5
            star = " ★" if has_edge else ""
            if proven_only and not has_edge:
                continue
            if has_edge:
                proven_edges.append((symbol, sig_type, r))
            rows.append((sig_type, total, n, hr, mr, predicted, star, r))

        if not rows:
            continue
        print(f"  {symbol}")
        print(f"  {'─' * 60}")
        for sig_type, total, n, hr, mr, predicted, star, r in rows:
            print(
                f"  {sig_type:<16} | signals={total:>3}  resolved={n:>3}  "
                f"hit_rate={f'{hr:.0%}' if hr is not None else 'N/A':>5}  "
                f"mean_return={f'{mr:+.2f}%' if mr is not None else 'N/A':>8}  "
                f"predicted={predicted}{star}"
            )

            if sig_type in ("overbought", "oversold") and r.observations:
                for obs in r.observations[-8:]:
                    status = "✓" if obs.correct else ("✗" if obs.correct is False else "?")
                    ret_str = (
                        f"{obs.return_pct:+.2f}%" if obs.return_pct is not None else "unresolved"
                    )
                    print(
                        f"    {obs.signal_date}  RSI={obs.signal_rsi:.1f}  "
                        f"entry=${obs.entry_price:.2f}  {status} {ret_str}"
                    )
        print()

    # Summary of all proven edges sorted by mean return
    if proven_edges:
        print(f"\n{'=' * 70}")
        print("  ★ PROVEN EDGES SUMMARY (sorted by mean return, descending)")
        print(f"{'=' * 70}")
        proven_edges.sort(key=lambda x: x[2].mean_return or 0.0, reverse=True)
        for sym, sig_type, r in proven_edges:
            tag = f"rsi_{sig_type}_{sym.lower()}"
            hr = r.hit_rate
            mr = r.mean_return
            n = len(r.resolved)
            print(
                f"  {tag:<32} hit={f'{hr:.0%}' if hr else 'N/A':>5}  "
                f"mean={f'{mr:+.2f}%' if mr else 'N/A':>8}  n={n}"
            )
        print()


# ── Thesis updater ─────────────────────────────────────────────────────────────


def update_thesis_file(
    symbol: str, sig_type: SignalType, result: BacktestResult, horizon_days: int
) -> None:
    """Patch the Historical Evidence section in the matching thesis doc."""
    thesis_dir = ROOT / "docs" / "portfolio" / "theses"
    # Find most recent file matching symbol + rough signal type
    tag_map = {
        "overbought": "overbought",
        "oversold": "oversold",
        "oversold_exit": "oversold-exit",
        "overbought_exit": "overbought-exit",
    }
    pattern = f"*-{symbol.upper()}-*{tag_map.get(sig_type, sig_type)}*.md"
    matches = sorted(thesis_dir.glob(pattern), reverse=True)
    if not matches:
        return
    path = matches[0]
    content = path.read_text()

    hr = result.hit_rate
    n = len(result.resolved)
    total = len(result.observations)
    mr = result.mean_return
    predicted = PREDICTED_DIRECTION[sig_type]

    section = f"""
## Historical Backtest Evidence (2-Year RSI-14 Study)

**Signal type**: {sig_type} | **Predicted direction**: {predicted} | **Horizon**: {horizon_days}d

| Metric | Value |
|--------|-------|
| Total signals (2y) | {total} |
| Resolved (horizon closed) | {n} |
| **Hit rate** | **{f"{hr:.1%}" if hr else "N/A"}** |
| Mean {horizon_days}d return | {f"{mr:+.2f}%" if mr else "N/A"} |
| Gate to live (≥5 obs, >55%) | {"✅ MET" if hr and hr > 0.55 and n >= 5 else "⏳ NOT YET"} |

### Signal history (last 10)

| Date | RSI | Entry | {horizon_days}d Return | Correct |
|------|-----|-------|--------|---------|
"""
    for obs in result.observations[-10:]:
        ret_str = f"{obs.return_pct:+.2f}%" if obs.return_pct is not None else "pending"
        correct_str = "✓" if obs.correct else ("✗" if obs.correct is False else "?")
        section += f"| {obs.signal_date} | {obs.signal_rsi:.1f} | ${obs.entry_price:.2f} | {ret_str} | {correct_str} |\n"

    marker = "## Historical Backtest Evidence"
    if marker in content:
        # Replace existing section
        start = content.index(marker)
        # Find next h2 after this one
        next_h2 = content.find("\n## ", start + 1)
        if next_h2 == -1:
            content = content[:start] + section.lstrip()
        else:
            content = content[:start] + section.lstrip() + "\n" + content[next_h2 + 1 :]
    else:
        content = content.rstrip() + "\n" + section

    path.write_text(content)
    print(f"  Updated: {path.name}")


# ── BetaBeliefLedger pre-population ───────────────────────────────────────────


def populate_ledger(all_results: dict[str, dict[SignalType, BacktestResult]]) -> None:
    """Print the Python snippet to pre-populate BetaBeliefLedger with historical data."""
    print("\n# BetaBeliefLedger pre-population snippet:")
    print("# (paste into scripts/run_portfolio_loop.py or run standalone)\n")
    print("from cohezion.integrations.robinhood_analysis import BetaBeliefLedger")
    print("ledger = BetaBeliefLedger()")

    for symbol, sig_map in sorted(all_results.items()):
        for sig_type, result in sig_map.items():
            tag = f"rsi_{sig_type}_{symbol.lower()}"
            for obs in result.resolved:
                outcome = "correct" if obs.correct else "incorrect"
                print(
                    f"ledger.update('{tag}', correct={obs.correct})  "
                    f"# {obs.signal_date} RSI={obs.signal_rsi} → {outcome}"
                )
    print()


# ── CLI ────────────────────────────────────────────────────────────────────────

# Watchlist organized by sector for wider coverage.
# Tier 1: Core holdings and original watchlist
# Tier 2: Sector ETFs (broad coverage, liquid, RSI signals well-studied)
# Tier 3: High-conviction individual names (AI/tech focus given $75 account size)
WATCH_SYMBOLS = [
    # ── Original watchlist ──────────────────────────────────────────────────
    "BND",  # US Aggregate Bond
    "NVDA",  # GPU/AI semiconductor
    "VTI",  # Total US equity
    "VWO",  # Emerging markets
    "VEA",  # Developed international
    # ── Equity sector ETFs ──────────────────────────────────────────────────
    "QQQ",  # Nasdaq-100 / mega-cap tech
    "XLK",  # Tech sector SPDR
    "XLV",  # Healthcare sector
    "XLE",  # Energy sector
    "XLF",  # Financials sector
    "XLY",  # Consumer discretionary
    "XLP",  # Consumer staples
    "XLU",  # Utilities (bond-proxy, RSI overbought interesting)
    "XLI",  # Industrials
    "VNQ",  # Real estate / REITs
    # ── Fixed income alternatives ────────────────────────────────────────────
    "TLT",  # 20+ Year Treasury (rate-sensitive, volatile RSI)
    "TIP",  # Treasury Inflation-Protected
    "AGG",  # US Aggregate Bond alt (iShares, parallel to BND)
    # ── Commodities ─────────────────────────────────────────────────────────
    "GLD",  # Gold ETF (safe-haven, RSI signals strong historically)
    "SLV",  # Silver ETF (more volatile than GLD)
    # ── AI / semiconductor individual names ─────────────────────────────────
    "AMD",  # GPU competitor to NVDA, high RSI swing amplitude
    "MSFT",  # Azure AI / cloud; steadier than NVDA, different RSI profile
    "META",  # AI infra spending leader, high beta
    "AAPL",  # Large weight in QQQ/VTI; RSI patterns well-studied
    "TSLA",  # High-beta, wide RSI swings — oversold signals historically strong
]


CORE_SYMBOLS = ["BND", "NVDA", "VTI", "VWO", "VEA"]  # original 5, fast check


def main() -> None:
    parser = argparse.ArgumentParser(description="RSI signal backtest for watchlist")
    parser.add_argument(
        "--symbol",
        nargs="+",
        default=WATCH_SYMBOLS,
        help="Symbols to backtest (default: all watchlist)",
    )
    parser.add_argument("--core", action="store_true", help="Run only the 5 core symbols (fast)")
    parser.add_argument(
        "--horizon", type=int, default=7, help="Forward return horizon in trading days (default: 7)"
    )
    parser.add_argument("--period", default="2y", help="yfinance history period (default: 2y)")
    parser.add_argument(
        "--update-theses",
        action="store_true",
        help="Patch thesis markdown files with backtest results",
    )
    parser.add_argument(
        "--populate-ledger",
        action="store_true",
        help="Print BetaBeliefLedger pre-population snippet",
    )
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument(
        "--proven-only",
        action="store_true",
        help="Show only signals with proven edge (hit_rate>55%, n>=5)",
    )
    args = parser.parse_args()
    if args.core:
        args.symbol = CORE_SYMBOLS

    print(f"Running {args.horizon}-day RSI-14 backtest on: {', '.join(args.symbol)}")
    all_results: dict[str, dict[SignalType, BacktestResult]] = {}

    for sym in args.symbol:
        print(f"  Fetching {sym} ({args.period} daily)...")
        all_results[sym] = run_backtest(sym, horizon_days=args.horizon, period=args.period)

    if args.json:
        out: dict = {}
        for sym, sig_map in all_results.items():
            out[sym] = {}
            for sig_type, result in sig_map.items():
                out[sym][sig_type] = {
                    "total_signals": len(result.observations),
                    "resolved": len(result.resolved),
                    "hit_rate": result.hit_rate,
                    "mean_return_pct": result.mean_return,
                    "predicted": PREDICTED_DIRECTION[sig_type],
                    "has_proven_edge": (result.hit_rate or 0) > 0.55 and len(result.resolved) >= 5,
                }
        print(json.dumps(out, indent=2))
        return

    print_report(all_results, args.horizon, proven_only=args.proven_only)

    if args.update_theses:
        print("Updating thesis files...")
        for sym, sig_map in all_results.items():
            for sig_type, result in sig_map.items():
                if result.resolved:
                    update_thesis_file(sym, sig_type, result, args.horizon)

    if args.populate_ledger:
        populate_ledger(all_results)


if __name__ == "__main__":
    main()
