#include "../../userspace/runtime/abi/include/bmo_abi.h"
#ifdef BMO_MSVC_WINDOW
#include "msvc_window.h"
#endif

extern "C" {
__declspec(dllimport) unsigned long long GetTickCount64(void);
__declspec(dllimport) void* GetStdHandle(unsigned long selector);
__declspec(dllimport) int WriteFile(void* handle, const void* buffer, unsigned long count,
                                    unsigned long* written, void* overlapped);

volatile unsigned long long phase = 0x424d4f58;
volatile unsigned long long first_ms;
volatile unsigned long long second_ms;
static const unsigned char text[] = "BMO-X2";
static constexpr char hello[] = "Hola mundo desde C++ / MSVC en BMO-X2\r\n";
unsigned long written;
volatile unsigned long long index = 1;
volatile unsigned char scratch[6000];

void bmo_main(void) {
    if (first_ms || second_ms || scratch[5999]) for (;;) {}
    scratch[index & 3] = text[index & 3];
    first_ms = GetTickCount64();
    bmo_wait(2, 1, 3);
    second_ms = GetTickCount64();
    if (WriteFile(nullptr, hello, sizeof(hello)-1, &written, nullptr) || written) for (;;) {}
    if (second_ms >= first_ms + 20 && scratch[1] == 'M' &&
        WriteFile(GetStdHandle(static_cast<unsigned long>(-11)), hello, sizeof(hello)-1, &written, nullptr) &&
        written == sizeof(hello)-1) {
        phase = 0x53454332;
#ifdef BMO_MSVC_WINDOW
        draw_window();
        bmo_director_window(window_pixels);
#endif
    }
    for (;;) {}
}
}
