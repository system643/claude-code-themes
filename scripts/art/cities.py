"""The ten city themes: original landmark sprites and night skyline scenes.

Every landmark is drawn by hand from simple shapes (no photos, no third-party art).
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import paint as p
from paint import H, W
from sprites import Grid


def grid_xy():
    return np.mgrid[:H, :W]


def draw_on(canvas, fn):
    image = p.to_image(canvas)
    fn(ImageDraw.Draw(image))
    canvas[:] = p.to_canvas(image)


def skyline(canvas, base, x0, x1, heights, color, seed, window_colors, density=0.15):
    """Generic buildings with lit windows between x0 and x1."""
    rng = np.random.default_rng(seed)
    image = p.to_image(canvas)
    draw = ImageDraw.Draw(image)
    windows = Image.new("RGB", (W, H))
    wd = ImageDraw.Draw(windows)
    x = x0
    while x < x1:
        w, h = int(rng.integers(50, 130)), int(rng.integers(*heights))
        draw.rectangle([x, base - h, x + w, H], fill=color)
        for wy in range(base - h + 14, base, 20):
            for wx in range(x + 7, x + w - 7, 13):
                if rng.random() < density:
                    wd.rectangle([wx, wy, wx + 5, wy + 8], fill=window_colors[int(rng.integers(0, len(window_colors)))])
        x += w + int(rng.integers(2, 16))
    canvas[:] = p.to_canvas(image) + np.asarray(windows, float) * 0.5 + np.asarray(windows.filter(ImageFilter.GaussianBlur(7)), float) * 0.6


def water(canvas, top, color, glints, seed):
    y, x = grid_xy()
    sea = (y > top).astype(float)
    p.blend(canvas, color, sea)
    for gx, gcolor, width in glints:
        ripples = np.clip((p.stretched(20, 150, seed) - 0.45) * 2.6, 0, 1)
        p.add_light(canvas, gcolor, ripples * np.exp(-((x - gx) / width) ** 2) * sea * 0.45)


# ---------- Sprites (20 × 12) ----------

def eiffel_sprite():
    frames = []
    sparkles = [[(3, 9), (7, 12), (10, 4)], [(5, 8), (9, 6), (6, 13)], [(2, 10), (8, 14), (10, 15)], [(4, 9), (7, 7), (9, 13)]]
    for k, spots in enumerate(sparkles):
        g = Grid()
        g.put(0, [9, 10], "b" if k % 2 else "i").put(1, [9, 10], "i").put(2, range(8, 12), "i").put(3, range(8, 12), "i")
        g.put(4, range(8, 12), "i").put(5, range(7, 13), "p").put(6, [7, 8, 11, 12], "i").put(7, [6, 7, 12, 13], "i")
        g.put(8, range(5, 15), "p").put(9, [5, 6, 7, 12, 13, 14], "i").put(10, [4, 5, 14, 15], "i").put(11, [3, 4, 15, 16], "i")
        for r, c in spots:
            g.put(r, [c], "w")
        frames.append(g.rows())
    return frames, {"i": "#C9A86A", "p": "#E8C887", "w": "#FFFFFF", "b": "#FFF2C4"}, ["b", "w"]


def skytree_sprite():
    frames = []
    for k in range(4):
        g = Grid()
        for r in range(7, 12):
            half = (r - 6) * 1.3
            g.put(r, range(max(0, round(4 - half)), min(9, round(4 + half) + 1)), "f")
        g.put(7, [4], "s").put(8, [3, 4, 5], "s")
        g.put(0, [13], "l" if k % 2 else "L").put(1, [13], "t").put(2, [13], "t").put(3, range(12, 15), "d")
        for r in range(4, 12):
            g.put(r, [13], "t")
        g.put(6, range(12, 15), "d").put(9, [12, 14], "t").put(10, [12, 14], "t").put(11, [11, 12, 14, 15], "t")
        g.put(3, [12 + k % 3], "L")
        frames.append(g.rows())
    return frames, {"t": "#C8D4E8", "d": "#7AA2F7", "f": "#3B4A6B", "s": "#F0F4FF", "l": "#BB9AF7", "L": "#7DCFFF"}, ["l", "L"]


def empire_sprite():
    frames = []
    rng = np.random.default_rng(3)
    for k in range(4):
        g = Grid()
        g.put(0, [9, 10], "r" if k % 2 else "s").put(1, [9, 10], "s").put(2, [9, 10], "s").put(3, range(8, 12), "b")
        g.rect(4, 5, 7, 12, "b").rect(6, 8, 6, 13, "b").rect(9, 11, 5, 14, "b")
        for r in range(4, 12):
            for c in range(5, 15):
                if g.cells[r][c] == "b" and rng.random() < 0.3:
                    g.put(r, [c], "y")
        frames.append(g.rows())
    return frames, {"b": "#4A5468", "y": "#FFD66B", "r": "#FF5E5E", "s": "#C0C8D8"}, ["r", "y"]


def bigben_sprite():
    hands = [[(3, 9), (4, 10)], [(4, 10), (4, 11)], [(5, 10), (4, 10)], [(4, 9), (4, 8)]]
    frames = []
    for spots in hands:
        g = Grid()
        g.put(0, [9, 10], "r").put(1, range(8, 12), "r").put(2, range(7, 13), "r")
        g.rect(3, 5, 7, 12, "t").rect(3, 5, 8, 11, "c")
        for r, c in spots:
            g.put(r, [c], "h")
        g.rect(6, 11, 7, 12, "t")
        for r in (7, 9):
            g.put(r, [8, 11], "w")
        frames.append(g.rows())
    return frames, {"t": "#C8A96E", "r": "#3D5A4C", "c": "#F5EBC8", "h": "#2B2B2B", "w": "#FFD27A"}, ["c"]


def burj_sprite():
    frames = []
    widths = [(9, 10), (9, 10), (9, 10), (9, 10), (8, 11), (8, 11), (7, 11), (7, 12), (6, 12), (6, 13), (5, 13), (5, 14)]
    for k in range(4):
        g = Grid()
        for r, (c0, c1) in enumerate(widths):
            g.put(r, range(c0, c1 + 1) if r > 2 else [9 + (r % 2 == 0 and 0)], "b")
        g.put(0, [9], "r" if k % 2 else "b")
        for r in range(4, 12, 2):
            g.put(r, [widths[r][0] + 1 + (k + r) % 2], "y")
        g.put(1, [2, 3], "m").put(2, [1], "m").put(3, [2, 3], "m")
        frames.append(g.rows())
    return frames, {"b": "#9AA8C0", "y": "#FFE08A", "r": "#FF6B6B", "m": "#F5E6B8"}, ["r"]


def colosseum_sprite():
    frames = []
    for k in range(4):
        g = Grid()
        g.put(4, range(4, 14), "s").rect(5, 11, 2, 17, "s")
        for c in range(14, 18):
            g.put(4, [c], ".")
        g.put(5, [16, 17], ".")
        for r in (6, 8, 10):
            for c in range(3 + (r // 2) % 2, 17, 2):
                g.put(r, [c], "l" if (c + k + r) % 5 == 0 else "a")
        for i, (r, c) in enumerate(((0, 3), (1, 15), (2, 8), (0, 18))):
            if (i + k) % 2:
                g.put(r, [c], "w")
        frames.append(g.rows())
    return frames, {"s": "#D9B48A", "a": "#5A3A20", "l": "#FFB347", "w": "#FFFFFF"}, ["l"]


def seoul_sprite():
    frames = []
    for pod in ("p", "q", "r", "q"):
        g = Grid()
        for c in range(W):
            top = 8 + round(abs(c - 9.5) / 3.5)
            for r in range(min(top, 11), 12):
                g.put(r, [c], "m")
        g.put(0, [10], "t")
        for r in range(1, 9):
            g.put(r, [10], "t")
        g.put(3, range(8, 13), pod).put(4, range(8, 13), pod).put(2, [9, 10, 11], "t")
        frames.append(g.rows())
    return frames, {"m": "#2E4A3A", "t": "#D0D8E0", "p": "#FF6B9D", "q": "#6BC7FF", "r": "#B8F06B"}, ["p", "q", "r"]


def opera_sprite():
    frames = []
    for k in range(4):
        g = Grid()
        for x0, height, width, key in ((2, 6, 7, "s"), (7, 7, 7, "S"), (11, 5, 6, "s"), (14, 4, 4, "S")):
            for r in range(height):
                row = 8 - r
                span = round(width * (1 - r / height) ** 0.7)
                g.put(row, range(x0, x0 + span), key)
        g.put(9, range(1, 19), "b")
        g.put(10, range(0, W), "w").put(11, range(0, W), "w")
        for c in range(0, W, 4):
            g.put(10 + (c // 4 + k) % 2, [(c + k) % W], "W")
        frames.append(g.rows())
    return frames, {"s": "#F4F1EA", "S": "#CFC8B8", "b": "#8A7A66", "w": "#2F6FC0", "W": "#8FC4FF"}, ["s"]


def christ_sprite():
    frames = []
    for k in range(4):
        g = Grid()
        for r in range(8, 12):
            half = (r - 7) * 2.2
            g.put(r, range(round(9.5 - half), round(9.5 + half) + 1), "m")
        g.put(0, [9, 10], "s").put(1, range(8, 12), "s").put(2, range(3, 17), "s").put(3, range(8, 12), "s")
        g.rect(4, 7, 8, 11, "s").put(7, [7, 12], "s")
        for i in range(5):
            c = (i * 5 + k * 2) % W
            g.put(5 + i % 2, [c, (c + 1) % W], "c")
        frames.append(g.rows())
    return frames, {"s": "#E8E4DA", "m": "#2F5D3A", "c": "#B8C4D0"}, ["s"]


def mbs_sprite():
    frames = []
    for k in range(4):
        g = Grid()
        for x0 in (3, 8, 13):
            g.rect(3, 10, x0, x0 + 2, "b")
            for r in range(4, 10, 2):
                g.put(r, [x0 + (r + k) % 3], "y")
        g.put(2, range(2, 18), "p").put(2, [18], "p")
        g.put(11, range(0, W), "w")
        for i in range(3):
            c = 4 + i * 5 + (k % 2)
            g.put(1, [c], "l").put(0, [c + 1], "l")
        frames.append(g.rows())
    return frames, {"b": "#B8C0CC", "p": "#8090A8", "w": "#2A6FB0", "l": "#9BE6FF", "y": "#FFE08A"}, ["l"]


# ---------- Scenes ----------

def paris():
    canvas = p.vertical((18, 20, 48), (74, 52, 96), 1.3)
    y, x = grid_xy()
    p.stars(canvas, 500, H * 0.5, seed=301, tint=(230, 225, 255))
    p.glow(canvas, 1950, 980, 520, (255, 190, 120), 0.25)

    def roofs(d):
        rng = np.random.default_rng(302)
        xx = 900
        while xx < W:
            w = int(rng.integers(120, 220))
            top = 1080 - int(rng.integers(60, 140))
            d.polygon([(xx, 1150), (xx, top + 30), (xx + 20, top), (xx + w - 20, top), (xx + w, top + 30), (xx + w, 1150)], fill=(24, 22, 40))
            for cx in range(xx + 25, xx + w - 20, 45):
                d.rectangle([cx, top - 18, cx + 10, top], fill=(24, 22, 40))
            xx += w + int(rng.integers(0, 8))

    def eiffel(d):
        fill = (40, 30, 30)
        cx, base, h = 1950, 1150, 1000
        d.polygon([(cx - 6, base - h - 60), (cx + 6, base - h - 60), (cx + 16, base - h), (cx - 16, base - h)], fill=fill)
        d.polygon([(cx - 16, base - h), (cx + 16, base - h), (cx + 70, base - 520), (cx - 70, base - 520)], fill=fill)
        d.rectangle([cx - 90, base - 530, cx + 90, base - 505], fill=fill)
        d.polygon([(cx - 75, base - 505), (cx + 75, base - 505), (cx + 150, base - 300), (cx - 150, base - 300)], fill=fill)
        d.rectangle([cx - 175, base - 310, cx + 175, base - 280], fill=fill)
        d.polygon([(cx - 160, base - 280), (cx - 40, base - 280), (cx - 110, base - 120), (cx - 260, base)], fill=fill)
        d.polygon([(cx + 160, base - 280), (cx + 40, base - 280), (cx + 110, base - 120), (cx + 260, base)], fill=fill)
        d.arc([cx - 150, base - 230, cx + 150, base + 90], 180, 360, fill=fill, width=16)

    draw_on(canvas, roofs)
    draw_on(canvas, eiffel)
    tower = p.shape_mask(eiffel, binary=True)
    p.add_light(canvas, (255, 190, 90), tower * (0.35 + 0.25 * p.noise(W, H, 40, 2, 303)))
    p.sprinkle(canvas, 120, (1700, 150, 2200, 1150), (255, 245, 210), sizes=(1.5, 2.0), blur=1, seed=304, strength=0.6)
    beam = p.shape_mask(lambda d: d.polygon([(1950, 90), (2560, 0), (2560, 60)], fill=255), blur=20)
    p.add_light(canvas, (255, 230, 160), beam * 0.18)
    water(canvas, 1150, (16, 16, 34), [(1950, (255, 200, 120), 220)], 305)
    p.readable(canvas)
    return p.finish(canvas)


def tokyo():
    canvas = p.vertical((22, 14, 44), (110, 50, 110), 1.4)
    y, x = grid_xy()
    p.stars(canvas, 300, H * 0.35, seed=311, tint=(255, 220, 255))

    def fuji(d):
        d.polygon([(900, 1100), (1450, 560), (1560, 560), (2150, 1100)], fill=(58, 46, 96))
        d.polygon([(1340, 670), (1450, 560), (1560, 560), (1680, 680), (1600, 700), (1540, 660), (1480, 705), (1410, 670)], fill=(236, 230, 250))

    draw_on(canvas, fuji)
    skyline(canvas, 1180, 1000, W, (160, 460), (20, 16, 36), 312, [(255, 120, 200), (122, 162, 247), (255, 214, 120)])

    def skytree(d):
        cx, base = 2150, 1240
        d.polygon([(cx - 70, base), (cx - 22, base - 700), (cx + 22, base - 700), (cx + 70, base)], fill=(28, 24, 46))
        d.rectangle([cx - 30, base - 1180, cx + 30, base - 700], fill=(28, 24, 46))
        d.ellipse([cx - 75, base - 760, cx + 75, base - 690], fill=(28, 24, 46))
        d.ellipse([cx - 55, base - 1000, cx + 55, base - 950], fill=(28, 24, 46))
        d.rectangle([cx - 6, base - 1330, cx + 6, base - 1180], fill=(28, 24, 46))

    draw_on(canvas, skytree)
    tree = p.shape_mask(skytree, binary=True)
    p.add_light(canvas, (150, 140, 255), tree * 0.35)
    for yy in (535, 270):
        p.glow(canvas, 2150, yy, 90, (120, 170, 255), 0.6)
    p.sprinkle(canvas, 220, (1100, 0, W, 1300), (255, 183, 205), sizes=(2, 3, 4), blur=1, seed=313, strength=0.7)
    p.blend(canvas, (16, 12, 28), (y > 1240).astype(float))
    p.readable(canvas)
    return p.finish(canvas)


def new_york():
    canvas = p.vertical((8, 14, 34), (30, 44, 78), 1.1)
    y, x = grid_xy()
    p.stars(canvas, 400, H * 0.45, seed=321)
    p.moon(canvas, 1500, 300, 70, color=(240, 240, 230), halo=(140, 170, 255))
    skyline(canvas, 1130, 1050, W, (200, 620), (14, 18, 32), 322, [(255, 214, 140), (255, 240, 200), (150, 190, 255)], 0.22)

    def empire(d):
        cx, base, fill = 2050, 1130, (12, 15, 28)
        d.rectangle([cx - 120, base - 520, cx + 120, base], fill=fill)
        d.rectangle([cx - 90, base - 760, cx + 90, base - 520], fill=fill)
        d.rectangle([cx - 60, base - 900, cx + 60, base - 760], fill=fill)
        d.rectangle([cx - 35, base - 980, cx + 35, base - 900], fill=fill)
        d.polygon([(cx - 18, base - 980), (cx + 18, base - 980), (cx + 6, base - 1120), (cx - 6, base - 1120)], fill=fill)
        d.line([(cx, base - 1120), (cx, base - 1230)], fill=fill, width=6)

    def liberty(d):
        sx, base, fill = 1300, 1180, (20, 40, 46)
        d.polygon([(sx - 60, base), (sx - 40, base - 90), (sx + 40, base - 90), (sx + 60, base)], fill=fill)
        d.polygon([(sx - 22, base - 90), (sx - 16, base - 260), (sx + 16, base - 260), (sx + 22, base - 90)], fill=fill)
        d.ellipse([sx - 14, base - 290, sx + 14, base - 258], fill=fill)
        d.line([(sx + 12, base - 240), (sx + 34, base - 330)], fill=fill, width=10)
        d.polygon([(sx + 26, base - 330), (sx + 44, base - 330), (sx + 35, base - 360)], fill=(255, 200, 100))

    draw_on(canvas, empire)
    p.glow(canvas, 2050, 1130 - 940, 70, (255, 90, 90), 0.6)
    p.glow(canvas, 2050, 1130 - 820, 110, (255, 255, 255), 0.25)
    water(canvas, 1180, (10, 16, 30), [(2050, (255, 210, 150), 260), (1500, (200, 210, 255), 120)], 323)
    draw_on(canvas, liberty)
    p.glow(canvas, 1335, 1180 - 345, 40, (255, 190, 90), 0.7)
    p.sprinkle(canvas, 400, (900, 0, W, H), (235, 240, 255), sizes=(1.5, 2.5, 3.5), blur=1, seed=324, strength=0.55)
    p.readable(canvas)
    return p.finish(canvas)


def london():
    canvas = p.vertical((26, 32, 44), (58, 66, 82), 1.0)
    y, x = grid_xy()
    p.add_light(canvas, (90, 100, 120), p.noise(W, H, 3, 5, 331) * np.clip(1 - y / 900, 0, 1) * 0.25)

    def eye(d):
        cx, cy, r = 1250, 760, 300
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(30, 34, 46), width=14)
        for a in range(0, 360, 20):
            rad = math.radians(a)
            d.line([(cx, cy), (cx + r * math.cos(rad), cy + r * math.sin(rad))], fill=(30, 34, 46), width=4)
        d.polygon([(cx - 10, cy), (cx + 10, cy), (cx + 120, 1130), (cx - 120, 1130)], fill=(30, 34, 46))

    def bridge(d):
        fill = (26, 28, 40)
        for tx in (1550, 1850):
            d.rectangle([tx - 45, 640, tx + 45, 1130], fill=fill)
            d.polygon([(tx - 55, 640), (tx, 540), (tx + 55, 640)], fill=fill)
        d.rectangle([1595, 720, 1805, 750], fill=fill)
        d.rectangle([1300, 940, 2100, 970], fill=fill)
        d.line([(1300, 870), (1505, 950)], fill=fill, width=10)
        d.line([(2100, 870), (1895, 950)], fill=fill, width=10)

    def bigben(d):
        fill = (34, 30, 30)
        cx, base = 2260, 1130
        d.rectangle([cx - 70, base - 760, cx + 70, base], fill=fill)
        d.rectangle([cx - 85, base - 900, cx + 85, base - 760], fill=fill)
        d.polygon([(cx - 85, base - 900), (cx, base - 1150), (cx + 85, base - 900)], fill=fill)
        d.line([(cx, base - 1150), (cx, base - 1230)], fill=fill, width=6)

    draw_on(canvas, eye)
    p.add_light(canvas, (200, 90, 140), p.shape_mask(eye, blur=3, binary=True) * 0.35)
    draw_on(canvas, bridge)
    draw_on(canvas, bigben)
    clock = (p.radial(2260, 1130 - 830, 55) < 1).astype(float)
    p.blend(canvas, (250, 230, 170), clock)
    p.glow(canvas, 2260, 1130 - 830, 140, (255, 210, 130), 0.45)
    water(canvas, 1130, (20, 26, 38), [(2260, (255, 210, 140), 160), (1700, (200, 200, 220), 260)], 333)
    p.readable(canvas)
    return p.finish(canvas)


def dubai():
    canvas = p.vertical((24, 22, 54), (196, 120, 70), 1.7)
    y, x = grid_xy()
    p.stars(canvas, 500, H * 0.45, seed=341, tint=(255, 240, 220))
    p.glow(canvas, 1800, 1100, 600, (255, 170, 90), 0.4)
    p.blend(canvas, (90, 56, 52), p.ridge_mask(1140, 40, 1.5, 342))
    skyline(canvas, 1160, 1150, W, (120, 380), (36, 26, 40), 343, [(255, 220, 150), (255, 190, 120)], 0.12)

    def burj(d):
        cx, base, fill = 2050, 1160, (28, 22, 36)
        steps = [(150, 0), (130, 160), (110, 330), (90, 500), (70, 660), (52, 800), (36, 930), (22, 1040)]
        for half, lift in steps:
            d.rectangle([cx - half, base - lift - 170, cx + half * 0.7, base - lift], fill=fill)
        d.polygon([(cx - 14, base - 1210), (cx + 8, base - 1210), (cx, base - 1380)], fill=fill)

    def burj_al_arab(d):
        bx, base, fill = 1350, 1240, (40, 30, 44)
        d.polygon([(bx, base), (bx, base - 420), (bx + 30, base - 420), (bx + 230, base)], fill=fill)
        d.line([(bx, base - 420), (bx + 30, base - 470)], fill=fill, width=8)

    draw_on(canvas, burj)
    p.glow(canvas, 2050, 1160 - 1380, 30, (255, 90, 90), 0.8)
    p.add_light(canvas, (255, 200, 140), p.shape_mask(burj, binary=True) * 0.2)
    water(canvas, 1240, (30, 26, 44), [(1800, (255, 180, 110), 300)], 344)
    draw_on(canvas, burj_al_arab)
    p.add_light(canvas, (120, 160, 255), p.shape_mask(burj_al_arab, blur=4, binary=True) * 0.35)
    p.readable(canvas)
    return p.finish(canvas)


def rome():
    canvas = p.vertical((40, 24, 54), (220, 120, 70), 1.6)
    y, x = grid_xy()
    p.glow(canvas, 1700, 1050, 500, (255, 170, 90), 0.4)

    def domes(d):
        fill = (46, 28, 34)
        d.rectangle([900, 1000, 1700, 1200], fill=fill)
        d.chord([1250, 760, 1450, 960], 180, 360, fill=fill)
        d.rectangle([1250, 855, 1450, 1000], fill=fill)
        d.rectangle([1335, 700, 1365, 770], fill=fill)
        for px in (1000, 1580, 2450):
            d.line([(px, 1200), (px + 20, 900)], fill=fill, width=14)
            d.ellipse([px - 110, 830, px + 150, 930], fill=fill)

    def colosseum(d):
        cx, base = 2080, 1200
        d.polygon([(cx - 420, base), (cx - 420, base - 380), (cx + 260, base - 420), (cx + 300, base - 300), (cx + 420, base - 250), (cx + 420, base)], fill=(70, 44, 36))
        for row, top in enumerate((base - 340, base - 230, base - 120)):
            for k in range(-9, 10):
                ax = cx + k * 44
                if ax + 30 > cx + 420 or (row == 0 and ax > cx + 250):
                    continue
                d.rectangle([ax, top, ax + 26, top + 70], fill=(30, 18, 16))
                d.chord([ax, top - 13, ax + 26, top + 13], 180, 360, fill=(30, 18, 16))

    draw_on(canvas, domes)
    draw_on(canvas, colosseum)
    arches = p.shape_mask(colosseum, binary=True)
    p.add_light(canvas, (255, 170, 80), p.shape_mask(lambda d: [d.rectangle([2080 + k * 44 + 3, 1200 - 230 + 6, 2080 + k * 44 + 23, 1200 - 230 + 66], fill=255) for k in range(-9, 6)], blur=3) * 0.8)
    p.add_light(canvas, (255, 150, 80), arches * 0.12)
    p.sprinkle(canvas, 70, (1200, 600, W, 1150), (255, 230, 140), sizes=(2.0, 2.5), seed=351, strength=0.6)
    p.blend(canvas, (30, 18, 22), (y > 1200).astype(float))
    p.readable(canvas)
    return p.finish(canvas)


def seoul():
    canvas = p.vertical((8, 18, 34), (26, 52, 70), 1.1)
    y, x = grid_xy()
    p.stars(canvas, 600, H * 0.6, seed=361)
    p.blend(canvas, (22, 38, 44), p.ridge_mask(820, 160, 2.2, 362))
    namsan = p.shape_mask(lambda d: d.chord([1650, 760, 2450, 1500], 180, 360, fill=255))
    p.blend(canvas, (18, 32, 36), namsan)

    def tower(d):
        cx, top = 2050, 330
        fill = (30, 40, 52)
        d.rectangle([cx - 14, top + 120, cx + 14, 790], fill=fill)
        d.rectangle([cx - 70, top + 120, cx + 70, top + 200], fill=fill)
        d.rectangle([cx - 4, top - 60, cx + 4, top + 120], fill=fill)

    draw_on(canvas, tower)
    p.blend(canvas, (255, 120, 170), np.clip(1.4 - p.radial(2050, 490, 70) * 1.2, 0, 1) * ((y > 455) & (y < 525)))
    p.glow(canvas, 2050, 490, 160, (255, 107, 157), 0.45)
    skyline(canvas, 1150, 1000, W, (100, 300), (14, 22, 30), 363, [(255, 230, 170), (150, 220, 255)], 0.18)

    def hanok(d):
        fill = (12, 16, 22)
        for hx, w in ((1250, 360), (1700, 300)):
            base = 1210
            d.rectangle([hx, base - 90, hx + w, base], fill=fill)
            d.polygon([(hx - 70, base - 80), (hx - 20, base - 150), (hx + w + 20, base - 150), (hx + w + 70, base - 80), (hx + w, base - 95), (hx, base - 95)], fill=fill)

    draw_on(canvas, hanok)
    p.blend(canvas, (10, 14, 20), (y > 1210).astype(float))
    p.sprinkle(canvas, 380, (900, 0, W, H), (230, 240, 255), sizes=(1.5, 2.5, 3.0), blur=1, seed=364, strength=0.5)
    p.readable(canvas)
    return p.finish(canvas)


def sydney():
    canvas = p.vertical((14, 22, 50), (60, 70, 120), 1.2)
    y, x = grid_xy()
    p.stars(canvas, 700, H * 0.55, seed=371)

    def harbour_bridge(d):
        fill = (22, 26, 44)
        d.arc([900, 700, 1700, 1500], 200, 340, fill=fill, width=36)
        d.rectangle([880, 1050, 1720, 1075], fill=fill)
        for px in (950, 1650):
            d.rectangle([px - 40, 930, px + 40, 1150], fill=fill)
        for k in range(9):
            hx = 1020 + k * 70
            d.line([(hx, 1050), (hx, 820 + abs(k - 4) ** 1.6 * 14)], fill=fill, width=6)

    def opera(d):
        base = 1150
        d.rectangle([1800, base - 30, 2450, base + 10], fill=(70, 62, 60))
        for sx, h, w in ((1850, 300, 240), (2020, 360, 260), (2200, 260, 210), (2340, 190, 150)):
            d.polygon([(sx, base - 30), (sx + w * 0.15, base - h), (sx + w * 0.55, base - h * 0.75), (sx + w, base - 30)], fill=(236, 232, 222))
            d.line([(sx + w * 0.15, base - h), (sx + w * 0.42, base - 30)], fill=(196, 190, 176), width=6)

    draw_on(canvas, harbour_bridge)
    water(canvas, 1150, (12, 20, 42), [(2100, (255, 240, 220), 280), (1300, (200, 210, 255), 200)], 372)
    draw_on(canvas, opera)
    p.add_light(canvas, (255, 210, 160), p.shape_mask(opera, blur=24, binary=True) * 0.25)
    p.readable(canvas)
    return p.finish(canvas)


def rio():
    canvas = p.vertical((26, 20, 60), (240, 130, 110), 1.8)
    y, x = grid_xy()
    p.stars(canvas, 300, H * 0.4, seed=381, tint=(255, 230, 230))

    def mountains(d):
        d.polygon([(900, 1150), (1150, 760), (1260, 700), (1380, 790), (1500, 1150)], fill=(40, 34, 60))
        d.polygon([(1450, 1150), (1560, 960), (1640, 940), (1700, 1150)], fill=(40, 34, 60))
        d.polygon([(1750, 1150), (1950, 640), (2080, 560), (2230, 650), (2500, 1150)], fill=(30, 28, 50))

    def christ(d):
        cx, base, fill = 2080, 560, (238, 232, 222)
        d.rectangle([cx - 16, base - 40, cx + 16, base], fill=fill)
        d.polygon([(cx - 26, base - 40), (cx - 16, base - 190), (cx + 16, base - 190), (cx + 26, base - 40)], fill=fill)
        d.rectangle([cx - 150, base - 185, cx + 150, base - 165], fill=fill)
        d.ellipse([cx - 14, base - 222, cx + 14, base - 190], fill=fill)

    draw_on(canvas, mountains)
    draw_on(canvas, christ)
    p.glow(canvas, 2080, 440, 200, (255, 240, 220), 0.3)
    water(canvas, 1150, (24, 22, 50), [(1700, (255, 160, 130), 380)], 382)
    lights = p.shape_mask(lambda d: [d.ellipse([lx - 2, 1135 + (lx % 7), lx + 2, 1139 + (lx % 7)], fill=255) for lx in range(950, 2450, 11)], blur=1)
    p.add_light(canvas, (255, 210, 140), lights * 1.2 + p.shape_mask(lambda d: d.rectangle([950, 1130, 2450, 1150], fill=255), blur=14) * 0.3)
    p.sprinkle(canvas, 60, (1200, 700, W, 1100), (255, 240, 160), sizes=(2.0, 2.5), seed=383, strength=0.5)
    p.readable(canvas)
    return p.finish(canvas)


def singapore():
    canvas = p.vertical((10, 14, 30), (34, 44, 80), 1.1)
    y, x = grid_xy()
    skyline(canvas, 1120, 1000, 1700, (200, 520), (16, 20, 34), 391, [(255, 220, 150), (160, 200, 255)], 0.2)

    def mbs(d):
        fill = (30, 36, 56)
        for tx in (1880, 2060, 2240):
            d.polygon([(tx - 50, 1120), (tx - 40, 660), (tx + 40, 660), (tx + 60, 1120)], fill=fill)
        d.polygon([(1790, 620), (2380, 610), (2420, 645), (1800, 660)], fill=fill)

    def supertrees(d):
        for sx, h in ((1250, 420), (1400, 520), (1560, 380)):
            d.polygon([(sx - 18, 1180), (sx - 6, 1180 - h), (sx + 6, 1180 - h), (sx + 18, 1180)], fill=(30, 40, 50))
            d.chord([sx - 110, 1180 - h - 60, sx + 110, 1180 - h + 60], 180, 360, fill=(30, 40, 50))

    draw_on(canvas, mbs)
    tower_mask = p.shape_mask(mbs, binary=True)
    windows = ((y // 22) % 2 == 0) & ((x // 16) % 2 == 0) & (p.noise(W, H, 80, 1, 392) > 0.45)
    p.add_light(canvas, (255, 220, 160), tower_mask * windows * 0.7)
    for k in range(4):
        beam = p.shape_mask(lambda d, k=k: d.line([(2080, 610), (1700 + k * 260, 0)], fill=255, width=6), blur=6)
        p.add_light(canvas, (150, 230, 255), beam * 0.35)
    draw_on(canvas, supertrees)
    for sx, h, color in ((1250, 420, (255, 90, 200)), (1400, 520, (120, 220, 255)), (1560, 380, (180, 255, 120))):
        p.glow(canvas, sx, 1180 - h, 120, color, 0.5)
    water(canvas, 1180, (12, 18, 36), [(2080, (255, 220, 160), 260), (1400, (150, 200, 255), 200)], 393)
    p.readable(canvas)
    return p.finish(canvas)
