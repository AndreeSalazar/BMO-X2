using Callback = void (*)();

// MSVC places its dynamic C++ initializers between these COFF subsections.
#pragma section(".CRT$XCA", read)
#pragma section(".CRT$XCZ", read)
__declspec(allocate(".CRT$XCA")) Callback const first_initializer = nullptr;
__declspec(allocate(".CRT$XCZ")) Callback const last_initializer = nullptr;

static Callback exit_callbacks[16];
static unsigned int exit_count;

extern "C" int atexit(Callback callback) {
    if (!callback || exit_count == sizeof(exit_callbacks) / sizeof(exit_callbacks[0])) {
        return -1;
    }
    exit_callbacks[exit_count++] = callback;
    return 0;
}

extern "C" void bmo_crt_initialize() {
    const auto end = reinterpret_cast<unsigned long long>(&last_initializer);
    auto address = reinterpret_cast<unsigned long long>(&first_initializer) + sizeof(Callback);
    for (; address < end; address += sizeof(Callback)) {
        const auto initializer = *reinterpret_cast<Callback const*>(address);
        if (initializer) {
            initializer();
        }
    }
}

extern "C" void bmo_crt_finalize() {
    while (exit_count) {
        const auto callback = exit_callbacks[--exit_count];
        exit_callbacks[exit_count] = nullptr;
        callback();
    }
}
