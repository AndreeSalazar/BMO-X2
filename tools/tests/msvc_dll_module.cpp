#ifdef BMO_DLL_LIFECYCLE
static volatile unsigned long long counter;
extern "C" void __ud2();
#pragma intrinsic(__ud2)

extern "C" int DllMain(void* module, unsigned long reason, void* reserved) {
    if (module != reinterpret_cast<void*>(0x40800000ull) || reserved) {
        __ud2();
    }
    if (reason == 1 && counter == 0) {
#ifdef BMO_DLL_REJECT_ATTACH
        return 0;
#else
        counter = 41;
        return 1;
#endif
    }
    if (reason == 0 && counter == 49) {
        counter = 0;
        return 1;
    }
    __ud2();
    return 0;
}
#else
static volatile unsigned long long counter = 41;
#endif

extern "C" __declspec(dllexport) unsigned long long BmoStep(unsigned long long increment) {
    const auto result = counter + increment;
    counter = result;
    return result;
}
