#include "../../userspace/runtime/abi/include/bmo_abi.h"

extern "C" __declspec(dllimport) unsigned long long BmoStep(unsigned long long increment);

static volatile unsigned long long step = 1;

extern "C" void bmo_main() {
    const auto first = BmoStep(step);
    const auto second = BmoStep(step + 1);
    bmo_invoke(4, 2, first == 42 && second == 44 ? 0 : 1, 0, 0);
}
