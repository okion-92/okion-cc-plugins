#!/usr/bin/env python3
"""
fetch_diff.py — 增量更新辅助脚本（缓存 + hash 对比）

重要：本脚本【不自己联网】。
拉取最新内容这一步由调用方使用当前可用的网页读取工具完成。
本脚本负责：接收"已抓取的内容" → 与本地缓存 hash 对比 → 报告是否变化 → 更新缓存。

用法：
  # 1) 对比某 key 的新内容与缓存
  python fetch_diff.py compare <key> --url <url> --content-file /tmp/fetched.txt
      输出 JSON: hash/URL/安装包是否变化，以及是否需要刷新对应章节

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
import re
import sys
from datetime import datetime, timezone

CACHE_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "reference", "source-cache"))

PACKAGE_URL_RE = re.compile(
    r"https://(?:pdpublic\.(?:mingdao|nocoly)\.com/private-deployment/offline/|"
    r"fastdl\.mongodb\.org/linux/|downloads\.mongodb\.com/compass/)"
    r"[A-Za-z0-9._/+%-]+",
    re.IGNORECASE,
)

VERSION_PATTERNS = {
    "mysql": re.compile(r"(?:mysql(?:-router|-shell)?)[-_](\d+\.\d+\.\d+)", re.IGNORECASE),
    "elasticsearch": re.compile(r"(?:elasticsearch(?:-analysis-ik)?)[-_](\d+\.\d+\.\d+)", re.IGNORECASE),
    "nginx": re.compile(r"nginx(?:-arm64)?[-_](\d+\.\d+\.\d+)", re.IGNORECASE),
    "mongodb": re.compile(r"mongodb[^\s/]*?[-_](\d+\.\d+\.\d+)", re.IGNORECASE),
    "redis": re.compile(r"redis[-_](\d+\.\d+\.\d+)", re.IGNORECASE),
    "kafka": re.compile(r"kafka(?:_[\d.]+)?[-_](\d+\.\d+\.\d+)", re.IGNORECASE),
    "prometheus": re.compile(r"prometheus[-_](\d+\.\d+\.\d+)", re.IGNORECASE),
    "grafana": re.compile(r"grafana[-_](\d+\.\d+\.\d+)", re.IGNORECASE),
    "docker": re.compile(r"docker[-_](\d+\.\d+\.\d+)", re.IGNORECASE),
    "kubernetes": re.compile(r"(?:kubernetes|kubeadm)[-_ :v]+(\d+\.\d+\.\d+)", re.IGNORECASE),
    "istio": re.compile(r"istio[-_ :]+(\d+\.\d+\.\d+)", re.IGNORECASE),
    "hap": re.compile(r"mingdaoyun-(?:hap|community):v?(\d+\.\d+\.\d+)", re.IGNORECASE),
    "file": re.compile(r"mingdaoyun-file[:/-]v?(\d+\.\d+\.\d+)", re.IGNORECASE),
    "minio": re.compile(r"RELEASE\.(\d{4}-\d{2}-\d{2}T[\d-]+Z)", re.IGNORECASE),
    "etcd": re.compile(r"etcd(?:-linux-(?:amd64|arm64))?[-_:]v?(\d+\.\d+\.\d+)", re.IGNORECASE),
    "milvus_operator": re.compile(r"milvus-operator(?::v?|(?:-linux-(?:amd64|arm64)-v?))(\d+\.\d+\.\d+)", re.IGNORECASE),
    "milvus": re.compile(r"milvus(?::v?|(?:-linux-(?:amd64|arm64)-v?))(\d+\.\d+\.\d+)", re.IGNORECASE),
    "hdp": re.compile(r"mingdaoyun-hdp(?::v?|(?:-linux-(?:amd64|arm64)-v?))(\d+\.\d+\.\d+)", re.IGNORECASE),
    "computinginstance": re.compile(r"mingdaoyun-computinginstance(?::v?|(?:-linux-(?:amd64|arm64)-v?))(\d+\.\d+\.\d+)", re.IGNORECASE),
    "alertmanager": re.compile(r"alertmanager[-_:]v?(\d+\.\d+\.\d+)", re.IGNORECASE),
    "prometheusalert": re.compile(r"prometheusalert[-_:]v?(\d+\.\d+\.\d+)", re.IGNORECASE),
    "kibana": re.compile(r"kibana[-_:]v?(\d+\.\d+\.\d+)", re.IGNORECASE),
    "victorialogs": re.compile(r"victoria-logs(?:-linux-(?:amd64|arm64))?[-_:]v?(\d+\.\d+\.\d+)", re.IGNORECASE),
    "promtail": re.compile(r"promtail(?:-linux-(?:amd64|arm64))?[-_:]v?(\d+\.\d+\.\d+)", re.IGNORECASE),
}


def _cache_path(key):
    return os.path.join(CACHE_DIR, f"{key}.json")


def _sha256(text):
    return "sha256:" + hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def _normalize_text(text):
    """清理 Windows/PowerShell 管道偶发产生的孤立代理字符。"""
    return text.encode("utf-8", errors="replace").decode("utf-8")


def _read_content(args):
    if args.content_file:
        with open(args.content_file, "r", encoding="utf-8") as f:
            return _normalize_text(f.read())
    return _normalize_text(sys.stdin.read())


def _read_cache(key):
    p = _cache_path(key)
    if not os.path.exists(p):
        return {}
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def _extract_metadata(text):
    """从已拉取页面中做轻量提取。

    只记录页面明示出现的安装包和版本，不猜测“最新版”。
    """
    package_urls = sorted(set(PACKAGE_URL_RE.findall(text)))
    searchable = text
    versions = {}
    for component, pattern in VERSION_PATTERNS.items():
        found = sorted(set(pattern.findall(searchable)))
        if found:
            versions[component] = found
    return {"versions": versions, "package_urls": package_urls}


def cmd_compare(args):
    new = _read_content(args)
    new_hash = _sha256(new)
    old = _read_cache(args.key)
    old_hash = old.get("hash")
    new_meta = _extract_metadata(new)
    old_packages = sorted(old.get("package_urls") or _extract_metadata(old.get("snapshot", ""))["package_urls"])
    new_packages = new_meta["package_urls"]
    requested_url = args.url or old.get("url") or ""
    url_changed = bool(args.url and old.get("url") and args.url.rstrip("/") != old.get("url", "").rstrip("/"))
    content_changed = old_hash != new_hash
    packages_changed = old_packages != new_packages
    print(json.dumps({
        "key": args.key,
        "changed": content_changed,
        "content_changed": content_changed,
        "url_changed": url_changed,
        "packages_changed": packages_changed,
        "requires_section_refresh": content_changed or url_changed or packages_changed,
        "url": requested_url,
        "old_url": old.get("url"),
        "old_hash": old_hash,
        "new_hash": new_hash,
        "cached": old_hash is not None,
        "old_package_urls": old_packages,
        "new_package_urls": new_packages,
        "versions": new_meta["versions"],
    }, ensure_ascii=False))


def cmd_commit(args):
    new = _read_content(args)
    os.makedirs(CACHE_DIR, exist_ok=True)
    meta = _extract_metadata(new)
    rec = {
        "url": args.url or "",
        "hash": _sha256(new),
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "versions": meta["versions"],
        "package_urls": meta["package_urls"],
        "snapshot": new,
    }
    with open(_cache_path(args.key), "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=2)
    print(json.dumps({
        "key": args.key,
        "committed": True,
        "hash": rec["hash"],
        "fetched_at": rec["fetched_at"],
        "versions": rec["versions"],
        "package_urls": rec["package_urls"],
    }, ensure_ascii=False))


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
            meta = _extract_metadata(rec.get("snapshot", ""))
            out.append({"key": k, "url": rec.get("url"), "fetched_at": rec.get("fetched_at"),
                        "hash": rec.get("hash"), "versions": rec.get("versions") or meta["versions"],
                        "package_urls": rec.get("package_urls") or meta["package_urls"],
                        "snapshot_chars": len(rec.get("snapshot", ""))})
    print(json.dumps({"cache_dir": CACHE_DIR, "exists": True, "entries": out}, ensure_ascii=False, indent=2))


def main():
    ap = argparse.ArgumentParser(description="HAP Skill 增量更新缓存/对比辅助（不联网）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("compare"); c.add_argument("key"); c.add_argument("--url"); c.add_argument("--content-file"); c.set_defaults(func=cmd_compare)
    c = sub.add_parser("commit"); c.add_argument("key"); c.add_argument("--url"); c.add_argument("--content-file"); c.set_defaults(func=cmd_commit)
    c = sub.add_parser("status"); c.add_argument("key", nargs="?"); c.set_defaults(func=cmd_status)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
