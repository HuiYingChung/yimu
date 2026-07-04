"""Generate the app icon (concept A: 譯 on a subtitle bar).

Draws a 256px master with Pillow and exports icon.ico (16-256px)
plus icon-256.png for docs. Rerun after design tweaks:
    python assets/make_icon.py
"""

import os

from PIL import Image, ImageDraw, ImageFont

TILE = "#16181d"
TEXT = "#ffffff"
ACCENT = "#ffd644"
FONT_PATH = r"C:\Windows\Fonts\msjhbd.ttc"  # Microsoft JhengHei Bold

HERE = os.path.dirname(os.path.abspath(__file__))


def draw_master(size: int = 256) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    radius = round(size * 0.22)
    d.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=TILE)

    font = ImageFont.truetype(FONT_PATH, round(size * 0.56))
    # center the glyph optically: slightly above center to leave room
    # for the subtitle bar below
    left, top, right, bottom = d.textbbox((0, 0), "譯", font=font)
    glyph_w, glyph_h = right - left, bottom - top
    x = (size - glyph_w) / 2 - left
    y = size * 0.42 - glyph_h / 2 - top
    d.text((x, y), "譯", font=font, fill=TEXT)

    bar_w, bar_h = size * 0.5, size * 0.07
    bar_y = size * 0.78
    d.rounded_rectangle(
        ((size - bar_w) / 2, bar_y, (size + bar_w) / 2, bar_y + bar_h),
        radius=bar_h / 2, fill=ACCENT,
    )
    return img


def main() -> None:
    master = draw_master(256)
    master.save(os.path.join(HERE, "icon-256.png"))
    master.save(
        os.path.join(HERE, "icon.ico"),
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (256, 256)],
    )
    print("wrote assets/icon.ico and assets/icon-256.png")


if __name__ == "__main__":
    main()
