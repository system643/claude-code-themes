"""Builds docs/banner.png (README header) and docs/social-preview.png (GitHub social card)
from the themes' wallpapers and pixel art. Deterministic, no network.

Usage: python scripts/art/social.py
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
THEMES = ROOT / "plugin" / "themes"
DOCS = ROOT / "docs"
URL = "github.com/sytem643/claude-code-themes"

NIGHT = (14, 12, 22)
INK = (246, 242, 236)
SOFT = (190, 184, 206)
DIM = (128, 122, 150)
# The app icon's gradient (app/icon.svg).
FLAME = [(0.0, (255, 154, 90)), (0.55, (217, 72, 59)), (1.0, (110, 59, 255))]

# Where each wallpaper's subject sits horizontally (0 = left, 1 = right).
FOCUS = {"paris": 0.27, "tokyo": 0.33, "dracula": 0.72, "abyss": 0.75, "volcano": 0.48,
         "synthwave": 0.53, "sakura": 0.6, "sydney": 0.6, "rio": 0.55, "london": 0.62}


# ---------- Tools ----------

FONT_DIRS = [Path("C:/Windows/Fonts"), Path("/System/Library/Fonts"), Path("/Library/Fonts"),
             Path.home() / "Library/Fonts", Path("/usr/share/fonts"), Path.home() / ".fonts"]
_found = {}


def font(names, size):
    """The first font of `names` found on this machine, else Pillow's default."""
    for name in names:
        if name not in _found:
            _found[name] = next((p for d in FONT_DIRS if d.exists() for p in d.rglob(name)), None)
        if _found[name]:
            return ImageFont.truetype(str(_found[name]), size)
    return ImageFont.load_default(size)


def bold(size):
    return font(["seguibl.ttf", "segoeuib.ttf", "SF-Pro-Display-Bold.otf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf", "Arial Bold.ttf"], size)


def regular(size):
    return font(["segoeui.ttf", "SF-Pro-Text-Regular.otf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf", "Arial.ttf"], size)


def semibold(size):
    return font(["seguisb.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf", "Arial Bold.ttf"], size)


def mono(size):
    return font(["CascadiaMono.ttf", "consola.ttf", "Menlo.ttc", "DejaVuSansMono.ttf", "LiberationMono-Regular.ttf"], size)


def hex_rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def mix(a, b, t):
    return tuple(int(round(x * (1 - t) + y * t)) for x, y in zip(a, b))


def ramp(t, stops=FLAME):
    """Color of a gradient at t (numpy array), as an (..., 3) array."""
    t = np.clip(t, 0, 1)
    out = np.zeros(t.shape + (3,))
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        k = np.clip((t - t0) / (t1 - t0), 0, 1)[..., None]
        inside = ((t >= t0) & (t <= t1))[..., None]
        out = np.where(inside, np.asarray(c0) * (1 - k) + np.asarray(c1) * k, out)
    return out


def rounded_mask(size, radius, supersample=4):
    w, h = size
    mask = Image.new("L", (w * supersample, h * supersample), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w * supersample - 1, h * supersample - 1], radius * supersample, fill=255)
    return mask.resize(size, Image.LANCZOS)


def glow(canvas, cx, cy, rx, ry, color, strength):
    """A soft elliptic light added to a float canvas."""
    h, w = canvas.shape[:2]
    y, x = np.ogrid[:h, :w]
    d = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
    canvas += np.asarray(color, float) * np.exp(-d)[..., None] * strength


def backdrop(width, height, unit, seed):
    """Night background: a faint vertical gradient, two glows and pixel stars."""
    t = np.linspace(0, 1, height)[:, None, None]
    canvas = np.asarray(NIGHT, float) * (1 - t) + np.asarray((9, 8, 14), float) * t * np.ones((height, width, 3))
    glow(canvas, width * 0.05, height * 0.2, width * 0.35, height * 0.9, (255, 120, 70), 0.10)
    glow(canvas, width * 0.62, height * 1.0, width * 0.45, height * 0.7, (110, 59, 255), 0.16)
    local = np.random.default_rng(seed)
    for _ in range(int(width * height / (unit * unit * 900))):
        x, y = local.integers(0, width), local.integers(0, height)
        size = unit * int(local.choice([1, 1, 1, 2]))
        canvas[y : y + size, x : x + size] += local.uniform(18, 60)
    return canvas


def to_image(canvas):
    return Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8))


# ---------- Themes ----------

def theme(theme_id):
    return json.loads((THEMES / theme_id / "theme.json").read_text(encoding="utf-8"))


def theme_ids():
    return sorted(p.name for p in THEMES.iterdir() if (p / "theme.json").exists())


def sprite(data, scale, frame=0):
    """A theme's pixel art as RGBA, each pixel a crisp `scale` × `scale` block."""
    art = data["pixelArt"]
    rows = art["frames"][frame]
    small = Image.new("RGBA", (max(len(r) for r in rows), len(rows)), (0, 0, 0, 0))
    for y, row in enumerate(rows):
        for x, key in enumerate(row):
            if key in art["palette"]:
                small.putpixel((x, y), hex_rgb(art["palette"][key]) + (255,))
    return small.resize((small.width * scale, small.height * scale), Image.NEAREST)


def cover(picture, width, height, focus=0.6):
    """Crops `picture` to fill width × height, centred on `focus` horizontally."""
    ratio = max(width / picture.width, height / picture.height)
    scaled = picture.resize((round(picture.width * ratio), round(picture.height * ratio)), Image.LANCZOS)
    left = int(np.clip(focus * scaled.width - width / 2, 0, scaled.width - width))
    top = (scaled.height - height) // 2
    return scaled.crop((left, top, left + width, top + height))


def card(theme_id, width, height, scale, unit, label=None, soften=0):
    """A wallpaper tile: the photo, a shade in the theme's background color,
    the pixel art at the bottom and an accent bar."""
    data = theme(theme_id)
    background = hex_rgb(data["terminal"]["background"])
    accent = hex_rgb(data["colors"]["accent"])
    wallpaper = Image.open(THEMES / theme_id / "assets" / "wallpaper.jpg").convert("RGB")
    picture = cover(wallpaper, width, height, FOCUS.get(theme_id, 0.6))
    if soften:  # Fewer fine details, a lighter PNG.
        picture = picture.filter(ImageFilter.GaussianBlur(soften))
    canvas = np.asarray(picture, float)
    t = np.clip((np.linspace(0, 1, height) - 0.35) / 0.5, 0, 1)[:, None, None] ** 1.3
    canvas = canvas * (1 - t * 0.9) + np.asarray(background, float) * t * 0.9
    tile = to_image(canvas)
    art = sprite(data, scale)
    bottom = height - 4 * unit - (14 * unit if label else 6 * unit)
    tile.paste(art, ((width - art.width) // 2, bottom - art.height), art)
    draw = ImageDraw.Draw(tile)
    if label:
        text = data["name"]
        size = 13 * unit
        face = semibold(size)
        while draw.textlength(text, font=face) > width - 12 * unit:
            size -= unit
            face = semibold(size)
        draw.text((width // 2, height - 11 * unit), text, font=face, fill=INK, anchor="mm")
    draw.rectangle([0, height - 3 * unit, width, height], fill=accent)
    return tile


def place(canvas_image, tile, x, y, radius, border=None):
    canvas_image.paste(tile, (x, y), rounded_mask(tile.size, radius))
    if border:
        ImageDraw.Draw(canvas_image).rounded_rectangle([x, y, x + tile.width - 1, y + tile.height - 1], radius, outline=border, width=1)


# ---------- Brand mark (app/icon.svg) ----------

def svg_path(d, steps=24):
    """Points of an SVG path made of M, L, C, S and Z commands."""
    tokens = re.findall(r"[A-Za-z]|-?(?:\d+\.?\d*|\.\d+)", d)
    points, i, cmd = [], 0, None
    x = y = 0.0
    ctrl = None

    def num():
        nonlocal i
        i += 1
        return float(tokens[i - 1])

    def curve(p0, p1, p2, p3):
        for k in range(1, steps + 1):
            t = k / steps
            points.append(tuple((1 - t) ** 3 * a + 3 * (1 - t) ** 2 * t * b + 3 * (1 - t) * t * t * c + t ** 3 * e
                                for a, b, c, e in zip(p0, p1, p2, p3)))

    while i < len(tokens):
        if tokens[i].isalpha():
            cmd = tokens[i]
            i += 1
        if cmd in "Zz":
            break
        ox, oy = (x, y) if cmd.islower() else (0.0, 0.0)
        if cmd in "Mm":
            x, y = num() + ox, num() + oy
            points.append((x, y))
            cmd = "l" if cmd == "m" else "L"
        elif cmd in "Ll":
            x, y = num() + ox, num() + oy
            points.append((x, y))
        elif cmd in "Cc":
            c1, c2, end = (num() + ox, num() + oy), (num() + ox, num() + oy), (num() + ox, num() + oy)
            curve((x, y), c1, c2, end)
            ctrl, (x, y) = c2, end
        elif cmd in "Ss":
            c1 = (2 * x - ctrl[0], 2 * y - ctrl[1]) if ctrl else (x, y)
            c2, end = (num() + ox, num() + oy), (num() + ox, num() + oy)
            curve((x, y), c1, c2, end)
            ctrl, (x, y) = c2, end
    return points


def brand_mark(size, supersample=4):
    """The app icon: a flame on a gradient rounded square (RGBA)."""
    big = size * supersample
    y, x = np.mgrid[:big, :big] / big
    canvas = ramp((x + y) / 2)
    canvas += 255 * np.clip(0.28 * (1 - y / 0.5), 0, None)[..., None]
    tile = to_image(canvas).convert("RGBA")
    square = Image.new("L", (big, big), 0)
    unit = big / 1024
    ImageDraw.Draw(square).rounded_rectangle([64 * unit, 64 * unit, 960 * unit, 960 * unit], 200 * unit, fill=255)
    tile.putalpha(square)
    svg = (ROOT / "app" / "icon.svg").read_text(encoding="utf-8")
    flame = re.search(r'<path fill="#fff" d="([^"]+)"', svg)
    if flame:
        ImageDraw.Draw(tile).polygon([(px * unit, py * unit) for px, py in svg_path(flame.group(1))], fill=(255, 255, 255, 255))
    return tile.resize((size, size), Image.LANCZOS)


def gradient_bar(width, height):
    t = np.linspace(0, 1, width)[None, :] * np.ones((height, 1))
    return to_image(ramp(t))


# ---------- Banner ----------

BANNER_THEMES = ["synthwave", "dracula", "paris", "tokyo", "abyss", "gruvbox", "sydney", "sakura"]


def banner(unit=2):
    """1280 × 320 at `unit` = 1; the README shows it at most ~1000 px wide."""
    width, height = 1280 * unit, 320 * unit
    image = to_image(backdrop(width, height, unit, seed=7))

    # Theme cards, a skyline of different heights, bottoms aligned.
    card_w, gap, count = 70 * unit, 9 * unit, len(BANNER_THEMES)
    right = width - 40 * unit
    left = right - count * card_w - (count - 1) * gap
    base = height - 40 * unit
    heights = [188, 228, 204, 244, 216, 236, 196, 222]
    for i, theme_id in enumerate(BANNER_THEMES):
        h = heights[i] * unit
        tile = card(theme_id, card_w, h, 3 * unit, unit, soften=unit * 0.6)
        place(image, tile, left + i * (card_w + gap), base - h, 10 * unit)
    draw = ImageDraw.Draw(image)

    # Mark, title, tagline.
    x0 = 56 * unit
    mark = brand_mark(64 * unit)
    image.paste(mark, (x0, 70 * unit), mark)
    title = bold(84 * unit)
    draw.text((x0 + 80 * unit, 102 * unit), "Ambiance", font=title, fill=INK, anchor="lm")
    draw.text((x0, 172 * unit), "Themes for your Claude Code sessions", font=regular(27 * unit), fill=SOFT, anchor="lm")
    image.paste(gradient_bar(56 * unit, 4 * unit), (x0, 200 * unit))
    features = f"{len(theme_ids())} themes · pixel art · wallpapers · live shaders"
    draw.text((x0, 238 * unit), features, font=mono(17 * unit), fill=mix(DIM, SOFT, 0.4), anchor="lm")
    return image


# ---------- Social preview ----------

MOSAIC = [
    ["tokyo", "dracula", "sakura", "orbit"],
    ["synthwave", "paris", "catppuccin", "christmas"],
    ["abyss", "gruvbox", "new-york", "volcano"],
]


def social_preview():
    """1280 × 640: the text stays inside a 56 px margin, only the mosaic bleeds."""
    width, height, unit = 1280, 640, 1
    image = to_image(backdrop(width, height, 2, seed=11))

    # Mosaic: three staggered columns bleeding off the top and bottom edges.
    tile_w, tile_h, gap = 188, 172, 14
    left = width - 40 - 3 * tile_w - 2 * gap
    for c, column in enumerate(MOSAIC):
        # Partial tiles show either their pixel art (top) or only photo (bottom).
        offset = [-102, 20, -102][c]
        for r, theme_id in enumerate(column):
            y = offset + r * (tile_h + gap)
            tile = card(theme_id, tile_w, tile_h, 4, unit, label=True)
            place(image, tile, left + c * (tile_w + gap), y, 14)
    fade = np.asarray(image, float)
    x = np.arange(width)[None, :, None]
    t = np.clip((x - left + 10) / 90, 0, 1)
    fade = fade * t + np.asarray(NIGHT, float) * (1 - t)
    image = to_image(fade)
    draw = ImageDraw.Draw(image)

    x0 = 72
    mark = brand_mark(84)
    image.paste(mark, (x0 - 6, 84), mark)
    draw.text((x0, 268), "Ambiance", font=bold(112), fill=INK, anchor="ls")
    draw.text((x0, 326), "Themes for your", font=regular(38), fill=SOFT, anchor="ls")
    draw.text((x0, 372), "Claude Code sessions", font=regular(38), fill=SOFT, anchor="ls")
    image.paste(gradient_bar(72, 5), (x0, 398))

    # One swatch per theme, in its accent color.
    ids = theme_ids()
    size, step = 9, 12
    for i, theme_id in enumerate(ids):
        accent = hex_rgb(theme(theme_id)["colors"]["accent"])
        sx = x0 + (i % 17) * step
        sy = 436 + (i // 17) * step
        draw.rounded_rectangle([sx, sy, sx + size, sy + size], 2, fill=accent)
    draw.text((x0 + 17 * step + 14, 442), f"{len(ids)} themes · plugin + desktop app", font=mono(17), fill=DIM, anchor="lm")

    draw.text((x0, 584), URL, font=mono(19), fill=DIM, anchor="ls")
    return image


def main():
    DOCS.mkdir(exist_ok=True)
    banner().save(DOCS / "banner.png", optimize=True)
    social_preview().save(DOCS / "social-preview.png", optimize=True)
    for name in ("banner.png", "social-preview.png"):
        path = DOCS / name
        print(path, Image.open(path).size, path.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    sys.exit(main())
