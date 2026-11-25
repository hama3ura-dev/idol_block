"""ブロック崩しのファビコン（ブラウザのタブに出る小さなアイコン）を作る。
使い方: python make_favicon.py <出力ファイル> [<確認用PNG>]
必要なもの: Python 3 だけ（追加のライブラリは不要）

  ・紺色の角丸の四角に、色付きのブロック・白いボール・白いパドルを描いた絵です。
  ・16 / 32 / 48 / 256 ピクセルの4サイズを1つの .ico にまとめます。
  ・小さいサイズでもつぶれにくいように、サイズごとに描き直しています。
"""
import struct
import sys
import zlib

BG = (11, 16, 32)          # 背景（ゲーム画面と同じ紺色）
BORDER = (59, 130, 246)    # 背景のふち（青）
ROW_COLORS = [(239, 68, 68), (249, 115, 22), (234, 179, 8), (34, 197, 94)]  # ゲームのブロックと同じ色
WHITE = (243, 244, 246)


def rounded_rect(x, y, x0, y0, x1, y1, r):
    """点 (x, y) が角丸四角形の中にあるか"""
    if not (x0 <= x <= x1 and y0 <= y <= y1):
        return False
    cx = min(max(x, x0 + r), x1 - r)
    cy = min(max(y, y0 + r), y1 - r)
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def shapes(size):
    """(判定関数, 色) のリスト。後ろのものほど上に描かれる。座標は 0〜1"""
    small = size <= 16
    rows = 3 if small else 4
    cols = 3 if small else 4
    gap = 0.06 if small else 0.035
    left, right, top = 0.12, 0.88, 0.13
    bh = 0.10 if small else 0.075
    bw = (right - left - gap * (cols - 1)) / cols
    out = []
    # 背景（ふち → 中身）
    out.append((lambda x, y: rounded_rect(x, y, 0, 0, 1, 1, 0.2), BORDER))
    edge = 0.0 if small else 0.035
    out.append((lambda x, y, e=edge: rounded_rect(x, y, e, e, 1 - e, 1 - e, 0.2 - e), BG))
    # ブロック（1個だけ壊れて欠けている）
    missing = (rows - 1, cols // 2)
    for r in range(rows):
        for c in range(cols):
            if (r, c) == missing:
                continue
            x0 = left + c * (bw + gap)
            y0 = top + r * (bh + gap)
            out.append((lambda x, y, x0=x0, y0=y0: rounded_rect(x, y, x0, y0, x0 + bw, y0 + bh, 0.015),
                        ROW_COLORS[r % len(ROW_COLORS)]))
    # ボール
    br = 0.085 if small else 0.07
    bx, by = 0.60, 0.66
    out.append((lambda x, y: (x - bx) ** 2 + (y - by) ** 2 <= br * br, WHITE))
    # パドル
    out.append((lambda x, y: rounded_rect(x, y, 0.27, 0.81, 0.73, 0.89 if small else 0.87, 0.035), WHITE))
    return out


def render(size, ss=6):
    """size×size の RGBA 画素を作る（ss×ss のスーパーサンプリングでなめらかに）"""
    shp = shapes(size)
    px = bytearray()
    for j in range(size):
        px.append(0)  # PNG の各行の先頭はフィルター番号
        for i in range(size):
            acc = [0, 0, 0, 0]
            for sj in range(ss):
                for si in range(ss):
                    x = (i + (si + 0.5) / ss) / size
                    y = (j + (sj + 0.5) / ss) / size
                    col = None
                    for test, c in shp:
                        if test(x, y):
                            col = c
                    if col:
                        acc[0] += col[0]; acc[1] += col[1]; acc[2] += col[2]; acc[3] += 255
            n = ss * ss
            a = acc[3] / n
            if a > 0:
                # 色は不透明な部分だけで平均する（角のふちが黒ずまないように）
                hits = acc[3] / 255
                px += bytes([min(255, round(acc[0] / hits)),
                             min(255, round(acc[1] / hits)),
                             min(255, round(acc[2] / hits)),
                             round(a)])
            else:
                px += b"\0\0\0\0"
    return bytes(px)


def png(size, raw):
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)  # 8bit RGBA
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


def ico(images):
    """images = [(size, png_bytes)]。PNG をそのまま入れた .ico（今のブラウザはすべて対応）"""
    head = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries, data = b"", b""
    for size, p in images:
        s = 0 if size >= 256 else size  # 256 は 0 と書く決まり
        entries += struct.pack("<BBBBHHII", s, s, 0, 0, 1, 32, len(p), offset + len(data))
        data += p
    return head + entries + data


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "favicon.ico"
    images = []
    for size in (16, 32, 48, 256):
        images.append((size, png(size, render(size, ss=6 if size <= 48 else 3))))
        print(f"{size}x{size}: {len(images[-1][1])} bytes")
    with open(out, "wb") as f:
        f.write(ico(images))
    print(f"{out}: saved")
    if len(sys.argv) > 2:  # 確認用に 256 の PNG も保存
        with open(sys.argv[2], "wb") as f:
            f.write(images[-1][1])


if __name__ == "__main__":
    main()
