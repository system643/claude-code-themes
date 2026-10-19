"""Renders a theme's pixel art as a PNG, to check it or show it in the gallery.

Usage: python scripts/art/preview_pixelart.py plugin/themes/dracula/theme.json out.png
"""
import json
import sys

from PIL import Image

SCALE = 12


def hex_color(value):
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def main(theme_path, out_path):
    theme = json.load(open(theme_path, encoding="utf-8"))
    art = theme["pixelArt"]
    palette = {key: hex_color(color) for key, color in art["palette"].items()}
    background = hex_color(theme.get("terminal", {}).get("background", "#000000"))
    frames = art["frames"] + [f for mood in theme.get("moods", {}).values() for f in mood.get("frames", [])]
    height = len(frames[0])
    width = max(len(row) for row in frames[0])
    sheet = Image.new("RGB", ((width + 2) * len(frames) * SCALE, (height + 2) * SCALE), background)
    for index, frame in enumerate(frames):
        for y, row in enumerate(frame):
            for x, key in enumerate(row):
                if key in palette:
                    left = ((width + 2) * index + 1 + x) * SCALE
                    top = (1 + y) * SCALE
                    sheet.paste(palette[key], (left, top, left + SCALE, top + SCALE))
    sheet.save(out_path)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
