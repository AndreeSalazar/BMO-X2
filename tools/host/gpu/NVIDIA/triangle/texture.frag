#version 450
layout(location = 0) in vec3 color;
layout(location = 0) out vec4 pixel;
layout(set = 0, binding = 0) uniform sampler2D tile;

void main() {
    vec2 uv = color.rg * vec2(1.0, 2.5) - vec2(0.0, 1.375);
    pixel = texture(tile, uv);
}
