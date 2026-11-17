#pragma once

extern "C" {
unsigned long long bmo_session_present(const unsigned int*);
unsigned int window_pixels[320 * 200];
}

namespace {
struct Glyph { char letter; unsigned char rows[7]; };
constexpr Glyph glyphs[] = {
    {'2', {14, 17, 1, 2, 4, 8, 31}},
    {'3', {30, 1, 1, 14, 1, 1, 30}},
    {'4', {2, 6, 10, 18, 31, 2, 2}},
    {'6', {14, 16, 16, 30, 17, 17, 14}},
    {'A', {14, 17, 17, 31, 17, 17, 17}},
    {'B', {30, 17, 17, 30, 17, 17, 30}},
    {'C', {14, 17, 16, 16, 16, 17, 14}},
    {'D', {30, 17, 17, 17, 17, 17, 30}},
    {'E', {31, 16, 16, 30, 16, 16, 31}},
    {'F', {31, 16, 16, 30, 16, 16, 16}},
    {'G', {14, 17, 16, 23, 17, 17, 15}},
    {'H', {17, 17, 17, 31, 17, 17, 17}},
    {'I', {14, 4, 4, 4, 4, 4, 14}},
    {'L', {16, 16, 16, 16, 16, 16, 31}},
    {'M', {17, 27, 21, 21, 17, 17, 17}},
    {'N', {17, 25, 21, 19, 17, 17, 17}},
    {'O', {14, 17, 17, 17, 17, 17, 14}},
    {'P', {30, 17, 17, 30, 16, 16, 16}},
    {'Q', {14, 17, 17, 17, 21, 18, 13}},
    {'R', {30, 17, 17, 30, 20, 18, 17}},
    {'S', {15, 16, 16, 14, 1, 1, 30}},
    {'T', {31, 4, 4, 4, 4, 4, 4}},
    {'U', {17, 17, 17, 17, 17, 17, 14}},
    {'V', {17, 17, 17, 17, 17, 10, 4}},
    {'W', {17, 17, 17, 21, 21, 21, 10}},
    {'X', {17, 17, 10, 4, 10, 17, 17}},
    {'Y', {17, 17, 10, 4, 4, 4, 4}},
    {'Z', {31, 1, 2, 4, 8, 16, 31}},
    {'-', {0, 0, 0, 31, 0, 0, 0}},
    {'/', {1, 2, 2, 4, 8, 8, 16}},
    {'+', {0, 4, 4, 31, 4, 4, 0}},
};

void rect(int x, int y, int w, int h, unsigned int color) {
    for (int row = y; row < y + h; ++row)
        for (int col = x; col < x + w; ++col)
            window_pixels[row * 320 + col] = color;
}

void label(int x, int y, const char* text, int scale, unsigned int color) {
    for (; *text; ++text, x += 6 * scale) {
        for (const auto& glyph : glyphs) {
            if (glyph.letter != *text) continue;
            for (int row = 0; row < 7; ++row)
                for (int col = 0; col < 5; ++col)
                    if (glyph.rows[row] & (16 >> col))
                        rect(x + col * scale, y + row * scale, scale, scale, color);
            break;
        }
    }
}

bool draw_window() {
    for (int y = 0; y < 200; ++y)
        rect(0, y, 320, 1, 0x0b101f + (y / 14) * 0x010102);
    rect(0, 0, 320, 23, 0x10192b);
    rect(0, 23, 320, 1, 0x324267);
    label(14, 8, "BMO-X2", 1, 0xeaf2ff);
    label(230, 8, "QEMU / RING 3", 1, 0x93aace);

    rect(25, 47, 272, 116, 0x0b1021);
    rect(24, 44, 272, 116, 0x455581);
    rect(25, 45, 270, 114, 0x141e33);
    rect(25, 45, 270, 18, 0x202c49);
    rect(32, 51, 5, 5, 0x7fe2d5);
    label(43, 51, "MSVC / C++", 1, 0xeaf2ff);

    label(36, 83, "HOLA VENTANA", 2, 0xf1f5ff);
    label(36, 108, "PE32+ / SBEF", 1, 0x8de8da);
    label(36, 125, "PRESENTACION CPU", 1, 0x9eb0d3);
    rect(228, 73, 56, 70, 0x0e1628);
    for (int y = 88; y < 128; ++y) {
        const int span = (y - 88) / 2;
        rect(256 - span, y, 2 * span + 1, 1, 0x74e2d0 - (y - 88) * 0x000101);
    }
    rect(24, 178, 272, 1, 0x455581);
    label(25, 185, "HOST / WIN64", 1, 0xa8bad5);
    label(233, 185, "GOP / CPU", 1, 0x8de8da);
    return bmo_session_present(window_pixels) == 0;
}
}
