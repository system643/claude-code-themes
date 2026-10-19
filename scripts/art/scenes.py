"""Procedural wallpaper scenes for the bundled themes (2560 × 1440, original art).

The subject sits on the right; `readable()` keeps the left and the bottom dark
so the terminal text and Claude Code's banner stay legible.
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import paint as p
from paint import H, W


def grid_xy():
    return np.mgrid[:H, :W]


def draw_on(canvas, fn):
    image = p.to_image(canvas)
    fn(ImageDraw.Draw(image))
    canvas[:] = p.to_canvas(image)


# ---------- Night skies ----------

def dracula():
    canvas = p.vertical((20, 14, 34), (52, 30, 70), 1.2)
    p.stars(canvas, 900, H * 0.7, seed=101, tint=(230, 210, 255))
    p.moon(canvas, 1960, 330, 150, color=(240, 230, 250), halo=(190, 120, 255))
    cliff = p.ridge_mask(1020, 120, 3, 102)
    p.blend(canvas, (16, 10, 24), cliff)

    def castle(d):
        fill = (12, 8, 18)
        d.polygon([(1600, 1040), (1660, 760), (2260, 760), (2330, 1040)], fill=fill)
        for x, w, h in ((1640, 70, 420), (1820, 90, 520), (2020, 80, 470), (2200, 70, 380)):
            d.rectangle([x, 1040 - h, x + w, 1040], fill=fill)
            d.polygon([(x - 12, 1040 - h), (x + w / 2, 1040 - h - 110), (x + w + 12, 1040 - h)], fill=fill)
        for x, y in ((1850, 640), (1860, 720), (2045, 700), (1665, 760), (2225, 800)):
            d.rectangle([x, y, x + 14, y + 26], fill=(255, 196, 108))

    draw_on(canvas, castle)
    for x, y in ((1850, 653), (2052, 713), (1672, 773)):
        p.glow(canvas, x, y, 40, (255, 150, 80), 0.4)

    def bats(d):
        rng = np.random.default_rng(103)
        for _ in range(9):
            x, y, s = rng.uniform(1500, 2400), rng.uniform(200, 560), rng.uniform(10, 22)
            d.polygon([(x, y), (x - s, y - s * 0.6), (x - s * 1.6, y + s * 0.1), (x - s * 0.5, y + s * 0.15), (x, y + s * 0.4),
                       (x + s * 0.5, y + s * 0.15), (x + s * 1.6, y + s * 0.1), (x + s, y - s * 0.6)], fill=(10, 6, 16))

    draw_on(canvas, bats)
    p.readable(canvas)
    return p.finish(canvas)


def catppuccin():
    canvas = p.vertical((30, 30, 46), (69, 55, 90), 1.1)
    y, x = grid_xy()
    p.stars(canvas, 600, H * 0.6, seed=111, tint=(245, 224, 220))
    p.moon(canvas, 1900, 340, 110, color=(249, 226, 175), halo=(245, 194, 231), shadow=tuple(canvas[340, 2100].astype(int)))
    for cx, cy, r in ((1500, 560, 160), (1720, 520, 200), (2050, 600, 180), (2320, 540, 150)):
        p.blend(canvas, (88, 91, 112), np.exp(-p.radial(cx, cy, r) ** 4) * 0.28)
    for base, amp, seed, color in ((980, 90, 112, (69, 71, 90)), (1080, 70, 113, (49, 50, 68))):
        p.blend(canvas, color, p.ridge_mask(base, amp, 2.5, seed))

    def kitty(d):
        fill = (24, 24, 37)
        cx, base = 1880, 1000
        d.ellipse([cx - 70, base - 150, cx + 70, base], fill=fill)
        d.ellipse([cx - 52, base - 240, cx + 52, base - 130], fill=fill)
        d.polygon([(cx - 48, base - 200), (cx - 40, base - 275), (cx - 8, base - 230)], fill=fill)
        d.polygon([(cx + 48, base - 200), (cx + 40, base - 275), (cx + 8, base - 230)], fill=fill)
        d.line([(cx + 60, base - 20), (cx + 130, base - 40), (cx + 150, base - 110)], fill=fill, width=18, joint="curve")

    draw_on(canvas, kitty)
    p.sprinkle(canvas, 60, (1300, 300, W, 900), (245, 194, 231), sizes=(1.5, 2.5), seed=114, strength=0.5)
    p.readable(canvas)
    return p.finish(canvas)


def nord():
    canvas = p.vertical((36, 41, 52), (59, 66, 82), 0.9)
    y, x = grid_xy()
    wave = 360 + 90 * np.sin(x / 520) + 40 * np.sin(x / 170)
    p.add_light(canvas, (136, 192, 208), np.exp(-((y - wave) / 150) ** 2) * (0.4 + 0.6 * p.stretched(120, 3, 121)) * (x / W) * 0.35)
    p.stars(canvas, 700, H * 0.65, seed=122, tint=(236, 239, 244))
    for base, amp, scale, seed, color in ((880, 220, 2.2, 123, (76, 86, 106)), (1000, 160, 3, 124, (59, 66, 82))):
        mask = p.ridge_mask(base, amp, scale, seed)
        p.blend(canvas, color, mask)
        p.add_light(canvas, (216, 222, 233), mask * np.clip(1 - (y - (base - amp * 1.4)) / 140, 0, 1) * 0.35)
    sea = (y > 1120).astype(float)
    p.blend(canvas, (46, 52, 64), sea)

    def icebergs(d):
        for x0, w, h in ((1500, 260, 120), (1880, 420, 190), (2340, 220, 100)):
            d.polygon([(x0, 1125), (x0 + w * 0.2, 1125 - h), (x0 + w * 0.55, 1125 - h * 0.8), (x0 + w * 0.75, 1125 - h * 1.1), (x0 + w, 1125)], fill=(200, 214, 228))
            d.polygon([(x0 + w * 0.1, 1125), (x0 + w * 0.5, 1180), (x0 + w * 0.9, 1125)], fill=(94, 129, 172))

    draw_on(canvas, icebergs)
    p.readable(canvas)
    return p.finish(canvas)


def solarized():
    canvas = p.vertical((0, 30, 38), (0, 43, 54), 1.0)
    p.stars(canvas, 900, H, seed=131, tint=(147, 161, 161))
    cx, cy = 2300, 720
    p.glow(canvas, cx, cy, 420, (203, 75, 22), 0.6)
    p.glow(canvas, cx, cy, 220, (181, 137, 0), 0.9)
    p.blend(canvas, (253, 200, 80), (p.radial(cx, cy, 150) < 1).astype(float))

    def orbits(d):
        for i, (r, planet, color, angle) in enumerate(((330, 18, (42, 161, 152), 2.6), (520, 28, (38, 139, 210), 3.0), (720, 22, (211, 54, 130), 2.7), (930, 40, (108, 113, 196), 3.25))):
            d.ellipse([cx - r, cy - r * 0.42, cx + r, cy + r * 0.42], outline=(7, 54, 66), width=3)
            px, py = cx + r * math.cos(angle), cy + r * 0.42 * math.sin(angle)
            d.ellipse([px - planet, py - planet, px + planet, py + planet], fill=color)

    draw_on(canvas, orbits)
    p.readable(canvas)
    return p.finish(canvas)


def orbit():
    canvas = p.vertical((4, 6, 14), (8, 12, 26), 1.0)
    p.stars(canvas, 1800, H, seed=141)
    y, x = grid_xy()
    cx, cy, r = 2500, 1900, 1150
    d = p.radial(cx, cy, r)
    planet = (d < 1).astype(float)
    p.add_light(canvas, (60, 140, 255), np.exp(-np.abs(d - 1) * 40) * 1.4)
    p.add_light(canvas, (40, 100, 220), np.exp(-(d - 1).clip(0) * 9) * (d > 1) * 0.5)
    land = p.noise(W, H, 6, 5, 142)
    p.blend(canvas, (14, 40, 90), planet)
    p.blend(canvas, (30, 90, 60), planet * np.clip((land - 0.55) * 6, 0, 1))
    p.add_light(canvas, (220, 230, 255), planet * np.clip((p.noise(W, H, 10, 4, 143) - 0.62) * 5, 0, 1) * 0.6)
    p.blend(canvas, (2, 4, 10), planet * np.clip((x - cx + 300) / -900, 0, 1) * 0.0)

    def station(d):
        sx, sy = 1850, 420
        d.rectangle([sx - 120, sy - 6, sx + 120, sy + 6], fill=(150, 160, 180))
        for dx in (-120, 90):
            d.rectangle([sx + dx, sy - 40, sx + dx + 30, sy + 40], fill=(40, 70, 140))
        d.ellipse([sx - 22, sy - 22, sx + 22, sy + 22], fill=(200, 205, 215))

    draw_on(canvas, station)
    p.readable(canvas)
    return p.finish(canvas)


# ---------- Cities ----------

def tokyo_night():
    canvas = p.vertical((16, 17, 30), (40, 34, 72), 1.3)
    p.stars(canvas, 400, H * 0.4, seed=151, tint=(192, 202, 245))
    p.moon(canvas, 2050, 300, 90, color=(224, 175, 104), halo=(187, 154, 247))
    rng = np.random.default_rng(152)
    image = p.to_image(canvas)
    d = ImageDraw.Draw(image)
    windows = Image.new("RGB", (W, H))
    wd = ImageDraw.Draw(windows)
    x = 1050
    while x < W:
        w, h = int(rng.integers(60, 150)), int(rng.integers(220, 620))
        d.rectangle([x, 1180 - h, x + w, H], fill=(21, 22, 34))
        for wy in range(1180 - h + 16, 1180, 22):
            for wx in range(x + 8, x + w - 8, 14):
                if rng.random() < 0.16:
                    wd.rectangle([wx, wy, wx + 6, wy + 9], fill=[(122, 162, 247), (187, 154, 247), (247, 118, 142), (224, 175, 104)][int(rng.integers(0, 4))])
        x += w + int(rng.integers(2, 20))
    # A pagoda and a torii gate in front of the city.
    px, base = 1500, 1240
    for i in range(5):
        w = 260 - i * 40
        top = base - 90 - i * 85
        d.rectangle([px - w * 0.35, top + 25, px + w * 0.35, top + 85], fill=(12, 12, 22))
        d.polygon([(px - w / 2 - 30, top + 30), (px, top - 10), (px + w / 2 + 30, top + 30), (px + w / 2, top + 40), (px - w / 2, top + 40)], fill=(12, 12, 22))
    d.line([(px, base - 520), (px, base - 600)], fill=(12, 12, 22), width=6)
    tx = 2150
    d.rectangle([tx - 150, 1000, tx - 125, 1260], fill=(150, 40, 60))
    d.rectangle([tx + 125, 1000, tx + 150, 1260], fill=(150, 40, 60))
    d.polygon([(tx - 220, 975), (tx + 220, 975), (tx + 190, 1000), (tx - 190, 1000)], fill=(170, 46, 66))
    d.rectangle([tx - 170, 1030, tx + 170, 1045], fill=(150, 40, 60))
    canvas[:] = p.to_canvas(image)
    canvas += np.asarray(windows, float) * 0.5 + np.asarray(windows.filter(ImageFilter.GaussianBlur(8)), float) * 0.7
    p.blend(canvas, (14, 15, 24), (grid_xy()[0] > 1250).astype(float))
    p.readable(canvas)
    return p.finish(canvas)


def digital_rain():
    canvas = np.zeros((H, W, 3)) + np.asarray((2, 8, 3), float)
    image = p.to_image(canvas)
    d = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 28)
    except OSError:
        font = ImageFont.load_default()
    rng = np.random.default_rng(161)
    glyphs = "0123456789$#@%&*<>{}[]=+:;ABCDEFHKMNXYZ"
    for col in range(0, W, 30):
        head = int(rng.integers(-H // 2, H))
        length = int(rng.integers(8, 40))
        bright = col / W
        for k in range(length):
            yy = head - k * 32
            if 0 <= yy < H:
                fade = (1 - k / length) * (0.25 + 0.75 * bright)
                color = (int(180 * fade), int(255 * fade), int(180 * fade)) if k == 0 else (0, int(200 * fade), int(70 * fade))
                d.text((col, yy), glyphs[int(rng.integers(0, len(glyphs)))], font=font, fill=color)
    canvas = p.to_canvas(image)
    canvas += p.to_canvas(image.filter(ImageFilter.GaussianBlur(6))) * 0.8
    p.readable(canvas, 0.6)
    return p.finish(canvas)


def phosphor():
    canvas = p.vertical((14, 8, 0), (30, 18, 2), 1.0)
    y, x = grid_xy()
    p.glow(canvas, 1900, 640, 700, (255, 140, 0), 0.25)

    def desk(d):
        d.rectangle([1450, 980, 2400, 1010], fill=(26, 16, 4))
        d.rounded_rectangle([1560, 320, 2240, 900], radius=40, fill=(40, 26, 8))
        d.rounded_rectangle([1620, 380, 2180, 820], radius=30, fill=(18, 10, 0))
        d.rectangle([1820, 900, 1980, 980], fill=(34, 22, 6))
        d.rectangle([1600, 1030, 2200, 1080], fill=(34, 22, 6))

    draw_on(canvas, desk)
    text = p.shape_mask(lambda d: [d.rectangle([1660, 420 + i * 42, 1660 + w, 440 + i * 42], fill=255)
                                   for i, w in enumerate((380, 260, 420, 180, 330, 240, 120, 40))])
    p.add_light(canvas, (255, 176, 0), text * 0.9)
    p.add_light(canvas, (255, 150, 0), p.shape_mask(lambda d: d.rounded_rectangle([1620, 380, 2180, 820], radius=30, fill=255), blur=40) * 0.35)
    canvas *= (0.9 + 0.1 * (np.sin(y * math.pi / 3) > 0))[..., None]
    p.readable(canvas)
    return p.finish(canvas)


def arcade():
    canvas = p.vertical((6, 6, 20), (16, 10, 40), 1.0)
    p.stars(canvas, 700, H, seed=171)
    s = 14
    alien = ["..#.....#..", "...#...#...", "..#######..", ".##.###.##.", "###########", "#.#######.#", "#.#.....#.#", "...##.##..."]
    colors = [(57, 255, 20), (255, 60, 200), (60, 220, 255), (255, 220, 60)]

    def invaders(d):
        for row in range(4):
            for col in range(6):
                ox, oy = 1300 + col * 190, 200 + row * 150
                for yy, line in enumerate(alien):
                    for xx, ch in enumerate(line):
                        if ch == "#":
                            d.rectangle([ox + xx * s, oy + yy * s, ox + xx * s + s - 2, oy + yy * s + s - 2], fill=colors[row])
        d.rectangle([1750, 1150, 1850, 1190], fill=(57, 255, 20))
        d.rectangle([1785, 1120, 1815, 1150], fill=(57, 255, 20))
        for bx in (1350, 1700, 2050, 2400):
            d.rectangle([bx, 1010, bx + 120, 1060], fill=(255, 80, 80))
        d.rectangle([1800, 700, 1806, 760], fill=(255, 255, 255))

    draw_on(canvas, invaders)
    p.add_light(canvas, (60, 255, 120), p.to_canvas(p.to_image(canvas).filter(ImageFilter.GaussianBlur(10)))[..., 1] / 255 * 0.0)
    p.readable(canvas)
    return p.finish(canvas)


def synthwave():
    canvas = p.vertical((20, 10, 40), (90, 20, 90), 1.4)
    y, x = grid_xy()
    p.stars(canvas, 400, H * 0.45, seed=181, tint=(255, 200, 255))
    cx, cy, r = 1850, 760, 330
    sun = (p.radial(cx, cy, r) < 1) & (y < 760)
    stripes = ~(((y - 560) % 48 < 12 + (y - 560) / 18) & (y > 560))
    t = np.clip((y - (cy - r)) / r, 0, 1)
    p.blend(canvas, (254, 222, 93), (sun & stripes) * (1 - t))
    p.blend(canvas, (255, 60, 160), (sun & stripes) * t)
    p.glow(canvas, cx, cy - 100, 520, (255, 60, 180), 0.35)
    p.blend(canvas, (40, 10, 60), p.ridge_mask(760, 120, 3, 182))
    floor = (y > 760).astype(float)
    p.blend(canvas, (22, 6, 36), floor)
    depth = np.clip((y - 760) / (H - 760), 0.001, 1)
    lines = (np.abs((np.clip(y - 760, 0, None) ** 0.6 * 6) % 40 - 20) < 2) * floor
    rays = (np.abs(((x - cx) / depth) % 220 - 110) < 3 / depth ** 0.2) * floor
    # The grid fades out on the left and at the very bottom, where the text goes.
    fade = np.clip((x - 900) / 900, 0, 1) * np.clip((H - 60 - y) / 300, 0.25, 1)
    p.add_light(canvas, (255, 60, 220), (lines + rays).clip(0, 1) * depth * 1.1 * fade)

    def palms(d):
        for px, h in ((1300, 520), (2380, 600)):
            d.line([(px, 1080), (px + 30, 1080 - h)], fill=(14, 4, 24), width=18)
            for a in range(0, 360, 45):
                rad = math.radians(a)
                d.line([(px + 30, 1080 - h), (px + 30 + 170 * math.cos(rad), 1080 - h + 90 * math.sin(rad) + 40)], fill=(14, 4, 24), width=14)

    draw_on(canvas, palms)
    p.readable(canvas)
    return p.finish(canvas)


# ---------- Nature ----------

def gruvbox():
    canvas = p.vertical((40, 30, 30), (214, 93, 14), 1.8)
    y, x = grid_xy()
    p.glow(canvas, 1900, 1000, 500, (250, 189, 47), 0.6)
    p.blend(canvas, (250, 200, 80), (p.radial(1900, 960, 140) < 1) * 0.95)

    def mesas(d):
        fill = (60, 36, 26)
        d.polygon([(1250, 1060), (1320, 760), (1600, 760), (1650, 1060)], fill=fill)
        d.polygon([(2050, 1060), (2120, 840), (2300, 840), (2380, 1060)], fill=fill)
        d.rectangle([0, 1040, W, H], fill=(40, 28, 22))
        for cx in (1500, 2200, 2450):
            d.rectangle([cx - 10, 900, cx + 10, 1060], fill=(29, 32, 33))
            d.rectangle([cx - 50, 950, cx - 30, 990], fill=(29, 32, 33))
            d.rectangle([cx - 50, 975, cx - 10, 990], fill=(29, 32, 33))

    draw_on(canvas, mesas)
    p.glow(canvas, 1800, 1150, 120, (254, 128, 25), 0.7)
    p.sprinkle(canvas, 90, (1700, 800, 1900, 1150), (254, 128, 25), seed=191, strength=0.8)
    p.readable(canvas)
    return p.finish(canvas)


def rose_pine():
    canvas = p.vertical((25, 23, 36), (110, 70, 90), 1.5)
    y, x = grid_xy()
    p.glow(canvas, 1900, 980, 600, (235, 188, 186), 0.4)
    p.stars(canvas, 300, H * 0.4, seed=201, tint=(224, 222, 244))
    image = p.to_image(canvas)
    d = ImageDraw.Draw(image)
    rng = np.random.default_rng(202)
    for layer, (base, color, count) in enumerate(((980, (64, 61, 82), 26), (1080, (38, 35, 58), 22), (1200, (25, 23, 36), 18))):
        for _ in range(count):
            p.pine(d, rng.uniform(1100, W + 50), base + rng.uniform(-30, 30), rng.uniform(220, 420) * (1 + layer * 0.25), color)
        d.rectangle([0, base, W, H], fill=color)
    canvas[:] = p.to_canvas(image)
    p.add_light(canvas, (235, 111, 146), np.exp(-((y - 1000) / 60) ** 2) * 0.12)
    p.sprinkle(canvas, 40, (1300, 700, W, 1150), (246, 193, 119), seed=203, strength=0.6)
    p.readable(canvas)
    return p.finish(canvas)


def everforest():
    canvas = p.vertical((35, 42, 46), (60, 72, 60), 1.0)
    y, x = grid_xy()
    p.glow(canvas, 1900, 500, 500, (167, 192, 128), 0.18)
    image = p.to_image(canvas)
    d = ImageDraw.Draw(image)
    rng = np.random.default_rng(211)
    for layer, (base, color, count) in enumerate(((900, (61, 72, 77), 30), (1020, (52, 63, 68), 26), (1160, (45, 53, 59), 22))):
        for _ in range(count):
            p.pine(d, rng.uniform(1000, W + 50), base + rng.uniform(-40, 40), rng.uniform(300, 520) * (1 + layer * 0.2), color)
        d.rectangle([0, base, W, H], fill=color)
    canvas[:] = p.to_canvas(image)
    p.sprinkle(canvas, 120, (1200, 500, W, 1300), (219, 188, 127), sizes=(1.5, 2.0, 2.5), seed=212, strength=0.9)
    p.readable(canvas)
    return p.finish(canvas)


def abyss():
    canvas = p.vertical((4, 30, 50), (1, 6, 14), 0.8)
    y, x = grid_xy()
    rays = np.clip(np.sin((x - y * 0.35) / 90) * 0.5 + 0.5, 0, 1) ** 6 * np.clip(1 - y / 900, 0, 1)
    p.add_light(canvas, (90, 200, 220), rays * 0.25)
    p.sprinkle(canvas, 400, (900, 0, W, H), (120, 220, 255), sizes=(0.8, 1.2, 1.8), seed=221, strength=0.35)

    def jelly(d, cx, cy, s):
        d.chord([cx - 80 * s, cy - 70 * s, cx + 80 * s, cy + 50 * s], 180, 360, fill=255)
        for i in range(6):
            tx = cx - 60 * s + i * 24 * s
            d.line([(tx, cy - 10 * s), (tx + 18 * s * math.sin(i), cy + 120 * s), (tx - 10 * s, cy + 220 * s)], fill=150, width=max(2, int(4 * s)), joint="curve")

    for cx, cy, s, color in ((1900, 520, 1.6, (94, 230, 208)), (2300, 820, 1.0, (122, 140, 255)), (1500, 860, 0.8, (200, 120, 255))):
        mask = p.shape_mask(lambda d, cx=cx, cy=cy, s=s: jelly(d, cx, cy, s))
        soft = p.shape_mask(lambda d, cx=cx, cy=cy, s=s: jelly(d, cx, cy, s), blur=30)
        p.add_light(canvas, color, mask * 0.6 + soft * 0.9)
    p.blend(canvas, (2, 8, 14), p.ridge_mask(1260, 60, 5, 222))
    p.readable(canvas)
    return p.finish(canvas)


def sakura():
    canvas = p.vertical((40, 24, 48), (190, 110, 130), 1.6)
    y, x = grid_xy()
    p.glow(canvas, 1950, 900, 520, (255, 190, 170), 0.4)

    def scene(d):
        d.polygon([(1450, 1100), (1950, 620), (2450, 1100)], fill=(70, 50, 80))
        d.polygon([(1830, 735), (1950, 620), (2070, 735), (2000, 760), (1950, 730), (1900, 760)], fill=(240, 230, 240))
        d.rectangle([0, 1090, W, H], fill=(36, 22, 40))
        px, base = 2250, 1100
        for i in range(3):
            w = 230 - i * 50
            top = base - 80 - i * 95
            d.rectangle([px - w * 0.35, top + 25, px + w * 0.35, top + 80], fill=(30, 16, 30))
            d.polygon([(px - w / 2 - 34, top + 30), (px, top - 14), (px + w / 2 + 34, top + 30)], fill=(30, 16, 30))
        d.line([(1100, 0), (1350, 200), (1500, 260), (1700, 240)], fill=(40, 22, 32), width=26, joint="curve")
        d.line([(1350, 200), (1420, 380)], fill=(40, 22, 32), width=14)

    draw_on(canvas, scene)
    p.sprinkle(canvas, 260, (1100, 0, 1800, 450), (255, 183, 197), sizes=(3, 4, 5), blur=1, seed=231, strength=0.9)
    p.sprinkle(canvas, 160, (1100, 300, W, 1300), (255, 183, 197), sizes=(2, 3), blur=1, seed=232, strength=0.7)
    p.readable(canvas)
    return p.finish(canvas)


def volcano():
    canvas = p.vertical((20, 6, 6), (70, 18, 8), 1.2)
    y, x = grid_xy()
    p.glow(canvas, 1950, 520, 500, (255, 90, 20), 0.5)

    def mountain(d):
        d.polygon([(1250, 1200), (1820, 560), (2080, 560), (2600, 1200)], fill=(32, 12, 10))
        d.rectangle([0, 1180, W, H], fill=(20, 8, 6))

    draw_on(canvas, mountain)
    lava = p.shape_mask(lambda d: [d.line(path, fill=255, width=14, joint="curve") for path in (
        [(1900, 570), (1870, 760), (1800, 900), (1760, 1100)], [(2000, 570), (2060, 720), (2150, 900), (2200, 1150)])], blur=2)
    p.add_light(canvas, (255, 110, 30), lava * 1.4 + p.shape_mask(lambda d: d.rectangle([1820, 540, 2080, 575], fill=255), blur=30) * 1.2)
    p.sprinkle(canvas, 300, (1700, 100, 2300, 560), (255, 150, 40), sizes=(1.5, 2.5, 3.5), seed=241, strength=0.9)
    p.add_light(canvas, (60, 40, 40), p.noise(W, H, 4, 4, 242) * np.clip(1 - y / 700, 0, 1) * 0.4)
    p.readable(canvas)
    return p.finish(canvas)


def lofi():
    canvas = p.vertical((28, 22, 18), (44, 34, 28), 1.0)
    y, x = grid_xy()
    # The window: city bokeh through rain.
    wx0, wy0, wx1, wy1 = 1350, 200, 2350, 1000
    window = ((x > wx0) & (x < wx1) & (y > wy0) & (y < wy1)).astype(float)
    p.blend(canvas, (30, 34, 58), window)
    p.sprinkle(canvas, 160, (wx0, 500, wx1, wy1), (255, 190, 120), sizes=(6, 10, 14), blur=6, seed=251, strength=0.35)
    p.sprinkle(canvas, 80, (wx0, 500, wx1, wy1), (140, 170, 255), sizes=(6, 10), blur=6, seed=252, strength=0.3)
    rain = p.shape_mask(lambda d: [d.line([(rx, ry), (rx - 3, ry + 40)], fill=140, width=2)
                                   for rx, ry in np.random.default_rng(253).uniform((wx0, wy0), (wx1, wy1), (500, 2))])
    p.add_light(canvas, (180, 200, 255), rain * window * 0.5)

    def room(d):
        d.rectangle([wx0 - 30, wy0 - 30, wx1 + 30, wy0], fill=(60, 44, 34))
        d.rectangle([wx0 - 30, wy1, wx1 + 30, wy1 + 40], fill=(60, 44, 34))
        d.rectangle([(wx0 + wx1) // 2 - 10, wy0, (wx0 + wx1) // 2 + 10, wy1], fill=(60, 44, 34))
        d.rectangle([wx0 - 30, wy0, wx0, wy1], fill=(60, 44, 34))
        d.rectangle([wx1, wy0, wx1 + 30, wy1], fill=(60, 44, 34))
        d.rectangle([2400, 760, 2560, 1040], fill=(70, 50, 40))
        d.ellipse([2250, 820, 2380, 900], fill=(80, 60, 46))
        for i in range(7):
            a = math.radians(200 + i * 22)
            d.ellipse([2300 + 150 * math.cos(a) - 40, 760 + 120 * math.sin(a) - 18, 2300 + 150 * math.cos(a) + 40, 760 + 120 * math.sin(a) + 18], fill=(50, 74, 50))
        d.rectangle([2270, 820, 2330, 1000], fill=(110, 70, 50))
        d.rounded_rectangle([1760, 940, 1860, 1040], radius=12, fill=(232, 213, 181))
        d.arc([1840, 960, 1890, 1010], 270, 90, fill=(232, 213, 181), width=10)

    draw_on(canvas, room)
    p.glow(canvas, 1810, 900, 160, (255, 180, 120), 0.25)
    p.glow(canvas, 2450, 300, 400, (255, 170, 90), 0.25)
    p.readable(canvas)
    return p.finish(canvas)


# ---------- Seasons ----------

def christmas():
    canvas = p.vertical((8, 16, 34), (20, 36, 56), 1.0)
    y, x = grid_xy()
    p.stars(canvas, 700, H * 0.6, seed=261, tint=(230, 240, 255))
    p.moon(canvas, 2000, 280, 80, color=(245, 245, 230), halo=(160, 190, 255))
    snow_ground = p.ridge_mask(1060, 60, 2, 262)
    p.blend(canvas, (120, 136, 158), snow_ground)
    image = p.to_image(canvas)
    d = ImageDraw.Draw(image)
    rng = np.random.default_rng(263)
    for _ in range(26):
        p.pine(d, rng.uniform(1150, W + 40), 1080 + rng.uniform(-20, 40), rng.uniform(220, 420), (16, 50, 36), snow=(230, 238, 246))
    lights = []
    for cx, w in ((1700, 300), (2150, 240)):
        base = 1090
        d.rectangle([cx - w / 2, base - 170, cx + w / 2, base], fill=(70, 40, 30))
        d.polygon([(cx - w / 2 - 30, base - 170), (cx, base - 300), (cx + w / 2 + 30, base - 170)], fill=(230, 238, 246))
        for wx in (cx - w / 4, cx + w / 6):
            d.rectangle([wx - 20, base - 120, wx + 20, base - 70], fill=(255, 200, 110))
            lights.append((wx, base - 95, 60, (255, 170, 80)))
        for i in range(9):
            lx = cx - w / 2 - 20 + i * (w + 40) / 8
            ly = base - 170 + 12 * math.sin(i / 8 * math.pi)
            color = [(255, 77, 77), (255, 213, 74), (77, 166, 255), (67, 160, 71)][i % 4]
            d.ellipse([lx - 7, ly - 7, lx + 7, ly + 7], fill=color)
            lights.append((lx, ly, 28, color))
    canvas[:] = p.to_canvas(image)
    for lx, ly, r, color in lights:
        p.glow(canvas, lx, ly, r, color, 0.5)
    p.sprinkle(canvas, 500, (900, 0, W, H), (240, 245, 255), sizes=(1.5, 2.5, 3.5), blur=1, seed=264, strength=0.7)
    p.readable(canvas)
    return p.finish(canvas)


def halloween():
    canvas = p.vertical((14, 8, 24), (50, 20, 50), 1.2)
    y, x = grid_xy()
    p.stars(canvas, 400, H * 0.5, seed=271, tint=(255, 220, 200))
    p.moon(canvas, 1950, 360, 200, color=(255, 214, 140), halo=(255, 140, 60))
    hill = p.ridge_mask(1000, 70, 2, 272)
    p.blend(canvas, (16, 8, 18), hill)

    def scene(d):
        fill = (12, 6, 14)
        hx, base = 1950, 960
        d.rectangle([hx - 200, base - 260, hx + 200, base], fill=fill)
        d.polygon([(hx - 240, base - 260), (hx - 60, base - 470), (hx + 120, base - 260)], fill=fill)
        d.rectangle([hx + 80, base - 420, hx + 170, base - 260], fill=fill)
        d.polygon([(hx + 60, base - 420), (hx + 125, base - 520), (hx + 190, base - 420)], fill=fill)
        for wx, wy in ((hx - 140, base - 200), (hx + 40, base - 200), (hx - 70, base - 330), (hx + 110, base - 370)):
            d.rectangle([wx, wy, wx + 46, wy + 62], fill=(255, 150, 40))
        for tx, h, lean in ((1450, 520, -1), (2420, 600, 1)):
            d.line([(tx, 1050), (tx + 30 * lean, 1050 - h)], fill=fill, width=26)
            for k in range(5):
                by = 1050 - h * (0.45 + k * 0.12)
                d.line([(tx + 20 * lean * k / 5, by), (tx + lean * (140 - k * 18), by - 90), (tx + lean * (190 - k * 20), by - 70)], fill=fill, width=10, joint="curve")
        rng = np.random.default_rng(273)
        for _ in range(12):
            bx, by, s = rng.uniform(1500, 2450), rng.uniform(150, 650), rng.uniform(10, 24)
            d.polygon([(bx, by), (bx - s, by - s * 0.6), (bx - s * 1.6, by + s * 0.1), (bx - s * 0.5, by + s * 0.15), (bx, by + s * 0.4),
                       (bx + s * 0.5, by + s * 0.15), (bx + s * 1.6, by + s * 0.1), (bx + s, by - s * 0.6)], fill=fill)
        for px in (1650, 1760, 2250):
            d.ellipse([px - 46, 1080, px + 46, 1150], fill=(255, 117, 24))
            d.polygon([(px - 18, 1100), (px - 6, 1088), (px + 6, 1100)], fill=(255, 230, 120))

    draw_on(canvas, scene)
    for wx, wy in ((1833, 791), (2013, 791), (1903, 661), (2083, 621), (1650, 1110), (1760, 1110), (2250, 1110)):
        p.glow(canvas, wx, wy, 70, (255, 140, 40), 0.45)
    p.add_light(canvas, (120, 90, 140), p.noise(W, H, 3, 4, 274) * np.exp(-((y - 1080) / 120) ** 2) * 0.5)
    p.readable(canvas)
    return p.finish(canvas)


def one_dark():
    canvas = p.vertical((24, 26, 31), (40, 44, 52), 1.0)
    p.stars(canvas, 300, H, seed=281, tint=(171, 178, 191))
    cx, cy = 1950, 700
    p.glow(canvas, cx, cy, 300, (97, 175, 239), 0.35)
    rings = Image.new("L", (W, H), 0)
    for angle in (0, 60, 120):
        ring = Image.new("L", (1400, 1400), 0)
        ImageDraw.Draw(ring).ellipse([100, 520, 1300, 880], outline=255, width=8)
        ring = ring.rotate(angle, resample=Image.BICUBIC)
        rings.paste(ring, (cx - 700, cy - 700), ring)
    mask = np.asarray(rings, float) / 255
    p.add_light(canvas, (198, 120, 221), mask * 0.9 + np.asarray(rings.filter(ImageFilter.GaussianBlur(14)), float) / 255 * 0.8)
    p.blend(canvas, (229, 192, 123), (p.radial(cx, cy, 70) < 1).astype(float))
    p.glow(canvas, cx, cy, 160, (229, 192, 123), 0.5)
    for ex, ey, color in ((cx + 590, cy, (152, 195, 121)), (cx - 300, cy - 500, (224, 108, 117)), (cx - 280, cy + 500, (86, 182, 194))):
        p.blend(canvas, color, (p.radial(ex, ey, 26) < 1).astype(float))
        p.glow(canvas, ex, ey, 70, color, 0.5)
    p.readable(canvas)
    return p.finish(canvas)
