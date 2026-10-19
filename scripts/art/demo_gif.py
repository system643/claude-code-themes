"""Builds docs/demo.gif and docs/showcase.png: a Claude Code terminal
switching from theme to theme (wallpaper, animated pixel art, banner, status line).

Usage: python scripts/art/demo_gif.py
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
THEMES = ROOT / "plugin" / "themes"
DOCS = ROOT / "docs"
SIZE = (960, 540)
ORDER = ["paris", "synthwave", "new-york", "dracula", "tokyo", "christmas", "london", "digital-rain"]


def font(size):
    for name in ("CascadiaMono.ttf", "consola.ttf", "DejaVuSansMono.ttf", "Menlo.ttc"):
        for folder in (Path("C:/Windows/Fonts"), Path("/usr/share/fonts/truetype/dejavu"), Path("/System/Library/Fonts")):
            if (folder / name).exists():
                return ImageFont.truetype(str(folder / name), size)
    return ImageFont.load_default()


MONO, SMALL = font(17), font(14)


def hex_rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def terminal(theme, wallpaper, frame_index, verb_index):
    term = theme["terminal"]
    image = Image.new("RGB", SIZE, hex_rgb(term["background"]))
    opacity = term.get("effects", {}).get("backgroundImageOpacity", 0.85)
    image = Image.blend(image, wallpaper, opacity)
    draw = ImageDraw.Draw(image)

    # Window bar.
    draw.rectangle([0, 0, SIZE[0], 30], fill=tuple(int(c * 0.6) for c in hex_rgb(term["background"])))
    for i, color in enumerate(((255, 95, 87), (254, 188, 46), (40, 200, 64))):
        draw.ellipse([14 + i * 20, 10, 26 + i * 20, 22], fill=color)
    draw.text((90, 8), f"{theme['emoji'] if theme['emoji'].isascii() else ''}{theme['name']} — claude", font=SMALL, fill=(220, 220, 220))

    fg = hex_rgb(term["foreground"])
    colors = {k: hex_rgb(v) for k, v in theme["colors"].items()}
    draw.text((24, 50), "Claude Code v2.1", font=MONO, fill=fg)
    draw.text((24, 74), "~/projects/my-app", font=MONO, fill=tuple(int(c * 0.7) for c in fg))

    # Banner: animated pixel art, title, quote.
    art = theme.get("pixelArt")
    top = 330
    if art:
        frame = art["frames"][frame_index % len(art["frames"])]
        scale = 5
        for y, row in enumerate(frame):
            for x, key in enumerate(row):
                color = art["palette"].get(key)
                if color:
                    draw.rectangle([24 + x * scale, top + y * scale, 24 + (x + 1) * scale - 1, top + (y + 1) * scale - 1], fill=hex_rgb(color))
    left = 24 + 20 * 5 + 24
    title = f"{theme['name'].upper()} · {theme.get('tagline', '')}"
    draw.text((left, top + 6), title, font=MONO, fill=colors["secondary"])
    quote = theme["quotes"][verb_index % len(theme["quotes"])]
    if len(quote) > 62:
        quote = quote[:60] + "…"
    draw.text((left, top + 30), f"“{quote}”", font=MONO, fill=colors["muted"])
    draw.text((left, top + 54), "/ambiance to switch · hide", font=MONO, fill=tuple(int(c * 0.6) for c in fg))

    verbs = theme.get("spinnerVerbs", ["Thinking"])
    draw.text((24, 250), "› fix the login bug", font=MONO, fill=fg)
    draw.text((24, 276), f"* {verbs[verb_index % len(verbs)]}…", font=MONO, fill=colors["accent"])

    draw.line([(16, 420), (SIZE[0] - 16, 420)], fill=tuple(int(c * 0.5) for c in fg), width=1)
    draw.text((24, 430), "› ", font=MONO, fill=fg)
    draw.line([(16, 460), (SIZE[0] - 16, 460)], fill=tuple(int(c * 0.5) for c in fg), width=1)
    status = theme.get("status", {}).get("working", "working")
    draw.text((24, 474), f"{theme['name']} · {status}", font=MONO, fill=colors["accent"])
    return image


def main():
    frames, durations, stills = [], [], []
    for theme_id in ORDER:
        theme = json.loads((THEMES / theme_id / "theme.json").read_text(encoding="utf-8"))
        wall_path = THEMES / theme_id / theme["terminal"]["effects"]["backgroundImage"]
        wallpaper = Image.open(wall_path).convert("RGB").resize(SIZE, Image.LANCZOS)
        for i in range(10):
            frames.append(terminal(theme, wallpaper, i, i // 4))
            durations.append(250)
        stills.append(terminal(theme, wallpaper, 0, 0))

    DOCS.mkdir(exist_ok=True)
    small = [f.resize((720, 405), Image.LANCZOS).quantize(colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) for f in frames]
    small[0].save(DOCS / "demo.gif", save_all=True, append_images=small[1:], duration=durations, loop=0, optimize=True)

    rows = (len(stills) + 1) // 2
    sheet = Image.new("RGB", (SIZE[0] * 2 + 30, (SIZE[1] + 10) * rows + 10), (18, 18, 20))
    for i, still in enumerate(stills):
        sheet.paste(still, (10 + (i % 2) * (SIZE[0] + 10), 10 + (i // 2) * (SIZE[1] + 10)))
    sheet.resize((sheet.width // 2, sheet.height // 2), Image.LANCZOS).save(DOCS / "showcase.png", optimize=True)
    for name in ("demo.gif", "showcase.png"):
        print(DOCS / name, (DOCS / name).stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
