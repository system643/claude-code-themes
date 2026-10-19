"""Checks the themes in plugin/themes and rebuilds the gallery.

- gallery/index.json: the list the app reads for "Discover";
- gallery/previews/<id>.png: a preview (pixel art on the theme's background).

Usage: python scripts/build_gallery.py [--check]
With --check, fails (exit code 1) on any problem without writing anything:
that's what the pull request check runs.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THEMES = ROOT / "plugin" / "themes"
GALLERY = ROOT / "gallery"
ALLOWED = {".json", ".png", ".jpg", ".jpeg", ".gif", ".wav", ".ogg", ".md"}
MAX_FILE = 8 * 1024 * 1024
MAX_THEME = 20 * 1024 * 1024
REQUIRED = ["id", "name", "tagline", "emoji", "colors", "quotes", "terminal"]
HEX = re.compile(r"#[0-9a-fA-F]{6}")
# The terminal scheme's colors: the app writes them into terminal config files.
TERMINAL_COLORS = ["background", "foreground", "cursorColor", "selectionBackground", "black", "red", "green", "yellow", "blue", "purple",
                   "cyan", "white", "brightBlack", "brightRed", "brightGreen", "brightYellow", "brightBlue", "brightPurple", "brightCyan", "brightWhite"]


def is_hex(value):
    return isinstance(value, str) and HEX.fullmatch(value) is not None


def inside(folder, relative):
    """`relative` names a file of the theme, without leaving its folder."""
    return isinstance(relative, str) and (folder / relative).resolve().is_relative_to(folder.resolve()) and (folder / relative).is_file()


def luminance(hex_color):
    channels = [int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def check_theme(folder):
    problems = []
    path = folder / "theme.json"
    try:
        theme = json.loads(path.read_text(encoding="utf-8"))
    except Exception as error:
        return None, [f"{path}: unreadable JSON ({error})"]

    for key in REQUIRED:
        if key not in theme:
            problems.append(f"{folder.name}: missing field \"{key}\"")
    if theme.get("id") != folder.name:
        problems.append(f"{folder.name}: \"id\" must match the folder name")

    terminal = theme.get("terminal", {})
    for key in TERMINAL_COLORS:
        if key in terminal and not is_hex(terminal[key]):
            problems.append(f"{folder.name}: terminal.{key} must be a #RRGGBB color")
    for key, value in theme.get("colors", {}).items():
        if not is_hex(value):
            problems.append(f"{folder.name}: colors.{key} must be a #RRGGBB color")
    background, foreground = terminal.get("background"), terminal.get("foreground")
    if is_hex(background) and is_hex(foreground):
        ratio = contrast(background, foreground)
        if ratio < 4.5:
            problems.append(f"{folder.name}: text hard to read on the background (contrast {ratio:.1f}, 4.5 minimum)")

    art = theme.get("pixelArt")
    if art:
        frames = art.get("frames", [])
        sizes = {(len(f), len(row)) for f in frames for row in f} or {(0, 0)}
        if len(sizes) != 1:
            problems.append(f"{folder.name}: every pixel-art frame must be the same size")
        if not all(is_hex(color) for color in art.get("palette", {}).values()):
            problems.append(f"{folder.name}: pixel-art palette colors must be #RRGGBB")
        palette = set(art.get("palette", {}))
        used = {c for f in frames for row in f for c in row if c != "."}
        if used - palette:
            problems.append(f"{folder.name}: colors missing from the palette: {''.join(sorted(used - palette))}")

    total = 0
    for file in folder.rglob("*"):
        if not file.is_file():
            continue
        size = file.stat().st_size
        total += size
        if file.suffix.lower() not in ALLOWED:
            problems.append(f"{folder.name}: file not allowed {file.relative_to(folder)} (allowed types: {', '.join(sorted(ALLOWED))})")
        if size > MAX_FILE:
            problems.append(f"{folder.name}: {file.relative_to(folder)} is over 8 MB")
    if total > MAX_THEME:
        problems.append(f"{folder.name}: the theme is over 20 MB in total")

    for kind, file in theme.get("sounds", {}).items():
        if not inside(folder, file):
            problems.append(f"{folder.name}: sound \"{kind}\" not found in the theme folder ({file})")
    images = [terminal.get("effects", {}).get("backgroundImage")] + [w.get("file") for w in theme.get("wallpapers", [])]
    for image in filter(None, images):
        if not inside(folder, image):
            problems.append(f"{folder.name}: wallpaper not found in the theme folder ({image})")
    return theme, problems


def preview(theme, out):
    from PIL import Image

    background = theme["terminal"]["background"]
    art = theme.get("pixelArt")
    image = Image.new("RGB", (480, 270), background)
    if art:
        frame = art["frames"][0]
        scale = min(360 // len(frame[0]), 200 // len(frame))
        left = (480 - len(frame[0]) * scale) // 2
        top = (270 - len(frame) * scale) // 2
        for y, row in enumerate(frame):
            for x, key in enumerate(row):
                color = art["palette"].get(key)
                if color:
                    image.paste(color, (left + x * scale, top + y * scale, left + (x + 1) * scale, top + (y + 1) * scale))
    # Pillow versions encode the same pixels differently: an unchanged preview
    # is left alone, so the gallery job only commits real changes.
    if out.exists() and Image.open(out).convert("RGB").tobytes() == image.tobytes():
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out, optimize=True)


def main():
    # The Windows console is not UTF-8 by default: "✓" would crash the print.
    sys.stdout.reconfigure(encoding="utf-8")
    check_only = "--check" in sys.argv
    entries, problems = [], []
    for folder in sorted(p for p in THEMES.iterdir() if p.is_dir()):
        theme, found = check_theme(folder)
        problems += found
        if theme is None:
            continue
        files = sorted(str(f.relative_to(folder)).replace("\\", "/") for f in folder.rglob("*") if f.is_file() and f.suffix != ".md")
        entries.append(
            {
                "id": theme["id"],
                "name": theme.get("name"),
                "tagline": theme.get("tagline", ""),
                "description": theme.get("description", ""),
                "emoji": theme.get("emoji", ""),
                "author": theme.get("author", ""),
                "universe": theme.get("universe", ""),
                "tags": theme.get("tags", []),
                "featured": bool(theme.get("featured", False)),
                "colors": theme.get("colors", {}),
                "background": theme.get("terminal", {}).get("background"),
                "preview": f"gallery/previews/{theme['id']}.png",
                "files": files,
            }
        )
        if not check_only:
            preview(theme, GALLERY / "previews" / f"{theme['id']}.png")

    if problems:
        print("\n".join(f"✗ {p}" for p in problems))
        sys.exit(1)
    if check_only:
        print(f"✓ {len(entries)} valid themes")
        return

    index_path = GALLERY / "index.json"
    previous = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {}
    weekly = previous.get("weekly") if previous.get("weekly") in {e["id"] for e in entries} else entries[0]["id"]
    index = {"version": 1, "weekly": weekly, "themes": entries}
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"✓ {len(entries)} themes, gallery written to {index_path}")


if __name__ == "__main__":
    main()
