// Cherry blossom petals drifting down.
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
    float petal = 0.0;
    for (float layer = 0.0; layer < 3.0; layer += 1.0) {
        vec2 p = px;
        p.y -= Time * (16.0 + layer * 10.0);
        p.x -= Time * (10.0 + layer * 6.0) + sin(p.y * 0.02 + layer * 2.3 + Time * 0.8) * 18.0;
        vec2 q = p;
        q.x *= 0.6;
        petal += particles(q, 52.0 + layer * 26.0, 0.12, 3.2 + layer * 1.0, layer * 9.0);
    }
    color.rgb += petal * backgroundMask(color.rgb) * vec3(1.0, 0.62, 0.74) * 1.1;
    fragColor = color;
}
