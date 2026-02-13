#!/usr/bin/env bash
set -euo pipefail

export FRED_API_KEY="${FRED_API_KEY:-9d62dbc3a316156305acf75c54742969}"
VENV="/home/ubuntu/.openclaw/workspace/.venv_fred/bin/python"
GOG="/home/ubuntu/.openclaw/workspace/tools/gogcli/bin/gog"
SID="1HoBsppsZcJxhVG28IVJoZfSYBovfaTiZiQqgnQ_I1wg"
ACCOUNT="wenjun81@gmail.com"
CSV="/home/ubuntu/.openclaw/workspace/myrepo/fred_outputs/macro_dashboard_latest.csv"

$VENV /home/ubuntu/.openclaw/workspace/myrepo/fred_macro_system.py

python3 - << 'PY'
import csv, json, subprocess, pathlib
csv_path=pathlib.Path('/home/ubuntu/.openclaw/workspace/myrepo/fred_outputs/macro_dashboard_latest.csv')
rows=list(csv.reader(csv_path.open('r',encoding='utf-8-sig')))
sid='1HoBsppsZcJxhVG28IVJoZfSYBovfaTiZiQqgnQ_I1wg'
acct='wenjun81@gmail.com'
gog='/home/ubuntu/.openclaw/workspace/tools/gogcli/bin/gog'
subprocess.run([gog,'sheets','clear',sid,'流水帐!J:Q','--account',acct,'--json'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
values_json=json.dumps(rows,ensure_ascii=False)
subprocess.run([gog,'sheets','update',sid,'流水帐!J1:P200','--values-json',values_json,'--input','USER_ENTERED','--account',acct,'--json'],check=True)
print('Synced dashboard to 流水帐!J:P')
PY

echo "FRED pipeline done"