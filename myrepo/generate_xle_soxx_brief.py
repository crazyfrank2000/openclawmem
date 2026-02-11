#!/usr/bin/env python3
import csv
import datetime as dt
import io
import json
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent
CFG = json.loads((BASE / 'automation_config.json').read_text(encoding='utf-8'))
OUT = BASE / 'daily_xle_soxx_brief.md'


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


def build_md(xle, soxx):
    now = dt.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
    return f"""# 每日收盘简报：XLE / SOXX

_生成时间：{now}_

## XLE（能源）
- 最新交易日：{xle['date']}
- 收盘价：{xle['close']:.2f}
- 日涨跌：{xle['ret1']:+.2f}%
- 20日涨跌：{xle['ret20']:+.2f}%
- 20日区间：{xle['low20']:.2f} ~ {xle['high20']:.2f}
- 成交量：{xle['vol']:,}

## SOXX（半导体）
- 最新交易日：{soxx['date']}
- 收盘价：{soxx['close']:.2f}
- 日涨跌：{soxx['ret1']:+.2f}%
- 20日涨跌：{soxx['ret20']:+.2f}%
- 20日区间：{soxx['low20']:.2f} ~ {soxx['high20']:.2f}
- 成交量：{soxx['vol']:,}

数据源：Stooq（公开行情）
"""


def main():
    xle = summarize('xle.us', load_stooq_daily('xle.us'))
    soxx = summarize('soxx.us', load_stooq_daily('soxx.us'))
    md = build_md(xle, soxx)
    OUT.write_text(md, encoding='utf-8')
    print(str(OUT))


if __name__ == '__main__':
    main()
