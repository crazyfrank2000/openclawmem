# google_docs_append

Append text to a Google Doc (Diary) **into the document body** using Google Docs API.

This implements the "B方案" (no Maton) by reusing gogcli OAuth credentials + exported refresh token.

## Files
- `append_to_doc.py` — appends text at end of document (`endOfSegmentLocation`).
- `requirements.txt`

## Secrets (NOT committed)
- `secrets/gog_refresh_token.json` — exported via `gog auth tokens export` (contains refresh token)
- `~/.config/gogcli/credentials.json` — OAuth client id/secret used by gogcli

## Setup
```bash
cd /home/ubuntu/.openclaw/workspace/code/google_docs_append
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage
```bash
python append_to_doc.py --doc-id <DOC_ID> --text "\n...\n"
```
