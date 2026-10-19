"""Writes the Windows Terminal effect shaders (HLSL) into app/src-tauri/shaders/.

Windows Terminal compiles one file per effect, so the shared helpers are
copied into each of them.
Usage: python scripts/build_shaders.py
"""
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "app" / "src-tauri" / "shaders"

COMMON = """// Shared by Ambiance's Windows Terminal effects (experimental.pixelShaderPath).
// Every effect only paints over the background: the text stays sharp and readable.
Texture2D shaderTexture;
SamplerState samplerState;

cbuffer PixelShaderSettings {
    float  Time;
    float  Scale;
    float2 Resolution;
    float4 Background;
};

float hash(float2 p) {
    return frac(sin(dot(p, float2(127.1, 311.7))) * 43758.5453);
}

// 1 over the background (dark or photo), fading to 0 under bright text.
float backgroundMask(float3 color) {
    return 1.0 - smoothstep(0.55, 0.85, dot(color, float3(0.299, 0.587, 0.114)));
}

// One particle per `size`-pixel cell, in a `density` share of the cells.
float particles(float2 px, float size, float density, float radius, float seed) {
    float2 cell = floor(px / size);
    float h = hash(cell + seed);
    if (h < 1.0 - density) return 0.0;
    float2 center = (cell + float2(0.2 + 0.6 * hash(cell + seed + 1.3), 0.2 + 0.6 * hash(cell + seed + 2.7))) * size;
    float d = length(px - center);
    float halo = exp(-d / (radius * 1.6)) * 0.45;
    return (smoothstep(radius, 0.0, d) + halo) * (0.5 + 0.5 * h);
}
"""

EFFECTS = {
    "stars": ("Softly twinkling stars over the background.", """
float4 main(float4 pos : SV_POSITION, float2 tex : TEXCOORD) : SV_TARGET {
    float4 color = shaderTexture.Sample(samplerState, tex);
    float2 px = tex * Resolution / Scale;
    float star = 0.0;
    for (float layer = 0.0; layer < 2.0; layer += 1.0) {
        float size = 26.0 + layer * 19.0;
        float2 cell = floor(px / size);
        float h = hash(cell + layer * 7.0);
        float twinkle = 0.55 + 0.45 * sin(Time * (1.2 + h * 2.5) + h * 40.0);
        star += particles(px, size, 0.06, 2.0 + layer * 0.6, layer * 7.0) * twinkle;
    }
    color.rgb += star * backgroundMask(color.rgb) * float3(0.75, 0.82, 1.0) * 1.2;
    return color;
}"""),
    "embers": ("Embers rising from the bottom of the screen, flickering.", """
float4 main(float4 pos : SV_POSITION, float2 tex : TEXCOORD) : SV_TARGET {
    float4 color = shaderTexture.Sample(samplerState, tex);
    float2 px = tex * Resolution / Scale;
    float glow = 0.0;
    for (float layer = 0.0; layer < 3.0; layer += 1.0) {
        float2 p = px;
        p.y += Time * (22.0 + layer * 14.0);
        p.x += sin(p.y * 0.02 + layer * 2.0 + Time * 0.7) * 10.0;
        float flicker = 0.6 + 0.4 * sin(Time * 7.0 + layer * 3.1 + p.y * 0.05);
        glow += particles(p, 46.0 + layer * 23.0, 0.12, 2.6 + layer * 0.8, layer * 13.0) * flicker;
    }
    float rise = saturate(tex.y * 0.9 + 0.25);
    color.rgb += glow * rise * backgroundMask(color.rgb) * float3(1.0, 0.52, 0.18) * 1.6;
    return color;
}"""),
    "snow": ("Snow falling and swaying.", """
float4 main(float4 pos : SV_POSITION, float2 tex : TEXCOORD) : SV_TARGET {
    float4 color = shaderTexture.Sample(samplerState, tex);
    float2 px = tex * Resolution / Scale;
    float flakes = 0.0;
    for (float layer = 0.0; layer < 3.0; layer += 1.0) {
        float2 p = px;
        p.y -= Time * (18.0 + layer * 16.0);
        p.x += sin(p.y * 0.015 + layer * 1.7 + Time * 0.5) * 14.0;
        flakes += particles(p, 38.0 + layer * 21.0, 0.14, 2.0 + layer * 0.8, layer * 5.0) * (0.6 + layer * 0.25);
    }
    color.rgb += flakes * backgroundMask(color.rgb) * float3(0.85, 0.9, 1.0) * 1.1;
    return color;
}"""),
    "crt": ("Cathode-ray screen: scanlines, a slight flicker and a vignette.", """
float4 main(float4 pos : SV_POSITION, float2 tex : TEXCOORD) : SV_TARGET {
    float4 color = shaderTexture.Sample(samplerState, tex);
    float scan = 0.88 + 0.12 * sin(tex.y * Resolution.y * 3.14159 / Scale);
    float flicker = 0.985 + 0.015 * sin(Time * 60.0);
    float2 centered = tex - 0.5;
    float vignette = 1.0 - 0.45 * dot(centered, centered) * 2.0;
    color.rgb *= scan * flicker * vignette;
    color.rgb += float3(0.0, 0.012, 0.006);
    return color;
}"""),
    "glow": ("A neon-like glow around the text.", """
float4 main(float4 pos : SV_POSITION, float2 tex : TEXCOORD) : SV_TARGET {
    float4 color = shaderTexture.Sample(samplerState, tex);
    float2 texel = 1.6 * Scale / Resolution;
    float3 halo = float3(0.0, 0.0, 0.0);
    for (float x = -2.0; x <= 2.0; x += 1.0) {
        for (float y = -2.0; y <= 2.0; y += 1.0) {
            halo += shaderTexture.Sample(samplerState, tex + float2(x, y) * texel).rgb;
        }
    }
    halo /= 25.0;
    float pulse = 0.85 + 0.15 * sin(Time * 1.5);
    color.rgb += max(halo - 0.08, 0.0) * 0.55 * pulse * backgroundMask(color.rgb);
    return color;
}"""),
    "matrix": ("Falling green streaks of digital rain.", """
float4 main(float4 pos : SV_POSITION, float2 tex : TEXCOORD) : SV_TARGET {
    float4 color = shaderTexture.Sample(samplerState, tex);
    float2 px = tex * Resolution / Scale;
    float column = floor(px.x / 14.0);
    float speed = 60.0 + 140.0 * hash(float2(column, 1.0));
    float offset = hash(float2(column, 2.0)) * 2000.0;
    float head = fmod(Time * speed + offset, Resolution.y / Scale + 400.0) - 200.0;
    float trail = saturate(1.0 - (head - px.y) / 220.0) * step(px.y, head);
    float cellOn = step(0.35, hash(float2(column, floor(px.y / 16.0) + floor(Time * 8.0))));
    // Thin vertical strokes rather than blocks, so the rain stays in the background.
    float stroke = step(fmod(px.x, 14.0), 2.0) * step(fmod(px.y, 16.0), 11.0);
    float glyph = trail * cellOn * stroke;
    float bright = step(head - 16.0, px.y) * step(px.y, head) * stroke;
    color.rgb += (glyph * float3(0.0, 0.45, 0.15) + bright * float3(0.4, 0.9, 0.5) * 0.5) * backgroundMask(color.rgb) * 0.75;
    return color;
}"""),
    "bubbles": ("Bubbles rising and wobbling, like the deep sea.", """
float4 main(float4 pos : SV_POSITION, float2 tex : TEXCOORD) : SV_TARGET {
    float4 color = shaderTexture.Sample(samplerState, tex);
    float2 px = tex * Resolution / Scale;
    float ring = 0.0;
    for (float layer = 0.0; layer < 2.0; layer += 1.0) {
        float2 p = px;
        p.y += Time * (20.0 + layer * 18.0);
        p.x += sin(p.y * 0.03 + layer + Time) * 6.0;
        float size = 60.0 + layer * 40.0;
        float2 cell = floor(p / size);
        float h = hash(cell + layer * 3.0);
        if (h > 0.82) {
            float2 center = (cell + 0.5) * size;
            float r = 3.0 + 4.0 * h + layer * 2.0;
            float d = length(p - center);
            ring += smoothstep(1.4, 0.0, abs(d - r)) * 0.8 + smoothstep(r, 0.0, d) * 0.08;
        }
    }
    color.rgb += ring * backgroundMask(color.rgb) * float3(0.55, 0.9, 1.0) * 0.95;
    return color;
}"""),
    "petals": ("Cherry blossom petals drifting down.", """
float4 main(float4 pos : SV_POSITION, float2 tex : TEXCOORD) : SV_TARGET {
    float4 color = shaderTexture.Sample(samplerState, tex);
    float2 px = tex * Resolution / Scale;
    float petal = 0.0;
    for (float layer = 0.0; layer < 3.0; layer += 1.0) {
        float2 p = px;
        p.y -= Time * (16.0 + layer * 10.0);
        p.x -= Time * (10.0 + layer * 6.0) + sin(p.y * 0.02 + layer * 2.3 + Time * 0.8) * 18.0;
        float2 q = p;
        q.x *= 0.6;
        petal += particles(q, 52.0 + layer * 26.0, 0.12, 3.2 + layer * 1.0, layer * 9.0);
    }
    color.rgb += petal * backgroundMask(color.rgb) * float3(1.0, 0.62, 0.74) * 1.1;
    return color;
}"""),
    "rain": ("Rain streaks running down a window.", """
float4 main(float4 pos : SV_POSITION, float2 tex : TEXCOORD) : SV_TARGET {
    float4 color = shaderTexture.Sample(samplerState, tex);
    float2 px = tex * Resolution / Scale;
    float streaks = 0.0;
    for (float layer = 0.0; layer < 2.0; layer += 1.0) {
        float column = floor(px.x / (9.0 + layer * 5.0));
        float h = hash(float2(column, layer * 7.0));
        if (h > 0.7) {
            float speed = 260.0 + 220.0 * h + layer * 120.0;
            float y = fmod(px.y - Time * speed - h * 900.0, 180.0 + h * 140.0);
            float width = 9.0 + layer * 5.0;
            float x = abs(px.x - (column + 0.5) * width);
            streaks += smoothstep(26.0, 0.0, abs(y)) * smoothstep(1.6, 0.4, x) * (0.4 + 0.6 * h);
        }
    }
    color.rgb += streaks * backgroundMask(color.rgb) * float3(0.7, 0.8, 1.0) * 0.8;
    return color;
}"""),
    "fireflies": ("Fireflies drifting and blinking softly.", """
float4 main(float4 pos : SV_POSITION, float2 tex : TEXCOORD) : SV_TARGET {
    float4 color = shaderTexture.Sample(samplerState, tex);
    float2 px = tex * Resolution / Scale;
    float light = 0.0;
    for (float layer = 0.0; layer < 2.0; layer += 1.0) {
        float2 p = px;
        p.x += sin(Time * 0.4 + layer * 2.0 + p.y * 0.01) * 20.0;
        p.y += cos(Time * 0.3 + layer + p.x * 0.01) * 14.0;
        float2 cell = floor(p / (70.0 + layer * 30.0));
        float h = hash(cell + layer * 11.0);
        float blink = saturate(sin(Time * (0.8 + h * 1.6) + h * 30.0) * 1.6 - 0.4);
        light += particles(p, 70.0 + layer * 30.0, 0.14, 4.5 + layer, layer * 11.0) * blink;
    }
    color.rgb += light * backgroundMask(color.rgb) * float3(0.95, 0.9, 0.4) * 1.3;
    return color;
}"""),
}

# Ghostty (macOS, Linux) runs Shadertoy-style GLSL: iChannel0 is the terminal
# screen, iTime the clock, and fragCoord starts at the bottom-left corner. The
# HLSL bodies are translated; the helpers below keep the same names.
GLSL_COMMON = """// Shared by Ambiance's Ghostty effects (custom-shader, Shadertoy format).
// Every effect only paints over the background: the text stays sharp and readable.
#define Scale 1.0
#define Time iTime
#define Resolution iResolution.xy

float saturate(float x) { return clamp(x, 0.0, 1.0); }

float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

float backgroundMask(vec3 color) {
    return 1.0 - smoothstep(0.55, 0.85, dot(color, vec3(0.299, 0.587, 0.114)));
}

float particles(vec2 px, float size, float density, float radius, float seed) {
    vec2 cell = floor(px / size);
    float h = hash(cell + seed);
    if (h < 1.0 - density) return 0.0;
    vec2 center = (cell + vec2(0.2 + 0.6 * hash(cell + seed + 1.3), 0.2 + 0.6 * hash(cell + seed + 2.7))) * size;
    float d = length(px - center);
    float halo = exp(-d / (radius * 1.6)) * 0.45;
    return (smoothstep(radius, 0.0, d) + halo) * (0.5 + 0.5 * h);
}

// `tex` runs top to bottom, as in the Windows Terminal version.
vec4 sampleScreen(vec2 t) {
    return texture(iChannel0, vec2(t.x, 1.0 - t.y));
}
"""


def to_glsl(body):
    import re

    out = body.replace(
        "float4 main(float4 pos : SV_POSITION, float2 tex : TEXCOORD) : SV_TARGET {",
        "void mainImage(out vec4 fragColor, in vec2 fragCoord) {\n    vec2 tex = vec2(fragCoord.x, iResolution.y - fragCoord.y) / iResolution.xy;",
    )
    out = out.replace("shaderTexture.Sample(samplerState, ", "sampleScreen(")
    out = re.sub(r"\bfloat([234])\b", r"vec\1", out)
    out = re.sub(r"\bfrac\(", "fract(", out)
    out = re.sub(r"\bfmod\(", "mod(", out)
    return out.replace("return color;", "fragColor = color;")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, (title, body) in EFFECTS.items():
        (OUT / f"{name}.hlsl").write_text(f"// {title}\n{COMMON}{body}\n", encoding="utf-8")
        (OUT / f"{name}.glsl").write_text(f"// {title}\n{GLSL_COMMON}{to_glsl(body)}\n", encoding="utf-8")
        print("✓", name)
