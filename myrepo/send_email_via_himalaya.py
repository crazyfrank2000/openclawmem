#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
CFG = json.loads((BASE / 'automation_config.json').read_text(encoding='utf-8'))


def main():
    if len(sys.argv) < 3:
        print('Usage: send_email_via_himalaya.py <subject> <body_file>')
        sys.exit(2)

    subject = sys.argv[1]
    body_file = Path(sys.argv[2])
    body = body_file.read_text(encoding='utf-8')

    msg = (
        f"From: {CFG['from_email']}\\n"
        f"To: {CFG['to_email']}\\n"
        f"Subject: {subject}\\n"
        "\\n"
        f"{body}"
    )

    cmd = ['himalaya', 'message', 'send', '-a', CFG['email_account'], msg]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        print('EMAIL_SEND_FAILED')
        print(proc.stderr.strip())
        sys.exit(proc.returncode)

    print('EMAIL_SENT')


if __name__ == '__main__':
    main()
