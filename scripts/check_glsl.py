"""Compiles every Ghostty shader (GLSL, Shadertoy format) with glslangValidator.

Ghostty silently skips a shader that does not compile, so this catches mistakes
before users see a plain terminal. Usage: python3 scripts/check_glsl.py
"""
import subprocess
import sys
import tempfile
from pathlib import Path

SHADERS = Path(__file__).resolve().parents[1] / "app" / "src-tauri" / "shaders"

# What Ghostty wraps a Shadertoy-style shader with.
PRELUDE = """#version 430 core
uniform vec3 iResolution;
uniform float iTime;
uniform sampler2D iChannel0;
out vec4 _fragColor;
"""
EPILOGUE = """
void main() {
    mainImage(_fragColor, gl_FragCoord.xy);
}
"""


def main():
    failed = 0
    for shader in sorted(SHADERS.glob("*.glsl")):
        with tempfile.NamedTemporaryFile("w", suffix=".frag", delete=False, encoding="utf-8") as wrapped:
            wrapped.write(PRELUDE + shader.read_text(encoding="utf-8") + EPILOGUE)
        result = subprocess.run(["glslangValidator", wrapped.name], capture_output=True, text=True)
        Path(wrapped.name).unlink()
        if result.returncode == 0:
            print(f"✓ {shader.name}")
        else:
            failed += 1
            print(f"✗ {shader.name}\n{result.stdout}{result.stderr}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
