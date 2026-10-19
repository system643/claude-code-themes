// Bubbles rising and wobbling, like the deep sea.
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
}
