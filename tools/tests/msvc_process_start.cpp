#include "../../userspace/runtime/abi/include/bmo_abi.h"

extern "C" {
__declspec(dllimport) const wchar_t* GetCommandLineW(void);
__declspec(dllimport) void ExitProcess(unsigned long);
__declspec(dllimport) void* GetStdHandle(unsigned long);
__declspec(dllimport) int WriteFile(void*, const void*, unsigned long, unsigned long*, void*);
}

static unsigned long written;

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
    if (bmo_invoke(4, 2, 0x100000000ull, 0, 0).status != BMO_BAD_ARG) ExitProcess(93);
    static constexpr char message[] = "GetCommandLineW and ExitProcess OK\r\n";
    if (written || !WriteFile(GetStdHandle(static_cast<unsigned long>(-11)), message, sizeof(message) - 1,
                   &written, nullptr) || written != sizeof(message) - 1) ExitProcess(94);
    ExitProcess(BMO_WIN64_EXIT_CODE);
    bmo_invoke(4, 2, 95, 0, 0);
}
