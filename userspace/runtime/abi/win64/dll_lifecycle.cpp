#include "../include/bmo_abi.h"

extern "C" __declspec(dllimport) int BmoDllEntry(void* module, unsigned long reason, void* reserved);
extern "C" unsigned int bmo_dll_client_main();
extern "C" void bmo_crt_initialize();
extern "C" void bmo_crt_finalize();

extern "C" void bmo_main() {
    auto* const module = reinterpret_cast<void*>(0x40800000ull);
    if (!BmoDllEntry(module, 1, nullptr)) {
        bmo_invoke(4, 2, 2, 0, 0);
        return;
    }
    bmo_crt_initialize();
    const auto status = bmo_dll_client_main();
    bmo_crt_finalize();
    BmoDllEntry(module, 0, nullptr);
    bmo_invoke(4, 2, status, 0, 0);
}
