#!/usr/bin/env python3
"""
优先调用 Cursor Agent 获取 AAPL 最近 52 周市场表现；
若超时或失败，则回退到 Google Finance 页面抓取。

输出文件：aapl_52week_performance.md
"""

from __future__ import annotations

import datetime as dt
import re
import subprocess
import urllib.request
from pathlib import Path

AGENT_BIN = "/home/ubuntu/.local/bin/agent"
OUTPUT_MD = Path(__file__).with_name("aapl_52week_performance.md")

PROMPT = """
请通过 Google Finance 获取 AAPL（Apple Inc.）最近 52 周市场表现，并输出为简洁的 Markdown。
要求：
1) 包含：当前价、52周最高、52周最低、距52周高点/低点的差值（金额和百分比）、52周区间位置。
2) 给出数据时间（含时区），并注明数据来源为 Google Finance。
3) 用中文输出，结构清晰，最多 12 行正文。
4) 不要输出额外解释；仅返回 Markdown 正文。
""".strip()


def run_agent(prompt: str, timeout_sec: int = 45) -> str:
    cmd = [AGENT_BIN, "--print", "--output-format", "text", prompt]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec)
    if proc.returncode != 0:
        raise RuntimeError(f"agent exit={proc.returncode}, stderr={proc.stderr.strip()}")
    out = proc.stdout.strip()
    if not out:
        raise RuntimeError("agent empty output")
    return out


def _extract_number(text: str, label: str) -> float:
    # 从类似“52-week high 260.10”或“52周高 260.10”后抓数值
    pattern = rf"{label}[^0-9\-]*([0-9]+(?:\.[0-9]+)?)"
    m = re.search(pattern, text, flags=re.IGNORECASE)
    if not m:
        raise ValueError(f"无法解析字段: {label}")
    return float(m.group(1))


def fallback_from_google_finance() -> str:
    url = "https://www.google.com/finance/quote/AAPL:NASDAQ?hl=en"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        html = resp.read().decode("utf-8", errors="ignore")

    plain = re.sub(r"<[^>]+>", " ", html)
    plain = re.sub(r"\s+", " ", plain)

    # 先从结构化属性抓当前价，抓不到再回退到文本匹配
    m_price = re.search(r'data-last-price="([0-9]+(?:\.[0-9]+)?)"', html)
    if m_price:
        price = float(m_price.group(1))
    else:
        try:
            price = _extract_number(plain, r"current price")
        except Exception:
            price = _extract_number(plain, r"price")

    high52 = _extract_number(plain, r"52-week high")
    low52 = _extract_number(plain, r"52-week low")

    diff_high = price - high52
    pct_high = (diff_high / high52) * 100 if high52 else 0.0
    diff_low = price - low52
    pct_low = (diff_low / low52) * 100 if low52 else 0.0
    pos = ((price - low52) / (high52 - low52) * 100) if high52 != low52 else 0.0

    tstr = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return (
        f"- 数据时间：{tstr}\n"
        f"- 当前价：${price:.2f}\n"
        f"- 52周最高：${high52:.2f}\n"
        f"- 52周最低：${low52:.2f}\n"
        f"- 距52周高点：{diff_high:+.2f} 美元（{pct_high:+.2f}%）\n"
        f"- 距52周低点：{diff_low:+.2f} 美元（{pct_low:+.2f}%）\n"
        f"- 52周区间位置：{pos:.2f}%\n"
        f"- 数据来源：Google Finance"
    )


def main() -> None:
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    try:
        content = run_agent(PROMPT, timeout_sec=45)
        method = "Cursor Agent"
    except Exception as e:
        content = fallback_from_google_finance()
        method = f"Google Finance fallback（agent失败: {e}）"

    final_md = (
        "# AAPL 最近52周市场表现\n\n"
        f"_生成时间：{now}_\n"
        f"_生成方式：{method}_\n\n"
        f"{content}\n"
    )

    OUTPUT_MD.write_text(final_md, encoding="utf-8")
    print(f"已写入: {OUTPUT_MD}")


if __name__ == "__main__":
    main()
