# market_risk_metrics

Compute basic risk/return metrics for a stock/ETF using ~3 years of daily data from Yahoo Finance.

## Metrics
- Average daily return
- Daily volatility
- Annualized volatility
- Annualized Sharpe ratio (risk-free rate default 0, configurable)
- Historical VaR / Expected Shortfall (ES) at 95% and 99%

## Install
```bash
python3 -m pip install -r requirements.txt
```

## Usage
```bash
python3 risk_metrics.py SPY
python3 risk_metrics.py QQQ --rf 0.04
python3 risk_metrics.py AAPL --years 3
```

## Notes
- Uses **Adjusted Close** when available.
- VaR/ES are **historical** (non-parametric) on daily returns.
