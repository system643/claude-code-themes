"""Synthesized sound helpers for the bundled themes (no third-party sounds).

Each theme has three short sounds: start (the theme is applied), success (a
check passes) and error (a check fails).
"""
import wave
from pathlib import Path

import numpy as np

RATE = 22050
rng = np.random.default_rng(42)


def timeline(seconds):
    return np.linspace(0, seconds, int(RATE * seconds), endpoint=False)


def lowpass(signal, amount):
    out = np.empty_like(signal)
    acc = 0.0
    for i, x in enumerate(signal):
        acc += amount * (x - acc)
        out[i] = acc
    return out


def save(path, signal, gain=0.6):
    signal = signal / (np.max(np.abs(signal)) + 1e-9) * gain
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes((signal * 32767).astype(np.int16).tobytes())


def tones(freqs, length=0.12, decay=0.25, wave_shape="sine", tremolo=0.0):
    """Notes played one after another, each with a soft attack and a decay."""
    parts = []
    for f in freqs:
        t = timeline(length + decay)
        if wave_shape == "square":
            osc = np.sign(np.sin(2 * np.pi * f * t)) * 0.5
        elif wave_shape == "saw":
            osc = 2 * (t * f - np.floor(0.5 + t * f)) * 0.6
        elif wave_shape == "bell":
            osc = sum(np.sin(2 * np.pi * f * k * t) / k ** 1.5 for k in (1, 2.76, 5.4))
        else:
            osc = np.sin(2 * np.pi * f * t)
        if tremolo:
            osc = osc * (0.7 + 0.3 * np.sin(2 * np.pi * tremolo * t))
        parts.append(osc * np.exp(-t / decay) * np.minimum(1, t / 0.004))
    out = np.zeros(int(RATE * (length * len(freqs) + decay)) + 10)
    for i, part in enumerate(parts):
        start = int(i * length * RATE)
        out[start : start + part.size] += part
    return out


def noise_burst(seconds, color=0.08, decay=0.2):
    t = timeline(seconds)
    return lowpass(rng.uniform(-1, 1, t.size), color) * np.exp(-t / decay)


# Three sounds (start, success, error) per style.
STYLES = {
    "chime": lambda: (tones([880, 1320], 0.25, 1.2), tones([1046, 1318, 1568], 0.15, 1.0), tones([392, 370], 0.3, 0.8)),
    "synth": lambda: (tones([523, 784, 1046], wave_shape="square"), tones([659, 988, 1318, 1568], 0.08, wave_shape="square"), tones([220, 165], 0.15, 0.3, "square")),
    "sparkle": lambda: (tones([1568, 2093, 2637, 3136], 0.06, 0.6), tones([1046, 1568, 2093], 0.1, 0.9), tones([311, 277, 247], 0.18, 0.5)),
    "retro": lambda: (tones([262, 330, 392, 523], 0.07, 0.15, "square"), tones([523, 659, 784, 1046, 1318], 0.06, 0.2, "square"), tones([196, 185, 175, 165], 0.12, 0.25, "square")),
    "outrun": lambda: (tones([220, 330, 440], 0.18, 0.8, "saw"), tones([440, 554, 659, 880], 0.12, 0.7, "saw"), tones([147, 139], 0.25, 0.6, "saw")),
    "bell": lambda: (tones([659, 988], 0.3, 1.4, "bell"), tones([784, 988, 1175], 0.2, 1.2, "bell"), tones([330, 311], 0.35, 1.0, "bell")),
    "jingle": lambda: (tones([1319, 1319, 1319], 0.12, 0.4, "bell", 18), tones([1319, 1568, 1047, 1175, 1319], 0.1, 0.5, "bell", 18), tones([392, 349], 0.25, 0.6, "bell")),
    "spooky": lambda: (tones([220, 233, 220, 208], 0.22, 0.9, "saw", 5), tones([440, 523, 622, 740], 0.12, 0.6, "sine", 7), tones([147, 139, 131], 0.3, 0.9, "saw", 4)),
    "bubble": lambda: (tones([400, 600, 900], 0.08, 0.15), tones([500, 750, 1100, 1500], 0.06, 0.12), tones([300, 200], 0.15, 0.3)),
    "rumble": lambda: (noise_burst(0.9, 0.04, 0.4), tones([196, 294, 392], 0.15, 0.6, "saw") + 0, noise_burst(0.7, 0.02, 0.3)),
    "cozy": lambda: (tones([523, 659, 784], 0.18, 0.9), tones([587, 740, 880, 1175], 0.14, 0.8), tones([440, 415], 0.25, 0.7)),
}
