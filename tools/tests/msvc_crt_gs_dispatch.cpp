// One vendor handler and bounded virtual unwind using live Win64 stack frames.
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

struct CpuContext {
    Word pc;
    Word rsp;
    Word stack_begin;
    Word nonvolatile[8]; // RBX, RBP, RSI, RDI, R12-R15
    Word xmm[10][2];     // XMM6-XMM15
};

struct ExpectedUnwind {
    Word wrapper_pc;
    Word wrapper_rsp;
    Word caller_pc;
    Word caller_rsp;
    Word caller_rbx;
    Word caller_rsi;
    Word caller_rdi;
    Word caller_r12;
    Word caller_xmm6[2];
};

extern "C" {

#pragma section(".rdata$BMO", read)
__declspec(allocate(".rdata$BMO")) extern const volatile FixtureImage bmo_gs_image = {
    0x424d4f4753444953ull, 0, 0, 0, 0
};

volatile unsigned int bmo_gs_dispatch_active;
ExpectedUnwind bmo_gs_expected;

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
static_assert(sizeof(CpuContext) == 248 && sizeof(ExpectedUnwind) == 80);

static bool readonly_range(Rva start, Rva bytes) {
    return start >= bmo_gs_image.readonly_begin && start <= bmo_gs_image.readonly_end &&
           bytes <= bmo_gs_image.readonly_end - start;
}

static const RuntimeFunction* find_function(Word control_pc) {
    const Word base = bmo_gs_image.base;
    const Rva table_bytes = bmo_gs_image.table_bytes;
    if (control_pc < base || control_pc - base > 0xffffffffu ||
        !table_bytes || table_bytes % sizeof(RuntimeFunction) ||
        !readonly_range(bmo_gs_image.table, table_bytes)) return nullptr;

    const auto* table = reinterpret_cast<const RuntimeFunction*>(base + bmo_gs_image.table);
    const Rva pc = static_cast<Rva>(control_pc - base);
    for (unsigned int index = 0; index < table_bytes / sizeof(RuntimeFunction); ++index) {
        if (table[index].begin <= pc && pc < table[index].end) {
            return &table[index];
        }
    }
    return nullptr;
}

extern "C" int bmo_gs_dispatch(Word control_pc, Word frame) {
    const Word base = bmo_gs_image.base;
    const auto* found = find_function(control_pc);
    if (!found || !readonly_range(found->unwind, 4)) return 0;
    const auto* info = reinterpret_cast<const unsigned char*>(base + found->unwind);
    const unsigned int slots = info[2];
    const unsigned int tail = 4 + ((slots + 1) & ~1u) * 2;
    // This call is in the body of a fixed RSP frame with a v1 exception handler.
    if ((info[0] != 0x09 && info[0] != 0x19) || info[3] ||
        control_pc - base - found->begin < info[1] || !readonly_range(found->unwind, tail + 8)) return 0;

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

static bool stack_range(const CpuContext& context, Word address, Word bytes) {
    constexpr Word stack_bytes = 4096;
    return !(address & 7) && address >= context.stack_begin &&
           address - context.stack_begin <= stack_bytes - bytes;
}

static bool pop_word(CpuContext& context, Word& value) {
    if (!stack_range(context, context.rsp, sizeof(Word))) return false;
    value = *reinterpret_cast<const Word*>(context.rsp);
    context.rsp += sizeof(Word);
    return true;
}

static bool restore_unwind_codes(CpuContext& context, const unsigned char* info, bool chained) {
    constexpr int register_slot[16] = {-1, -1, -1, 0, -1, 1, 2, 3, -1, -1, -1, -1, 4, 5, 6, 7};
    unsigned int previous_offset = info[1];
    unsigned int saved = 0;
    unsigned int xmm_saved = 0;
    bool adjusted = false;
    for (unsigned int slot = 0; slot < info[2]; ++slot) {
        const unsigned int offset = info[4 + slot * 2];
        const unsigned int code = info[5 + slot * 2];
        if (!offset || offset > previous_offset) return false;
        previous_offset = offset;
        const unsigned int op = code & 15;
        const unsigned int operand = code >> 4;
        if (chained && op != 4) return false;
        if (op == 2 && !adjusted) { // UWOP_ALLOC_SMALL
            context.rsp += 8 * (operand + 1);
            adjusted = true;
        } else if (op == 1 && !adjusted && !operand) { // UWOP_ALLOC_LARGE, scaled form
            if (++slot >= info[2]) return false;
            const auto* size = info + 4 + slot * 2;
            const unsigned int units = size[0] | (size[1] << 8);
            if (units <= 16) return false;
            context.rsp += 8 * units;
            adjusted = true;
        } else if (op == 0 && register_slot[operand] >= 0 && !(saved & (1u << operand))) {
            if (!pop_word(context, context.nonvolatile[register_slot[operand]])) return false;
            saved |= 1u << operand;
            adjusted = true;
        } else if ((op == 4 || op == 8) && !adjusted) { // UWOP_SAVE_NONVOL / UWOP_SAVE_XMM128
            if (++slot >= info[2]) return false;
            const auto* encoded = info + 4 + slot * 2;
            const unsigned int units = encoded[0] | (encoded[1] << 8);
            const Word address = context.rsp + units * (op == 4 ? 8ull : 16ull);
            const auto* value = reinterpret_cast<const Word*>(address);
            if (op == 4) {
                if (register_slot[operand] < 0 || (saved & (1u << operand)) ||
                    !stack_range(context, address, 8)) return false;
                context.nonvolatile[register_slot[operand]] = value[0];
                saved |= 1u << operand;
            } else {
                if (operand < 6 || (xmm_saved & (1u << operand)) ||
                    !stack_range(context, address, 16)) return false;
                context.xmm[operand - 6][0] = value[0];
                context.xmm[operand - 6][1] = value[1];
                xmm_saved |= 1u << operand;
            }
        } else {
            return false;
        }
    }
    return true;
}

static bool unwind_fixed_frame(CpuContext& context) {
    // The current PC is a return address from the callee, in the caller body.
    if (!context.pc) return false;
    const Word control_pc = context.pc - 1;
    const Word base = bmo_gs_image.base;
    const auto* function = find_function(control_pc);
    for (unsigned int depth = 0; depth < 8; ++depth) {
        if (!function || !readonly_range(function->unwind, 4)) return false;
        const auto* info = reinterpret_cast<const unsigned char*>(base + function->unwind);
        const unsigned int flags = info[0] >> 3;
        const bool chained = flags == 4;
        const unsigned int tail = 4 + ((info[2] + 1) & ~1u) * 2;
        if ((info[0] & 7) != 1 || flags > 4 || info[3] ||
            (!depth && control_pc - base - function->begin < info[1]) ||
            !readonly_range(function->unwind, tail + (chained ? sizeof(RuntimeFunction) : 0)) ||
            !restore_unwind_codes(context, info, chained)) return false;
        if (!chained) return pop_word(context, context.pc) && context.pc && find_function(context.pc - 1);

        const auto* parent = reinterpret_cast<const RuntimeFunction*>(info + tail);
        if (parent->begin >= function->begin) return false;
        function = find_function(base + parent->begin);
        if (!function || function->begin != parent->begin ||
            function->end != parent->end || function->unwind != parent->unwind) return false;
    }
    return false;
}

extern "C" int bmo_gs_cpu_dispatch(CpuContext* context) {
    // Undo the faulting leaf's call, then inspect its live protected parent.
    if (!pop_word(*context, context->pc) || !context->pc ||
        bmo_gs_dispatch(context->pc - 1, context->rsp) != 1) return 0;
    if (!unwind_fixed_frame(*context) || context->pc != bmo_gs_expected.wrapper_pc ||
        context->rsp != bmo_gs_expected.wrapper_rsp || context->nonvolatile[0] != 0x12340003 ||
        context->nonvolatile[2] != 0x12340006 || context->nonvolatile[3] != 0x12340007 ||
        context->nonvolatile[4] != 0x1234000c || context->xmm[0][0] != ~0ull ||
        context->xmm[0][1] != ~0ull) return 0;
    return unwind_fixed_frame(*context) && context->pc == bmo_gs_expected.caller_pc &&
           context->rsp == bmo_gs_expected.caller_rsp &&
           context->nonvolatile[0] == bmo_gs_expected.caller_rbx &&
           context->nonvolatile[2] == bmo_gs_expected.caller_rsi &&
           context->nonvolatile[3] == bmo_gs_expected.caller_rdi &&
           context->nonvolatile[4] == bmo_gs_expected.caller_r12 &&
           context->xmm[0][0] == bmo_gs_expected.caller_xmm6[0] &&
           context->xmm[0][1] == bmo_gs_expected.caller_xmm6[1];
}
