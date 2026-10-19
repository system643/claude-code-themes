"""Photo wallpapers: freely licensed photographs from Wikimedia Commons.

Each entry names a Commons file, the part of the picture to keep and a short
title. The script downloads the photo, crops it to 16:9, grades it so the
terminal text stays readable (darker on the left and at the bottom, where
Claude Code writes), and saves it as the theme's wallpaper. It also records the
author and license in photos.lock.json, in each theme.json and in
docs/CREDITS.md, so the generators can run offline afterwards.

Usage: python scripts/art/photos.py [theme-id ...]
"""
import hashlib
import io
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
THEMES = REPO / "plugin" / "themes"
CACHE = HERE / ".photo-cache"
LOCK = HERE / "photos.lock.json"
CREDITS = REPO / "docs" / "CREDITS.md"
API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "AmbianceThemeBuilder/0.3 (https://github.com/sytem643/claude-code-themes)"
SIZE = (2560, 1440)

# focus: where the crop is centered (0 to 1, left to right and top to bottom).
# zoom: the share of the largest 16:9 crop that is kept (1 keeps it all).
# lift: overall brightness (below 1 for bright photos). soften: blur radius on the text side.
# mirror: flips the photo so its subject moves away from the text.
PHOTOS = {
    "paris": {"file": "File:Eiffel Tower and Pont Alexandre III at night.jpg", "name": "The Eiffel Tower and the Seine at blue hour", "focus": (0.5, 0.5)},
    "tokyo": {"file": "File:Minato City, Tokyo, Japan (Night)-denoised.jpg", "name": "Tokyo Tower and Minato by night", "focus": (0.5, 0.5)},
    "new-york": {"file": "File:2024-11-17-Lower Manhattan-0593.jpg", "name": "Lower Manhattan lighting up at dusk", "focus": (0.5, 0.5)},
    "london": {"file": "File:Palace of Westminster, London - Feb 2007.jpg", "name": "Westminster and Big Ben at dusk", "focus": (0.6, 0.5)},
    "dubai": {"file": "File:Dubai skyline unsplash.jpg", "name": "The Dubai skyline reflected at night", "focus": (0.5, 0.5)},
    "rome": {"file": "File:Sant'Angelo bridge, dusk, Rome, Italy.jpg", "name": "St. Peter's dome over the Tiber at sunset", "focus": (0.5, 0.5)},
    "seoul": {"file": "File:N Seoul Tower view 2.jpg", "name": "Seoul by night from Namsan", "focus": (0.5, 0.5)},
    "rio": {"file": "File:Rio de Janeiro Mountains.jpg", "name": "Sugarloaf Mountain and Corcovado at sunset", "focus": (0.5, 0.5)},
    "sydney": {"file": "File:Sydney Opera House and Harbour Bridge Dusk (2) 2019-06-21.jpg", "name": "The Opera House and Harbour Bridge at dusk", "focus": (0.5, 0.5)},
    "singapore": {"file": "File:Marina Bay, Singapur, 2023-08-16, DD 87-89 HDR.jpg", "name": "Marina Bay reflected at night", "focus": (0.55, 0.5)},
    "abyss": {"file": "File:Meduse-Chrysaora hysoscella-Nausicaa-07-2024-Luc-Viatour.jpg", "name": "A compass jellyfish drifting in the dark", "focus": (0.5, 0.5)},
    "aurora": {"file": "File:Lofoten, Norway (Unsplash).jpg", "name": "Northern lights over the Lofoten", "focus": (0.5, 0.5)},
    "catppuccin": {"file": "File:Příchovice - old window and cat.jpg", "name": "A cat at an old wooden window", "focus": (0.5, 0.6)},
    "christmas": {"file": "File:Jaszczurówka at Winter.jpg", "name": "A wooden chapel in the snowy forest at night", "focus": (0.5, 0.5)},
    "dracula": {"file": "File:Хотинська фортеця в місячну ніч.jpg", "name": "Khotyn Fortress under the moon", "focus": (0.5, 0.5)},
    "everforest": {"file": "File:Foggy Fanal forest in Seixal, Porto Moniz, Madeira, 2023 May.jpg", "name": "The foggy laurel forest of Fanal, Madeira", "focus": (0.5, 0.5)},
    "grimoire": {"file": "File:Long Room Interior, Trinity College Dublin, Ireland - Diliff.jpg", "name": "The Long Room library, Trinity College Dublin", "focus": (0.5, 0.45), "soften": 4},
    "gruvbox": {"file": "File:2022-06-14 USA, AZ, Saguaro DSC 6133 DxO.jpg", "name": "Saguaros at sunset, Arizona", "focus": (0.5, 0.5)},
    "halloween": {"file": "File:Carved pumpkin as face (Unsplash).jpg", "name": "Jack-o'-lanterns glowing in the dark", "focus": (0.5, 0.5)},
    "lofi": {"file": "File:2016-02 Raindrops on windows Palace of Westminster.jpg", "name": "City lights through a rainy window", "focus": (0.5, 0.5)},
    "neon-2087": {"file": "File:Hong Kong Harbour Night 2019-06-11.jpg", "name": "Hong Kong harbour at night", "focus": (0.5, 0.5), "lift": 0.85, "soften": 6},
    "nord": {"file": "File:Table iceberg west of Sjuøyane, Arctic ocean.jpg", "name": "A table iceberg adrift in the Arctic Ocean", "focus": (0.5, 0.5), "mirror": True},
    "orbit": {"file": "File:Good Morning From the International Space Station.jpg", "name": "Night falls on Earth, seen from the ISS", "focus": (0.5, 0.5)},
    "rose-pine": {"file": "File:Pine trees sunset. (Unsplash).jpg", "name": "Pines against the evening sky", "focus": (0.5, 0.5), "lift": 1.15},
    "sakura": {"file": "File:Chuurei-tou Fujiyoshida 17025277650 c59733d6ba o.jpg", "name": "Chureito Pagoda, Mount Fuji and cherry blossoms", "focus": (0.5, 0.5), "author": "reggiepen (Flickr)"},
    "solarized": {"file": "File:Crimea, Ai-Petri, low clouds.jpg", "name": "Sunrise over a sea of clouds", "focus": (0.5, 0.5), "lift": 0.72},
    "tokyo-night": {"file": "File:Colorful neon street signs in Kabukichō, Shinjuku, Tokyo.jpg", "name": "Neon signs in Kabukichō, Shinjuku", "focus": (0.5, 0.5), "lift": 0.85, "soften": 9},
    "volcano": {"file": "File:Fimmvorduhals 2010 03 27 dawn.jpg", "name": "The Fimmvörðuháls eruption at dawn, Iceland", "focus": (0.5, 0.5), "lift": 1.1},
}


def api(params):
    url = API + "?" + urllib.parse.urlencode({**params, "format": "json"})
    return json.loads(fetch(url))


def fetch(url):
    for attempt in range(5):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            return urllib.request.urlopen(request, timeout=60).read()
        except Exception as error:  # noqa: BLE001
            if attempt == 4:
                raise
            print(f"  retrying ({error})")
            time.sleep(3 + attempt * 4)
    return b""


def strip(html):
    text = re.sub(r"<[^>]+>", "", html or "")
    return re.sub(r"\s+", " ", text).strip()


def describe(title):
    """The photo's size, author and license, plus a download URL wide enough for the crop."""
    page = next(iter(api({"action": "query", "titles": title, "prop": "imageinfo", "iiprop": "size|extmetadata|url"})["query"]["pages"].values()))
    info = page["imageinfo"][0]
    width, height = info["width"], info["height"]
    # Wide enough that the 16:9 crop is at least 2560 x 1440, never wider than the original.
    wanted = min(width, max(3200, int(1600 * width / height)))
    scaled = next(iter(api({"action": "query", "titles": title, "prop": "imageinfo", "iiprop": "url", "iiurlwidth": wanted})["query"]["pages"].values()))
    meta = info["extmetadata"]
    return {
        "file": title,
        "source": info["descriptionurl"],
        "download": scaled["imageinfo"][0].get("thumburl") or info["url"],
        "author": strip(meta.get("Artist", {}).get("value")) or strip(meta.get("Credit", {}).get("value")) or "see the source page",
        "license": strip(meta.get("LicenseShortName", {}).get("value")),
        "licenseUrl": meta.get("LicenseUrl", {}).get("value", ""),
    }


def crop(picture, focus, zoom):
    width, height = picture.size
    target = SIZE[0] / SIZE[1]
    crop_w, crop_h = (height * target, height) if width / height > target else (width, width / target)
    crop_w, crop_h = crop_w * zoom, crop_h * zoom
    left = min(max(focus[0] * width - crop_w / 2, 0), width - crop_w)
    top = min(max(focus[1] * height - crop_h / 2, 0), height - crop_h)
    return picture.crop((round(left), round(top), round(left + crop_w), round(top + crop_h))).resize(SIZE, Image.LANCZOS)


def hex_rgb(value):
    return np.array([int(value[i:i + 2], 16) for i in (1, 3, 5)], dtype=np.float32)


def grade(picture, background, lift=1.0, soften=2.0):
    """Darkens where Claude Code writes and pulls the shadows toward the theme's background.

    soften: a blur radius, full on the left edge and fading out by the middle,
    so busy details do not fight with the text.
    """
    sharp = np.asarray(picture, dtype=np.float32)
    h, w = sharp.shape[:2]
    fx = np.linspace(0, 1, w, dtype=np.float32)[None, :]
    fy = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    blurred = np.asarray(picture.filter(ImageFilter.GaussianBlur(soften * w / 2560)), dtype=np.float32)
    blur_mask = (np.clip(1 - fx * 1.8, 0, 1) ** 1.2)[..., None]
    pixels = sharp * (1 - blur_mask) + blurred * blur_mask
    left = np.clip(1 - fx * 1.7, 0, 1) ** 1.6 * 0.45
    bottom = np.clip((fy - 0.55) / 0.45, 0, 1) ** 1.3 * 0.4
    top = np.clip(1 - fy * 4, 0, 1) ** 2 * 0.25
    vignette = np.minimum(np.hypot(fx - 0.6, fy - 0.45) / 0.8, 1.2) ** 2 * 0.25
    darken = 1 - np.minimum(left + bottom + top + vignette + 0.12, 0.85)
    luminance = (pixels @ np.array([0.299, 0.587, 0.114], dtype=np.float32)) / 255
    shadow = (1 - luminance) ** 2 * 0.35
    toned = pixels * (1 - shadow[..., None]) + hex_rgb(background) * shadow[..., None]
    graded = toned * (darken * lift)[..., None]
    return Image.fromarray(np.clip(graded, 0, 255).astype(np.uint8))


def credit_line(entry):
    return f"Photo: {entry['author']}, {entry['license']}, via Wikimedia Commons"


def build(theme_id, spec, lock):
    theme_file = THEMES / theme_id / "theme.json"
    theme = json.loads(theme_file.read_text(encoding="utf-8"))
    entry = describe(spec["file"])
    CACHE.mkdir(exist_ok=True)
    cached = CACHE / f"{theme_id}-{hashlib.sha1(entry['download'].encode()).hexdigest()[:10]}.jpg"
    if not cached.exists():
        cached.write_bytes(fetch(entry["download"]))
    picture = Image.open(io.BytesIO(cached.read_bytes())).convert("RGB")
    picture = crop(picture, spec.get("focus", (0.5, 0.5)), spec.get("zoom", 1.0))
    if spec.get("mirror"):
        picture = picture.transpose(Image.FLIP_LEFT_RIGHT)
    picture = grade(picture, theme["terminal"]["background"], spec.get("lift", 1.0), spec.get("soften", 2.0))
    picture.save(THEMES / theme_id / "assets" / "wallpaper.jpg", quality=86, optimize=True, progressive=True)

    entry.pop("download")
    entry["name"] = spec["name"]
    if "author" in spec:
        entry["author"] = spec["author"]
    lock[theme_id] = entry
    theme["wallpapers"] = [wallpaper_entry(theme_id, lock)]
    theme_file.write_text(json.dumps(theme, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("✓", theme_id, "·", credit_line(entry))


def load_lock():
    return json.loads(LOCK.read_text(encoding="utf-8")) if LOCK.exists() else {}


def wallpaper_entry(theme_id, lock=None):
    """The theme.json wallpaper entry for a photo theme, or None when the theme keeps its painted scene."""
    entry = (load_lock() if lock is None else lock).get(theme_id)
    if entry is None:
        return None
    return {"name": entry["name"], "file": "assets/wallpaper.jpg", "credit": credit_line(entry), "source": entry["source"]}


def write_credits(lock):
    rows = "\n".join(
        f"| {json.loads((THEMES / theme_id / 'theme.json').read_text(encoding='utf-8'))['name']} | [{entry['name']}]({entry['source']}) "
        f"| {entry['author']} | [{entry['license']}]({entry['licenseUrl']}) |"
        if entry["licenseUrl"] else
        f"| {json.loads((THEMES / theme_id / 'theme.json').read_text(encoding='utf-8'))['name']} | [{entry['name']}]({entry['source']}) "
        f"| {entry['author']} | {entry['license']} |"
        for theme_id, entry in sorted(lock.items())
    )
    section = (
        "<!-- photos:start -->\n"
        "These wallpapers are photographs from Wikimedia Commons, used under their free licenses. "
        "They were cropped, darkened and color-graded for terminal use by `scripts/art/photos.py`; "
        "the adapted versions are shared under the same license as the original.\n\n"
        "| Ambiance theme | Photo | Author | License |\n| --- | --- | --- | --- |\n"
        f"{rows}\n"
        "<!-- photos:end -->"
    )
    text = CREDITS.read_text(encoding="utf-8")
    text = re.sub(r"<!-- photos:start -->.*<!-- photos:end -->", lambda _: section, text, flags=re.S)
    CREDITS.write_text(text, encoding="utf-8")


def main():
    wanted = sys.argv[1:] or list(PHOTOS)
    lock = load_lock()
    for theme_id in wanted:
        build(theme_id, PHOTOS[theme_id], lock)
        LOCK.write_text(json.dumps(lock, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    write_credits(lock)


if __name__ == "__main__":
    main()
