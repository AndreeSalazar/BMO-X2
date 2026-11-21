#version 450

layout(push_constant) uniform Rotation { float angle; } rotation;
layout(location = 0) out vec3 color;

const vec3 vertices[3] = vec3[3](
    vec3(0.0, -0.78, 0.0), vec3(0.70, 0.42, 0.0), vec3(-0.70, 0.42, 0.0)
);
const vec3 palette[3] = vec3[3](
    vec3(0.97, 0.65, 1.00), vec3(0.25, 0.95, 0.83), vec3(0.29, 0.55, 1.00)
);

void main() {
    vec3 axis = normalize(vec3(0.26, 0.86, 0.24));
    vec3 p = vertices[gl_VertexIndex];
    float s = sin(rotation.angle), c = cos(rotation.angle);
    vec3 q = p * c + cross(axis, p) * s + axis * dot(axis, p) * (1.0 - c);
    gl_Position = vec4(q.x * 0.75, q.y, 0.45 + q.z * 0.2, 1.0 + q.z * 0.35);
    color = palette[gl_VertexIndex];
}
