#include "../../userspace/runtime/abi/include/bmo_abi.h"

extern "C" {
__declspec(dllimport) const wchar_t* GetCommandLineW(void);
__declspec(dllimport) const char* GetCommandLineA(void);
__declspec(dllimport) void GetStartupInfoW(void*);
__declspec(dllimport) unsigned GetACP(void);
__declspec(dllimport) unsigned GetOEMCP(void);
__declspec(dllimport) int IsValidCodePage(unsigned);
__declspec(dllimport) int GetCPInfo(unsigned, void*);
__declspec(dllimport) int MultiByteToWideChar(unsigned, unsigned, const char*, int, wchar_t*, int);
__declspec(dllimport) int WideCharToMultiByte(unsigned, unsigned, const wchar_t*, int, char*, int, const char*, int*);
__declspec(dllimport) int QueryPerformanceCounter(long long*);
__declspec(dllimport) int QueryPerformanceFrequency(long long*);
__declspec(dllimport) int IsProcessorFeaturePresent(unsigned long);
__declspec(dllimport) int IsDebuggerPresent(void);
__declspec(dllimport) unsigned long GetModuleFileNameW(void*, wchar_t*, unsigned long);
__declspec(dllimport) unsigned long GetLastError(void);
__declspec(dllimport) void SetLastError(unsigned long);
__declspec(dllimport) void ExitProcess(unsigned long);
__declspec(dllimport) void* GetStdHandle(unsigned long);
__declspec(dllimport) int SetStdHandle(unsigned long, void*);
__declspec(dllimport) int WriteFile(void*, const void*, unsigned long, unsigned long*, void*);
__declspec(dllimport) unsigned long TlsAlloc(void);
__declspec(dllimport) int TlsFree(unsigned long);
__declspec(dllimport) void* TlsGetValue(unsigned long);
__declspec(dllimport) int TlsSetValue(unsigned long, void*);
__declspec(dllimport) void InitializeSListHead(void*);
using FlsCallback = void (*)(void*);
__declspec(dllimport) unsigned long FlsAlloc(FlsCallback);
__declspec(dllimport) int FlsFree(unsigned long);
__declspec(dllimport) void* FlsGetValue(unsigned long);
__declspec(dllimport) int FlsSetValue(unsigned long, void*);
__declspec(dllimport) unsigned long GetCurrentThreadId(void);
__declspec(dllimport) int InitializeCriticalSectionEx(void*, unsigned long, unsigned long);
__declspec(dllimport) int InitializeCriticalSectionAndSpinCount(void*, unsigned long);
__declspec(dllimport) void EnterCriticalSection(void*);
__declspec(dllimport) void LeaveCriticalSection(void*);
__declspec(dllimport) void DeleteCriticalSection(void*);
__declspec(dllimport) wchar_t* GetEnvironmentStringsW(void);
__declspec(dllimport) int FreeEnvironmentStringsW(wchar_t*);
__declspec(dllimport) int SetEnvironmentVariableW(const wchar_t*, const wchar_t*);
__declspec(dllimport) void* GetCurrentProcess(void);
__declspec(dllimport) unsigned long GetCurrentProcessId(void);
__declspec(dllimport) int TerminateProcess(void*, unsigned);
}

static unsigned long written;
static volatile unsigned char startup[106];
static unsigned long slots[64];
alignas(16) static volatile bmo_word slist[4];
static unsigned long fls_slots[128];
static unsigned long exit_slot;
static unsigned releases;
static int token;
static wchar_t large_environment_value[512];

struct LargeReadOnly {
    unsigned char start;
    unsigned char middle[228 * 1024 - 2];
    unsigned char end;
};

static const LargeReadOnly large_readonly = {0x42, {}, 0x6d};
static volatile unsigned char large_private[8192];

static void check_image_path(void) {
    constexpr wchar_t expected[] = LR"(X:\BMO-X2\minigzip demo.exe)";
    constexpr auto length = sizeof(expected) / sizeof(expected[0]) - 1;
    wchar_t full[length + 2] = {};
    full[length + 1] = 0x55;
    SetLastError(123);
    if (GetModuleFileNameW(nullptr, full, length + 1) != length || GetLastError() != 123 ||
        full[length + 1] != 0x55) ExitProcess(166);
    for (unsigned i = 0; i <= length; ++i) if (full[i] != expected[i]) ExitProcess(167);
    wchar_t short_path[] = {0xffff, 0xffff, 0xffff, 0x55};
    if (GetModuleFileNameW(nullptr, short_path, 3) != 3 || GetLastError() != 122 ||
        short_path[0] != L'X' || short_path[1] != L':' || short_path[2] ||
        short_path[3] != 0x55) ExitProcess(168);
    if (GetModuleFileNameW(nullptr, short_path, 0) || GetLastError() != 122 ||
        GetModuleFileNameW(reinterpret_cast<void*>(12345), short_path, 3) ||
        GetLastError() != 126 || short_path[0] != L'X') ExitProcess(169);
}

static void check_std_handles(void) {
    constexpr auto in = static_cast<unsigned long>(-10);
    constexpr auto out = static_cast<unsigned long>(-11);
    constexpr auto err = static_cast<unsigned long>(-12);
    auto* original = GetStdHandle(out);
    auto* redirected = reinterpret_cast<void*>(0x1234);
    if (!original || GetStdHandle(in) || GetStdHandle(err) != original ||
        !SetStdHandle(out, redirected) || GetStdHandle(out) != redirected ||
        GetStdHandle(err) != original) ExitProcess(170);
    unsigned long count = 1;
    if (WriteFile(GetStdHandle(out), "X", 1, &count, nullptr) || count ||
        !SetStdHandle(out, original) || GetStdHandle(out) != original) ExitProcess(171);
    if (!SetStdHandle(in, redirected) || GetStdHandle(in) != redirected ||
        !SetStdHandle(in, nullptr) || GetStdHandle(in) ||
        SetStdHandle(0, original) || GetLastError() != 87 ||
        reinterpret_cast<bmo_word>(GetStdHandle(0)) != ~bmo_word{0} || GetLastError() != 87) ExitProcess(172);
}

static void check_platform(void) {
    long long frequency = 0, start = -1, end = -1;
    SetLastError(123);
    if (IsDebuggerPresent() || !IsProcessorFeaturePresent(2) || !IsProcessorFeaturePresent(6) ||
        !IsProcessorFeaturePresent(9) || !IsProcessorFeaturePresent(10) || !IsProcessorFeaturePresent(12) ||
        IsProcessorFeaturePresent(23) || IsProcessorFeaturePresent(39) || IsProcessorFeaturePresent(40) ||
        IsProcessorFeaturePresent(41) || IsProcessorFeaturePresent(0xfffffffful) ||
        !QueryPerformanceFrequency(&frequency) || frequency != 1000000000 ||
        !QueryPerformanceCounter(&start) || start < 0 || GetLastError() != 123) ExitProcess(163);
    const auto seq = bmo_invoke(2, 1, 0, 0, 0);
    if (seq.status != BMO_OK || bmo_wait(2, seq.value, static_cast<bmo_word>(start) + 10000151).status != BMO_TIMED_OUT ||
        !QueryPerformanceCounter(&end) || end - start < 10000151 || GetLastError() != 123) ExitProcess(164);
    if (QueryPerformanceCounter(nullptr) || GetLastError() != 87 ||
        QueryPerformanceFrequency(nullptr) || GetLastError() != 87) ExitProcess(165);
}

static void check_text_encoding(void) {
    constexpr unsigned utf8 = 65001;
    constexpr wchar_t wide[] = L"A\u00f1\u20ac\U0001f600";
    constexpr char bytes[] = "A\xc3\xb1\xe2\x82\xac\xf0\x9f\x98\x80";
    wchar_t decoded[7] = {};
    char encoded[12] = {};
    unsigned char info[20];
    for (auto& byte : info) byte = 0xa5;
    SetLastError(123);
    if (GetOEMCP() != utf8 || !IsValidCodePage(utf8) || IsValidCodePage(0) || IsValidCodePage(1252) ||
        !GetCPInfo(1, info) || GetLastError() != 123) ExitProcess(148);
    if (info[0] != 4 || info[4] != '?' || info[18] != 0xa5 || info[19] != 0xa5) ExitProcess(149);
    for (unsigned i = 1; i < 18; ++i) {
        if (i != 4 && info[i]) ExitProcess(150);
    }
    if (GetCPInfo(1252, info) || GetLastError() != 87 || info[0] != 4) ExitProcess(151);
    decoded[6] = 0x55;
    encoded[11] = 0x55;
    if (MultiByteToWideChar(utf8, 8, bytes, -1, nullptr, 0) != 6 ||
        MultiByteToWideChar(0, 8, bytes, -1, decoded, 6) != 6 || decoded[6] != 0x55 ||
        WideCharToMultiByte(utf8, 0x80, wide, -1, nullptr, 0, nullptr, nullptr) != 11 ||
        WideCharToMultiByte(3, 0x80, wide, -1, encoded, 11, nullptr, nullptr) != 11 ||
        encoded[11] != 0x55) ExitProcess(152);
    for (unsigned i = 0; i < 6; ++i) if (decoded[i] != wide[i]) ExitProcess(153);
    for (unsigned i = 0; i < 11; ++i) if (encoded[i] != bytes[i]) ExitProcess(154);

    constexpr char embedded[] = {'X', 0, 'Y'};
    if (MultiByteToWideChar(utf8, 0, embedded, 3, decoded, 3) != 3 ||
        decoded[0] != L'X' || decoded[1] || decoded[2] != L'Y' ||
        WideCharToMultiByte(utf8, 0, decoded, 3, encoded, 3, nullptr, nullptr) != 3 ||
        encoded[0] != 'X' || encoded[1] || encoded[2] != 'Y') ExitProcess(155);

    constexpr char malformed[] = "\xed\xa0\x80" "Q\xe2\x81";
    if (MultiByteToWideChar(utf8, 8, malformed, 6, nullptr, 0) || GetLastError() != 1113 ||
        MultiByteToWideChar(utf8, 0, malformed, 6, decoded, 4) != 4 ||
        decoded[0] != 0xfffd || decoded[1] != 0xfffd || decoded[2] != L'Q' ||
        decoded[3] != 0xfffd) ExitProcess(156);
    static constexpr wchar_t lone[] = {0xd800, L'Q'};
    if (WideCharToMultiByte(utf8, 0x80, lone, 2, nullptr, 0, nullptr, nullptr) || GetLastError() != 1113 ||
        WideCharToMultiByte(utf8, 0, lone, 2, encoded, 4, nullptr, nullptr) != 4 ||
        static_cast<unsigned char>(encoded[0]) != 0xef || static_cast<unsigned char>(encoded[1]) != 0xbf ||
        static_cast<unsigned char>(encoded[2]) != 0xbd || encoded[3] != 'Q') ExitProcess(157);

    decoded[1] = 0x55;
    encoded[1] = 0x55;
    if (MultiByteToWideChar(utf8, 0, bytes, -1, decoded, 1) || GetLastError() != 122 ||
        decoded[1] != 0x55 || WideCharToMultiByte(utf8, 0, wide, -1, encoded, 1, nullptr, nullptr) ||
        GetLastError() != 122 || encoded[1] != 0x55) ExitProcess(158);
    int used_default = 77;
    if (MultiByteToWideChar(utf8, 1, bytes, -1, decoded, 6) || GetLastError() != 1004 ||
        WideCharToMultiByte(utf8, 0x400, wide, -1, encoded, 11, nullptr, nullptr) ||
        GetLastError() != 1004 || WideCharToMultiByte(utf8, 0, wide, -1, encoded, 11, nullptr, &used_default) ||
        GetLastError() != 87 || used_default != 77) ExitProcess(159);
    if (MultiByteToWideChar(utf8, 0, bytes, 0, decoded, 6) || GetLastError() != 87 ||
        WideCharToMultiByte(utf8, 0, wide, -1, nullptr, 2, nullptr, nullptr) || GetLastError() != 87 ||
        WideCharToMultiByte(utf8, 0, wide, -1, encoded, -1, nullptr, nullptr) || GetLastError() != 87 ||
        MultiByteToWideChar(utf8, 0, reinterpret_cast<const char*>(decoded), 2, decoded, 2) ||
        GetLastError() != 87) ExitProcess(160);
}

template <unsigned N>
static bool environment_matches(const wchar_t* block, const wchar_t (&expected)[N]) {
    if (!block) return false;
    for (unsigned index = 0; index < N; ++index) {
        if (block[index] != expected[index]) return false;
    }
    return true;
}

static void check_environment(void) {
    auto* initial = GetEnvironmentStringsW();
    if (!environment_matches(initial, L"\0") || !FreeEnvironmentStringsW(initial)) ExitProcess(134);
    if (!SetEnvironmentVariableW(L"Z_LAST", L"") ||
        !SetEnvironmentVariableW(L"bmo_NAME", L"uno")) ExitProcess(135);
    auto* before = GetEnvironmentStringsW();
    if (!environment_matches(before, L"bmo_NAME=uno\0Z_LAST=\0")) ExitProcess(136);
    if (!SetEnvironmentVariableW(L"BMO_name", L"dos \u00f1 \U0001f600")) ExitProcess(137);
    auto* after = GetEnvironmentStringsW();
    if (after == before || !environment_matches(after, L"bmo_NAME=dos \u00f1 \U0001f600\0Z_LAST=\0") ||
        !environment_matches(before, L"bmo_NAME=uno\0Z_LAST=\0")) ExitProcess(138);
    if (GetEnvironmentStringsW() || GetLastError() != 8 || FreeEnvironmentStringsW(before + 1) ||
        GetLastError() != 87) ExitProcess(139);
    if (!FreeEnvironmentStringsW(before) || FreeEnvironmentStringsW(before) || GetLastError() != 87 ||
        !FreeEnvironmentStringsW(after)) ExitProcess(140);
    for (unsigned index = 0; index < 511; ++index) large_environment_value[index] = L'X';
    if (SetEnvironmentVariableW(L"BMO_name", large_environment_value) || GetLastError() != 8 ||
        SetEnvironmentVariableW(L"a=b", L"x") || GetLastError() != 87) ExitProcess(141);
    after = GetEnvironmentStringsW();
    if (!environment_matches(after, L"bmo_NAME=dos \u00f1 \U0001f600\0Z_LAST=\0") ||
        !FreeEnvironmentStringsW(after)) ExitProcess(142);
    if (!SetEnvironmentVariableW(L"BMO_NAME", L"x") ||
        !SetEnvironmentVariableW(L"a_first", L"y")) ExitProcess(143);
    after = GetEnvironmentStringsW();
    if (!environment_matches(after, L"a_first=y\0bmo_NAME=x\0Z_LAST=\0") ||
        !FreeEnvironmentStringsW(after)) ExitProcess(144);
    if (!SetEnvironmentVariableW(L"bmo_name", nullptr) ||
        !SetEnvironmentVariableW(L"Z_LAST", nullptr) ||
        !SetEnvironmentVariableW(L"A_FIRST", nullptr) ||
        !SetEnvironmentVariableW(L"absent", nullptr)) ExitProcess(145);
    after = GetEnvironmentStringsW();
    if (!environment_matches(after, L"\0") || !FreeEnvironmentStringsW(after)) ExitProcess(146);
}

struct CriticalSection {
    bmo_word debug_info;
    long lock_count;
    long depth;
    bmo_word owner;
    bmo_word semaphore;
    bmo_word spin_count;
};
static_assert(sizeof(CriticalSection) == 40);

static void check_critical_sections(void) {
    CriticalSection first, second;
    const auto thread = GetCurrentThreadId();
    if (!thread || !InitializeCriticalSectionEx(&first, 4000, 0x01000000ul) ||
        !InitializeCriticalSectionAndSpinCount(&second, 2000)) ExitProcess(125);
    if (first.lock_count != -1 || first.depth || first.owner || first.spin_count ||
        second.lock_count != -1 || second.depth || second.owner || second.spin_count) ExitProcess(126);
    EnterCriticalSection(&first);
    EnterCriticalSection(&first);
    EnterCriticalSection(&second);
    if (first.owner != thread || second.owner != thread || first.depth != 2 ||
        second.depth != 1 || first.lock_count != -2 || second.lock_count != -2) ExitProcess(127);
    LeaveCriticalSection(&first);
    if (first.owner != thread || first.lock_count != -2 || first.depth != 1) ExitProcess(128);
    LeaveCriticalSection(&first);
    if (first.owner || first.depth || first.lock_count != -1 || second.depth != 1) ExitProcess(129);
    LeaveCriticalSection(&second);
    DeleteCriticalSection(&first);
    DeleteCriticalSection(&second);
    if (first.debug_info || first.lock_count || first.depth || first.owner ||
        first.semaphore || first.spin_count || second.debug_info) ExitProcess(130);
    if (InitializeCriticalSectionEx(&first, 0, 0xfffffffful) || GetLastError() != 87 ||
        first.debug_info || first.lock_count) ExitProcess(131);
    if (!InitializeCriticalSectionEx(&first, 0, 0)) ExitProcess(132);
    EnterCriticalSection(&first);
    if (first.depth != 1 || first.owner != thread) ExitProcess(133);
    LeaveCriticalSection(&first);
    DeleteCriticalSection(&first);
}

static void on_fls_free(void* value) {
    if (value != &token || FlsGetValue(fls_slots[0]) || GetLastError()) ExitProcess(113);
    ++releases;
}

static void on_fls_exit(void* value) {
    if (value != &token || FlsGetValue(exit_slot) != &token || GetLastError()) ExitProcess(114);
    static constexpr char message[] = "FLS OK\r\n";
    unsigned long count;
    if (!WriteFile(GetStdHandle(static_cast<unsigned long>(-11)), message, sizeof(message) - 1,
                   &count, nullptr) || count != sizeof(message) - 1) ExitProcess(115);
}

static void check_fls(void) {
    for (auto& slot : fls_slots) {
        slot = FlsAlloc(on_fls_free);
        if (slot >= 128 || FlsGetValue(slot) || GetLastError()) ExitProcess(116);
    }
    if (FlsAlloc(nullptr) != 0xfffffffful || GetLastError() != 259) ExitProcess(117);
    if (!FlsSetValue(fls_slots[0], &token) || FlsGetValue(fls_slots[0]) != &token ||
        !FlsFree(fls_slots[0]) || releases != 1) ExitProcess(118);
    if (FlsFree(fls_slots[0]) || GetLastError() != 87) ExitProcess(119);
    for (unsigned index = 1; index < 128; ++index) {
        if (!FlsFree(fls_slots[index])) ExitProcess(120);
    }
    if (releases != 1 || FlsSetValue(128, &token) || GetLastError() != 87) ExitProcess(121);
    SetLastError(0);
    if (FlsGetValue(128) || GetLastError() != 87) ExitProcess(122);
    exit_slot = FlsAlloc(on_fls_exit);
    if (exit_slot != fls_slots[0] || FlsGetValue(exit_slot) || !FlsSetValue(exit_slot, &token)) ExitProcess(123);
}

static void check_dynamic_tls(void) {
    for (auto& slot : slots) {
        slot = TlsAlloc();
        SetLastError(123);
        if (slot >= 64 || TlsGetValue(slot) || GetLastError()) ExitProcess(103);
        if (!TlsSetValue(slot, &slot) || TlsGetValue(slot) != &slot) ExitProcess(104);
    }
    for (auto& slot : slots) {
        if (TlsGetValue(slot) != &slot) ExitProcess(105);
    }
    if (TlsAlloc() != 0xfffffffful || GetLastError() != 259) ExitProcess(106);
    if (!TlsFree(slots[0]) || TlsFree(slots[0]) || GetLastError() != 87) ExitProcess(107);
    const auto recycled = TlsAlloc();
    if (recycled != slots[0] || TlsGetValue(recycled) || GetLastError()) ExitProcess(108);
    if (TlsSetValue(64, &slots[0]) || GetLastError() != 87) ExitProcess(109);
    SetLastError(0);
    if (TlsGetValue(64) || GetLastError() != 87) ExitProcess(110);
    for (auto slot : slots) {
        if (!TlsFree(slot)) ExitProcess(111);
    }
}

extern "C" void bmo_main(void) {
    const volatile auto& large = large_readonly;
    if (large.start != 0x42 || large.middle[sizeof(large.middle) / 2] || large.end != 0x6d) ExitProcess(124);
    if (large_private[0] || large_private[sizeof(large_private) - 1]) ExitProcess(161);
    large_private[sizeof(large_private) - 1] = large.end;
    if (large_private[0] || large_private[sizeof(large_private) - 1] != 0x6d) ExitProcess(162);
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
    check_dynamic_tls();
    check_fls();
    check_critical_sections();
    check_environment();
    check_text_encoding();
    check_platform();
    check_image_path();
    check_std_handles();
    for (auto& word : slist) word = ~bmo_word{0};
    InitializeSListHead(const_cast<bmo_word*>(slist));
    if (slist[0] || slist[1] || slist[2] != ~bmo_word{0} || slist[3] != ~bmo_word{0}) ExitProcess(112);
    const auto process_id = GetCurrentProcessId();
    if (!process_id || process_id != GetCurrentProcessId() ||
        reinterpret_cast<bmo_word>(GetCurrentProcess()) != ~bmo_word{0} ||
        TerminateProcess(nullptr, 1) || GetLastError() != 6) ExitProcess(147);
    if (bmo_invoke(4, 2, 0x100000000ull, 0, 0).status != BMO_BAD_ARG) ExitProcess(93);
    static constexpr char message[] = "Win64 startup, last error, TLS and SList OK\r\n";
    if (written || !WriteFile(GetStdHandle(static_cast<unsigned long>(-11)), message, sizeof(message) - 1,
                   &written, nullptr) || written != sizeof(message) - 1) ExitProcess(94);
#ifdef BMO_WIN64_TERMINATE
    TerminateProcess(GetCurrentProcess(), BMO_WIN64_EXIT_CODE);
#else
    ExitProcess(BMO_WIN64_EXIT_CODE);
#endif
    bmo_invoke(4, 2, 95, 0, 0);
}
