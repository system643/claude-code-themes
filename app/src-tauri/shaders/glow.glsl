// A neon-like glow around the text.
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
    vec2 texel = 1.6 * Scale / Resolution;
    vec3 halo = vec3(0.0, 0.0, 0.0);
    for (float x = -2.0; x <= 2.0; x += 1.0) {
        for (float y = -2.0; y <= 2.0; y += 1.0) {
            halo += sampleScreen(tex + vec2(x, y) * texel).rgb;
        }
    }
    halo /= 25.0;
    float pulse = 0.85 + 0.15 * sin(Time * 1.5);
    color.rgb += max(halo - 0.08, 0.0) * 0.55 * pulse * backgroundMask(color.rgb);
    fragColor = color;
}
