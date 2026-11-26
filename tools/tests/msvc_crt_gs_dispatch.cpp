// One vendor handler and bounded virtual unwind using live Win64 stack frames.
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <stddef.h>

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
    Word caller_rbp;
    Word wrapper_rbp;
    Word fixed_rsp;
};

struct ExpectedPrologue {
    Word caller_pc;
    Word caller_rsp;
    Word caller_rsi;
    Word caller_rdi;
    Word caller_rbp;
};

struct TrapRegisters {
    Word rax, rcx, rdx, r8, r9, r10, r11;
    Word flags, cs, ss;
};

extern "C" {

#pragma section(".rdata$BMO", read)
__declspec(allocate(".rdata$BMO")) extern const volatile FixtureImage bmo_gs_image = {
    0x424d4f4753444953ull, 0, 0, 0, 0
};

volatile unsigned int bmo_gs_dispatch_active;
ExpectedUnwind bmo_gs_expected;
ExpectedPrologue bmo_gs_prologue_expected;
CONTEXT bmo_gs_win_context;
EXCEPTION_RECORD bmo_gs_exception_record;
Word bmo_gs_seh_target;
extern volatile unsigned int bmo_gs_test_mode;
int bmo_test_gs_cpu_fault();

EXCEPTION_ROUTINE __GSHandlerCheck;
void bmo_test_gs_epilogue_suffix();
void bmo_test_gs_epilogue_add();
void bmo_test_gs_epilogue_lea();
void bmo_test_gs_epilogue_jump();
void bmo_test_gs_epilogue_invalid();
}

static_assert(sizeof(FixtureImage) == 24 && sizeof(RuntimeFunction) == 12);
static_assert(sizeof(RuntimeFunction) == sizeof(RUNTIME_FUNCTION) &&
              offsetof(RuntimeFunction, unwind) == offsetof(RUNTIME_FUNCTION, UnwindData));
static_assert(sizeof(CpuContext) == 248 && sizeof(ExpectedUnwind) == 104);
static_assert(sizeof(ExpectedPrologue) == 40);
static_assert(sizeof(TrapRegisters) == 80 && offsetof(CONTEXT, FltSave) == 256);
static_assert(alignof(CONTEXT) >= 16);

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

static int dispatch_gs(Word control_pc, Word frame, EXCEPTION_RECORD* exception, CONTEXT* captured) {
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

    DISPATCHER_CONTEXT context = {
        control_pc, base, reinterpret_cast<RUNTIME_FUNCTION*>(const_cast<RuntimeFunction*>(found)),
        frame, 0, captured, &__GSHandlerCheck, const_cast<Rva*>(trailer + 1), nullptr, 0, 0
    };
    bmo_gs_dispatch_active = 1;
    const int result = __GSHandlerCheck(exception, reinterpret_cast<void*>(frame), captured, &context);
    bmo_gs_dispatch_active = 0;
    return result;
}

extern "C" int bmo_gs_dispatch(Word control_pc, Word frame) {
    return dispatch_gs(control_pc, frame, nullptr, nullptr);
}

static void capture_win_context(const CpuContext& cpu, const TrapRegisters& trap) {
    auto& win = bmo_gs_win_context;
    win.ContextFlags = CONTEXT_FULL;
    win.Rip = cpu.pc;
    win.Rsp = cpu.rsp;
    win.EFlags = static_cast<DWORD>(trap.flags);
    win.SegCs = static_cast<WORD>(trap.cs);
    win.SegSs = static_cast<WORD>(trap.ss);
    win.Rax = trap.rax;
    win.Rcx = trap.rcx;
    win.Rdx = trap.rdx;
    win.R8 = trap.r8;
    win.R9 = trap.r9;
    win.R10 = trap.r10;
    win.R11 = trap.r11;
    win.Rbx = cpu.nonvolatile[0];
    win.Rbp = cpu.nonvolatile[1];
    win.Rsi = cpu.nonvolatile[2];
    win.Rdi = cpu.nonvolatile[3];
    win.R12 = cpu.nonvolatile[4];
    win.R13 = cpu.nonvolatile[5];
    win.R14 = cpu.nonvolatile[6];
    win.R15 = cpu.nonvolatile[7];
    win.MxCsr = win.FltSave.MxCsr;
    bmo_gs_exception_record.ExceptionCode = EXCEPTION_ILLEGAL_INSTRUCTION;
    bmo_gs_exception_record.ExceptionAddress = reinterpret_cast<void*>(cpu.pc);
}

static bool stack_range(const CpuContext& context, Word address, Word bytes) {
    constexpr Word stack_bytes = 4096;
    return !(address & 7) && address >= context.stack_begin &&
           address - context.stack_begin <= stack_bytes - bytes;
}

static volatile unsigned int seh_filter_calls;
static volatile unsigned int seh_except_calls;
static volatile unsigned int seh_outer_filter_calls;
static volatile unsigned int seh_outer_except_calls;
static volatile unsigned int seh_cleanup_order;

extern "C" __declspec(noinline) void bmo_gs_seh_finally() {
    __try {
        bmo_test_gs_cpu_fault();
    } __finally {
        seh_cleanup_order = AbnormalTermination() && seh_cleanup_order == 1 ? 2 : 0;
    }
}

__declspec(noinline) static LONG fixture_filter(const EXCEPTION_POINTERS* pointers) {
    if (pointers->ExceptionRecord->ExceptionCode != EXCEPTION_ILLEGAL_INSTRUCTION ||
        reinterpret_cast<Word>(pointers->ExceptionRecord->ExceptionAddress) != pointers->ContextRecord->Rip ||
        pointers->ContextRecord->Rax != 0x6000) return EXCEPTION_CONTINUE_SEARCH;
    seh_filter_calls = seh_filter_calls + 1;
    return bmo_gs_test_mode == 0x424d4f08 ? EXCEPTION_EXECUTE_HANDLER : EXCEPTION_CONTINUE_SEARCH;
}

extern "C" __declspec(noinline) int bmo_gs_seh_client() {
    __try {
        if (bmo_test_gs_cpu_fault() != 0) return 0;
    } __except (fixture_filter(GetExceptionInformation())) {
        seh_except_calls = seh_except_calls + 1;
    }
    return seh_filter_calls == 1 &&
           seh_except_calls == (bmo_gs_test_mode == 0x424d4f08 ? 1u : 0u);
}

__declspec(noinline) static LONG fixture_outer_filter(const EXCEPTION_POINTERS* pointers) {
    const bool cleanup_case = bmo_gs_test_mode == 0x424d4f0b;
    if (seh_filter_calls != (cleanup_case ? 0u : 1u) || seh_except_calls || seh_cleanup_order ||
        pointers->ExceptionRecord->ExceptionCode !=
        EXCEPTION_ILLEGAL_INSTRUCTION || reinterpret_cast<Word>(pointers->ExceptionRecord->ExceptionAddress) !=
        pointers->ContextRecord->Rip || pointers->ContextRecord->Rax != 0x6000) return EXCEPTION_CONTINUE_SEARCH;
    seh_outer_filter_calls = seh_outer_filter_calls + 1;
    if (cleanup_case) seh_cleanup_order = 1;
    return EXCEPTION_EXECUTE_HANDLER;
}

extern "C" __declspec(noinline) int bmo_gs_seh_outer() {
    const bool cleanup_case = bmo_gs_test_mode == 0x424d4f0b;
    __try {
        if (cleanup_case) bmo_gs_seh_finally();
        else bmo_gs_seh_client();
    } __except (fixture_outer_filter(GetExceptionInformation())) {
        if (cleanup_case) seh_cleanup_order = seh_cleanup_order == 2 ? 3 : 0;
        seh_outer_except_calls = seh_outer_except_calls + 1;
    }
    return seh_filter_calls == (cleanup_case ? 0u : 1u) && seh_except_calls == 0 &&
           seh_cleanup_order == (cleanup_case ? 3u : 0u) &&
           seh_outer_filter_calls == 1 && seh_outer_except_calls == 1;
}

struct SehScope {
    Rva begin;
    Rva end;
    Rva filter;
    Rva target;
};

extern "C" EXCEPTION_DISPOSITION __C_specific_handler(EXCEPTION_RECORD* record, void* frame,
                                                       CONTEXT* cpu, DISPATCHER_CONTEXT* dispatcher) {
    const auto& dispatch = *dispatcher;
    const Word base = dispatch.ImageBase;
    const Word data = reinterpret_cast<Word>(dispatch.HandlerData);
    if (!record || !cpu || (record->ExceptionFlags != 0 && record->ExceptionFlags != EXCEPTION_UNWINDING) ||
        data < base || data - base > 0xffffffffu ||
        !readonly_range(static_cast<Rva>(data - base), sizeof(Rva) + sizeof(SehScope))) {
        return ExceptionContinueSearch;
    }
    const auto* count = reinterpret_cast<const Rva*>(data);
    if (*count != 1) return ExceptionContinueSearch;
    const auto& scope = *reinterpret_cast<const SehScope*>(count + 1);
    const auto& fn = *dispatch.FunctionEntry;
    const Word pc = dispatch.ControlPc - base;
    const auto* filter_entry = find_function(base + scope.filter);
    if (scope.begin < fn.BeginAddress || scope.end > fn.EndAddress || scope.begin >= scope.end ||
        pc < scope.begin || pc >= scope.end ||
        !filter_entry || scope.filter != filter_entry->begin) return ExceptionContinueSearch;

    if (record->ExceptionFlags == EXCEPTION_UNWINDING) {
        if (!scope.target) {
            using Termination = void (*)(BOOLEAN, void*);
            const auto termination = reinterpret_cast<Termination>(base + scope.filter);
            termination(TRUE, frame);
        }
        return ExceptionContinueSearch;
    }
    if (scope.target < fn.BeginAddress || scope.target >= fn.EndAddress) return ExceptionContinueSearch;
    using Filter = LONG (*)(EXCEPTION_POINTERS*, void*);
    const auto filter = reinterpret_cast<Filter>(base + scope.filter);
    EXCEPTION_POINTERS pointers{record, cpu};
    if (filter(&pointers, frame) == EXCEPTION_EXECUTE_HANDLER) bmo_gs_seh_target = base + scope.target;
    return ExceptionContinueSearch;
}

static bool unwind_frame(CpuContext& context, Word control_pc);

static bool visit_seh_frame(const CpuContext& stack, Word pc, Word rsp, Word expected_function,
                            bool cleanup = false) {
    const Word base = bmo_gs_image.base;
    const auto* entry = find_function(pc);
    if (!entry || base + entry->begin != expected_function ||
        !stack_range(stack, rsp, sizeof(Word)) || !readonly_range(entry->unwind, 4)) return false;
    const auto* info = reinterpret_cast<const unsigned char*>(base + entry->unwind);
    const unsigned int tail = 4 + ((info[2] + 1) & ~1u) * 2;
    const unsigned int required = cleanup ? 0x10 : 0x08;
    if ((info[0] & ~0x18u) != 1 || !(info[0] & required) || info[3] ||
        !readonly_range(entry->unwind, tail + 4) || pc - base - entry->begin < info[1]) return false;
    const auto* handler = reinterpret_cast<const Rva*>(info + tail);
    if (base + *handler != reinterpret_cast<Word>(&__C_specific_handler)) return false;
    DISPATCHER_CONTEXT dispatch = {
        pc, base, reinterpret_cast<RUNTIME_FUNCTION*>(const_cast<RuntimeFunction*>(entry)),
        rsp, cleanup ? bmo_gs_seh_target : 0, &bmo_gs_win_context,
        reinterpret_cast<PEXCEPTION_ROUTINE>(&__C_specific_handler),
        const_cast<Rva*>(handler + 1), nullptr, 0, 0
    };
    bmo_gs_exception_record.ExceptionFlags = cleanup ? EXCEPTION_UNWINDING : 0;
    __C_specific_handler(&bmo_gs_exception_record, reinterpret_cast<void*>(rsp),
                         &bmo_gs_win_context, &dispatch);
    bmo_gs_exception_record.ExceptionFlags = 0;
    return true;
}

static int dispatch_seh(CpuContext& caller) {
    bmo_gs_seh_target = 0;
    if (bmo_gs_test_mode == 0x424d4f0b) {
        const Word inner_pc = caller.pc - 1;
        const Word inner_rsp = caller.rsp;
        const auto* frame = find_function(inner_pc);
        const Word inner = reinterpret_cast<Word>(&bmo_gs_seh_finally);
        if (!frame || bmo_gs_image.base + frame->begin != inner || !unwind_frame(caller, inner_pc) ||
            !visit_seh_frame(caller, caller.pc - 1, caller.rsp, reinterpret_cast<Word>(&bmo_gs_seh_outer)) ||
            !bmo_gs_seh_target || !visit_seh_frame(caller, inner_pc, inner_rsp, inner, true) ||
            seh_cleanup_order != 2) return 0;
        return 2;
    }
    if (!visit_seh_frame(caller, caller.pc - 1, caller.rsp, reinterpret_cast<Word>(&bmo_gs_seh_client))) return 0;
    if (!bmo_gs_seh_target && bmo_gs_test_mode == 0x424d4f0a && seh_filter_calls == 1) {
        if (!unwind_frame(caller, caller.pc - 1) ||
            !visit_seh_frame(caller, caller.pc - 1, caller.rsp, reinterpret_cast<Word>(&bmo_gs_seh_outer))) return 0;
    }
    return bmo_gs_seh_target ? 2 : 0;
}

static bool pop_word(CpuContext& context, Word& value) {
    if (!stack_range(context, context.rsp, sizeof(Word))) return false;
    value = *reinterpret_cast<const Word*>(context.rsp);
    context.rsp += sizeof(Word);
    return true;
}

static constexpr int register_slot[16] = {-1, -1, -1, 0, -1, 1, 2, 3, -1, -1, -1, -1, 4, 5, 6, 7};

static bool frame_pointer_active(const unsigned char* info, unsigned int code_limit) {
    for (unsigned int slot = 0; slot < info[2]; ++slot) {
        const unsigned int code = info[5 + slot * 2];
        const unsigned int op = code & 15;
        if (code == 3) return info[4 + slot * 2] <= code_limit;
        if (op == 1 || op == 4 || op == 8) ++slot;
    }
    return false;
}

static bool restore_unwind_codes(CpuContext& context, const unsigned char* info, bool chained,
                                 Word fixed_rsp, bool& used_frame_pointer, unsigned int code_limit) {
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
        if (op != 0 && op != 2 && op != 3 && op != 4 && op != 8 && !(op == 1 && !operand)) return false;
        const bool has_operand = op == 1 || op == 4 || op == 8;
        const auto* encoded = info + 6 + slot * 2;
        if (has_operand && ++slot >= info[2]) return false;
        if (offset > code_limit) continue;
        if (op == 3 && !operand && info[3] && !adjusted && !used_frame_pointer) { // UWOP_SET_FPREG
            context.rsp = fixed_rsp;
            used_frame_pointer = true;
        } else if (op == 2 && !adjusted) { // UWOP_ALLOC_SMALL
            context.rsp += 8 * (operand + 1);
            adjusted = true;
        } else if (op == 1 && !adjusted && !operand) { // UWOP_ALLOC_LARGE, scaled form
            const unsigned int units = encoded[0] | (encoded[1] << 8);
            if (units <= 16) return false;
            context.rsp += 8 * units;
            adjusted = true;
        } else if (op == 0 && register_slot[operand] >= 0 && !(saved & (1u << operand))) {
            if (!pop_word(context, context.nonvolatile[register_slot[operand]])) return false;
            saved |= 1u << operand;
            adjusted = true;
        } else if ((op == 4 || op == 8) && !adjusted) { // UWOP_SAVE_NONVOL / UWOP_SAVE_XMM128
            const unsigned int units = encoded[0] | (encoded[1] << 8);
            const Word address = fixed_rsp + units * (op == 4 ? 8ull : 16ull);
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

enum class Epilogue { absent, invalid, restored };
static Epilogue unwind_epilogue(CpuContext& context, Word pc, const RuntimeFunction& function,
                                unsigned int frame_register);

static bool unwind_frame(CpuContext& context, Word control_pc) {
    const Word base = bmo_gs_image.base;
    const auto* function = find_function(control_pc);
    if (!function || !readonly_range(function->unwind, 4)) return false;
    const auto* initial = reinterpret_cast<const unsigned char*>(base + function->unwind);
    const unsigned int frame = initial[3];
    const unsigned int code_limit = static_cast<unsigned int>(control_pc - base - function->begin);
    const bool in_prologue = code_limit < initial[1];
    if ((initial[0] & 7) != 1 || (initial[0] >> 3) > 4) return false;
    if (!in_prologue) {
        const auto result = unwind_epilogue(context, control_pc, *function, frame & 15);
        if (result != Epilogue::absent) return result == Epilogue::restored;
    }
    if (in_prologue && (initial[0] >> 3) == 4) return false;
    const unsigned int initial_bytes = 4 + ((initial[2] + 1) & ~1u) * 2;
    if (!readonly_range(function->unwind, initial_bytes)) return false;
    const bool frame_active = frame && (!in_prologue || frame_pointer_active(initial, code_limit));
    Word fixed_rsp = context.rsp;
    bool used_frame_pointer = false;
    const int frame_slot = register_slot[frame & 15];
    if (frame && frame_slot < 0) return false;
    if (frame_active) {
        const Word displacement = frame & 0xf0;
        if (context.nonvolatile[frame_slot] < displacement) return false;
        fixed_rsp = context.nonvolatile[frame_slot] - displacement;
        if (fixed_rsp < context.rsp || !stack_range(context, fixed_rsp, sizeof(Word))) return false;
    }
    for (unsigned int depth = 0; depth < 8; ++depth) {
        if (!function || !readonly_range(function->unwind, 4)) return false;
        const auto* info = reinterpret_cast<const unsigned char*>(base + function->unwind);
        const unsigned int flags = info[0] >> 3;
        const bool chained = flags == 4;
        const unsigned int tail = 4 + ((info[2] + 1) & ~1u) * 2;
        if ((info[0] & 7) != 1 || flags > 4 || info[3] != frame ||
            !readonly_range(function->unwind, tail + (chained ? sizeof(RuntimeFunction) : 0)) ||
            !restore_unwind_codes(context, info, chained, fixed_rsp, used_frame_pointer,
                                  depth ? info[1] : code_limit)) return false;
        if (!chained) {
            return used_frame_pointer == frame_active && pop_word(context, context.pc) &&
                   context.pc && find_function(context.pc - 1);
        }

        const auto* parent = reinterpret_cast<const RuntimeFunction*>(info + tail);
        if (parent->begin >= function->begin) return false;
        function = find_function(base + parent->begin);
        if (!function || function->begin != parent->begin ||
            function->end != parent->end || function->unwind != parent->unwind) return false;
    }
    return false;
}

static long long signed_displacement(const unsigned char* bytes, unsigned int size) {
    Word value = 0;
    for (unsigned int index = 0; index < size; ++index) {
        value |= static_cast<Word>(bytes[index]) << (index * 8);
    }
    const Word limit = 1ull << (size * 8);
    return static_cast<long long>(value) -
           (value & (limit >> 1) ? static_cast<long long>(limit) : 0);
}

// Recognize a suffix before reading saved registers or publishing changes.
static Epilogue unwind_epilogue(CpuContext& context, Word pc, const RuntimeFunction& function,
                                unsigned int frame_register) {
    const Word base = bmo_gs_image.base;
    const Word end = base + function.end;
    const auto* first = reinterpret_cast<const unsigned char*>(pc);
    Word rsp = context.rsp;
    bool valid_adjustment = true;
    if (end - pc >= 3 && (first[0] == 0x48 || first[0] == 0x49)) {
        const unsigned int modrm = first[2];
        unsigned int size = 0;
        Word stack_base = context.rsp;
        if (first[0] == 0x48 && modrm == 0xc4 && (first[1] == 0x83 || first[1] == 0x81)) {
            size = first[1] == 0x83 ? 1 : 4;
        } else if (first[1] == 0x8d && (modrm & 0x38) == 0x20) {
            const unsigned int reg = (modrm & 7) + (first[0] == 0x49 ? 8 : 0);
            // This subset uses a ModRM base and disp8/disp32 without a SIB byte.
            if (reg != frame_register || register_slot[reg] < 0 || (modrm & 7) == 4) return Epilogue::absent;
            if ((modrm >> 6) == 1) size = 1;
            if ((modrm >> 6) == 2) size = 4;
            stack_base = context.nonvolatile[register_slot[reg]];
        }
        if (!size || end - pc < 3 + size) return Epilogue::absent;
        rsp = stack_base + signed_displacement(first + 3, size);
        valid_adjustment = stack_range(context, stack_base, sizeof(Word)) && rsp >= context.rsp;
        pc += 3 + size;
    }
    unsigned int seen = 0;
    unsigned int slots[8];
    unsigned int count = 0;
    bool terminal = false;
    while (pc < end) {
        unsigned int opcode = *reinterpret_cast<const unsigned char*>(pc++);
        unsigned int extended = 0;
        if (opcode == 0x41 && pc < end) {
            extended = 8;
            opcode = *reinterpret_cast<const unsigned char*>(pc++);
        }
        if (opcode == 0xc3 && !extended) {
            terminal = true;
            break;
        }
        if (opcode == 0xff && !extended && end - pc >= 5) {
            const auto* branch = reinterpret_cast<const unsigned char*>(pc);
            if (branch[0] != 0x25) return Epilogue::absent;
            const Word pointer = pc + 5 + signed_displacement(branch + 1, 4);
            if (pointer < base || pointer - base > 0xffffffffu || (pointer & 7) ||
                !readonly_range(static_cast<Rva>(pointer - base), sizeof(Word))) return Epilogue::absent;
            const Word target = *reinterpret_cast<const Word*>(pointer);
            const auto* destination = find_function(target);
            if (!destination || destination->begin == function.begin ||
                target != base + destination->begin) return Epilogue::absent;
            // A tail transfer leaves the original caller return slot in place.
            terminal = true;
            break;
        }
        if (opcode < 0x58 || opcode > 0x5f) return Epilogue::absent;
        const unsigned int reg = opcode - 0x58 + extended;
        const int slot = register_slot[reg];
        if (slot < 0 || (seen & (1u << reg)) || count == 8) return Epilogue::absent;
        slots[count++] = static_cast<unsigned int>(slot);
        seen |= 1u << reg;
    }
    if (!terminal) return Epilogue::absent;
    if (!valid_adjustment || !stack_range(context, rsp, sizeof(Word) * (count + 1))) return Epilogue::invalid;
    const auto* saved = reinterpret_cast<const Word*>(rsp);
    const Word caller = saved[count];
    if (!caller || !find_function(caller - 1)) return Epilogue::invalid;
    for (unsigned int index = 0; index < count; ++index) context.nonvolatile[slots[index]] = saved[index];
    context.rsp = rsp + sizeof(Word) * (count + 1);
    context.pc = caller;
    return Epilogue::restored;
}

extern "C" int bmo_gs_cpu_dispatch(CpuContext* context, const TrapRegisters* trap) {
    capture_win_context(*context, *trap);
    const auto& win = bmo_gs_win_context;
    if (win.Rax != 0x6000 || win.Rcx != 0x6001 || win.Rdx != 0x6002 ||
        win.R8 != 0x6008 || win.R9 != 0x6009 || win.R10 != 0x6010 || win.R11 != 0x6011 ||
        !(win.EFlags & 1) || win.SegCs != 0x8b || win.SegSs != 0x83 ||
        win.Xmm0.Low != ~0ull || static_cast<Word>(win.Xmm0.High) != ~0ull ||
        win.Xmm6.Low != context->xmm[0][0] ||
        static_cast<Word>(win.Xmm6.High) != context->xmm[0][1]) return 0;
    // Undo the faulting leaf's call, then inspect its live protected parent.
    if (!pop_word(*context, context->pc) || !context->pc) return 0;
    if (bmo_gs_test_mode >= 0x424d4f08 && bmo_gs_test_mode <= 0x424d4f0b) return dispatch_seh(*context);
    if (dispatch_gs(context->pc - 1, context->rsp, &bmo_gs_exception_record,
                    &bmo_gs_win_context) != 1) return 0;
    if (!unwind_frame(*context, context->pc - 1) || context->pc != bmo_gs_expected.wrapper_pc ||
        context->rsp != bmo_gs_expected.wrapper_rsp || context->nonvolatile[0] != 0x12340003 ||
        context->nonvolatile[1] != bmo_gs_expected.wrapper_rbp ||
        context->rsp + 64 != bmo_gs_expected.fixed_rsp ||
        context->nonvolatile[2] != 0x12340006 || context->nonvolatile[3] != 0x12340007 ||
        context->nonvolatile[4] != 0x1234000c || context->xmm[0][0] != ~0ull ||
        context->xmm[0][1] != ~0ull) return 0;
    return unwind_frame(*context, context->pc - 1) && context->pc == bmo_gs_expected.caller_pc &&
           context->rsp == bmo_gs_expected.caller_rsp &&
           context->nonvolatile[0] == bmo_gs_expected.caller_rbx &&
           context->nonvolatile[1] == bmo_gs_expected.caller_rbp &&
           context->nonvolatile[2] == bmo_gs_expected.caller_rsi &&
           context->nonvolatile[3] == bmo_gs_expected.caller_rdi &&
           context->nonvolatile[4] == bmo_gs_expected.caller_r12 &&
           context->xmm[0][0] == bmo_gs_expected.caller_xmm6[0] &&
           context->xmm[0][1] == bmo_gs_expected.caller_xmm6[1];
}

static bool matches_prologue_caller(const CpuContext& context) {
    return context.pc == bmo_gs_prologue_expected.caller_pc &&
           context.rsp == bmo_gs_prologue_expected.caller_rsp &&
           context.nonvolatile[1] == bmo_gs_prologue_expected.caller_rbp &&
           context.nonvolatile[2] == bmo_gs_prologue_expected.caller_rsi &&
           context.nonvolatile[3] == bmo_gs_prologue_expected.caller_rdi;
}

extern "C" int bmo_gs_cpu_prologue(CpuContext* context, const TrapRegisters* trap) {
    capture_win_context(*context, *trap);
    const auto* function = find_function(context->pc);
    if (!function || !readonly_range(function->unwind, 4)) return 0;
    const auto* info = reinterpret_cast<const unsigned char*>(bmo_gs_image.base + function->unwind);
    const Word relative_pc = context->pc - bmo_gs_image.base - function->begin;
    if (relative_pc >= info[1] || (info[3] & 15) != 5 ||
        !readonly_range(function->unwind, 4 + ((info[2] + 1) & ~1u) * 2) ||
        frame_pointer_active(info, static_cast<unsigned int>(relative_pc)) ||
        context->nonvolatile[2] != 0x43210006 ||
        context->nonvolatile[3] != 0x43210007) return 0;
    // After three of the epilogue's four pops, the saved RSI and RIP
    // are still on the live stack. RDI is already restored.
    const Word captured_rsp = context->rsp;
    const Word captured_rbp = context->nonvolatile[1];
    const Word captured_rsi = context->nonvolatile[2];
    const Word captured_rdi = context->nonvolatile[3];
    const Word epilogues[] = {reinterpret_cast<Word>(&bmo_test_gs_epilogue_add),
                              reinterpret_cast<Word>(&bmo_test_gs_epilogue_lea),
                              reinterpret_cast<Word>(&bmo_test_gs_epilogue_jump)};
    for (const Word epilogue : epilogues) {
        // Project the live frame to the state after sub rsp,40 / lea rbp,[rsp+32].
        context->rsp = captured_rsp - 40;
        context->nonvolatile[1] = captured_rsp - 8;
        context->nonvolatile[2] = captured_rsi;
        context->nonvolatile[3] = captured_rdi;
        if (!unwind_frame(*context, epilogue) || !matches_prologue_caller(*context)) return 0;
    }
    context->rsp = context->stack_begin + 4096 - sizeof(Word);
    const Word outside = context->rsp;
    const Word prior_pc = context->pc;
    const Word prior_rsi = context->nonvolatile[2];
    if (unwind_frame(*context, epilogues[0]) || context->rsp != outside ||
        context->pc != prior_pc || context->nonvolatile[2] != prior_rsi) return 0;
    const Word malformed = reinterpret_cast<Word>(&bmo_test_gs_epilogue_invalid);
    if (unwind_epilogue(*context, malformed, *function, 5) != Epilogue::absent ||
        context->rsp != outside || context->pc != prior_pc || context->nonvolatile[2] != prior_rsi) return 0;
    context->rsp = captured_rsp;
    context->rsp += 24;
    context->nonvolatile[3] = bmo_gs_prologue_expected.caller_rdi;
    if (!unwind_frame(*context, reinterpret_cast<Word>(&bmo_test_gs_epilogue_suffix)) ||
        !matches_prologue_caller(*context)) return 0;
    context->pc = bmo_gs_image.base + function->begin + relative_pc;
    context->rsp = captured_rsp;
    context->nonvolatile[1] = captured_rbp;
    context->nonvolatile[2] = captured_rsi;
    context->nonvolatile[3] = captured_rdi;
    return unwind_frame(*context, context->pc) && matches_prologue_caller(*context);
}
