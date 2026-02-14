#!/usr/bin/env python3
"""Compute simple risk/return metrics for a stock/ETF using ~3 years of daily data.

Data source: Yahoo Finance via yfinance.
Metrics:
- Average daily return
- Daily volatility
- Annualized volatility
- Annualized Sharpe ratio (rf=0 by default)
- Historical VaR/ES at 95% and 99% (based on daily returns)

Example:
  python risk_metrics.py SPY
  python risk_metrics.py QQQ --rf 0.04
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from typing import Tuple

import numpy as np
import pandas as pd


def _require(pkg: str) -> None:
    raise SystemExit(
        f"Missing dependency: {pkg}. Install with: pip install -r requirements.txt"
    )


try:
    import yfinance as yf
except Exception:  # pragma: no cover
    yf = None


TRADING_DAYS = 252


@dataclass
class Metrics:
    ticker: str
    start: pd.Timestamp
    end: pd.Timestamp
    n_obs: int
    avg_daily_return: float
    vol_daily: float
    vol_annual: float
    sharpe_annual: float
    var95: float
    es95: float
    var99: float
    es99: float


def fetch_prices(ticker: str, years: int = 3) -> pd.Series:
    if yf is None:
        _require("yfinance")

    end = pd.Timestamp.now(tz="UTC").normalize()
    start = end - pd.DateOffset(years=years)

    df = yf.download(
        ticker,
        start=start.date().isoformat(),
        end=(end + pd.Timedelta(days=1)).date().isoformat(),
        interval="1d",
        auto_adjust=False,
        progress=False,
    )

    if df is None or len(df) == 0:
        raise ValueError(f"No price data returned for ticker '{ticker}'.")

    # Prefer Adj Close if present
    if "Adj Close" in df.columns:
        px = df["Adj Close"].copy()
    elif "Close" in df.columns:
        px = df["Close"].copy()
    else:
        raise ValueError("Price dataframe missing Close/Adj Close columns.")

    # yfinance may return a DataFrame (e.g., column labeled by ticker). Normalize to Series.
    if isinstance(px, pd.DataFrame):
        if px.shape[1] == 0:
            raise ValueError("Empty price frame after selecting close column")
        px = px.iloc[:, 0]

    px = px.dropna()
    if len(px) < 50:
        raise ValueError(
            f"Not enough observations for '{ticker}' after cleaning (n={len(px)})."
        )
    px.name = "adj_close"
    return px


def returns_from_prices(px: pd.Series) -> pd.Series:
    rets = px.pct_change().dropna()
    rets.name = "ret"
    return rets


def historical_var_es(returns: pd.Series, alpha: float) -> Tuple[float, float]:
    """Historical (non-parametric) VaR/ES for left tail.

    Returns are in decimal form, e.g. -0.02 is -2% daily.
    VaR is the alpha-quantile (e.g., 5% quantile for 95% VaR).
    ES is the mean of returns <= VaR.
    """
    if not (0 < alpha < 1):
        raise ValueError("alpha must be in (0,1)")

    q = float(np.quantile(returns.values, alpha))
    tail = returns[returns <= q]
    es = float(tail.mean()) if len(tail) else q
    return q, es


def compute_metrics(ticker: str, rf_annual: float = 0.0, years: int = 3) -> Metrics:
    px = fetch_prices(ticker, years=years)
    rets = returns_from_prices(px)

    avg_daily = float(rets.mean())
    vol_daily = float(rets.std(ddof=1))
    vol_annual = vol_daily * math.sqrt(TRADING_DAYS)

    rf_daily = rf_annual / TRADING_DAYS
    excess_daily = rets - rf_daily
    excess_annual = float(excess_daily.mean()) * TRADING_DAYS
    sharpe = excess_annual / vol_annual if vol_annual > 0 else float("nan")

    var95, es95 = historical_var_es(rets, 0.05)
    var99, es99 = historical_var_es(rets, 0.01)

    return Metrics(
        ticker=ticker.upper(),
        start=px.index.min(),
        end=px.index.max(),
        n_obs=int(rets.shape[0]),
        avg_daily_return=avg_daily,
        vol_daily=vol_daily,
        vol_annual=vol_annual,
        sharpe_annual=sharpe,
        var95=var95,
        es95=es95,
        var99=var99,
        es99=es99,
    )


def fmt_pct(x: float, digits: int = 2) -> str:
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "n/a"
    return f"{x*100:.{digits}f}%"


def fmt_num(x: float, digits: int = 2) -> str:
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "n/a"
    return f"{x:.{digits}f}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Compute Sharpe/vol/VaR/ES from 3y daily Yahoo Finance data"
    )
    ap.add_argument("ticker", help="Ticker symbol, e.g. SPY, QQQ, AAPL")
    ap.add_argument(
        "--years",
        type=int,
        default=3,
        help="Lookback window in years (default: 3)",
    )
    ap.add_argument(
        "--rf",
        type=float,
        default=0.0,
        help="Annual risk-free rate as decimal (default: 0.0; example: 0.04)",
    )

    args = ap.parse_args(argv)

    try:
        m = compute_metrics(args.ticker, rf_annual=args.rf, years=args.years)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    print(f"Ticker: {m.ticker}")
    print(f"Window: {m.start.date()} → {m.end.date()}  (n={m.n_obs} daily returns)")
    print("")
    print("Return/Vol")
    print(f"- Avg daily return:  {fmt_pct(m.avg_daily_return, 3)}")
    print(f"- Daily vol (σ):     {fmt_pct(m.vol_daily, 3)}")
    print(f"- Annual vol (σ):    {fmt_pct(m.vol_annual, 2)}")
    print(f"- Sharpe (annual):   {fmt_num(m.sharpe_annual, 2)}  (rf={args.rf:.2%})")
    print("")
    print("Historical tail risk (daily returns)")
    print(f"- VaR 95%: {fmt_pct(m.var95, 2)}   | ES 95%: {fmt_pct(m.es95, 2)}")
    print(f"- VaR 99%: {fmt_pct(m.var99, 2)}   | ES 99%: {fmt_pct(m.es99, 2)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
