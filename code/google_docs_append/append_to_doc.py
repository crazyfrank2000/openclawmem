#!/usr/bin/env python3
"""Append text to a Google Doc (at end of body) using Google Docs API.

Auth model: reuse gogcli OAuth client credentials + exported refresh token.

Usage:
  python append_to_doc.py --doc-id <DOC_ID> --text "hello" \
    --gog-credentials ~/.config/gogcli/credentials.json \
    --gog-token ../../secrets/gog_refresh_token.json

Notes:
- Token export file contains sensitive refresh token. Keep it under secrets/.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/documents"]


def load_gog_credentials(path: str) -> tuple[str, str]:
    obj = json.loads(Path(path).read_text())
    return obj["client_id"], obj["client_secret"]


def load_refresh_token(path: str) -> tuple[str, str]:
    obj = json.loads(Path(path).read_text())
    # gog export format contains refresh_token under services buckets; try common places
    if "refresh_token" in obj:
        return obj["email"], obj["refresh_token"]

    # Newer gog token export nests tokens
    tokens = obj.get("tokens") or obj.get("token") or {}
    if isinstance(tokens, dict) and "refresh_token" in tokens:
        return obj.get("email", ""), tokens["refresh_token"]

    # Fallback: search recursively
    def find_refresh(x):
        if isinstance(x, dict):
            if "refresh_token" in x:
                return x["refresh_token"]
            for v in x.values():
                r = find_refresh(v)
                if r:
                    return r
        if isinstance(x, list):
            for v in x:
                r = find_refresh(v)
                if r:
                    return r
        return None

    rt = find_refresh(obj)
    if not rt:
        raise ValueError("refresh_token not found in gog token export")
    return obj.get("email", ""), rt


def append_text(doc_id: str, text: str, client_id: str, client_secret: str, refresh_token: str) -> dict:
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )

    service = build("docs", "v1", credentials=creds, cache_discovery=False)

    req = {
        "requests": [
            {
                "insertText": {
                    "endOfSegmentLocation": {},
                    "text": text,
                }
            }
        ]
    }
    return service.documents().batchUpdate(documentId=doc_id, body=req).execute()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc-id", required=True)
    ap.add_argument("--text", required=True)
    ap.add_argument(
        "--gog-credentials",
        default=str(Path.home() / ".config/gogcli/credentials.json"),
    )
    ap.add_argument(
        "--gog-token",
        default=str(Path(__file__).resolve().parents[2] / "secrets" / "gog_refresh_token.json"),
    )
    args = ap.parse_args()

    client_id, client_secret = load_gog_credentials(args.gog_credentials)
    _, refresh_token = load_refresh_token(args.gog_token)

    res = append_text(args.doc_id, args.text, client_id, client_secret, refresh_token)
    print(json.dumps({"status": "ok", "replies": len(res.get("replies", []))}, ensure_ascii=False))


if __name__ == "__main__":
    main()
