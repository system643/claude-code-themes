// Cherry blossom petals drifting down.
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
}
