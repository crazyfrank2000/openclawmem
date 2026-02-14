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


def make_service(client_id: str, client_secret: str, refresh_token: str):
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )
    return build("docs", "v1", credentials=creds, cache_discovery=False)


def create_doc(title: str, client_id: str, client_secret: str, refresh_token: str) -> str:
    service = make_service(client_id, client_secret, refresh_token)
    doc = service.documents().create(body={"title": title}).execute()
    return doc["documentId"]


def append_text(doc_id: str, text: str, client_id: str, client_secret: str, refresh_token: str) -> dict:
    service = make_service(client_id, client_secret, refresh_token)

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


def append_daily_summary_styled(
    doc_id: str,
    title_line: str,
    sections: list[tuple[str, list[str]]],
    client_id: str,
    client_secret: str,
    refresh_token: str,
) -> dict:
    """Append a daily summary using Google Docs styles.

    - Title line is applied as HEADING_2.
    - Section headers are bold.
    - Section bullets are real bullet lists.

    Note: This appends at end of document.
    """

    service = make_service(client_id, client_secret, refresh_token)

    # Find current end index
    doc = service.documents().get(documentId=doc_id).execute()
    body = doc.get("body", {}).get("content", [])
    end_index = body[-1]["endIndex"] - 1  # before the final newline

    # Build text to insert
    lines: list[str] = ["\n", "\n", title_line, "\n", "\n"]
    section_header_ranges: list[tuple[int, int]] = []
    bullet_para_ranges: list[tuple[int, int]] = []

    cursor = end_index
    insert_text = "".join(lines)
    cursor += len(insert_text)

    # Title range excludes preceding newlines
    title_start = end_index + 2
    title_end = title_start + len(title_line)

    for header, bullets in sections:
        # Header
        header_prefix = f"{header}\n"
        h_start = end_index + len(insert_text)
        insert_text += header_prefix
        h_end = h_start + len(header)
        section_header_ranges.append((h_start, h_end))

        # Bullets (as plain paragraphs, then convert to bullets)
        b_start = end_index + len(insert_text)
        if bullets:
            for b in bullets:
                insert_text += f"{b}\n"
        else:
            insert_text += "\n"
        b_end = end_index + len(insert_text)
        # Apply bullets to the paragraphs containing bullet lines
        if bullets:
            bullet_para_ranges.append((b_start, b_end))

        # Spacing between sections
        insert_text += "\n"

    requests = []

    # Insert text at explicit location
    requests.append({"insertText": {"location": {"index": end_index}, "text": insert_text}})

    # Apply heading style to title line
    requests.append(
        {
            "updateParagraphStyle": {
                "range": {"startIndex": title_start, "endIndex": title_end + 1},
                "paragraphStyle": {"namedStyleType": "HEADING_2"},
                "fields": "namedStyleType",
            }
        }
    )

    # Bold section headers
    for s, e in section_header_ranges:
        requests.append(
            {
                "updateTextStyle": {
                    "range": {"startIndex": s, "endIndex": e},
                    "textStyle": {"bold": True},
                    "fields": "bold",
                }
            }
        )

    # Convert bullet paragraphs to bullet lists
    for s, e in bullet_para_ranges:
        requests.append(
            {
                "createParagraphBullets": {
                    "range": {"startIndex": s, "endIndex": e},
                    "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE",
                }
            }
        )

    return service.documents().batchUpdate(documentId=doc_id, body={"requests": requests}).execute()


def main():
    ap = argparse.ArgumentParser()

    ap.add_argument("--doc-id", help="Target Google Doc ID")
    ap.add_argument("--text", help="Raw text to append")

    ap.add_argument("--create-doc", metavar="TITLE", help="Create a new Google Doc and print its docId")

    ap.add_argument("--daily-title", help="Title line for styled daily summary")
    ap.add_argument(
        "--daily-sections-json",
        help=(
            "JSON array of sections: [[\"1）市场情况\", [\"a\",\"b\"]], ...]. "
            "If a section bullet list is empty, it will be left blank."
        ),
    )

    ap.add_argument(
        "--gog-credentials",
        default=str(Path.home() / ".config/gogcli/credentials.json"),
    )
    ap.add_argument(
        "--gog-token",
        # Default to workspace-relative secrets path (this repo layout)
        default=str(Path(__file__).resolve().parent / "secrets" / "gog_refresh_token.json"),
    )

    args = ap.parse_args()

    client_id, client_secret = load_gog_credentials(args.gog_credentials)
    _, refresh_token = load_refresh_token(args.gog_token)

    if args.create_doc:
        doc_id = create_doc(args.create_doc, client_id, client_secret, refresh_token)
        print(json.dumps({"status": "ok", "docId": doc_id}, ensure_ascii=False))
        return

    if args.daily_title and args.daily_sections_json:
        if not args.doc_id:
            raise SystemExit("--doc-id is required for styled daily summary")
        raw = json.loads(args.daily_sections_json)
        sections = [(h, list(bullets)) for h, bullets in raw]
        res = append_daily_summary_styled(
            args.doc_id,
            args.daily_title,
            sections,
            client_id,
            client_secret,
            refresh_token,
        )
        print(json.dumps({"status": "ok", "replies": len(res.get("replies", []))}, ensure_ascii=False))
        return

    if args.text:
        if not args.doc_id:
            raise SystemExit("--doc-id is required when using --text")
        res = append_text(args.doc_id, args.text, client_id, client_secret, refresh_token)
        print(json.dumps({"status": "ok", "replies": len(res.get("replies", []))}, ensure_ascii=False))
        return

    raise SystemExit("Nothing to do. Use --create-doc, or --text, or --daily-title + --daily-sections-json")


if __name__ == "__main__":
    main()
