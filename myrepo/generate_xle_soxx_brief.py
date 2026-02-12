#!/usr/bin/env python3
import csv
import datetime as dt
import io
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent
OUT = BASE / 'daily_xle_soxx_brief.md'

SYMBOLS = [
    ('xle.us', 'XLE（能源）'),
    ('soxx.us', 'SOXX（半导体）'),
    ('qqq.us', 'QQQ（纳指100ETF）'),
    ('spy.us', 'SPY（标普500ETF）'),
    ('gld.us', 'GLD（黄金ETF）'),
    ('slv.us', 'SLV（白银ETF）'),
    ('vwo.us', 'VWO（新兴市场ETF）'),
]


def load_stooq_daily(symbol: str):
    url = f'https://stooq.com/q/d/l/?s={symbol}&i=d'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    raw = urllib.request.urlopen(req, timeout=20).read().decode('utf-8', errors='ignore')
    rows = list(csv.DictReader(io.StringIO(raw)))
    clean = []
    for r in rows:
        try:
            d = dt.datetime.strptime(r['Date'], '%Y-%m-%d').date()
            c = float(r['Close'])
            v = float(r.get('Volume') or 0)
            clean.append((d, c, v))
        except Exception:
            continue
    clean.sort(key=lambda x: x[0])
    if len(clean) < 22:
        raise RuntimeError(f'{symbol} 历史数据不足')
    return clean


def summarize(symbol: str, data):
    last_d, last_c, last_v = data[-1]
    prev_c = data[-2][1]
    ret1 = (last_c / prev_c - 1) * 100
    c20 = data[-21][1]
    ret20 = (last_c / c20 - 1) * 100
    closes = [x[1] for x in data[-20:]]
    high20 = max(closes)
    low20 = min(closes)
    return {
        'symbol': symbol.upper().replace('.US', ''),
        'date': str(last_d),
        'close': last_c,
        'ret1': ret1,
        'ret20': ret20,
        'high20': high20,
        'low20': low20,
        'vol': int(last_v),
    }


def build_md(items):
    now = dt.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
    lines = [
        '# 每日收盘简报：重点ETF',
        '',
        f'_生成时间：{now}_',
        '',
    ]

    for title, info in items:
        lines.extend([
            f'## {title}',
            f"- 最新交易日：{info['date']}",
            f"- 收盘价：{info['close']:.2f}",
            f"- 日涨跌：{info['ret1']:+.2f}%",
            f"- 20日涨跌：{info['ret20']:+.2f}%",
            f"- 20日区间：{info['low20']:.2f} ~ {info['high20']:.2f}",
            f"- 成交量：{info['vol']:,}",
            '',
        ])

    lines.append('数据源：Stooq（公开行情）')
    lines.append('')
    return '\n'.join(lines)


def main():
    items = []
    for symbol, title in SYMBOLS:
        info = summarize(symbol, load_stooq_daily(symbol))
        items.append((title, info))

    md = build_md(items)
    OUT.write_text(md, encoding='utf-8')
    print(str(OUT))


if __name__ == '__main__':
    main()
