"""Original pixel art for the bundled themes: 20 × 12 pixels, a few frames each.

Each sprite function returns (frames, palette, eyes): `eyes` are the palette
keys that turn red when the theme gets angry (see `angry`).
"""
import math

W, H = 20, 12


class Grid:
    def __init__(self):
        self.cells = [["."] * W for _ in range(H)]

    def put(self, row, cols, key):
        if 0 <= row < H:
            for c in cols:
                if 0 <= c < W:
                    self.cells[row][c] = key
        return self

    def rect(self, r0, r1, c0, c1, key):
        for r in range(r0, r1 + 1):
            self.put(r, range(c0, c1 + 1), key)
        return self

    def mirror(self):
        """Copies the left half onto the right half."""
        for row in self.cells:
            for c in range(W // 2):
                if row[c] != ".":
                    row[W - 1 - c] = row[c]
        return self

    def rows(self):
        return ["".join(r) for r in self.cells]


def shift(frame, dx=0, dy=0):
    out = [["."] * W for _ in range(H)]
    for y, row in enumerate(frame):
        for x, key in enumerate(row):
            if key != "." and 0 <= x + dx < W and 0 <= y + dy < H:
                out[y + dy][x + dx] = key
    return ["".join(r) for r in out]


def recolor(frame, mapping):
    return ["".join(mapping.get(k, k) for k in row) for row in frame]


def angry(frames, eyes):
    """Two shaking frames, eyes (or glow) turned red."""
    base = recolor(frames[0], {key: "R" for key in eyes})
    return [shift(base, -1), shift(base, 1)]


# ---------- Sprites ----------

def bat():
    def body(g):
        g.put(2, [7], "p").rect(3, 6, 6, 9, "p").put(5, [7], "r").put(7, [7, 8, 9], "p").put(7, [8], "w")
        g.put(8, [7, 8, 9], "p").put(9, [8, 9], "p")

    up = Grid()
    up.put(0, [0], "p").put(1, [0, 1], "p").put(2, [0, 1, 2], "p").put(3, range(1, 6), "p").put(4, range(2, 6), "p").put(5, range(3, 6), "p")
    body(up)
    down = Grid()
    down.put(4, [4, 5], "p").put(5, range(1, 6), "p").put(6, range(0, 6), "p").put(7, range(0, 4), "p").put(8, [0, 1], "p")
    body(down)
    a, b = up.mirror().rows(), down.mirror().rows()
    return [a, b, a, b], {"p": "#BD93F9", "r": "#FF5555", "w": "#F8F8F2"}, ["r"]


def cat():
    def face(blink=False, twitch=False):
        g = Grid()
        g.put(1 if not twitch else 2, [4], "b").put(2, [4, 5], "b").put(3, [4, 5, 6], "b")
        g.rect(4, 9, 3, 9, "b").put(3, [7, 8, 9], "b").put(10, range(4, 10), "b")
        g.put(6, [5, 6], "b" if blink else "e").put(7, [5, 6], "e")
        g.put(8, [9], "n").put(8, [1, 2], "w").put(9, [0, 1, 2], "w").put(2, [5], "i")
        return g.mirror().rows()

    open_, blink, twitch = face(), face(blink=True), face(twitch=True)
    return [open_, open_, blink, open_, twitch, open_], {"b": "#FAB387", "e": "#1E1E2E", "n": "#F5C2E7", "w": "#CDD6F4", "i": "#F5C2E7"}, ["e"]


def snowy_peaks():
    frames = []
    for phase in range(4):
        g = Grid()
        for x in range(W):
            height = max(0, 7 - abs(x - 6)) if x < 12 else max(0, 6 - abs(x - 15))
            for y in range(11 - height, 12):
                g.put(y, [x], "m")
            if height >= 3:
                g.put(11 - height, [x], "s").put(12 - height, [x], "s")
        for i, (x, y) in enumerate(((2, 1), (9, 0), (15, 2), (18, 0), (5, 4), (12, 3))):
            g.put((y + phase + i % 2) % 7, [x], "f")
        frames.append(g.rows())
    return frames, {"m": "#4C566A", "s": "#ECEFF4", "f": "#88C0D0"}, ["f"]


def lantern():
    frames = []
    for flicker in ("l", "L", "l", "M"):
        g = Grid()
        g.put(0, [9, 10], "k").put(1, range(7, 13), "k")
        for r, (c0, c1) in enumerate(((7, 12), (6, 13), (5, 14), (5, 14), (6, 13), (7, 12)), start=2):
            g.put(r, range(c0, c1 + 1), flicker)
        for r, (c0, c1) in ((3, (6, 13)), (5, (5, 14)), (7, (7, 12))):
            g.put(r, range(c0, c1 + 1), "d")
        g.put(8, range(7, 13), "k").put(9, [9, 10], "t").put(10, [9, 10], "t").put(11, [8, 11], "t")
        frames.append(g.rows())
    return frames, {"k": "#15161E", "l": "#F7768E", "L": "#FF9E64", "M": "#E0AF68", "d": "#BB4A60", "t": "#E0AF68"}, ["l", "L", "M"]


def campfire():
    frames = []
    shapes = [
        [(2, [9]), (3, [8, 9, 10]), (4, [8, 9, 10, 11]), (5, [7, 8, 9, 10, 11]), (6, [7, 8, 9, 10, 11, 12])],
        [(1, [10]), (2, [9, 10]), (3, [8, 9, 10, 11]), (4, [7, 8, 9, 10, 11]), (5, [7, 8, 9, 10, 11, 12]), (6, [7, 8, 9, 10, 11, 12])],
        [(2, [10]), (3, [9, 10, 11]), (4, [8, 9, 10, 11]), (5, [8, 9, 10, 11, 12]), (6, [7, 8, 9, 10, 11, 12])],
    ]
    for shape in shapes + [shapes[1]]:
        g = Grid()
        for row, cols in shape:
            g.put(row, cols, "o")
        for row, cols in shape[2:]:
            g.put(row, cols[1:-1], "y")
        g.put(7, range(6, 14), "o").put(7, range(8, 12), "y")
        g.put(8, range(4, 16), "w").put(9, range(5, 15), "W").put(8, [6, 12], "W").put(10, [3, 4, 15, 16], "w")
        g.put(0 if len(frames) % 2 else 1, [6 + len(frames) * 2 % 9], "e")
        frames.append(g.rows())
    return frames, {"o": "#FE8019", "y": "#FABD2F", "w": "#7C6F64", "W": "#504945", "e": "#FB4934"}, ["y", "o"]


def rose():
    frames = []
    for sway in (0, 1, 0, -1):
        g = Grid()
        g.put(1, [8, 9, 10], "p").put(2, range(7, 12), "p").put(3, range(6, 13), "p").put(4, range(6, 13), "p").put(5, range(7, 12), "p")
        g.put(2, [9], "r").put(3, [8, 9, 10], "r").put(4, [9], "r").put(3, [11], "R").put(2, [8], "R")
        for r in range(6, 12):
            g.put(r, [9 + (sway if r < 9 else 0)], "s")
        g.put(8, [10, 11, 12], "l").put(7, [12, 13], "l").put(9, [6, 7, 8], "l").put(10, [5, 6], "l")
        frames.append(g.rows())
    return frames, {"p": "#EB6F92", "r": "#EBBCBA", "R": "#F6C177", "s": "#31748F", "l": "#9CCFD8"}, ["r", "R"]


def sun():
    frames = []
    for diagonal in (False, True, False, True):
        g = Grid()
        g.rect(4, 7, 7, 12, "y").put(3, range(8, 12), "y").put(8, range(8, 12), "y").put(5, [6, 13], "y").put(6, [6, 13], "y")
        g.put(5, [9], "o").put(5, [10], "o").put(6, [8, 11], "o")
        if diagonal:
            for i in range(2):
                g.put(1 + i, [5 + i, 14 - i], "r").put(10 - i, [5 + i, 14 - i], "r")
        else:
            g.put(0, [9, 10], "r").put(1, [9, 10], "r").put(10, [9, 10], "r").put(11, [9, 10], "r")
            g.put(5, [3, 4, 15, 16], "r").put(6, [3, 4, 15, 16], "r")
        frames.append(g.rows())
    return frames, {"y": "#B58900", "o": "#CB4B16", "r": "#2AA198"}, ["o"]


def atom():
    frames = []
    orbit = [(x, y) for x, y in ((3, 5), (5, 2), (9, 1), (14, 2), (16, 5), (14, 9), (9, 10), (5, 9))]
    for step in range(len(orbit)):
        g = Grid()
        for i in range(36):
            a = i / 36 * 2 * math.pi
            g.put(round(5.5 + 4.5 * math.sin(a)), [round(9.5 + 7 * math.cos(a))], "o")
            g.put(round(5.5 + 4.5 * math.sin(a + 1.0) * 0.6 + 1.5 * math.cos(a)), [round(9.5 + 3 * math.cos(a + 1.0))], "q")
        g.rect(5, 6, 9, 10, "n")
        x, y = orbit[step]
        g.put(y, [x, x + 1], "e")
        frames.append(g.rows())
    return frames, {"o": "#61AFEF", "q": "#C678DD", "n": "#E5C07B", "e": "#98C379"}, ["n"]


def synth_sun():
    frames = []
    for offset in range(2):
        g = Grid()
        g.put(0, range(7, 13), "y").put(1, range(5, 15), "y").put(2, range(4, 16), "o")
        g.put(3, range(3, 17), "p").put(5, range(2, 18), "p")
        g.put(6, range(0, W), "h")
        for row in ((8, 11) if offset else (7, 10)):
            g.put(row, range(0, W), "g")
        for row in range(7, 12):
            for k in (-2, -1, 1, 2):
                g.put(row, [round(9.5 + k * (1.5 + (row - 6) * 0.9))], "g")
        frames.append(g.rows())
    return frames, {"y": "#FEDE5D", "o": "#FF9F43", "p": "#FF7EDB", "h": "#36F9F6", "g": "#8A5FB0"}, ["y", "o", "p"]


def forest():
    frames = []
    for phase in range(4):
        g = Grid()
        for x0, h in ((3, 9), (9, 11), (15, 8)):
            for r in range(h):
                half = max(0, (r + 1) // 2 - (1 if r % 3 == 0 and r else 0))
                g.put(11 - h + r, range(x0 - half, x0 + half + 1), "t")
            g.put(11, [x0], "k")
        for i, (x, y) in enumerate(((1, 2), (7, 4), (13, 1), (18, 5), (11, 7), (5, 8))):
            if (i + phase) % 3:
                g.put(y, [x], "f")
        frames.append(g.rows())
    return frames, {"t": "#A7C080", "k": "#859289", "f": "#DBBC7F"}, ["f"]


def rain_columns():
    frames = []
    heads = [(1, 0), (4, 5), (7, 2), (10, 8), (13, 3), (16, 6), (18, 1)]
    for step in range(6):
        g = Grid()
        for x, start in heads:
            head = (start + step * 2) % 16
            for k in range(5):
                y = head - k
                if 0 <= y < H:
                    g.put(y, [x], "h" if k == 0 else ("g" if k < 3 else "d"))
        frames.append(g.rows())
    return frames, {"h": "#E6FFE6", "g": "#33FF66", "d": "#0F7A2E"}, ["h", "g"]


def monitor():
    frames = []
    for cursor in (True, False):
        g = Grid()
        g.rect(0, 8, 2, 17, "c").rect(1, 7, 3, 16, "s")
        g.put(2, [4, 5], "a").put(2, [7, 8, 9, 10], "a").put(4, [4], "a").put(4, [5], "a")
        if cursor:
            g.put(4, [6, 7], "A")
        g.put(9, range(8, 12), "c").put(10, range(5, 15), "c").put(11, range(3, 17), "k")
        frames.append(g.rows())
    return frames, {"c": "#5A4120", "s": "#1A1000", "a": "#FFB000", "A": "#FFD27A", "k": "#3A2A10"}, ["a", "A"]


def invader():
    def alien(arms_up):
        g = Grid()
        g.put(1, [6], "g").put(2, [7], "g").rect(3, 3, 6, 9, "g").put(4, [5, 6], "g").put(4, [8, 9], "g").put(4, [7], "e")
        g.rect(5, 6, 4, 9, "g").put(5, [6], "e")
        if arms_up:
            g.put(4, [3], "g").put(3, [3], "g").put(7, [4, 6], "g").put(8, [5], "g")
        else:
            g.put(6, [3], "g").put(7, [3], "g").put(7, [5, 7], "g").put(8, [4], "g")
        g.put(10, [1 + (0 if arms_up else 1)], "s").put(11, [6], "s")
        return g.mirror().rows()

    a, b = alien(True), alien(False)
    return [a, b], {"g": "#39FF14", "e": "#0A0A1A", "s": "#FFFFFF"}, ["g"]


def rocket():
    frames = []
    for flame in (0, 1, 2, 1):
        g = Grid()
        g.put(0, [9, 10], "w").put(1, range(8, 12), "w").rect(2, 7, 7, 12, "w").put(3, [9, 10], "b").put(4, [9, 10], "b")
        g.put(6, [6, 13], "r").put(7, [5, 6, 13, 14], "r").put(8, [5, 14], "r").put(8, range(8, 12), "g")
        g.put(9, range(8, 12), "o").put(10, range(9 - (flame > 0), 11 + (flame > 0)), "y" if flame != 2 else "o")
        if flame:
            g.put(11, [9, 10], "y")
        for i, (x, y) in enumerate(((2, 1), (17, 3), (1, 8), (18, 10))):
            if (i + flame) % 2:
                g.put(y, [x], "s")
        frames.append(g.rows())
    return frames, {"w": "#DCE3F0", "b": "#4FA3FF", "r": "#FF5E5E", "g": "#8A94A8", "o": "#FF9F43", "y": "#FFE066", "s": "#FFFFFF"}, ["b"]


def jellyfish():
    frames = []
    for pulse in range(4):
        g = Grid()
        wide = pulse in (1, 2)
        g.put(1, range(7, 13), "j").put(2, range(5 - wide, 15 + wide), "j").put(3, range(4 - wide, 16 + wide), "j").put(4, range(4 - wide, 16 + wide), "J")
        g.put(2, [7, 12], "g").put(3, [9, 10], "g")
        for i, x in enumerate((5, 8, 11, 14)):
            for r in range(5, 11):
                g.put(r, [x + round(math.sin((r + pulse + i) * 1.1))], "t")
        g.put((pulse * 3) % 12, [1], "s").put((pulse * 3 + 6) % 12, [18], "s")
        frames.append(g.rows())
    return frames, {"j": "#5EE6D0", "J": "#2BB3A0", "g": "#D0FFF6", "t": "#7A8CFF", "s": "#9CEFFF"}, ["g"]


def blossom():
    frames = []
    for phase in range(4):
        g = Grid()
        g.put(2, range(0, 9), "b").put(3, range(7, 13), "b").put(4, [12, 13, 14], "b").put(1, [4, 5], "b").put(5, [14, 15], "b")
        for x, y in ((1, 1), (3, 3), (6, 1), (8, 4), (11, 2), (13, 3), (15, 4), (16, 6), (5, 0)):
            g.put(y, [x, x + 1], "p").put(y + 1, [x], "P")
        for i, (x, y) in enumerate(((3, 6), (9, 7), (14, 8), (6, 9), (17, 10))):
            g.put(min(11, y + phase), [x + (phase + i) % 2], "p")
        frames.append(g.rows())
    return frames, {"b": "#5C3B44", "p": "#FFB7C5", "P": "#FF85A2"}, ["p", "P"]


def coffee():
    frames = []
    for phase in range(4):
        g = Grid()
        g.rect(5, 10, 4, 13, "c").put(11, range(5, 13), "c").put(5, range(5, 13), "f")
        g.put(6, [14, 15], "c").put(7, [16], "c").put(8, [16], "c").put(9, [14, 15], "c")
        g.put(11, range(2, 17), "s").put(8, [7, 8, 9], "h")
        for i, x in enumerate((6, 9, 12)):
            for r in range(0, 4):
                g.put(r, [x + round(math.sin((r + phase + i * 2) * 1.3))], "v")
        frames.append(g.rows())
    return frames, {"c": "#E8D5B5", "f": "#6F4E37", "s": "#A0826D", "h": "#D98E73", "v": "#9C8F87"}, ["h"]


def volcano():
    frames = []
    for phase in range(4):
        g = Grid()
        for r in range(4, 12):
            half = (r - 3) * 1.2
            g.put(r, range(round(9.5 - half - 1), round(9.5 + half + 1)), "m")
        g.put(4, range(8, 12), "l").put(5, [9, 10], "l").put(6 + phase % 2, [8], "l").put(7 + phase % 3, [11], "l").put(9, [7 - phase % 2], "L")
        for i, (dx, h) in enumerate(((-3, 3), (0, 4), (3, 2), (-1, 2))):
            y = 3 - ((phase + i) % 4)
            if y >= 0:
                g.put(y, [9 + dx + (i % 2)], "L" if i % 2 else "l")
        frames.append(g.rows())
    return frames, {"m": "#3A1E1A", "l": "#FF4E1A", "L": "#FFB020"}, ["l", "L"]


def xmas_tree():
    frames = []
    lights = [(4, 9), (5, 7), (6, 11), (7, 8), (8, 12), (8, 6), (9, 10), (6, 9)]
    colors = "rgby"
    for phase in range(4):
        g = Grid()
        g.put(0, [9, 10], "S").put(1, [9, 10], "S")
        for r in range(2, 10):
            half = (r - 1) * 0.9
            g.put(r, range(round(9.5 - half), round(9.5 + half)), "t")
        g.put(10, [9, 10], "k").put(11, [9, 10], "k").put(11, range(3, 7), "p").put(11, range(13, 17), "q")
        for i, (r, c) in enumerate(lights):
            g.put(r, [c], colors[(i + phase) % 4])
        frames.append(g.rows())
    return frames, {"S": "#FFD54A", "t": "#1F8A4C", "k": "#7A4A2A", "r": "#FF4D4D", "g": "#FFFFFF", "b": "#4DA6FF", "y": "#FFD54A", "p": "#E53935", "q": "#43A047"}, ["S"]


def pumpkin():
    frames = []
    for glow in ("y", "Y", "y", "O"):
        g = Grid()
        g.put(1, [9, 10], "s").put(2, [10], "s")
        g.put(3, range(5, 15), "o").rect(4, 9, 3, 16, "o").put(10, range(5, 15), "o")
        for c in (6, 9, 10, 13):
            g.put(4, [c], "O").put(9, [c], "O")
        g.put(5, [6, 7], glow).put(6, [6, 7], glow).put(5, [12, 13], glow).put(6, [12, 13], glow)
        g.put(8, [6, 8, 10, 12], glow).put(9, [7, 9, 11, 13], glow).put(8, [7, 9, 11], glow)
        frames.append(g.rows())
    return frames, {"s": "#4CAF50", "o": "#FF7518", "O": "#C4500C", "y": "#FFE066", "Y": "#FFF3B0"}, ["y", "Y"]
