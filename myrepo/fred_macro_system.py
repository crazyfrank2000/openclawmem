import os
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

API_KEY = os.getenv("FRED_API_KEY", "")
BASE = "https://api.stlouisfed.org/fred"
OUT = Path("/home/ubuntu/.openclaw/workspace/myrepo/fred_outputs")
OUT.mkdir(parents=True, exist_ok=True)

SERIES = {
    "CPI": "CPIAUCSL",
    "PCE": "PCEPI",
    "失业率": "UNRATE",
    "非农就业": "PAYEMS",
    "零售销售": "RSAFS",
    "工业产出": "INDPRO",
    "芝加哥联储NAI": "CFNAI",
    "30Y按揭利率": "MORTGAGE30US",
    "2Y国债": "DGS2",
    "10Y国债": "DGS10",
    "3M国债": "TB3MS",
    "10Y实际利率": "DFII10",
    "BAA": "BAA",
    "AAA": "AAA",
    "初请失业金": "ICSA",
    "联邦基金利率": "FEDFUNDS",
}

LEADING_FOR_RISK = {
    "初请失业金": 1.0,
    "芝加哥联储NAI": -1.0,
    "BAA-AAA": 1.2,
    "10Y-3M": -1.0,
}

POLICY_COMPONENTS = {
    "联邦基金利率": 1.0,
    "10Y-2Y": -0.8,
    "BAA-AAA": 1.0,
    "10Y实际利率": 0.8,
}


def fred_get_series(series_id, start="2000-01-01"):
    url = f"{BASE}/series/observations"
    params = {
        "series_id": series_id,
        "api_key": API_KEY,
        "file_type": "json",
        "observation_start": start,
    }
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    j = r.json()
    obs = j.get("observations", [])
    df = pd.DataFrame(obs)
    if df.empty:
        return pd.Series(dtype=float)
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    s = df.set_index("date")["value"].dropna()
    return s


def latest_and_changes(s: pd.Series):
    if s.empty:
        return np.nan, np.nan, np.nan, np.nan
    s = s.sort_index()
    last = s.iloc[-1]
    now = s.index[-1]

    def get_prev(months):
        target = now - pd.DateOffset(months=months)
        sub = s.loc[:target]
        return sub.iloc[-1] if len(sub) else np.nan

    p1, p3, p12 = get_prev(1), get_prev(3), get_prev(12)
    c1 = (last - p1) if pd.notna(p1) else np.nan
    c3 = (last - p3) if pd.notna(p3) else np.nan
    c12 = (last - p12) if pd.notna(p12) else np.nan
    return last, c1, c3, c12


def zscore(x: pd.Series, window=90):
    mu = x.rolling(window, min_periods=max(12, window//4)).mean()
    sd = x.rolling(window, min_periods=max(12, window//4)).std(ddof=0)
    return (x - mu) / sd.replace(0, np.nan)


def main():
    if not API_KEY:
        raise SystemExit("请先设置环境变量 FRED_API_KEY")

    raw = {}
    for name, sid in SERIES.items():
        raw[name] = fred_get_series(sid)

    # 衍生因子
    factors = {}
    factors["10Y-2Y"] = raw["10Y国债"].dropna() - raw["2Y国债"].dropna()
    factors["10Y-3M"] = raw["10Y国债"].dropna() - raw["3M国债"].dropna()
    factors["BAA-AAA"] = raw["BAA"].dropna() - raw["AAA"].dropna()

    dashboard_rows = []
    for k, s in {**raw, **factors}.items():
        if s.empty:
            continue
        last, c1, c3, c12 = latest_and_changes(s)
        # 红绿灯（简化阈值）
        light = "🟢"
        if k in ["失业率", "初请失业金", "BAA-AAA", "联邦基金利率", "10Y实际利率"] and c3 > 0:
            light = "🟡"
        if k in ["BAA-AAA", "初请失业金"] and c1 > 0 and c3 > 0:
            light = "🔴"
        if k in ["10Y-2Y", "10Y-3M"] and last < 0:
            light = "🔴"
        dashboard_rows.append({
            "指标": k,
            "最新值": round(float(last), 4),
            "1个月变化": round(float(c1), 4) if pd.notna(c1) else None,
            "3个月变化": round(float(c3), 4) if pd.notna(c3) else None,
            "12个月变化": round(float(c12), 4) if pd.notna(c12) else None,
            "状态": light,
            "最新日期": s.index[-1].date().isoformat(),
        })

    dashboard = pd.DataFrame(dashboard_rows).sort_values("指标")
    dashboard.to_csv(OUT / "macro_dashboard_latest.csv", index=False, encoding="utf-8-sig")

    # 日频对齐（宏观->交易频率）
    idx = pd.date_range(end=pd.Timestamp.utcnow().normalize(), periods=900, freq="D")
    daily = pd.DataFrame(index=idx)
    for k in ["CPI", "PCE", "失业率", "非农就业", "初请失业金", "联邦基金利率", "10Y国债", "2Y国债", "BAA", "AAA", "芝加哥联储NAI"]:
        s = raw[k].copy()
        if s.empty:
            continue
        daily[k] = s.reindex(idx).ffill()

    daily["10Y-2Y"] = daily["10Y国债"] - daily["2Y国债"]
    daily["BAA-AAA"] = daily["BAA"] - daily["AAA"]
    daily["10Y-3M"] = raw["10Y国债"].reindex(idx).ffill() - raw["3M国债"].reindex(idx).ffill()

    # 差分 / 二阶差分
    for col in ["CPI", "PCE", "失业率", "初请失业金", "BAA-AAA", "10Y-2Y"]:
        if col in daily.columns:
            daily[f"d_{col}"] = daily[col].diff(21)
            daily[f"dd_{col}"] = daily[f"d_{col}"].diff(21)

    # Risk-on/off 指数
    risk_parts = []
    for col, w in LEADING_FOR_RISK.items():
        if col in daily.columns:
            risk_parts.append(w * zscore(daily[col]))
    daily["risk_off_index"] = pd.concat(risk_parts, axis=1).mean(axis=1)

    # Policy Tightness
    policy_parts = []
    for col, w in POLICY_COMPONENTS.items():
        if col in daily.columns:
            policy_parts.append(w * zscore(daily[col]))
    daily["policy_tightness_index"] = pd.concat(policy_parts, axis=1).mean(axis=1)

    # Regime
    daily["growth_proxy"] = zscore(daily["非农就业"].diff(63)) * -1 + zscore(daily["初请失业金"].diff(63))
    daily["inflation_proxy"] = zscore(daily["CPI"].diff(63)) + zscore(daily["PCE"].diff(63))

    def regime(g, i):
        if pd.isna(g) or pd.isna(i):
            return None
        g_up = g < 0
        i_up = i > 0
        if g_up and (not i_up):
            return "增长上行+通胀下行（Risk-on）"
        if (not g_up) and i_up:
            return "增长下行+通胀上行（最困难）"
        if g_up and i_up:
            return "增长上行+通胀上行（再通胀交易）"
        return "增长下行+通胀下行（衰退交易）"

    daily["regime"] = [regime(g, i) for g, i in zip(daily["growth_proxy"], daily["inflation_proxy"])]

    daily.to_csv(OUT / "macro_daily_features.csv", encoding="utf-8-sig")

    snap = daily.dropna(subset=["risk_off_index", "policy_tightness_index"])
    if snap.empty:
        risk_val = float("nan")
        policy_val = float("nan")
        regime_val = "样本不足（可扩大历史区间）"
    else:
        last = snap.iloc[-1]
        risk_val = float(last["risk_off_index"])
        policy_val = float(last["policy_tightness_index"])
        regime_val = str(last["regime"])

    report = f"""# FRED 宏观量化系统（自动生成）\n\n生成时间(UTC): {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}\n\n## 一、宏观看板（最新）\n\n见文件：`macro_dashboard_latest.csv`\n\n## 二、当前状态快照\n- Risk-off 指数: **{risk_val:.2f}**（越高越偏防御）\n- Policy Tightness 指数: **{policy_val:.2f}**（越高越偏紧）\n- 当前 Regime: **{regime_val}**\n\n## 三、策略化落地（已实现）\n1. 宏观指标自动抓取（FRED）\n2. 1/3/12 月变化与红绿灯\n3. 关键利差与信用压力（10Y-2Y,10Y-3M,BAA-AAA）\n4. 差分与二阶差分（Δ, ΔΔ）\n5. 宏观日频化（前值填充）\n6. Risk-off / Policy Tightness 双指数\n7. 增长-通胀四象限 Regime\n\n## 四、下一步建议（我可以继续做）\n- 接入资产价格（日频：SPX/QQQ/TLT/GLD/DXY）做事件窗口回测（t-1到t+3）\n- 叠加经济数据“预期值”形成 surprise 因子（如 CPI surprise）\n- 把信号写入你的 Google Sheet 并配置 Telegram 阈值报警\n"""
    (OUT / "macro_report_cn.md").write_text(report, encoding="utf-8")
    print("DONE")
    print("OUT_DIR", OUT)


if __name__ == "__main__":
    main()
