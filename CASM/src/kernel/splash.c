#include "splash.h"
#include "splash_bytes.h"
#include "../frontend/internal.h"
#include <stdint.h>
#include <stdio.h>

int casm_splash(const unsigned char *source, size_t length, const char *hex, const char *ir, int hd) {
    Parser p = {0};
    uint64_t mask[64][2] = {{0}};
    const unsigned cells = hd ? 64 : 32;
    const unsigned row_bytes = cells / 8;
    const unsigned char *renderer = hd ? splash_hd_renderer : splash_renderer;
    const size_t renderer_bytes = hd ? sizeof splash_hd_renderer : sizeof splash_renderer;
    const size_t body_bytes = renderer_bytes + cells * 2 * row_bytes;
    const char *profile = hd ? "ring0-splash-hd-0.1" : "ring0-splash-0.1";
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
    for (unsigned row = 0; row < cells; row++) {
        if (p.token != TOK_STRING || p.text_length != cells + 1)
            return casm_reject(&p, CASM_RULE_SYNTAX, "Logo row width does not match the profile.");
        for (unsigned col = 0; col < cells; col++) {
            unsigned char cell = p.text[col];
            if (cell == '#' || cell == 'o') mask[row][cell == 'o'] |= UINT64_C(1) << col;
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
    for (size_t i = 0; i < renderer_bytes; i++)
        if (fprintf(out, "%02X%c", (unsigned)renderer[i], i % 16 == 15 ? '\n' : ' ') < 0) ok = 0;
    if (fputc('\n', out) == EOF) ok = 0;
    for (unsigned row = 0; row < cells; row++)
        for (unsigned plane = 0; plane < 2; plane++)
            for (unsigned byte = 0; byte < row_bytes; byte++)
                if (fprintf(out, "%02X%c", (unsigned)((mask[row][plane] >> (byte * 8)) & 255),
                            plane == 1 && byte + 1 == row_bytes ? '\n' : ' ') < 0) ok = 0;
    if (fclose(out)) ok = 0;
    if (!ok) return 0;
    out = fopen(ir, "wb");
    if (!out) return 0;
    ok = fprintf(out, "{\"Schema\":6,\"Target\":\"x86_64\",\"ABI\":\"ring0-splash\","
        "\"Profile\":\"%s\",\"Entry\":\"kernel_main\",\"RequiredCPL\":0,"
        "\"Logo\":{\"Line\":%u,\"Offset\":%zu,\"Width\":%u,\"Height\":%u,\"Scale\":%u,\"Frames\":3},"
        "\"Terminal\":{\"Line\":%u,\"Offset\":%u},\"BodyBytes\":%zu}\n",
        profile, start, renderer_bytes, cells, cells, 256 / cells, terminal, hd ? 216u : 213u, body_bytes) >= 0;
    if (fclose(out)) ok = 0;
    if (ok) printf("GREEN [RING0-SPLASH] %zu body bytes; unverified HEX and IR written.\n", body_bytes);
    return ok;
}
