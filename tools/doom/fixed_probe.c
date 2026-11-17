#include "m_fixed.h"

/* Return zero only when the original DoomGeneric arithmetic agrees. */
int doom_fixed_check(void) {
    return FixedMul(FRACUNIT + FRACUNIT / 2, FRACUNIT * 2) != FRACUNIT * 3
        || FixedMul(-FRACUNIT, FRACUNIT / 2) != -FRACUNIT / 2
        || FixedDiv(FRACUNIT * 3, FRACUNIT * 2) != FRACUNIT + FRACUNIT / 2
        || FixedDiv(FRACUNIT, 0) != 2147483647;
}

#ifdef BMO_HOST
int main(void) {
    return doom_fixed_check();
}
#elif defined(BMO_EXTERNAL)
#include "guest_invoke.h"

static const volatile fixed_t operands[] __attribute__((section(".rodata.doom"))) = {
    FRACUNIT + FRACUNIT / 2, FRACUNIT * 2
};
static volatile fixed_t seed = FRACUNIT * 3;
static volatile fixed_t result __attribute__((section(".bss.doom_result")));

#ifdef BMO_WAD
#include <stdint.h>
#include "engine_include/stdio.h"

static unsigned long read_wad(unsigned long offset) {
    return doom_invoke(4, 4, offset, 0);
}

static unsigned long find_e1m1(unsigned long *remaining) {
    if (doom_invoke(1, 4, 0, 0) != ~0ul || read_wad(~0ul) != ~0ul
        || read_wad(0) != 0x44415749) {
        return 0;
    }
    unsigned long count = read_wad(4);
    unsigned long directory = read_wad(8);
    if (count == 0 || count > 65536 || directory < 12 || directory > 0x1000000) {
        return 0;
    }
    if (read_wad(directory + 16 * count - 4) == ~0ul) {
        return 0;
    }
    for (unsigned long i = 0; i < count; ++i) {
        unsigned long record = directory + 16 * i;
        if (read_wad(record + 8) == 0x314d3145 && read_wad(record + 12) == 0) {
            *remaining = count - i - 1;
            return record + 16;
        }
    }
    return 0;
}

static int check_file(void) {
    if (doom_invoke(1, 5, 0, 0) != ~0ul) {
        return 0;
    }
    FILE *file = fopen("doom1.wad", "rb");
    if (!file) {
        return 0;
    }
    uint32_t header[3];
    uint32_t last;
    unsigned long length = doom_invoke(4, 5, 0, 0);
    int ok = fread(header, sizeof(header[0]), 3, file) == 3
        && header[0] == 0x44415749 && header[1] == read_wad(4) && header[2] == read_wad(8)
        && ftell(file) == 12
        && fseek(file, -4, SEEK_END) == 0 && ftell(file) == (long)(length - 4)
        && fread(&last, 4, 1, file) == 1 && last == read_wad(length - 4)
        && fread(&last, 4, 1, file) == 0 && feof(file)
        && fseek(file, 1, SEEK_END) == -1
        && fseek(file, 0, SEEK_SET) == 0 && !feof(file);
    return fclose(file) == 0 && ok;
}

typedef struct {
    unsigned long start;
    unsigned long size;
} Lump;

static Lump find_lump(unsigned long record, unsigned long count,
                      unsigned long name_lo, unsigned long name_hi) {
    for (unsigned long i = 0; i < count && i < 10; ++i, record += 16) {
        if (read_wad(record + 8) == name_lo && read_wad(record + 12) == name_hi) {
            unsigned long start = read_wad(record);
            unsigned long size = read_wad(record + 4);
            if (start >= 12 && start <= 0x1000000 && size >= 4 && size <= 0x1000000
                && read_wad(start + size - 4) != ~0ul) {
                return (Lump){start, size};
            }
            break;
        }
    }
    return (Lump){0, 0};
}

static void fill(unsigned long x, unsigned long y, unsigned long w,
                 unsigned long h, unsigned long color) {
    if (doom_invoke(1, 1, x | y << 16 | w << 32 | h << 48, color) != 0) {
        __builtin_trap();
    }
}

static void line(int x, int y, int end_x, int end_y) {
    int dx = end_x >= x ? end_x - x : x - end_x;
    int dy = end_y >= y ? y - end_y : end_y - y;
    int sx = x < end_x ? 1 : -1;
    int sy = y < end_y ? 1 : -1;
    int error = dx + dy;
    for (;;) {
        fill(x, y, 1, 1, 0x6ee7b7);
        if (x == end_x && y == end_y) {
            break;
        }
        int twice = 2 * error;
        if (twice >= dy) {
            error += dy;
            x += sx;
        }
        if (twice <= dx) {
            error += dx;
            y += sy;
        }
    }
}

static int draw_e1m1(void) {
    unsigned long remaining;
    unsigned long record = find_e1m1(&remaining);
    if (!record) {
        return 0;
    }
    Lump vertices = find_lump(record, remaining, 0x54524556, 0x53455845); /* VERTEXES */
    Lump lines = find_lump(record, remaining, 0x454e494c, 0x53464544); /* LINEDEFS */
    if (!vertices.size || vertices.size % 4 || vertices.size > 4096
        || !lines.size || lines.size % 14 || lines.size > 14336) {
        return 0;
    }
    int min_x = 32767, min_y = 32767, max_x = -32768, max_y = -32768;
    for (unsigned long offset = 0; offset < vertices.size; offset += 4) {
        unsigned long pair = read_wad(vertices.start + offset);
        int x = (int16_t)pair, y = (int16_t)(pair >> 16);
        if (x < min_x) min_x = x;
        if (x > max_x) max_x = x;
        if (y < min_y) min_y = y;
        if (y > max_y) max_y = y;
    }
    int span_x = max_x - min_x, span_y = max_y - min_y;
    int span = span_x > span_y ? span_x : span_y;
    if (!span) {
        return 0;
    }
    fill(0, 0, 640, 400, 0x0d0e17);
    for (unsigned long offset = 0; offset < lines.size; offset += 14) {
        unsigned long ends = read_wad(lines.start + offset);
        unsigned long a = (ends & 0xffff) * 4, b = (ends >> 16) * 4;
        if (a >= vertices.size || b >= vertices.size) {
            return 0;
        }
        a = read_wad(vertices.start + a);
        b = read_wad(vertices.start + b);
        line(320 + ((int16_t)a * 2 - min_x - max_x) * 150 / span,
             220 + (min_y + max_y - (int16_t)(a >> 16) * 2) * 150 / span,
             320 + ((int16_t)b * 2 - min_x - max_x) * 150 / span,
             220 + (min_y + max_y - (int16_t)(b >> 16) * 2) * 150 / span);
    }
    return 1;
}
#endif

void bmo_main(void) {
    if (doom_fixed_check() || result != 0) {
        __builtin_trap();
    }
    fixed_t product = FixedMul(operands[0], operands[1]);
    if (product != seed || product != FRACUNIT * 3) {
        __builtin_trap();
    }
    seed = product / 3;
    result = product;
#ifdef BMO_WAD
    if (!check_file() || !draw_e1m1()) {
        __builtin_trap();
    }
#endif
    const unsigned long rect = 24ul | 32ul << 16 | 96ul << 32 | 40ul << 48;
    if (doom_invoke(2, 1, rect, 0xff0000) != 257
        || doom_invoke(1, 1, rect, 0x6ee7b7) != 0) {
        __builtin_trap();
    }
    for (;;) {
        __asm__ volatile("pause");
    }
}
#else
#include "../../userspace/runtime/abi/include/bmo_abi.h"

extern _Noreturn void doom_probe_complete(void);

void bmo_main(void) {
    if (doom_fixed_check()) {
        __builtin_trap();
    }
    bmo_result reply = bmo_invoke(1, BMO_OP_ECHO, FRACUNIT * 3, 0, 0);
    if (reply.status != BMO_OK || reply.value != FRACUNIT * 3) {
        __builtin_trap();
    }
    reply = bmo_invoke(0, BMO_OP_ECHO, 0, 0, 0);
    if (reply.status != -2 || reply.value != 0) {
        __builtin_trap();
    }
    reply = bmo_wait(1, 0, 0);
    if (reply.status != -4 || reply.value != 0) {
        __builtin_trap();
    }
    doom_probe_complete();
}
#endif
