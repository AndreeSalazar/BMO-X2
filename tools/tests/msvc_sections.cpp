#include "../../userspace/runtime/abi/include/bmo_abi.h"
#ifdef BMO_MSVC_WINDOW
#include "msvc_window.h"
#endif

extern "C" {
__declspec(dllimport) unsigned long long GetTickCount64(void);
__declspec(dllimport) void* GetStdHandle(unsigned long selector);
__declspec(dllimport) int WriteFile(void* handle, const void* buffer, unsigned long count,
                                    unsigned long* written, void* overlapped);

#ifdef BMO_MSVC_EXTERNAL_HEAP
__declspec(dllimport) void* GetProcessHeap(void);
__declspec(dllimport) void* HeapAlloc(void*, unsigned long, size_t);
__declspec(dllimport) void* HeapReAlloc(void*, unsigned long, void*, size_t);
__declspec(dllimport) int HeapFree(void*, unsigned long, void*);

static bool check_heap() {
    const unsigned long zero = 8, in_place = 16;
    constexpr size_t capacity = 65536;
    void* heap = GetProcessHeap();
    auto* first = static_cast<unsigned char*>(HeapAlloc(heap, zero, 31));
    void* neighbor = HeapAlloc(heap, 0, 32);
    if (!heap || !first || !neighbor || (reinterpret_cast<size_t>(first) & 15) ||
        HeapAlloc(nullptr, 0, 1) || HeapAlloc(heap, 0, capacity + 1) || !HeapFree(heap, 0, nullptr) ||
        HeapFree(heap, 0, first + 16) || HeapReAlloc(heap, in_place, first, 64)) {
        return false;
    }
    for (size_t i = 0; i < 31; ++i) {
        if (first[i]) return false;
        first[i] = static_cast<unsigned char>(i + 1);
    }
    auto* moved = static_cast<unsigned char*>(HeapReAlloc(heap, zero, first, 65));
    if (!moved || moved == first || HeapFree(heap, 0, first)) return false;
    for (size_t i = 0; i < 65; ++i) {
        if (moved[i] != (i < 31 ? i + 1 : 0)) return false;
    }
    if (!HeapFree(heap, 0, neighbor) || HeapReAlloc(heap, 0, moved, capacity) ||
        moved[30] != 31 || HeapReAlloc(heap, in_place, moved, 17) != moved ||
        HeapReAlloc(heap, in_place | zero, moved, 80) != moved || moved[16] != 17 ||
        moved[17] || moved[79] || !HeapFree(heap, 0, moved)) return false;
    auto* whole = static_cast<volatile unsigned char*>(HeapAlloc(heap, zero, capacity));
    if (!whole || whole[capacity - 1]) return false;
    whole[capacity - 1] = 0xff;
    if (HeapAlloc(heap, 0, 1) || !HeapFree(heap, 0, const_cast<unsigned char*>(whole))) return false;
    void* empty = HeapAlloc(heap, 0, 0);
    return empty && HeapFree(heap, 0, empty);
}
#endif

#ifdef BMO_MSVC_PACKAGE_FILE
__declspec(dllimport) void* CreateFileW(const wchar_t*, unsigned long, unsigned long,
                                      void*, unsigned long, unsigned long, void*);
__declspec(dllimport) int ReadFile(void*, void*, unsigned long, unsigned long*, void*);
__declspec(dllimport) int CloseHandle(void*);
__declspec(dllimport) unsigned long GetLastError(void);

static bool check_package_file() {
    constexpr unsigned long generic_read = 0x80000000, open_existing = 3;
    constexpr unsigned long chunk = 200, file_size = 1027;
    void* invalid = reinterpret_cast<void*>(static_cast<size_t>(-1));
    if (CreateFileW(L"missing.bin", generic_read, 1, nullptr, open_existing, 0, nullptr) != invalid ||
        GetLastError() != 2 ||
        CreateFileW(L"input.bin", 0x40000000, 1, nullptr, open_existing, 0, nullptr) != invalid ||
        GetLastError() != 5) return false;
    void* file = CreateFileW(L"input.bin", generic_read, 1, nullptr, open_existing, 0, nullptr);
    if (file == invalid ||
        CreateFileW(L"input.bin", generic_read, 1, nullptr, open_existing, 0, nullptr) != invalid ||
        GetLastError() != 32) return false;
    auto* buffer = static_cast<unsigned char*>(HeapAlloc(GetProcessHeap(), 0, chunk));
    if (!buffer) return false;
    unsigned long received = 0;
    if (ReadFile(file, buffer, 1, &received, &received) || received || GetLastError() != 87) return false;
    unsigned long offset = 0;
    while (offset < file_size) {
        const unsigned long remaining = file_size - offset;
        if (!ReadFile(file, buffer, chunk, &received, nullptr) ||
            received != (remaining < chunk ? remaining : chunk)) return false;
        for (unsigned long index = 0; index < received; ++index) {
            if (buffer[index] != static_cast<unsigned char>(29 * (offset + index) + BMO_PACKAGE_SEED)) return false;
        }
        offset += received;
    }
    if (!ReadFile(file, buffer, chunk, &received, nullptr) || received ||
        !CloseHandle(file) || CloseHandle(file) || GetLastError() != 6) return false;
    void* reopened = CreateFileW(L"input.bin", generic_read, 1, nullptr, open_existing, 0, nullptr);
    return reopened != invalid && reopened != file &&
        !ReadFile(file, buffer, 1, &received, nullptr) && !received && GetLastError() == 6 &&
        ReadFile(reopened, buffer, 1, &received, nullptr) && received == 1 &&
        buffer[0] == BMO_PACKAGE_SEED && CloseHandle(reopened) && HeapFree(GetProcessHeap(), 0, buffer);
}
#endif

volatile unsigned long long phase = 0x424d4f58;
volatile unsigned long long first_ms;
volatile unsigned long long second_ms;
static const unsigned char text[] = "BMO-X2";
static constexpr char hello[] = "Hola mundo desde C++ / MSVC en BMO-X2\r\n";
unsigned long written;
volatile unsigned long long index = 1;
volatile unsigned char scratch[6000];

void bmo_main(void) {
#ifdef BMO_MSVC_EXTERNAL_HEAP
    if (!check_heap()) {
        bmo_invoke(4, 2, 4, 0, 0);
        return;
    }
#endif
#ifdef BMO_MSVC_PACKAGE_FILE
    if (!check_package_file()) {
        bmo_invoke(4, 2, 5, 0, 0);
        return;
    }
#endif
#ifdef BMO_MSVC_EXTERNAL_CONSOLE
    if (first_ms || second_ms || scratch[5999]) {
        bmo_invoke(4, 2, 1, 0, 0);
        return;
    }
#else
    if (first_ms || second_ms || scratch[5999]) for (;;) {}
#endif
    scratch[index & 3] = text[index & 3];
    first_ms = GetTickCount64();
#ifdef BMO_MSVC_EXTERNAL_CONSOLE
    const auto clock = bmo_invoke(2, 2, 0, 0, 0);
    const auto wait = bmo_wait(2, 0, clock.value + 25'000'000);
    const auto oversized = bmo_invoke(4, 1, 0, 9, 0);
    if (clock.status || wait.status != BMO_TIMED_OUT || wait.value ||
        oversized.status != BMO_BAD_ARG || oversized.value) {
        bmo_invoke(4, 2, 2, 0, 0);
        return;
    }
#else
    bmo_wait(2, 1, 3);
#endif
    second_ms = GetTickCount64();
#ifdef BMO_MSVC_EXTERNAL_CONSOLE
    const bool invalid_handle = !WriteFile(nullptr, hello, sizeof(hello)-1, &written, nullptr) && !written;
    const bool completed = invalid_handle && second_ms >= first_ms + 20 && scratch[1] == 'M' &&
        WriteFile(GetStdHandle(static_cast<unsigned long>(-11)), hello, sizeof(hello)-1, &written, nullptr) &&
        written == sizeof(hello)-1;
    bmo_invoke(4, 2, completed ? 0 : 3, 0, 0);
#else
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
#endif
}
}
