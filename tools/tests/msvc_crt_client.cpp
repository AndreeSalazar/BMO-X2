#include "../../userspace/runtime/abi/include/bmo_abi.h"

extern "C" {
int abs(int);
long long llabs(long long);
unsigned long long strlen(const char*);
int strcmp(const char*, const char*);
int strncmp(const char*, const char*, unsigned long long);
#ifdef BMO_CRT_GS_NATIVE
unsigned long long strspn(const char*, const char*);
unsigned long long strcspn(const char*, const char*);
int bmo_test_gs_dispatch();
int bmo_test_gs_cpu_fault();
int bmo_test_gs_call_client();
int bmo_test_gs_prologue();
#endif
int atexit(void (*)());
void bmo_crt_initialize();
void bmo_crt_finalize();
unsigned long long bmo_session_stdout(unsigned int selector);
int bmo_session_write(unsigned long long handle, const unsigned char* buffer,
                      unsigned int count, unsigned int* written, unsigned long long overlapped);
}

#ifdef BMO_CRT_GS
extern "C" {
extern volatile unsigned long long __security_cookie;
volatile unsigned int bmo_gs_test_mode = 0x424d4f00;
}
#endif

static auto* volatile crt_abs = &abs;
static auto* volatile crt_llabs = &llabs;
static auto* volatile crt_strlen = &strlen;
static auto* volatile crt_strcmp = &strcmp;
static auto* volatile crt_strncmp = &strncmp;
#ifdef BMO_CRT_GS_NATIVE
static auto* volatile crt_strspn = &strspn;
static auto* volatile crt_strcspn = &strcspn;
#endif
static volatile unsigned int phase;

struct Lifecycle {
    Lifecycle() {
        if (crt_abs(-42) == 42) phase = 1;
    }
    ~Lifecycle() {
        if (phase == 3) phase = 4;
    }
};

static Lifecycle lifecycle;

static void on_exit() {
    if (phase == 2) phase = 3;
}

extern "C" __declspec(noinline) int bmo_crt_client_main() {
    const char text[] = "123 BMO-X2";
#ifdef BMO_CRT_GS_NATIVE
    if (crt_strspn(text, "0123456789") != 3 || crt_strcspn(text, " -") != 3 ||
        crt_strspn(text + 4, "0123456789") != 0 || crt_strcspn(text + 4, "?") != 6) {
        return 1;
    }
#endif
    if (phase != 1 || crt_llabs(-4294967297ll) != 4294967297ll ||
        crt_strlen(text) != 10 || crt_strcmp(text + 4, "BMO-X2") != 0 ||
        crt_strcmp("A", "B") >= 0 || crt_strncmp(text, "1234", 3) != 0 ||
        crt_strncmp(text, "1234", 4) >= 0 || atexit(on_exit) != 0) {
        return 1;
    }
    phase = 2;
#ifdef BMO_CRT_GS
    // Mutate the reference after the compiler saved its cookie, with no stack write.
    if (bmo_gs_test_mode == 0x424d4f01) {
        __security_cookie = __security_cookie ^ 1;
    }
#ifdef BMO_CRT_GS_NATIVE
    const auto mode = bmo_gs_test_mode;
    if (mode == 0x424d4f07 && bmo_test_gs_prologue() != 1) return 1;
    if (mode >= 0x424d4f02 && mode <= 0x424d4f06) {
        const auto original = __security_cookie;
        if (mode & 1) __security_cookie = original ^ 1;
        const int disposition = mode >= 0x424d4f04 ? bmo_test_gs_cpu_fault() : bmo_test_gs_dispatch();
        __security_cookie = original;
        if (disposition != 1 || (mode & 1)) return 1;
        if (mode == 0x424d4f06) {
            bmo_test_gs_cpu_fault();
            return 1;
        }
    }
#endif
#endif
    return 0;
}

extern "C" void bmo_main() {
    bmo_crt_initialize();
#ifdef BMO_CRT_GS_NATIVE
    const int status = bmo_test_gs_call_client();
#else
    const int status = bmo_crt_client_main();
#endif
    bmo_crt_finalize();
    if (status || phase != 4) {
        bmo_invoke(4, 2, 1, 0, 0);
        return;
    }
    static constexpr unsigned char crt_message[] = "MSVC CRT: inicio, main y cierre OK\r\n";
    const unsigned char* message = crt_message;
    unsigned int length = sizeof(crt_message) - 1;
#ifdef BMO_CRT_GS_NATIVE
    if (bmo_gs_test_mode == 0x424d4f02) {
        static constexpr unsigned char handler_message[] = "MSVC CRT: __GSHandlerCheck OK\r\n";
        message = handler_message;
        length = sizeof(handler_message) - 1;
    }
    if (bmo_gs_test_mode == 0x424d4f04) {
        static constexpr unsigned char unwind_message[] = "MSVC CRT: unwind de dos marcos OK\r\n";
        message = unwind_message;
        length = sizeof(unwind_message) - 1;
    }
    if (bmo_gs_test_mode == 0x424d4f07) {
        static constexpr unsigned char prologue_message[] = "MSVC CRT: prologo RBP y epilogo pop/ret OK\r\n";
        message = prologue_message;
        length = sizeof(prologue_message) - 1;
    }
#endif
    unsigned int written = 0;
    const auto handle = bmo_session_stdout(static_cast<unsigned int>(-11));
    const bool complete = bmo_session_write(handle, message, length, &written, 0) && written == length;
    bmo_invoke(4, 2, complete ? 0 : 2, 0, 0);
}
