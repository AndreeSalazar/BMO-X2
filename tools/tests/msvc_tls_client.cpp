#include "../../userspace/runtime/abi/include/bmo_abi.h"

static constinit thread_local unsigned long long value = 41;
static volatile unsigned long long visits = 0;
static unsigned long long* first_value;

extern "C" void bmo_main() {
    const auto thread = visits;
    const auto slot = reinterpret_cast<unsigned long long>(&value);
    const auto base = 0x40e00200ull + thread * 4096;
    auto* const tail = reinterpret_cast<volatile unsigned long long*>(base + 16);
    bool good = thread < 2 && slot == base + 8 && value == 41 && *tail == 0;
    if (thread == 0) {
        first_value = &value;
    } else {
        good = good && first_value && first_value != &value && *first_value == 50;
    }
    value += 9;
    *tail = 77;
    visits = thread + 1;
    bmo_invoke(4, 2, good ? 0 : 1, 0, 0);
}
