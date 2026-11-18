// Freestanding PE fixture: one internal DIR64 pointer, no CRT or DLL imports.
using u64 = unsigned long long;

static volatile u64 counter = 1;
static volatile u64* volatile counter_address = &counter;

extern "C" __declspec(noreturn) void entry(void) {
    for (;;) {
        counter = *counter_address + 1;
    }
}
