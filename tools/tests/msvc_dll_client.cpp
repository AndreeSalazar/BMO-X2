#include "../../userspace/runtime/abi/include/bmo_abi.h"

extern "C" __declspec(dllimport) unsigned long long BmoStep(unsigned long long increment);

static volatile unsigned long long step = 1;

#ifdef BMO_DLL_LIFECYCLE
extern "C" void __ud2();
#pragma intrinsic(__ud2)

static volatile unsigned int constructors;

struct LifecycleCheck {
    unsigned long long increment;
    unsigned long long expected;

    LifecycleCheck(unsigned long long value, unsigned long long result) noexcept
        : increment(value), expected(result) {
        if (BmoStep(0) != 41) {
            __ud2();
        }
        constructors += 1;
    }

    ~LifecycleCheck() noexcept {
        if (BmoStep(increment) != expected) {
            __ud2();
        }
    }
};

static LifecycleCheck first_destructor(3, 49);
static LifecycleCheck second_destructor(2, 46);

extern "C" unsigned int bmo_dll_client_main() {
    const auto first = BmoStep(step);
    const auto second = BmoStep(step + 1);
    return constructors == 2 && first == 42 && second == 44 ? 0 : 1;
}
#else
extern "C" void bmo_main() {
    const auto first = BmoStep(step);
    const auto second = BmoStep(step + 1);
    bmo_invoke(4, 2, first == 42 && second == 44 ? 0 : 1, 0, 0);
}
#endif
