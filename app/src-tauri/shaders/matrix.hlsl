// Falling green streaks of digital rain.
// Shared by Ambiance's Windows Terminal effects (experimental.pixelShaderPath).
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
}
