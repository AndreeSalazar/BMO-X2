#include "../../userspace/runtime/abi/include/bmo_abi.h"

extern "C" {
__declspec(dllimport) const wchar_t* GetCommandLineW(void);
__declspec(dllimport) const char* GetCommandLineA(void);
__declspec(dllimport) void GetStartupInfoW(void*);
__declspec(dllimport) unsigned GetACP(void);
__declspec(dllimport) unsigned long GetLastError(void);
__declspec(dllimport) void SetLastError(unsigned long);
__declspec(dllimport) void ExitProcess(unsigned long);
__declspec(dllimport) void* GetStdHandle(unsigned long);
__declspec(dllimport) int WriteFile(void*, const void*, unsigned long, unsigned long*, void*);
}

static unsigned long written;
static volatile unsigned char startup[106];

extern "C" void bmo_main(void) {
    static constexpr wchar_t expected[] =
        LR"cmd("minigzip demo.exe" -c "" "datos )cmd"
        L"\u00f1\U0001f600"
        LR"cmd(.bin" a\"b "C:\dir con espacio\\")cmd";
    const auto* command_line = GetCommandLineW();
    if (!command_line || command_line != GetCommandLineW() ||
        (reinterpret_cast<bmo_word>(command_line) & 1)) ExitProcess(91);
    for (auto unit : expected) {
        if (*command_line++ != unit) ExitProcess(92);
    }
    static constexpr char expected_ansi[] =
        R"cmd("minigzip demo.exe" -c "" "datos )cmd"
        "\xc3\xb1\xf0\x9f\x98\x80"
        R"cmd(.bin" a\"b "C:\dir con espacio\\")cmd";
    const auto* command_ansi = GetCommandLineA();
    if (GetACP() != 65001 || !command_ansi || command_ansi != GetCommandLineA()) ExitProcess(96);
    for (auto unit : expected_ansi) {
        if (*command_ansi++ != unit) ExitProcess(97);
    }
    if (GetLastError()) ExitProcess(98);
    SetLastError(0xa1b2c3d4ul);
    for (auto& byte : startup) byte = 0xa5;
    GetStartupInfoW(const_cast<unsigned char*>(&startup[1]));
    if (startup[0] != 0xa5 || startup[1] != 104 || startup[105] != 0xa5) ExitProcess(99);
    for (unsigned index = 2; index < 105; ++index) {
        if (startup[index]) ExitProcess(100);
    }
    if (GetLastError() != 0xa1b2c3d4ul) ExitProcess(101);
    SetLastError(0);
    if (GetLastError()) ExitProcess(102);
    if (bmo_invoke(4, 2, 0x100000000ull, 0, 0).status != BMO_BAD_ARG) ExitProcess(93);
    static constexpr char message[] = "Win64 startup info and last error OK\r\n";
    if (written || !WriteFile(GetStdHandle(static_cast<unsigned long>(-11)), message, sizeof(message) - 1,
                   &written, nullptr) || written != sizeof(message) - 1) ExitProcess(94);
    ExitProcess(BMO_WIN64_EXIT_CODE);
    bmo_invoke(4, 2, 95, 0, 0);
}
