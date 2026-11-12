/* Deliberately closed grammar, independent of the metal64 program model. */
#include "stop.h"
#include "../frontend/internal.h"
#include <stdio.h>
#include <string.h>

static const char context_hex[] =
    "FA 48 89 E6 31 C0 48 39 EF 75 24\n"
    "48 B9 4D 45 54 41 4C 36 34 21 48 39 0F 75 15\n"
    "83 7F 78 01 75 0F\n"
    "48 8D A7 00 40 01 00 68 42 4D 4F 32 5A FF C0\n"
    "F4 EB FD\n";

static const char fault_hex[] =
    /* Check the bridge context before any write. */
    "FA 48 89 E6 31 C0 48 39 EF 75 7C 48 B9 4D 45 54 41 4C 36 34 21 48 39 0F 75 6D 83 7F 78 01 75 67\n"
    /* Switch stack, address the IDT and resolve the handler. */
    "48 8D A7 00 40 01 00 4C 8D 85 00 40 01 00 48 8D 15 49 00 00 00\n"
    /* Write the #UD gate using the current code selector. */
    "66 41 89 50 60 8C C8 66 41 89 40 62 66 41 C7 40 64 00 8E 48 C1 EA 10 66 41 89 50 66 48 C1 EA 10 41 89 50 68 41 C7 40 6C 00 00 00 00\n"
    /* Install the bounded IDTR. */
    "66 41 C7 80 00 01 00 00 6F 00 4D 89 80 02 01 00 00 41 0F 01 98 00 01 00 00\n"
    /* Trigger #UD. Skip the handler on fallthrough. */
    "0F 0B EB 09\n"
    /* Capture the saved RIP and tag vector 6. */
    "48 8B 14 24 B8 06 00 00 00\n"
    /* Terminal for both outcomes. */
    "F4 EB FD\n";

static const char memory_hex[] =
    /* Validate handoff and clear result registers. */
    "FA 45 31 DB 45 31 E4 48 39 EF 0F 85 C6 00 00 00 48 B9 4D 45 54 41 4C 36 34 21 48 39 0F 0F 85 B3 00 00 00 83 7F 78 01 0F 85 A9 00 00 00\n"
    /* Bound map size, stride and descriptor count. */
    "4C 8B 4D 60 49 83 F9 28 0F 82 9B 00 00 00 49 81 F9 00 01 00 00 0F 87 8E 00 00 00 4C 8B 55 50 4D 39 CA 0F 82 81 00 00 00 49 81 FA 00 00 01 00 77 78 4C 89 D0 31 D2 49 F7 F1 48 85 D2 75 6B 4C 8D 85 00 10 00 00\n"
    /* Find the first conventional frame outside the boot reservations. */
    "41 83 38 07 75 53 49 83 78 18 00 74 4C 4D 8B 58 08 41 F7 C3 FF 0F 00 00 75 3F 49 81 FB 00 00 10 00 72 36 49 81 FB 00 F0 FF 0F 77 2D 4C 3B 5D 08 74 27 49 39 EB 72 0C 48 8D 85 00 00 02 00 49 39 C3 72 16\n"
    /* Write a marker and check its readback. */
    "48 BA 42 46 52 41 4D 45 30 21 49 89 13 49 39 13 41 0F 94 C4 EB 0B\n"
    /* Advance within the bounded descriptor array. */
    "4D 01 C8 4D 29 CA 75 9F 45 31 DB\n"
    /* Stop. */
    "F4 EB FD\n";

static const char frame_cycle_hex[] =
    /* Guard the handoff and clear results. */
    "FA 45 31 DB 45 31 E4 45 31 ED 45 31 F6 48 39 EF 0F 85 93 01 00 00 48 B9 "
    "4D 45 54 41 4C 36 34 21 48 39 0F 0F 85 80 01 00 00 83 7F 78 01 0F 85 76 "
    "01 00 00\n"
    /* Validate map geometry. */
    "4C 8B 4D 60 49 83 F9 28 0F 82 68 01 00 00 49 81 F9 00 01 00 00 0F 87 5B "
    "01 00 00 4C 8B 55 50 4D 39 CA 0F 82 4E 01 00 00 49 81 FA 00 00 01 00 0F "
    "87 41 01 00 00 4C 89 D0 31 D2 49 F7 F1 48 85 D2 0F 85 30 01 00 00 4C 8D "
    "85 00 10 00 00\n"
    /* Select a conventional frame. */
    "41 83 38 07 0F 85 10 01 00 00 49 83 78 18 00 0F 84 05 01 00 00 4D 8B 58 "
    "08 41 F7 C3 FF 0F 00 00 0F 85 F4 00 00 00 49 81 FB 00 00 10 00 0F 82 E7 "
    "00 00 00 49 81 FB 00 F0 FF 0F 0F 87 DA 00 00 00 4C 3B 5D 08 0F 84 D0 00 "
    "00 00 49 39 EB 72 10 48 8D 85 00 00 02 00 49 39 C3 0F 82 BB 00 00 00\n"
    /* Exercise ownership, exhaustion, release and reuse. */
    "BB 01 00 00 00 E8 C3 00 00 00 0F 83 BA 00 00 00 41 39 DD 0F 85 B1 00 00 "
    "00 41 83 CE 01 FC 4C 89 DF 48 B8 42 46 52 41 4D 45 30 21 B9 00 02 00 00 "
    "F3 48 AB 48 89 EF BB 02 00 00 00 E8 8D 00 00 00 0F 82 84 00 00 00 41 83 "
    "FD 01 75 7E 41 83 CE 02 E8 86 00 00 00 72 73 41 83 FD 01 75 6D 48 B8 42 "
    "46 52 41 4D 45 30 21 49 39 03 75 5E 49 39 83 F8 0F 00 00 75 55 41 83 CE "
    "04 BB 01 00 00 00 E8 58 00 00 00 73 45 45 85 ED 75 40 41 83 CE 08 E8 48 "
    "00 00 00 72 35 45 85 ED 75 30 41 83 CE 10 BB 02 00 00 00 E8 25 00 00 00 "
    "73 20 41 39 DD 75 1B 41 83 CE 20 41 BC 01 00 00 00 EB 0F\n"
    /* Advance to the next descriptor. */
    "4D 01 C8 4D 29 CA 0F 85 DA FE FF FF 45 31 DB\n"
    /* Halt with the observed state. */
    "F4 EB FD\n"
    /* Allocate to a nonzero owner. */
    "85 DB 74 28 45 85 ED 75 23 41 89 DD F9 C3\n"
    /* Scrub the frame before returning it to the pool. */
    "85 DB 74 1A 41 39 DD 75 15 31 C0 4C 89 DF B9 00 02 00 00 F3 48 AB 48 89 "
    "EF 45 31 ED F9 C3\n"
    /* Reject without changing ownership. */
    "F8 C3\n";

int casm_stop(const unsigned char *source, size_t length, const char *hex, const char *ir, KernelProfile profile) {
    Parser p = {0};
    size_t i;
    unsigned line;
    unsigned operation_line = 0;
    FILE *out;
    int ok;
    p.source = source; p.length = length; p.line = p.token_line = 1;
    for (i = 0; i < length; i++)
        if (!source[i] || source[i] > 127)
            return casm_reject(&p, CASM_RULE_SOURCE_ASCII, "Source must be ASCII without NUL bytes.");
    if (!casm_next(&p) || !casm_word(&p, "void") || !casm_word(&p, "kernel_main") ||
        !casm_expect(&p, '(') || !casm_word(&p, "void") || !casm_expect(&p, ')') ||
        !casm_expect(&p, '{')) return 0;
    line = p.token_line;
    if (profile != KERNEL_STOP) {
        operation_line = line;
        const char *operation = profile == KERNEL_CPU ? "cpu_identify" :
                                profile == KERNEL_FRAME_CYCLE ? "boot_frame_cycle" :
                                profile == KERNEL_FAULT ? "boot_fault" : profile == KERNEL_MEMORY ? "boot_memory" : "boot_stack";
        if (!casm_word(&p, operation) || !casm_expect(&p, '(') ||
            !casm_expect(&p, ')') || !casm_expect(&p, ';')) return 0;
        line = p.token_line;
    }
    if (!casm_word(&p, "cpu_halt") || !casm_expect(&p, '(') || !casm_expect(&p, ')') ||
        !casm_expect(&p, ';') || !casm_expect(&p, '}') || !casm_expect(&p, TOK_EOF)) return 0;
    out = fopen(hex, "wb");
    if (!out) return 0;
    /* CLI; HLT; JMP rel8 -3 to HLT. No return or inherited service call. */
    /* CPUID leaf zero returns the vendor and highest basic leaf in registers. */
    ok = fputs(profile == KERNEL_FRAME_CYCLE ? frame_cycle_hex : profile == KERNEL_MEMORY ? memory_hex :
               profile == KERNEL_FAULT ? fault_hex : profile == KERNEL_CONTEXT ? context_hex :
               profile == KERNEL_CPU ? "FA 31 C0 0F A2 F4 EB FD\n" : "FA F4 EB FD\n", out) >= 0;
    if (fclose(out)) ok = 0;
    if (!ok) return 0;
    out = fopen(ir, "wb");
    if (!out) return 0;
    if (profile == KERNEL_FRAME_CYCLE) {
        ok = fprintf(out, "{\n\"Schema\":9,\"Target\":\"x86_64\",\"ABI\":\"ring0-frame-cycle\","
            "\"Profile\":\"ring0-frame-cycle-0.1\",\"Entry\":\"kernel_main\",\"RequiredCPL\":0,"
            "\"Pool\":{\"Line\":%u,\"Capacity\":1,\"PageBytes\":4096,\"LimitExclusive\":268435456,\"ScrubOnRelease\":true},"
            "\"Terminal\":{\"Line\":%u,\"Offset\":425},\"BodyBytes\":474\n}\n", operation_line, line) >= 0;
    } else if (profile == KERNEL_MEMORY) {
        ok = fprintf(out, "{\n\"Schema\":8,\"Target\":\"x86_64\",\"ABI\":\"ring0-memory\","
            "\"Profile\":\"ring0-memory-0.1\",\"Entry\":\"kernel_main\",\"RequiredCPL\":0,"
            "\"Frame\":{\"Line\":%u,\"MapOffset\":4096,\"PageBytes\":4096,\"LimitExclusive\":268435456},"
            "\"Terminal\":{\"Line\":%u,\"Offset\":214},\"BodyBytes\":217\n}\n", operation_line, line) >= 0;
    } else if (profile == KERNEL_FAULT) {
        ok = fprintf(out, "{\n\"Schema\":7,\"Target\":\"x86_64\",\"ABI\":\"ring0-fault\","
            "\"Profile\":\"ring0-fault-0.1\",\"Entry\":\"kernel_main\",\"RequiredCPL\":0,"
            "\"Fault\":{\"Line\":%u,\"Vector\":6,\"Trigger\":122,\"Handler\":126,\"IdtOffset\":81920,\"IdtLimit\":111},"
            "\"Terminal\":{\"Line\":%u,\"Offset\":135},\"BodyBytes\":138\n}\n", operation_line, line) >= 0;
    } else if (profile == KERNEL_CONTEXT) {
        ok = fprintf(out, "{\n\"Schema\":5,\"Target\":\"x86_64\",\"ABI\":\"ring0-context\","
            "\"Profile\":\"ring0-context-0.1\",\"Entry\":\"kernel_main\",\"RequiredCPL\":0,"
            "\"Stack\":{\"Line\":%u,\"Low\":77824,\"Top\":81920},"
            "\"Terminal\":{\"Line\":%u,\"Offset\":47},\"BodyBytes\":50\n}\n", operation_line, line) >= 0;
    } else if (profile == KERNEL_CPU) {
        ok = fprintf(out, "{\n\"Schema\":4,\"Target\":\"x86_64\",\"ABI\":\"ring0-cpu\","
            "\"Profile\":\"ring0-cpu-0.1\",\"Entry\":\"kernel_main\",\"RequiredCPL\":0,"
            "\"Identification\":{\"Line\":%u,\"Offset\":1,\"Leaf\":0},"
            "\"Terminal\":{\"Line\":%u,\"Offset\":5},\"BodyBytes\":8\n}\n", operation_line, line) >= 0;
    } else {
        ok = fprintf(out, "{\n\"Schema\":3,\"Target\":\"x86_64\",\"ABI\":\"ring0-stop\","
        "\"Profile\":\"ring0-stop-0.1\",\"Entry\":\"kernel_main\",\"RequiredCPL\":0,"
        "\"Effects\":[\"mask-interrupts\",\"halt\"],"
        "\"Terminal\":{\"Line\":%u,\"Offset\":0},\"BodyBytes\":4\n}\n", line) >= 0;
    }
    if (fclose(out)) ok = 0;
    if (ok) puts(profile == KERNEL_FRAME_CYCLE ? "GREEN [RING0-FRAME-CYCLE] 474 body bytes; unverified HEX and IR written."
             : profile == KERNEL_MEMORY ? "GREEN [RING0-MEMORY] 217 body bytes; unverified HEX and IR written."
             : profile == KERNEL_FAULT ? "GREEN [RING0-FAULT] 138 body bytes; unverified HEX and IR written."
             : profile == KERNEL_CONTEXT ? "GREEN [RING0-CONTEXT] 50 body bytes; unverified HEX and IR written."
             : profile == KERNEL_CPU ? "GREEN [RING0-CPU] 8 body bytes; unverified HEX and IR written."
             : "GREEN [RING0-STOP] 4 body bytes; unverified HEX and IR written.");
    return ok;
}
