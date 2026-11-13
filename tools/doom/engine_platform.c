#include <stdio.h>
#include <stdint.h>
#include "doomgeneric.h"
#include "doomkeys.h"
#include "guest_invoke.h"

void DG_Init(void) {
    puts("BMO DOOM START");
    DG_SleepMs(1);
    doom_invoke(1, 1, (400ul << 48) | (640ul << 32), 0);
}

void DG_DrawFrame(void) {
    static int presented;
    if (!doom_invoke(1, 6, (uintptr_t)DG_ScreenBuffer, 0) && !presented) {
        presented = 1;
        puts("BMO DOOM FRAME");
    }
}

uint32_t DG_GetTicksMs(void) { return (uint32_t)doom_invoke(3, 3, 0, 0) * 10; }

void DG_SleepMs(uint32_t ms) {
    unsigned ticks = ms / 10 + (ms % 10 != 0);
    while (ticks) {
        unsigned step = ticks > 100 ? 100 : ticks;
        register unsigned long service __asm__("rax") = 1;
        unsigned long cap = 2, op = 0, duration = step;
        __asm__ volatile("syscall" : "+a"(service), "+D"(cap), "+S"(op), "+d"(duration)
                         :
                         : "rcx", "r11", "r8", "r9", "r10", "memory");
        if (service != 256) break;
        ticks -= step;
    }
}

int DG_GetKey(int *pressed, unsigned char *key) {
    static const unsigned char keys[128] = {
        [0x01] = KEY_ESCAPE, [0x02] = '1', [0x03] = '2', [0x04] = '3',
        [0x05] = '4', [0x06] = '5', [0x07] = '6', [0x08] = '7',
        [0x0e] = KEY_BACKSPACE, [0x0f] = KEY_TAB, [0x15] = 'y',
        [0x1c] = KEY_ENTER, [0x1d] = KEY_FIRE, [0x2a] = KEY_RSHIFT,
        [0x31] = 'n', [0x36] = KEY_RSHIFT, [0x38] = KEY_RALT, [0x39] = KEY_USE,
        [0x48] = KEY_UPARROW, [0x4b] = KEY_LEFTARROW,
        [0x4d] = KEY_RIGHTARROW, [0x50] = KEY_DOWNARROW,
    };
    for (unsigned i = 0; i < 16; ++i) {
        unsigned long scan = doom_invoke(2, 2, 0, 0);
        if (scan == 256 || scan == 257) break;
        if (scan > 255 || scan == 0xe0 || scan == 0xe1) continue;
        *key = keys[scan & 0x7f];
        if (!*key) continue;
        *pressed = !(scan & 0x80);
        return 1;
    }
    return 0;
}

void DG_SetWindowTitle(const char *title) { puts(title); }

/* IRET enters with a page-aligned stack and no return address. */
__attribute__((force_align_arg_pointer)) _Noreturn void _start(void) {
    static char *args[] = {
        "doom", "-iwad", "doom1.wad", "-warp", "1", "1",
        "-nosound", "-nomusic", "-nomouse", "-mb", "6", NULL
    };
    doomgeneric_Create(sizeof(args) / sizeof(args[0]) - 1, args);
    for (;;) doomgeneric_Tick();
}
