#!/usr/bin/env python3
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib import parse, request

API = "https://api.twitter.com/2/tweets/search/recent"


def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def x_recent_search(token, query, max_results=50):
    params = {
        "query": query,
        "max_results": str(max(10, min(max_results, 100))),
        "tweet.fields": "created_at,public_metrics,author_id",
        "expansions": "author_id",
        "user.fields": "username,name,verified,public_metrics",
        "sort_order": "recency",
    }
    url = API + "?" + parse.urlencode(params)
    req = request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with request.urlopen(req, timeout=20) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body)


def build_query(accounts, keywords):
    acct = " OR ".join([f"from:{a.lstrip('@')}" for a in accounts[:40]])
    kw = " OR ".join([f'"{k}"' if " " in k else k for k in keywords[:25]])
    base = f"(({acct}) OR ({kw})) -is:retweet -is:reply"
    return base


def fmt_item(tw, user_map, account_tags=None):
    u = user_map.get(tw.get("author_id"), {})
    username = u.get("username", "unknown")
    text = " ".join((tw.get("text") or "").replace("\n", " ").split())
    text = text[:220] + ("…" if len(text) > 220 else "")
    created = tw.get("created_at", "")
    m = tw.get("public_metrics", {})
    likes = m.get("like_count", 0)
    rts = m.get("retweet_count", 0)
    tag = (account_tags or {}).get(username, "未分类")
    return {
        "id": tw.get("id"),
        "username": username,
        "tag": tag,
        "created_at": created,
        "text": text,
        "likes": likes,
        "retweets": rts,
        "url": f"https://x.com/{username}/status/{tw.get('id')}"
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["breaking", "digest"], default="breaking")
    p.add_argument("--config", default="/home/ubuntu/.openclaw/workspace/myrepo/x_monitor_config.json")
    p.add_argument("--state", default="/home/ubuntu/.openclaw/workspace/myrepo/x_monitor_state.json")
    p.add_argument("--token-file", default="/home/ubuntu/.openclaw/credentials/x_bearer_token.txt")
    args = p.parse_args()

    token = os.environ.get("X_BEARER_TOKEN")
    if not token:
        try:
            token = Path(args.token_file).read_text(encoding="utf-8").strip()
        except Exception:
            pass
    if token:
        token = parse.unquote(token.strip())
    if not token:
        print("NO_REPLY")
        return 0

    cfg = load_json(args.config, {"accounts": [], "keywords": []})
    state = load_json(args.state, {"seen": {}, "lastDigest": 0})

    query = build_query(cfg.get("accounts", []), cfg.get("keywords", []))
    try:
        data = x_recent_search(token, query, 60 if args.mode == "digest" else 30)
    except Exception:
        print("NO_REPLY")
        return 0

    users = {u.get("id"): u for u in data.get("includes", {}).get("users", [])}
    tweets = [fmt_item(t, users, cfg.get("account_tags", {})) for t in data.get("data", [])]

    new_items = []
    now = int(time.time())
    for t in tweets:
        tid = t["id"]
        if tid and tid not in state["seen"]:
            state["seen"][tid] = now
            new_items.append(t)

    # cleanup seen > 3 days
    cutoff = now - 3 * 86400
    state["seen"] = {k: v for k, v in state["seen"].items() if v >= cutoff}
    save_json(args.state, state)

    if args.mode == "breaking":
        if not new_items:
            print("NO_REPLY")
            return 0
        top = sorted(new_items, key=lambda x: (x["likes"] + x["retweets"]), reverse=True)[:3]
        lines = ["【X Breaking】"]
        for i, t in enumerate(top, 1):
            lines.append(f"{i}) [{t['tag']}][@{t['username']}] {t['text']}")
            lines.append(f"   {t['url']}")
        print("\n".join(lines))
        return 0

    # digest
    if not tweets:
        print("NO_REPLY")
        return 0
    top = sorted(tweets, key=lambda x: (x["likes"] + x["retweets"]), reverse=True)[:8]
    lines = ["【X Market Take（1h）】", "按影响力筛选的高热观点/新闻："]
    for i, t in enumerate(top, 1):
        lines.append(f"{i}) [{t['tag']}][@{t['username']}] {t['text']}")
    lines.append("提示：以上为信息摘要，建议结合主流媒体与官方公告交叉验证。")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
