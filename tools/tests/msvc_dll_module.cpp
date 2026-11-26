static volatile unsigned long long counter = 41;

extern "C" __declspec(dllexport) unsigned long long BmoStep(unsigned long long increment) {
    const auto result = counter + increment;
    counter = result;
    return result;
}
