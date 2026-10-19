// Falling green streaks of digital rain.
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
    float column = floor(px.x / 14.0);
    float speed = 60.0 + 140.0 * hash(vec2(column, 1.0));
    float offset = hash(vec2(column, 2.0)) * 2000.0;
    float head = mod(Time * speed + offset, Resolution.y / Scale + 400.0) - 200.0;
    float trail = saturate(1.0 - (head - px.y) / 220.0) * step(px.y, head);
    float cellOn = step(0.35, hash(vec2(column, floor(px.y / 16.0) + floor(Time * 8.0))));
    // Thin vertical strokes rather than blocks, so the rain stays in the background.
    float stroke = step(mod(px.x, 14.0), 2.0) * step(mod(px.y, 16.0), 11.0);
    float glyph = trail * cellOn * stroke;
    float bright = step(head - 16.0, px.y) * step(px.y, head) * stroke;
    color.rgb += (glyph * vec3(0.0, 0.45, 0.15) + bright * vec3(0.4, 0.9, 0.5) * 0.5) * backgroundMask(color.rgb) * 0.75;
    fragColor = color;
}
