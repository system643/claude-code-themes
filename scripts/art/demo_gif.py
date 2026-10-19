"""Builds docs/demo.gif and docs/showcase.png: a Claude Code session that
switches from theme to theme with /ambiance, and reacts to a failing then a
passing test run (wallpaper, animated pixel art, banner, status line, label).

Usage: python scripts/art/demo_gif.py
"""
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
THEMES = ROOT / "plugin" / "themes"
DOCS = ROOT / "docs"
SIZE = (960, 540)
# The GIF's story: each theme switches to the next one; Dracula runs the tests.
ORDER = ["paris", "synthwave", "dracula", "tokyo", "christmas", "digital-rain"]
MOOD_THEME = "dracula"
SHOWCASE = ["paris", "synthwave", "new-york", "dracula", "tokyo", "christmas", "london", "digital-rain"]
FONTS = [Path("C:/Windows/Fonts"), Path("/usr/share/fonts/truetype/dejavu"), Path("/System/Library/Fonts"), Path("/Library/Fonts")]


def font(names, size):
    for name in names:
        for folder in FONTS:
            if (folder / name).exists():
                return ImageFont.truetype(str(folder / name), size)
    return None


MONO = font(["CascadiaMono.ttf", "consola.ttf", "DejaVuSansMono.ttf", "Menlo.ttc"], 17) or ImageFont.load_default()
SMALL = font(["CascadiaMono.ttf", "consola.ttf", "DejaVuSansMono.ttf", "Menlo.ttc"], 14) or ImageFont.load_default()
# Glyphs that coding fonts often lack, and color emoji (both optional).
SYMBOL = font(["seguisym.ttf", "DejaVuSans.ttf", "Apple Symbols.ttf"], 17) or MONO
EMOJI = font(["seguiemj.ttf", "NotoColorEmoji.ttf", "Apple Color Emoji.ttc"], 16)
SYMBOLS = set("✻✗✓●")


def hex_rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def dim(color, factor):
    return tuple(int(c * factor) for c in color)


def write(draw, x, y, text, fill, emoji=""):
    """Draws `emoji` (color) then `text` (mono, symbols from a fallback font). Returns the end x."""
    if emoji and EMOJI is not None:
        draw.text((x, y + 1), emoji, font=EMOJI, embedded_color=True)
        x += 26
    for char in text:
        face = SYMBOL if char in SYMBOLS else MONO
        draw.text((x, y), char, font=face, fill=fill)
        x += MONO.getlength("m")
    return x


def width(text, emoji=""):
    return len(text) * MONO.getlength("m") + (26 if emoji and EMOJI is not None else 0)


class Theme:
    def __init__(self, theme_id):
        self.data = json.loads((THEMES / theme_id / "theme.json").read_text(encoding="utf-8"))
        term = self.data["terminal"]
        self.bg = hex_rgb(term["background"])
        self.fg = hex_rgb(term["foreground"])
        self.colors = {k: hex_rgb(v) for k, v in self.data["colors"].items()}
        self.red, self.green = hex_rgb(term["brightRed"]), hex_rgb(term["brightGreen"])
        wallpaper = Image.open(THEMES / theme_id / term["effects"]["backgroundImage"]).convert("RGB").resize(SIZE, Image.LANCZOS)
        self.base = Image.blend(Image.new("RGB", SIZE, self.bg), wallpaper, term["effects"].get("backgroundImageOpacity", 0.85))
        # Darker on the left and under the prompt, where the text goes.
        shade = Image.linear_gradient("L").rotate(90, expand=True).resize(SIZE)
        shade = shade.point(lambda v: int(150 * max(0.0, (v / 255 - 0.3) / 0.7) ** 1.4))
        footer = Image.linear_gradient("L").resize(SIZE).point(lambda v: int(170 * min(1.0, max(0.0, (v / 255 - 0.52) / 0.22))))
        mask = ImageChops.lighter(shade, footer)
        self.base = Image.composite(Image.new("RGB", SIZE, self.bg), self.base, mask)
        draw = ImageDraw.Draw(self.base)
        draw.rectangle([0, 0, SIZE[0], 30], fill=dim(self.bg, 0.6))
        for i, color in enumerate(((255, 95, 87), (254, 188, 46), (40, 200, 64))):
            draw.ellipse([14 + i * 20, 10, 26 + i * 20, 22], fill=color)
        draw.text((90, 8), f"Claude · {self.data['name']} — ~/projects/my-app", font=SMALL, fill=(220, 220, 220))

    def __getitem__(self, key):
        return self.data[key]

    def frames(self, mood):
        spec = self.data.get("moods", {}).get(mood, {})
        return spec.get("frames") or self.data["pixelArt"]["frames"]


def render(theme, tick, mood="idle", lines=(), prompt="", quote_index=0, working=False):
    """One frame of the session: transcript `lines` ([(text, color)]), banner, prompt and status line."""
    image = theme.base.copy()
    draw = ImageDraw.Draw(image)
    write(draw, 24, 48, "✻ Claude Code", theme.colors["accent"])
    write(draw, 24, 72, "~/projects/my-app", dim(theme.fg, 0.7))
    for i, (text, color) in enumerate(lines):
        write(draw, 24, 120 + i * 26, text, color)

    # The banner above the prompt: pixel art, title and the mood's quote.
    art = theme["pixelArt"]
    frames = theme.frames(mood)
    frame = frames[tick % len(frames)]
    top, scale = 318, 5
    for y, row in enumerate(frame):
        for x, key in enumerate(row):
            color = art["palette"].get(key)
            if color:
                draw.rectangle([24 + x * scale, top + y * scale, 24 + (x + 1) * scale - 1, top + (y + 1) * scale - 1], fill=hex_rgb(color))
    left = 24 + len(frame[0]) * scale + 24
    write(draw, left, top + 6, f"{theme['name'].upper()} · {theme['tagline']}"[:70], theme.colors["secondary"])
    spec = theme["moods"].get(mood, {}) if mood != "idle" else {}
    quotes = spec.get("quotes") or theme["quotes"]
    quote = quotes[quote_index % len(quotes)]
    write(draw, left, top + 30, f"“{quote[:60] + '…' if len(quote) > 62 else quote}”", theme.colors["muted"])
    write(draw, left, top + 54, "/ambiance to switch · hide", dim(theme.fg, 0.6))

    # The prompt, then the status line and the session label in the footer.
    draw.line([(16, 408), (SIZE[0] - 16, 408)], fill=dim(theme.fg, 0.5), width=1)
    end = write(draw, 24, 418, f"› {prompt}", theme.fg)
    if prompt and tick % 2 == 0:
        draw.rectangle([end + 1, 420, end + 9, 437], fill=theme.fg)
    draw.line([(16, 448), (SIZE[0] - 16, 448)], fill=dim(theme.fg, 0.5), width=1)
    status = spec.get("status") or theme["status"]["working" if working else "idle"]
    color = {"error": theme.red, "success": theme.green}.get(mood, theme.colors["accent"])
    write(draw, 24, 462, f"{theme['name']} · {status}", color, emoji=theme["emoji"])
    label = theme["name"]
    write(draw, SIZE[0] - 24 - width(label, theme["emoji"]), 462, label, theme.colors["secondary"], emoji=theme["emoji"])
    write(draw, 24, 494, "? for shortcuts", dim(theme.fg, 0.55))
    return image


def segment(theme, next_id):
    """The frames of one theme, as (image, duration in ms)."""
    out = []
    verbs = theme["spinnerVerbs"]
    ask = [("› fix the login bug", theme.fg)]
    for i in range(6):
        out.append((render(theme, i, lines=ask + [(f"✻ {verbs[i // 3 % len(verbs)]}…", theme.colors["accent"])], working=True), 250))
    done = ask + [("● Fixed: the session token was read before refresh.", theme.fg)]

    if theme["id"] == MOOD_THEME:
        run = done + [("› run the tests", theme.fg), ("● Bash(npm test)", theme.fg)]
        failed = run + [("  └ ✗ 2 failed, 46 passed", theme.red)]
        for i in range(8):
            out.append((render(theme, i, "error", failed), 250))
        passed = run + [("  └ ✓ 48 passed", theme.green)]
        for i in range(6):
            out.append((render(theme, i, "success", passed, quote_index=1), 250))
        done = passed

    for i in range(4):
        out.append((render(theme, i, lines=done), 250))
    command = f"/ambiance {next_id}"
    for n in range(2, len(command) + 1, 2):
        out.append((render(theme, n // 2, lines=done, prompt=command[:n]), 70))
    out.append((render(theme, 0, lines=done, prompt=command), 450))
    return out


def gif(frames, path):
    """Each theme gets one palette, so unchanged pixels stay identical and
    the GIF only stores what moves."""
    images, durations, palette, last = [], [], None, None
    for image, duration, theme in frames:
        if theme is not last:
            # The small but vivid colors (window buttons, test results) get
            # their own blocks so the palette keeps them.
            sample = Image.new("RGB", (SIZE[0], SIZE[1] + 120))
            sample.paste(image)
            vivid = [(255, 95, 87), (254, 188, 46), (40, 200, 64), theme.red, theme.green, theme.fg, *theme.colors.values()]
            for i, color in enumerate(vivid):
                sample.paste(color, (i * 80, SIZE[1], i * 80 + 80, SIZE[1] + 120))
            palette = sample.quantize(colors=255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
            last = theme
        images.append(image.quantize(palette=palette, dither=Image.Dither.NONE))
        durations.append(duration)
    images[0].save(path, save_all=True, append_images=images[1:], duration=durations, loop=0, optimize=False, disposal=1)


def main():
    themes = {theme_id: Theme(theme_id) for theme_id in ORDER}
    frames = []
    for i, theme_id in enumerate(ORDER):
        next_id = ORDER[(i + 1) % len(ORDER)]
        frames += [(image, duration, themes[theme_id]) for image, duration in segment(themes[theme_id], next_id)]
    DOCS.mkdir(exist_ok=True)
    gif(frames, DOCS / "demo.gif")

    stills = [render(Theme(theme_id), 0, lines=[("› fix the login bug", (220, 220, 220))]) for theme_id in SHOWCASE]
    rows = (len(stills) + 1) // 2
    sheet = Image.new("RGB", (SIZE[0] * 2 + 30, (SIZE[1] + 10) * rows + 10), (18, 18, 20))
    for i, still in enumerate(stills):
        sheet.paste(still, (10 + (i % 2) * (SIZE[0] + 10), 10 + (i // 2) * (SIZE[1] + 10)))
    sheet.resize((sheet.width // 2, sheet.height // 2), Image.LANCZOS).save(DOCS / "showcase.png", optimize=True)
    for name in ("demo.gif", "showcase.png"):
        print(DOCS / name, (DOCS / name).stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
