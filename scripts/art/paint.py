"""Shared painting helpers for the procedural wallpapers (2560 × 1440).

Every wallpaper keeps the left side and the bottom dark and calm: that's where
the terminal text and Claude Code's banner go. `readable()` takes care of it.
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 2560, 1440
rng = np.random.default_rng(1310)


# ---------- Tools ----------

def noise(width, height, scale, octaves=5, seed=0):
    """Fractal value noise in [0, 1], smooth, with no visible repeating pattern."""
    local = np.random.default_rng(seed)
    total = np.zeros((height, width))
    amplitude, weight = 1.0, 0.0
    for octave in range(octaves):
        cells = max(2, int(scale * 2**octave))
        grid = local.random((cells + 1, cells + 1))
        small = Image.fromarray((grid * 255).astype(np.uint8)).resize((width, height), Image.BICUBIC)
        total += np.asarray(small, dtype=float) / 255 * amplitude
        weight += amplitude
        amplitude *= 0.5
    return total / weight


def stretched(columns, rows, seed):
    """Stretched noise: `columns` × `rows` values scaled up to the whole screen."""
    grid = np.random.default_rng(seed).random((rows, columns))
    return np.asarray(Image.fromarray((grid * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), float) / 255


def vertical(top, bottom, curve=1.0):
    t = np.linspace(0, 1, H)[:, None, None] ** curve
    return np.asarray(top, float) * (1 - t) + np.asarray(bottom, float) * t * np.ones((H, W, 3))


def blend(canvas, color, mask):
    mask = np.clip(mask, 0, 1)[..., None]
    canvas[:] = canvas * (1 - mask) + np.asarray(color, float) * mask


def add_light(canvas, color, mask):
    canvas[:] = canvas + np.asarray(color, float) * np.clip(mask, 0, None)[..., None]


def radial(cx, cy, radius):
    y, x = np.ogrid[:H, :W]
    return np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / radius


def ridge_mask(base, amplitude, scale, seed, start=0, end=W):
    """Terrain silhouette: 1 below the ridge line."""
    line = noise(W, 1, scale, 6, seed)[0]
    heights = base - (line - 0.5) * 2 * amplitude
    y = np.arange(H)[:, None]
    mask = (y >= heights[None, :]).astype(float)
    mask[:, :start] = 0
    mask[:, end:] = 0
    return mask


def shape_mask(draw_fn, blur=0, binary=False):
    """A mask from drawing calls. With `binary`, any painted pixel counts fully,
    whatever color the drawing function uses (so scene drawers can be reused)."""
    layer = Image.new("RGB", (W, H), (0, 0, 0))
    draw_fn(ImageDraw.Draw(layer))
    gray = np.asarray(layer, float).max(axis=2)
    if binary:
        gray = (gray > 0) * 255.0
    if blur:
        gray = np.asarray(Image.fromarray(gray.astype(np.uint8)).filter(ImageFilter.GaussianBlur(blur)), float)
    return gray / 255


def readable(canvas, strength=0.55):
    """Darkens the left side (where text is written) and adds a vignette."""
    x = np.linspace(0, 1, W)[None, :]
    left = np.clip(1 - x * 1.6, 0, 1) ** 1.5 * strength
    vignette = np.clip(radial(W * 0.62, H * 0.45, W * 0.75), 0, 1.2) ** 2 * 0.45
    # The bottom too: Claude Code's banner and prompt sit there.
    yy = np.linspace(0, 1, H)[:, None]
    bottom = np.clip((yy - 0.6) / 0.4, 0, 1) ** 1.2 * 0.5 * np.clip(1.25 - np.linspace(0, 1, W)[None, :], 0.3, 1)
    canvas[:] = canvas * (1 - np.clip(left + vignette + bottom, 0, 0.85))[..., None]


def finish(canvas, grain=2.5):
    canvas += rng.normal(0, grain, canvas.shape)
    return Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8))


def stars(canvas, count, max_y, seed, tint=(210, 220, 255)):
    local = np.random.default_rng(seed)
    layer = Image.new("L", (W, H), 0)
    draw = ImageDraw.Draw(layer)
    for _ in range(count):
        x, y = local.integers(0, W), local.integers(0, int(max_y))
        r = local.choice([0.6, 0.8, 1.0, 1.4, 2.0], p=[0.35, 0.3, 0.2, 0.1, 0.05])
        draw.ellipse([x - r, y - r, x + r, y + r], fill=int(local.integers(90, 256)))
    sharp = np.asarray(layer, float) / 255
    halo = np.asarray(layer.filter(ImageFilter.GaussianBlur(3)), float) / 255
    add_light(canvas, tint, sharp * 0.9 + halo * 0.6)


def glow(canvas, cx, cy, radius, color, strength):
    """A soft round light."""
    add_light(canvas, color, np.exp(-radial(cx, cy, radius) ** 2) * strength)


def moon(canvas, cx, cy, r, color=(220, 225, 240), halo=(120, 135, 210), shadow=None):
    """A moon with its halo; `shadow` (the sky color) carves a crescent."""
    d = radial(cx, cy, r)
    add_light(canvas, halo, np.exp(-(d - 1) * 1.4) * (d > 1) * 0.5)
    blend(canvas, color, (d <= 1).astype(float) * (0.9 + 0.1 * noise(W, H, 40, 3, 9)))
    if shadow is not None:
        blend(canvas, shadow, (radial(cx + r * 0.38, cy - r * 0.18, r * 0.95) <= 1).astype(float))


def pine(draw, x, base, h, fill, snow=None):
    """A pine tree: stacked triangles, optionally with snow on the branches."""
    w = h * 0.42
    draw.rectangle([x - h * 0.03, base - h * 0.12, x + h * 0.03, base], fill=fill)
    for i in range(4):
        top = base - h + i * h * 0.2
        bottom = top + h * 0.38
        half = w * (0.35 + i * 0.22)
        draw.polygon([(x, top), (x - half, bottom), (x + half, bottom)], fill=fill)
        if snow:
            draw.polygon([(x, top), (x - half * 0.45, top + h * 0.12), (x + half * 0.45, top + h * 0.12)], fill=snow)


def to_image(canvas):
    return Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8))


def to_canvas(image):
    return np.asarray(image, float).copy()


def sprinkle(canvas, count, area, color, sizes=(1.0, 1.5, 2.0), blur=1.5, strength=1.0, seed=0):
    """Small glowing dots (embers, fireflies, petals, bubbles) inside `area` (x0, y0, x1, y1)."""
    local = np.random.default_rng(seed)
    layer = Image.new("L", (W, H), 0)
    draw = ImageDraw.Draw(layer)
    x0, y0, x1, y1 = area
    for _ in range(count):
        x, y = local.uniform(x0, x1), local.uniform(y0, y1)
        r = float(local.choice(sizes))
        draw.ellipse([x - r, y - r, x + r, y + r], fill=int(local.integers(120, 256)))
    sharp = np.asarray(layer, float) / 255
    soft = np.asarray(layer.filter(ImageFilter.GaussianBlur(blur * 4)), float) / 255
    add_light(canvas, color, (sharp + soft * 1.5) * strength)
