#!/usr/bin/env python3
"""
fetch_diff.py — 增量更新辅助脚本（缓存 + hash 对比）

重要：本脚本【不自己联网】。
拉取最新内容这一步由 Claude 在对话层用 web_fetch 完成（沙盒 curl 拉不到 mingdao/nocoly）。
本脚本负责：接收"已抓取的内容" → 与本地缓存 hash 对比 → 报告是否变化 → 更新缓存。

用法：
  # 1) 对比某 key 的新内容与缓存
  python fetch_diff.py compare <key> --content-file /tmp/fetched.txt
      输出 JSON: {"key":..., "changed": true/false, "old_hash":..., "new_hash":...}

  # 2) 提交（写入/更新缓存快照）
  python fetch_diff.py commit <key> --url <url> --content-file /tmp/fetched.txt

  # 3) 查看缓存状态
  python fetch_diff.py status [<key>]

缓存目录：与本脚本同级的 ../reference/source-cache/<key>.json
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import date

CACHE_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "reference", "source-cache"))


def _cache_path(key):
    return os.path.join(CACHE_DIR, f"{key}.json")


def _sha256(text):
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _read_content(args):
    if args.content_file:
        with open(args.content_file, "r", encoding="utf-8") as f:
            return f.read()
    return sys.stdin.read()


def cmd_compare(args):
    new = _read_content(args)
    new_hash = _sha256(new)
    p = _cache_path(args.key)
    old_hash = None
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            old_hash = json.load(f).get("hash")
    print(json.dumps({
        "key": args.key,
        "changed": old_hash != new_hash,
        "old_hash": old_hash,
        "new_hash": new_hash,
        "cached": old_hash is not None,
    }, ensure_ascii=False))


def cmd_commit(args):
    new = _read_content(args)
    os.makedirs(CACHE_DIR, exist_ok=True)
    rec = {
        "url": args.url or "",
        "hash": _sha256(new),
        "fetched_at": str(date.today()),
        "snapshot": new,
    }
    with open(_cache_path(args.key), "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=2)
    print(json.dumps({"key": args.key, "committed": True, "hash": rec["hash"], "fetched_at": rec["fetched_at"]}, ensure_ascii=False))


def cmd_status(args):
    if not os.path.isdir(CACHE_DIR):
        print(json.dumps({"cache_dir": CACHE_DIR, "exists": False, "entries": []}, ensure_ascii=False))
        return
    keys = [args.key] if args.key else sorted(
        f[:-5] for f in os.listdir(CACHE_DIR) if f.endswith(".json"))
    out = []
    for k in keys:
        p = _cache_path(k)
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                rec = json.load(f)
            out.append({"key": k, "url": rec.get("url"), "fetched_at": rec.get("fetched_at"),
                        "hash": rec.get("hash"), "snapshot_chars": len(rec.get("snapshot", ""))})
    print(json.dumps({"cache_dir": CACHE_DIR, "exists": True, "entries": out}, ensure_ascii=False, indent=2))


def main():
    ap = argparse.ArgumentParser(description="HAP Skill 增量更新缓存/对比辅助（不联网）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("compare"); c.add_argument("key"); c.add_argument("--content-file"); c.set_defaults(func=cmd_compare)
    c = sub.add_parser("commit"); c.add_argument("key"); c.add_argument("--url"); c.add_argument("--content-file"); c.set_defaults(func=cmd_commit)
    c = sub.add_parser("status"); c.add_argument("key", nargs="?"); c.set_defaults(func=cmd_status)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
