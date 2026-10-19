// Softly twinkling stars over the background.
// Shared by Ambiance's Ghostty effects (custom-shader, Shadertoy format).
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

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 tex = vec2(fragCoord.x, iResolution.y - fragCoord.y) / iResolution.xy;
    vec4 color = sampleScreen(tex);
    vec2 px = tex * Resolution / Scale;
    float star = 0.0;
    for (float layer = 0.0; layer < 2.0; layer += 1.0) {
        float size = 26.0 + layer * 19.0;
        vec2 cell = floor(px / size);
        float h = hash(cell + layer * 7.0);
        float twinkle = 0.55 + 0.45 * sin(Time * (1.2 + h * 2.5) + h * 40.0);
        star += particles(px, size, 0.06, 2.0 + layer * 0.6, layer * 7.0) * twinkle;
    }
    color.rgb += star * backgroundMask(color.rgb) * vec3(0.75, 0.82, 1.0) * 1.2;
    fragColor = color;
}
