#include "splash.h"
#include "splash_bytes.h"
#include "../frontend/internal.h"
#include <stdint.h>
#include <stdio.h>

int casm_splash(const unsigned char *source, size_t length, const char *hex, const char *ir) {
    Parser p = {0};
    uint32_t mask[32][2] = {{0}};
    unsigned start, terminal;
    int ok = 1;
    FILE *out;
    p.source = source; p.length = length; p.line = p.token_line = 1;
    for (size_t i = 0; i < length; i++)
        if (!source[i] || source[i] > 127)
            return casm_reject(&p, CASM_RULE_SOURCE_ASCII, "Splash source must be ASCII.");
    if (!casm_next(&p) || !casm_word(&p, "void") || !casm_word(&p, "kernel_main") ||
        !casm_expect(&p, '(') || !casm_word(&p, "void") || !casm_expect(&p, ')') ||
        !casm_expect(&p, '{')) return 0;
    start = p.token_line;
    if (!casm_word(&p, "boot_cat") || !casm_expect(&p, '(')) return 0;
    for (unsigned row = 0; row < 32; row++) {
        if (p.token != TOK_STRING || p.text_length != 33)
            return casm_reject(&p, CASM_RULE_SYNTAX, "Each logo row must have exactly 32 cells.");
        for (unsigned col = 0; col < 32; col++) {
            unsigned char cell = p.text[col];
            if (cell == '#' || cell == 'o') mask[row][cell == 'o'] |= UINT32_C(1) << col;
            else if (cell != '.')
                return casm_reject(&p, CASM_RULE_SYNTAX, "Logo cells must be '.', '#' or 'o'.");
        }
        if (!casm_next(&p)) return 0;
    }
    if (!casm_expect(&p, ')') || !casm_expect(&p, ';')) return 0;
    terminal = p.token_line;
    if (!casm_word(&p, "cpu_halt") || !casm_expect(&p, '(') || !casm_expect(&p, ')') ||
        !casm_expect(&p, ';') || !casm_expect(&p, '}') || !casm_expect(&p, TOK_EOF)) return 0;
    out = fopen(hex, "wb");
    if (!out) return 0;
    for (size_t i = 0; i < sizeof splash_renderer; i++)
        if (fprintf(out, "%02X%c", (unsigned)splash_renderer[i], i % 16 == 15 ? '\n' : ' ') < 0) ok = 0;
    if (fputc('\n', out) == EOF) ok = 0;
    for (unsigned row = 0; row < 32; row++)
        for (unsigned plane = 0; plane < 2; plane++)
            for (unsigned byte = 0; byte < 4; byte++)
                if (fprintf(out, "%02X%c", (unsigned)((mask[row][plane] >> (byte * 8)) & 255),
                            plane == 1 && byte == 3 ? '\n' : ' ') < 0) ok = 0;
    if (fclose(out)) ok = 0;
    if (!ok) return 0;
    out = fopen(ir, "wb");
    if (!out) return 0;
    ok = fprintf(out, "{\"Schema\":6,\"Target\":\"x86_64\",\"ABI\":\"ring0-splash\","
        "\"Profile\":\"ring0-splash-0.1\",\"Entry\":\"kernel_main\",\"RequiredCPL\":0,"
        "\"Logo\":{\"Line\":%u,\"Offset\":228,\"Width\":32,\"Height\":32,\"Scale\":8,\"Frames\":3},"
        "\"Terminal\":{\"Line\":%u,\"Offset\":213},\"BodyBytes\":484}\n", start, terminal) >= 0;
    if (fclose(out)) ok = 0;
    if (ok) puts("GREEN [RING0-SPLASH] 484 body bytes; unverified HEX and IR written.");
    return ok;
}
