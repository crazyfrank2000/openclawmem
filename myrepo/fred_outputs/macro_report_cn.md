# FRED 宏观量化系统（自动生成）

生成时间(UTC): 2026-02-13 04:45:54

## 一、宏观看板（最新）

见文件：`macro_dashboard_latest.csv`

## 二、当前状态快照
- Risk-off 指数: **nan**（越高越偏防御）
- Policy Tightness 指数: **nan**（越高越偏紧）
- 当前 Regime: **样本不足（可扩大历史区间）**

## 三、策略化落地（已实现）
1. 宏观指标自动抓取（FRED）
2. 1/3/12 月变化与红绿灯
3. 关键利差与信用压力（10Y-2Y,10Y-3M,BAA-AAA）
4. 差分与二阶差分（Δ, ΔΔ）
5. 宏观日频化（前值填充）
6. Risk-off / Policy Tightness 双指数
7. 增长-通胀四象限 Regime

## 四、下一步建议（我可以继续做）
- 接入资产价格（日频：SPX/QQQ/TLT/GLD/DXY）做事件窗口回测（t-1到t+3）
- 叠加经济数据“预期值”形成 surprise 因子（如 CPI surprise）
- 把信号写入你的 Google Sheet 并配置 Telegram 阈值报警
