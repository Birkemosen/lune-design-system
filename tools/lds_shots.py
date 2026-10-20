#!/usr/bin/env python3
"""README-skærmbillede: én side i lyst og mørkt tema, delt diagonalt.

    python tools/lds_shots.py PREVIEW.html OUT.png [--width 1200] [--height 1430] [--scale 1.4]

Tager to skærmbilleder med headless Chrome (prefers-color-scheme light/dark),
lægger det mørke under en diagonal fra øverste højre til nederste venstre
hjørne og sætter mærkerne «Light» / «Dark» i hjørnerne. Siden får luft i
toppen til mærket (en midlertidig kopi ved siden af originalen), og animation
er slået fra, så intet fanges midt i en overgang. Kræver Google Chrome og Pillow.
"""
import argparse
import os
import shutil
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFont

CHROME_PATHS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    shutil.which("google-chrome") or "",
    shutil.which("chromium") or "",
]
FONT_PATHS = ["/System/Library/Fonts/SFNS.ttf", "/System/Library/Fonts/HelveticaNeue.ttc",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
# Mærkerne følger LDS' flader (lyst: raised på bg, mørkt: raised på bg).
LIGHT_PILL = ((233, 231, 227), (24, 24, 22))
DARK_PILL = ((42, 43, 46), (245, 245, 243))


def chrome():
    for p in CHROME_PATHS:
        if p and os.path.exists(p):
            return p
    raise SystemExit("Google Chrome blev ikke fundet")


TOP_PAD_PX = 48


def padded_copy(page):
    """Kopi ved siden af originalen (relative stier virker) med luft i toppen."""
    src = open(page, encoding="utf-8").read()
    style = (f"<style>html{{padding-top:{TOP_PAD_PX}px!important}}"
             "*,*::before,*::after{transition:none!important;animation:none!important}</style>")
    src = src.replace("</head>", style + "</head>", 1) if "</head>" in src else style + src
    tmp = os.path.join(os.path.dirname(os.path.abspath(page)), ".lds-shot.html")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(src)
    return tmp


def shot(page, out, width, height, scale, scheme):
    # preferredColorScheme: 0 = mørkt, 1 = lyst
    subprocess.run([chrome(), "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-prefers-reduced-motion",
                    f"--force-device-scale-factor={scale}", f"--window-size={width},{height}",
                    "--virtual-time-budget=5000", f"--blink-settings=preferredColorScheme={0 if scheme == 'dark' else 1}",
                    f"--screenshot={out}", "file://" + os.path.abspath(page)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def pill(img, text, corner, colors, scale):
    draw = ImageDraw.Draw(img)
    font = None
    for p in FONT_PATHS:
        if os.path.exists(p):
            font = ImageFont.truetype(p, round(17 * scale))
            break
    font = font or ImageFont.load_default()
    pad_x, pad_y, margin = round(13 * scale), round(8 * scale), round(14 * scale)
    box = draw.textbbox((0, 0), text, font=font)
    w, h = box[2] - box[0] + 2 * pad_x, box[3] - box[1] + 2 * pad_y
    x = margin if corner == "tl" else img.width - margin - w
    y = margin if corner == "tl" else img.height - margin - h
    draw.rounded_rectangle((x, y, x + w, y + h), radius=h // 2, fill=colors[0])
    draw.text((x + pad_x - box[0], y + pad_y - box[1]), text, font=font, fill=colors[1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("page")
    ap.add_argument("out")
    ap.add_argument("--width", type=int, default=1200)
    ap.add_argument("--height", type=int, default=1430)
    ap.add_argument("--scale", type=float, default=1.4)
    a = ap.parse_args()
    page = padded_copy(a.page)
    with tempfile.TemporaryDirectory() as tmp:
        light, dark = os.path.join(tmp, "light.png"), os.path.join(tmp, "dark.png")
        try:
            shot(page, light, a.width, a.height, a.scale, "light")
            shot(page, dark, a.width, a.height, a.scale, "dark")
        finally:
            os.remove(page)
        li, di = Image.open(light).convert("RGB"), Image.open(dark).convert("RGB")
        W, H = li.size
        mask = Image.new("L", (W, H), 0)
        ImageDraw.Draw(mask).polygon([(W, 0), (W, H), (0, H)], fill=255)
        out = Image.composite(di, li, mask)
        pill(out, "Light", "tl", LIGHT_PILL, a.scale)
        pill(out, "Dark", "br", DARK_PILL, a.scale)
        out.save(a.out, optimize=True)
    print(f"{a.out}: {W}×{H}")


if __name__ == "__main__":
    main()
