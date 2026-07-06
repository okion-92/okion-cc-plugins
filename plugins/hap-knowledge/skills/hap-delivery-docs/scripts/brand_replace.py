#!/usr/bin/env python3
"""
brand_replace.py — mingdao ↔ nocoly 域名替换

规则（见 reference/brand-rules.md）：子域前缀保留，主域 mingdao.com → nocoly.com。
覆盖 docs-pd / docs-pdop / pdpublic 等所有 *.mingdao.com。
默认【不替换】第三方/CDN 域名 mingdaocloud.com 与阿里云镜像 registry.cn-hangzhou.aliyuncs.com。

用法：
  # 文本替换（stdin → stdout）
  echo "https://docs-pdop.mingdao.com/x" | python brand_replace.py --to nocoly
  # 文件就地替换
  python brand_replace.py --to nocoly --file some.txt --inplace
  # 反向（nocoly → mingdao）
  python brand_replace.py --to mingdao --file some.txt --inplace

注意：docx/pdf 等二进制文档不要直接跑本脚本；先 unpack 出 XML/文本再处理，
或由 Claude 在重组内容时按规则替换。本脚本主要用于纯文本/已解包 XML。
"""
import argparse
import re
import sys

# 仅替换 *.mingdao.com 主域；保留子域前缀。排除 mingdaocloud.com。
MINGDAO_RE = re.compile(r"(?<![\w.])([a-z0-9-]+)\.mingdao\.com", re.IGNORECASE)
NOCOLY_RE = re.compile(r"(?<![\w.])([a-z0-9-]+)\.nocoly\.com", re.IGNORECASE)


def to_nocoly(text):
    # 不能误伤 mingdaocloud.com：正则锚定 .mingdao.com，mingdaocloud.com 不匹配（因为是 mingdaocloud 而非 *.mingdao）
    return MINGDAO_RE.sub(lambda m: f"{m.group(1)}.nocoly.com", text)


def to_mingdao(text):
    return NOCOLY_RE.sub(lambda m: f"{m.group(1)}.mingdao.com", text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--to", choices=["nocoly", "mingdao"], required=True)
    ap.add_argument("--file")
    ap.add_argument("--inplace", action="store_true")
    args = ap.parse_args()

    fn = to_nocoly if args.to == "nocoly" else to_mingdao

    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            text = f.read()
        out = fn(text)
        if args.inplace:
            with open(args.file, "w", encoding="utf-8") as f:
                f.write(out)
            # 统计替换数
            n = len(MINGDAO_RE.findall(text)) if args.to == "nocoly" else len(NOCOLY_RE.findall(text))
            sys.stderr.write(f"replaced {n} domain(s) in {args.file}\n")
        else:
            sys.stdout.write(out)
    else:
        sys.stdout.write(fn(sys.stdin.read()))


if __name__ == "__main__":
    main()
