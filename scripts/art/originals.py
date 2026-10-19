"""Builds the three original showcase themes, free of any franchise:
Neon 2087 (cyberpunk), Aurora (far north), Grimoire (fantasy).

For each one: theme.json (animated pixel art included), wallpaper and sounds.
Usage: python scripts/art/originals.py
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).parent))
import sounds as synth  # noqa: E402
import paint as wp  # noqa: E402
import photos  # noqa: E402

ROOT = Path(__file__).resolve().parents[2] / "plugin" / "themes"
W, H = wp.W, wp.H
rng = np.random.default_rng(2087)


def grid():
    return [["."] * 20 for _ in range(12)]


def put(g, row, cols, ch):
    for c in cols:
        g[row][c] = ch


def rows(g):
    return ["".join(r) for r in g]


# ---------- Pixel art ----------

def neon_frames():
    frames, angry = [], []
    for scan in (6, 8, 10, 12, 10, 8):
        g = grid()
        put(g, 1, range(6, 14), "k")
        put(g, 2, range(4, 16), "k")
        for r in range(3, 9):
            put(g, r, range(3, 17), "k")
        put(g, 9, range(4, 16), "k")
        put(g, 10, range(6, 14), "k")
        put(g, 4, range(4, 16), "v")
        put(g, 5, range(4, 16), "v")
        put(g, 4, [scan, scan + 1], "w")
        put(g, 5, [scan, scan + 1], "w")
        put(g, 8, [7, 9, 11], "p")
        put(g, 0, [2, 17], "p")
        put(g, 11, [5, 14], "c")
        frames.append(rows(g))
    for blink in (True, False):
        g = grid()
        put(g, 1, range(6, 14), "k")
        put(g, 2, range(4, 16), "k")
        for r in range(3, 9):
            put(g, r, range(3, 17), "k")
        put(g, 9, range(4, 16), "k")
        put(g, 10, range(6, 14), "k")
        put(g, 4, range(4, 16), "r" if blink else "k")
        put(g, 5, range(4, 16), "r")
        put(g, 8, range(6, 14), "r" if blink else "p")
        angry.append(rows(g))
    return frames, angry


def aurora_frames():
    frames = []
    for phase in range(4):
        g = grid()
        for x in range(20):
            top = 1 + round(1.2 * math.sin((x + phase * 2) / 3))
            put(g, top, [x], "g")
            put(g, top + 1, [x], "c" if (x + phase) % 3 else "g")
            if (x + phase) % 4 == 0:
                put(g, top + 2, [x], "p")
        for x, y in ((2, 0), (16, 0), (9, 5), (18, 4)):
            if (x + phase) % 2 == 0:
                put(g, y, [x], "s")
        for x in range(20):
            height = max(0, 6 - abs(x - 6)) if x < 12 else max(0, 5 - abs(x - 15))
            for y in range(11 - height, 12):
                put(g, y, [x], "m")
            if height:
                put(g, 11 - height, [x], "w")
        frames.append(rows(g))
    angry = []
    for flash in (True, False):
        g = [list(r) for r in frames[0]]
        for x in range(20):
            for y in range(4):
                if g[y][x] in "gcp":
                    g[y][x] = "r" if flash else "p"
        angry.append(rows(g))
    return frames, angry


def grimoire_frames():
    frames = []
    for phase in range(4):
        g = grid()
        put(g, 9, range(2, 18), "b")
        put(g, 10, range(1, 19), "b")
        for r in range(6, 9):
            put(g, r, range(3, 10), "p")
            put(g, r, range(11, 17), "p")
        put(g, 5, range(4, 10), "p")
        put(g, 5, range(11, 16), "p")
        put(g, 6, [5, 6, 7], "l")
        put(g, 7, [5, 6], "l")
        put(g, 6, [12, 13, 14], "l")
        put(g, 7, [13, 14], "l")
        put(g, 5, [10], "b")
        put(g, 6, [10], "b")
        put(g, 7, [10], "b")
        put(g, 8, [10], "b")
        sparks = [((4 + phase * 3) % 18 + 1, 3 - phase % 3), ((13 + phase * 2) % 18 + 1, 1 + phase % 2), ((8 + phase * 5) % 18 + 1, phase % 3)]
        for x, y in sparks:
            put(g, max(0, y), [x], "y" if (x + phase) % 2 else "c")
        frames.append(rows(g))
    angry = []
    for flash in (True, False):
        g = [list(r) for r in frames[0]]
        for y in range(5):
            for x in range(20):
                if g[y][x] in "yc":
                    g[y][x] = "."
        put(g, 2, [6, 9, 12], "r" if flash else ".")
        put(g, 1, [8, 13], "." if flash else "r")
        angry.append(rows(g))
    return frames, angry


# ---------- Wallpapers ----------

def neon_wallpaper():
    canvas = wp.vertical((10, 6, 24), (40, 12, 46), curve=1.4)
    wp.add_light(canvas, (255, 40, 160), np.exp(-wp.radial(1900, 1150, 900)) * 0.45)
    wp.add_light(canvas, (0, 200, 255), np.exp(-wp.radial(900, 1250, 700)) * 0.25)
    image = Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8))
    draw = ImageDraw.Draw(image)
    local = np.random.default_rng(11)
    windows = Image.new("RGB", (W, H), (0, 0, 0))
    wd = ImageDraw.Draw(windows)
    for layer, (base, color) in enumerate(((1250, (16, 10, 28)), (1320, (10, 6, 18)))):
        xpos = -40
        while xpos < W:
            w = int(local.integers(70, 190))
            h = int(local.integers(250, 760 if layer == 0 else 520))
            draw.rectangle([xpos, base - h, xpos + w, H], fill=color)
            if local.random() < 0.3:
                draw.line([(xpos + w // 2, base - h), (xpos + w // 2, base - h - 60)], fill=color, width=3)
            for wy in range(base - h + 20, base, 26):
                for wx in range(xpos + 10, xpos + w - 10, 18):
                    if local.random() < 0.18:
                        tint = [(255, 60, 180), (0, 220, 255), (255, 200, 80), (160, 80, 255)][int(local.integers(0, 4))]
                        wd.rectangle([wx, wy, wx + 7, wy + 10], fill=tint)
            xpos += w + int(local.integers(4, 30))
    canvas = np.asarray(image, float).copy()
    glow = np.asarray(windows, float)
    canvas += glow * 0.55 + np.asarray(windows.filter(ImageFilter.GaussianBlur(10)), float) * 0.8
    # A neon sign and the rain.
    sign = wp.shape_mask(lambda d: d.rounded_rectangle([1720, 560, 1860, 860], radius=20, outline=255, width=8), blur=1)
    wp.add_light(canvas, (255, 60, 190), sign * 1.2 + wp.shape_mask(lambda d: d.rounded_rectangle([1720, 560, 1860, 860], radius=20, outline=255, width=8), blur=18) * 1.2)
    rain = Image.new("L", (W, H), 0)
    rd = ImageDraw.Draw(rain)
    for _ in range(1600):
        rx, ry = local.integers(0, W), local.integers(0, H)
        rd.line([(rx, ry), (rx - 8, ry + 40)], fill=int(local.integers(40, 120)), width=1)
    wp.add_light(canvas, (160, 180, 255), np.asarray(rain, float) / 255 * 0.5)
    wp.readable(canvas)
    return wp.finish(canvas)


def aurora_wallpaper():
    canvas = wp.vertical((4, 10, 20), (14, 30, 44), curve=0.9)
    y, x = np.mgrid[:H, :W]
    for offset, color, strength in ((0, (40, 220, 150), 0.7), (-140, (120, 90, 220), 0.4)):
        wave = 360 + offset + 140 * np.sin(x / 600 + 0.5) + 50 * np.sin(x / 210)
        curtain = np.exp(-((y - wave) / 190) ** 2) * (0.35 + 0.65 * wp.stretched(150, 3, 300 + offset)) * (x / W) ** 0.5
        wp.add_light(canvas, color, curtain * strength)
    wp.stars(canvas, 1500, H * 0.7, seed=61)
    for base, amp, scale, seed, color in ((950, 180, 2.5, 62, (30, 44, 60)), (1050, 120, 4, 63, (18, 28, 40))):
        mask = wp.ridge_mask(base, amp, scale, seed)
        wp.blend(canvas, color, mask)
        snow = mask * np.clip(1 - (y - (base - amp * 1.6)) / 120, 0, 1)
        wp.add_light(canvas, (140, 170, 190), snow * 0.25)
    lake = (y > 1160).astype(float)
    wp.blend(canvas, (8, 16, 24), lake)
    reflection = np.flipud(canvas.copy())
    canvas[:] = canvas * (1 - lake[..., None] * 0.35) + reflection * lake[..., None] * 0.35 * 0.6
    wp.readable(canvas)
    return wp.finish(canvas)


def grimoire_wallpaper():
    canvas = wp.vertical((14, 9, 20), (30, 18, 26), curve=1.2)
    image = Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8))
    draw = ImageDraw.Draw(image)
    local = np.random.default_rng(71)
    # Bookshelves.
    for shelf_y in range(260, 1300, 220):
        draw.rectangle([1150, shelf_y, W, shelf_y + 14], fill=(40, 24, 18))
        xpos = 1160
        while xpos < W - 20:
            w = int(local.integers(18, 42))
            h = int(local.integers(120, 190))
            tone = [(70, 30, 30), (40, 50, 80), (60, 70, 40), (90, 60, 30), (50, 30, 60)][int(local.integers(0, 5))]
            draw.rectangle([xpos, shelf_y - h, xpos + w, shelf_y], fill=tone)
            draw.line([(xpos + 4, shelf_y - h + 20), (xpos + w - 4, shelf_y - h + 20)], fill=(150, 120, 60), width=2)
            xpos += w + int(local.integers(1, 5))
    canvas = np.asarray(image, float).copy()
    canvas *= 0.55
    # Candles and their halos, floating runes.
    for cx, cy in ((1300, 1150), (1560, 930), (2200, 1180), (1900, 700)):
        wp.add_light(canvas, (255, 170, 80), np.exp(-wp.radial(cx, cy, 180) ** 2) * 0.6)
        candle = wp.shape_mask(lambda d, cx=cx, cy=cy: (d.rectangle([cx - 8, cy, cx + 8, cy + 70], fill=255)))
        wp.blend(canvas, (200, 180, 150), candle)
        flame = wp.shape_mask(lambda d, cx=cx, cy=cy: d.ellipse([cx - 7, cy - 26, cx + 7, cy - 2], fill=255), blur=2)
        wp.add_light(canvas, (255, 200, 110), flame * 2)
    runes = Image.new("L", (W, H), 0)
    rd = ImageDraw.Draw(runes)
    for _ in range(40):
        rx, ry = local.integers(1100, W - 60), local.integers(100, 1100)
        s = int(local.integers(10, 26))
        rd.line([(rx, ry), (rx, ry + s * 2)], fill=200, width=2)
        rd.line([(rx, ry + s // 2), (rx + s, ry)], fill=200, width=2)
        if local.random() < 0.5:
            rd.line([(rx, ry + s), (rx + s, ry + s * 2)], fill=200, width=2)
    wp.add_light(canvas, (120, 200, 255), np.asarray(runes.filter(ImageFilter.GaussianBlur(2)), float) / 255 * 0.9)
    wp.add_light(canvas, (140, 120, 255), np.asarray(runes.filter(ImageFilter.GaussianBlur(14)), float) / 255 * 0.8)
    wp.readable(canvas)
    return wp.finish(canvas)


# ---------- Sounds ----------

def tones(freqs, length=0.12, decay=0.25, wave="sine"):
    parts = []
    for f in freqs:
        t = synth.timeline(length + decay)
        osc = np.sin(2 * np.pi * f * t) if wave == "sine" else np.sign(np.sin(2 * np.pi * f * t)) * 0.5
        parts.append(osc * np.exp(-t / decay) * np.minimum(1, t / 0.004))
    out = np.zeros(int(synth.RATE * (length * len(freqs) + decay)) + 10)
    for i, p in enumerate(parts):
        start = int(i * length * synth.RATE)
        out[start : start + p.size] += p
    return out


def sounds_for(kind):
    if kind == "neon":
        return tones([523, 784, 1046], wave="square"), tones([659, 988, 1318, 1568], 0.08, wave="square"), tones([220, 165], 0.15, 0.3, wave="square")
    if kind == "aurora":
        return tones([880, 1320], 0.25, 1.2), tones([1046, 1318, 1568], 0.15, 1.0), tones([392, 370], 0.3, 0.8)
    return tones([1568, 2093, 2637, 3136], 0.06, 0.6), tones([1046, 1568, 2093], 0.1, 0.9), tones([311, 277, 247], 0.18, 0.5)


# ---------- Themes ----------

THEMES = {
    "neon-2087": {
        "name": "Neon 2087",
        "tagline": "Acid rain and city lights",
        "description": "A dense megacity glittering around the harbour at night.",
        "universe": "Original · Cyberpunk",
        "emoji": "🌃",
        "colors": {"accent": "#FF3DB4", "secondary": "#3DE8FF", "muted": "#B08CC8"},
        "banner": ["  [=======]  ", "  | >_  < |  ", "  [=======]  "],
        "palette": {"k": "#1C1430", "v": "#0FA3C4", "w": "#E8FFFF", "p": "#FF3DB4", "c": "#3DE8FF", "r": "#FF2A55"},
        "frames": neon_frames,
        "quotes": ["Connection established. The net is listening.", "It's raining on the city, the code stays dry.", "Implant updated, zero latency.", "In this city, even the bugs glow in neon.", "Upload complete. Next level."],
        "spinnerVerbs": ["Hacking the mainframe", "Decrypting the stream", "Recalibrating the implant", "Jacking into the net", "Compiling in neon", "Scanning the city"],
        "durationLines": ["Hacked in {d}", "Transferred in {d}", "Connected for {d}"],
        "status": {"idle": "standby", "working": "online"},
        "welcome": "Neon 2087: jacking into the net.",
        "moods": {"error": {"status": "red alert", "quotes": ["Intrusion detected: a test crashed.", "Corrupted signal. Tracing it back.", "System error. Stay cool, runner."]},
                  "success": {"status": "access granted", "quotes": ["Access granted. All green.", "System stable, the city breathes.", "Flawless run, runner."]}},
        "persona": ["You talk like a runner from a cyberpunk megacity: terse, efficient, a little jaded, with at most one network or neon metaphor per reply."],
        "terminal": {"name": "Claude · Neon 2087", "background": "#0C0718", "foreground": "#E6DCF5", "cursorColor": "#3DE8FF", "selectionBackground": "#3A1F5C",
                     "black": "#1C1430", "red": "#FF2A55", "green": "#3DFFA8", "yellow": "#FFD23D", "blue": "#3D8BFF", "purple": "#FF3DB4", "cyan": "#3DE8FF", "white": "#E6DCF5",
                     "brightBlack": "#5A4A78", "brightRed": "#FF6A88", "brightGreen": "#7DFFC6", "brightYellow": "#FFE27D", "brightBlue": "#7DB0FF", "brightPurple": "#FF7DCC", "brightCyan": "#8DF3FF", "brightWhite": "#FFFFFF",
                     "effects": {"backgroundImage": "assets/wallpaper.jpg", "backgroundImageOpacity": 0.85, "backgroundImageStretchMode": "uniformToFill", "shader": "crt", "cursorShape": "filledBox"}},
        "wallpaper": neon_wallpaper,
        "wallpaperName": "City in the rain",
        "sound": "neon",
    },
    "aurora": {
        "name": "Aurora",
        "tagline": "The far north sky",
        "description": "Northern lights swirling over the Lofoten islands.",
        "universe": "Original · Nature",
        "emoji": "🌌",
        "colors": {"accent": "#3DE0A0", "secondary": "#8FD3FF", "muted": "#8CA6B8"},
        "banner": ["   ~~~~~~~~   ", "  /\\    /\\   ", " /  \\/\\/  \\  "],
        "palette": {"g": "#3DE0A0", "c": "#5FD8E8", "p": "#9B7BFF", "s": "#FFFFFF", "m": "#2A3A4C", "w": "#DDEBF5", "r": "#FF6A6A"},
        "frames": aurora_frames,
        "quotes": ["The sky is dancing, take your time.", "A clear night for clear thinking.", "Every snowflake finds its place. So does every bug.", "The northern silence helps you think.", "The aurora rises over your code."],
        "spinnerVerbs": ["Following the lights", "Listening to the snow", "Breaking trail", "Watching the sky", "Stoking the campfire", "Reading the stars"],
        "durationLines": ["Gazed for {d}", "Hiked for {d}", "A {d} night"],
        "status": {"idle": "staying warm", "working": "under the lights"},
        "welcome": "Aurora: the sky lights up.",
        "moods": {"error": {"status": "blizzard", "quotes": ["A storm rolls in: a test fails.", "The wind shifts. Let's look at the error calmly.", "The ice cracked, we'll mend it."]},
                  "success": {"status": "clear skies", "quotes": ["Clear skies, all green.", "The aurora blazes: well done.", "The trail is set."]}},
        "persona": ["You speak with the calm of a far north guide: steady, warm, precise, with at most one image of snow, auroras or stars per reply."],
        "terminal": {"name": "Claude · Aurora", "background": "#06101C", "foreground": "#DCE9F2", "cursorColor": "#3DE0A0", "selectionBackground": "#1C3448",
                     "black": "#142232", "red": "#FF6A6A", "green": "#3DE0A0", "yellow": "#F2D27A", "blue": "#5FA8FF", "purple": "#9B7BFF", "cyan": "#5FD8E8", "white": "#DCE9F2",
                     "brightBlack": "#4A6278", "brightRed": "#FF9A9A", "brightGreen": "#8CF2C6", "brightYellow": "#F8E3A8", "brightBlue": "#9CC8FF", "brightPurple": "#C0A8FF", "brightCyan": "#A0ECF5", "brightWhite": "#FFFFFF",
                     "effects": {"backgroundImage": "assets/wallpaper.jpg", "backgroundImageOpacity": 0.85, "backgroundImageStretchMode": "uniformToFill", "shader": "snow", "cursorShape": "bar"}},
        "wallpaper": aurora_wallpaper,
        "wallpaperName": "Aurora over the frozen lake",
        "sound": "aurora",
    },
    "grimoire": {
        "name": "Grimoire",
        "tagline": "The wizards' library",
        "description": "Endless shelves of old books in a vaulted library.",
        "universe": "Original · Fantasy",
        "emoji": "📜",
        "colors": {"accent": "#FFB347", "secondary": "#C8A2FF", "muted": "#B0A090"},
        "banner": ["   .  *  .    ", "  _________   ", " /____|____\\  "],
        "palette": {"b": "#6B3A1E", "p": "#EADBC0", "l": "#9C8A6A", "y": "#FFD86B", "c": "#8FD8FF", "r": "#FF5A4A"},
        "frames": grimoire_frames,
        "quotes": ["Every function is a well-written spell.", "Runes never lie. Neither do logs.", "One page at a time, one bug at a time.", "Magic is mostly rigor.", "The grimoire opens to the right page."],
        "spinnerVerbs": ["Leafing through the grimoire", "Tracing a rune", "Brewing a potion", "Summoning a function", "Lighting a candle", "Deciphering a scroll"],
        "durationLines": ["Spell cast in {d}", "A {d} ritual", "Read for {d}"],
        "status": {"idle": "in the library", "working": "mid-spell"},
        "welcome": "Grimoire: the candles flicker to life.",
        "moods": {"error": {"status": "spell misfired", "quotes": ["The spell misfired: a test fails.", "A rune is drawn wrong. Let's reread it.", "Black smoke: we fix the formula."]},
                  "success": {"status": "spell cast", "quotes": ["Spell cast, all green.", "The runes glow: well done.", "The formula is perfect."]}},
        "persona": ["You talk like an old wizard librarian: learned, kind, mischievous, with at most one image of grimoires, runes or potions per reply."],
        "terminal": {"name": "Claude · Grimoire", "background": "#120B12", "foreground": "#EDE2CF", "cursorColor": "#FFB347", "selectionBackground": "#3A2632",
                     "black": "#22161E", "red": "#E0604E", "green": "#9CC77A", "yellow": "#FFB347", "blue": "#7AA2E0", "purple": "#C8A2FF", "cyan": "#8FD8D0", "white": "#EDE2CF",
                     "brightBlack": "#6A5560", "brightRed": "#FF8A7A", "brightGreen": "#BEE0A2", "brightYellow": "#FFD08A", "brightBlue": "#A8C4F0", "brightPurple": "#DEC6FF", "brightCyan": "#B4EAE4", "brightWhite": "#FFF8EC",
                     "effects": {"backgroundImage": "assets/wallpaper.jpg", "backgroundImageOpacity": 0.85, "backgroundImageStretchMode": "uniformToFill", "shader": "glow", "cursorShape": "underscore"}},
        "wallpaper": grimoire_wallpaper,
        "wallpaperName": "The candlelit library",
        "sound": "grimoire",
    },
}


def main():
    for theme_id, spec in THEMES.items():
        folder = ROOT / theme_id
        (folder / "assets").mkdir(parents=True, exist_ok=True)
        frames, angry = spec["frames"]()
        photo = photos.wallpaper_entry(theme_id)
        if photo is None:
            spec["wallpaper"]().save(folder / "assets" / "wallpaper.jpg", quality=90, optimize=True, progressive=True)
        for kind, signal in zip(("start", "success", "error"), sounds_for(spec["sound"])):
            synth.save(folder / "assets" / f"{kind}.wav", signal, gain=0.5)
        moods = spec["moods"]
        moods["error"]["frames"] = angry
        theme = {
            "$schema": "../../../docs/theme.schema.json",
            "id": theme_id,
            "name": spec["name"],
            "tagline": spec["tagline"],
            "description": spec["description"],
            "universe": spec["universe"],
            "author": "claude-code-themes",
            "featured": True,
            "emoji": spec["emoji"],
            "colors": spec["colors"],
            "banner": spec["banner"],
            "pixelArt": {"palette": spec["palette"], "fps": 4, "frames": frames},
            "quotes": spec["quotes"],
            "spinnerVerbs": spec["spinnerVerbs"],
            "durationLines": spec["durationLines"],
            "status": spec["status"],
            "welcome": spec["welcome"],
            "persona": spec["persona"],
            "moods": moods,
            "sounds": {"start": "assets/start.wav", "success": "assets/success.wav", "error": "assets/error.wav"},
            "wallpapers": [photo or {"name": spec["wallpaperName"], "file": "assets/wallpaper.jpg"}],
            "terminal": spec["terminal"],
        }
        (folder / "theme.json").write_text(json.dumps(theme, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("✓", theme_id)


if __name__ == "__main__":
    main()
