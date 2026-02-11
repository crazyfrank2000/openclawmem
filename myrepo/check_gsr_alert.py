#!/usr/bin/env python3
import csv
import datetime as dt
import io
import json
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent
CFG = json.loads((BASE / 'automation_config.json').read_text(encoding='utf-8'))
STATE = BASE / 'gsr_state.json'
OUT = BASE / 'gsr_alert.md'


def latest_close(symbol: str) -> tuple[str, float]:
    url = f'https://stooq.com/q/d/l/?s={symbol}&i=d'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    raw = urllib.request.urlopen(req, timeout=20).read().decode('utf-8', errors='ignore')
    rows = list(csv.DictReader(io.StringIO(raw)))
    for r in reversed(rows):
        try:
            return r['Date'], float(r['Close'])
        except Exception:
            continue
    raise RuntimeError(f'{symbol} 无法读取收盘价')


def main():
    # 使用 GLD/SLV 比值 *10 近似 GSR
    d1, gld = latest_close('gld.us')
    d2, slv = latest_close('slv.us')
    gsr = (gld / slv) * 10 if slv else 0

    threshold = float(CFG['gsr_threshold'])

    prev_below = None
    if STATE.exists():
        try:
            prev_below = json.loads(STATE.read_text(encoding='utf-8')).get('below')
        except Exception:
            prev_below = None

    below = gsr < threshold
    STATE.write_text(json.dumps({'below': below, 'gsr': gsr, 'ts': dt.datetime.utcnow().isoformat()}), encoding='utf-8')

    now = dt.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
    msg = (
        f"# GSR 异常提醒\n\n"
        f"- 监控时间：{now}\n"
        f"- GLD 最新：{gld:.2f}（{d1}）\n"
        f"- SLV 最新：{slv:.2f}（{d2}）\n"
        f"- 近似 GSR（GLD/SLV*10）：{gsr:.2f}\n"
        f"- 阈值：{threshold:.2f}\n"
    )

    if below and prev_below is not True:
        OUT.write_text(msg + "\n结论：已触发“小于阈值”新信号。", encoding='utf-8')
        print('ALERT_TRIGGERED')
        print(str(OUT))
    else:
        print('NO_ALERT')


if __name__ == '__main__':
    main()
