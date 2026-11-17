extern "C" unsigned int bmo_msvc_panel(unsigned int* output, unsigned int pixels) {
    constexpr unsigned int width = 160, height = 100;
    if (!output || pixels != width * height) return 0;
    for (unsigned int y = 0; y < height; ++y) {
        for (unsigned int x = 0; x < width; ++x) {
            unsigned int color = 0x131c31 + (y / 12) * 0x010102;
            const int span = (static_cast<int>(y) - 14) / 2;
            const int dx = static_cast<int>(x) - 80;
            if (y >= 14 && y < 82 && dx >= -span && dx <= span)
                color = 0x7ee7d5 - (y - 14) * 0x000101;
            output[y * width + x] = color;
        }
    }
    return 1;
}
