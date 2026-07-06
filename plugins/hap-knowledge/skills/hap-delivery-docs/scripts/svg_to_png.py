#!/usr/bin/env python3
"""
svg_to_png.py — 架构图 SVG 转 PNG

用法：
  python svg_to_png.py input.svg output.png [--scale 2.0]

依赖：cairosvg（pip install cairosvg --break-system-packages）
若 cairosvg 不可用，回退提示用 rsvg-convert / inkscape。
中文字体依赖系统 NotoSansCJK（环境已含 /usr/share/fonts/opentype/noto/）。
"""
import argparse
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--scale", type=float, default=2.0, help="输出缩放（默认2x，更清晰）")
    args = ap.parse_args()

    try:
        import cairosvg
    except ImportError:
        sys.stderr.write(
            "cairosvg 未安装。请执行：pip install cairosvg --break-system-packages\n"
            "或改用：rsvg-convert -o out.png in.svg / inkscape in.svg --export-filename=out.png\n")
        sys.exit(1)

    cairosvg.svg2png(url=args.input, write_to=args.output, scale=args.scale)
    print(f"OK: {args.input} -> {args.output} (scale={args.scale})")


if __name__ == "__main__":
    main()
