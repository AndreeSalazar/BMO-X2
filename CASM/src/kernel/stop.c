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
        if (!casm_word(&p, profile == KERNEL_CPU ? "cpu_identify" : "boot_stack") || !casm_expect(&p, '(') ||
            !casm_expect(&p, ')') || !casm_expect(&p, ';')) return 0;
        line = p.token_line;
    }
    if (!casm_word(&p, "cpu_halt") || !casm_expect(&p, '(') || !casm_expect(&p, ')') ||
        !casm_expect(&p, ';') || !casm_expect(&p, '}') || !casm_expect(&p, TOK_EOF)) return 0;
    out = fopen(hex, "wb");
    if (!out) return 0;
    /* CLI; HLT; JMP rel8 -3 to HLT. No return or inherited service call. */
    /* CPUID leaf zero returns the vendor and highest basic leaf in registers. */
    ok = fputs(profile == KERNEL_CONTEXT ? context_hex :
               profile == KERNEL_CPU ? "FA 31 C0 0F A2 F4 EB FD\n" : "FA F4 EB FD\n", out) >= 0;
    if (fclose(out)) ok = 0;
    if (!ok) return 0;
    out = fopen(ir, "wb");
    if (!out) return 0;
    if (profile == KERNEL_CONTEXT) {
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
    if (ok) puts(profile == KERNEL_CONTEXT ? "GREEN [RING0-CONTEXT] 50 body bytes; unverified HEX and IR written."
             : profile == KERNEL_CPU ? "GREEN [RING0-CPU] 8 body bytes; unverified HEX and IR written."
             : "GREEN [RING0-STOP] 4 body bytes; unverified HEX and IR written.");
    return ok;
}
