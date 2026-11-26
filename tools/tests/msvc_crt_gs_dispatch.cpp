// One synchronous call into the vendor handler using a live MSVC stack frame.
using Word = unsigned long long;
using Rva = unsigned int;

struct RuntimeFunction {
    Rva begin;
    Rva end;
    Rva unwind;
};

struct FixtureImage {
    Word base;
    Rva table;
    Rva table_bytes;
    Rva readonly_begin;
    Rva readonly_end;
};

extern "C" {

#pragma section(".rdata$BMO", read)
__declspec(allocate(".rdata$BMO")) extern const volatile FixtureImage bmo_gs_image = {
    0x424d4f4753444953ull, 0, 0, 0, 0
};

volatile unsigned int bmo_gs_dispatch_active;

struct DispatcherContext;
using Handler = int (*)(void*, Word, void*, DispatcherContext*);
struct DispatcherContext {
    Word control_pc;
    Word image_base;
    const RuntimeFunction* entry;
    Word establisher_frame;
    Word target_ip;
    void* context_record;
    Handler language_handler;
    const void* handler_data;
    void* history_table;
    unsigned int scope_index;
    unsigned int reserved;
};

int __GSHandlerCheck(void*, Word, void*, DispatcherContext*);
}

static_assert(sizeof(FixtureImage) == 24 && sizeof(RuntimeFunction) == 12);
static_assert(sizeof(DispatcherContext) == 80);

static bool readonly_range(Rva start, Rva bytes) {
    return start >= bmo_gs_image.readonly_begin && start <= bmo_gs_image.readonly_end &&
           bytes <= bmo_gs_image.readonly_end - start;
}

extern "C" int bmo_gs_dispatch(Word control_pc, Word frame) {
    const Word base = bmo_gs_image.base;
    const Rva table_bytes = bmo_gs_image.table_bytes;
    if (control_pc < base || control_pc - base > 0xffffffffu ||
        !table_bytes || table_bytes % sizeof(RuntimeFunction) ||
        !readonly_range(bmo_gs_image.table, table_bytes)) return 0;

    const auto* table = reinterpret_cast<const RuntimeFunction*>(base + bmo_gs_image.table);
    const Rva pc = static_cast<Rva>(control_pc - base);
    const RuntimeFunction* found = nullptr;
    for (unsigned int index = 0; index < table_bytes / sizeof(RuntimeFunction); ++index) {
        if (table[index].begin <= pc && pc < table[index].end) {
            found = &table[index];
            break;
        }
    }
    if (!found || !readonly_range(found->unwind, 4)) return 0;
    const auto* info = reinterpret_cast<const unsigned char*>(base + found->unwind);
    const unsigned int slots = info[2];
    const unsigned int tail = 4 + ((slots + 1) & ~1u) * 2;
    // This call is in the body of a fixed RSP frame with a v1 exception handler.
    if ((info[0] != 0x09 && info[0] != 0x19) || info[3] ||
        pc - found->begin < info[1] || !readonly_range(found->unwind, tail + 8)) return 0;

    Rva allocation = 0;
    for (unsigned int slot = 0; slot < slots; ++slot) {
        const unsigned int code = info[5 + slot * 2];
        const unsigned int op = code & 15;
        if (op == 0) continue; // UWOP_PUSH_NONVOL
        if (op != 2 || allocation) return 0; // UWOP_ALLOC_SMALL
        allocation = 8 * ((code >> 4) + 1);
    }
    const auto* trailer = reinterpret_cast<const Rva*>(info + tail);
    const Rva cookie_offset = trailer[1] & ~7u;
    if (allocation < 8 || cookie_offset > allocation - 8 || (trailer[1] & 4) ||
        base + trailer[0] != reinterpret_cast<Word>(&__GSHandlerCheck)) return 0;

    // The synchronous fixture supplies only the inputs used by this handler.
    DispatcherContext context = {control_pc, base, found, frame, 0, nullptr,
                                 &__GSHandlerCheck, trailer + 1, nullptr, 0, 0};
    bmo_gs_dispatch_active = 1;
    const int result = __GSHandlerCheck(nullptr, frame, nullptr, &context);
    bmo_gs_dispatch_active = 0;
    return result;
}
