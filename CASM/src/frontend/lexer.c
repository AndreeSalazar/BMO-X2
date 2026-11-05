#include "internal.h"
#include <stdio.h>
#include <string.h>

static int letter(unsigned char c) {
    return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || c == '_';
}
int casm_digit(unsigned char c) { return c >= '0' && c <= '9'; }
static int append(Parser *p, unsigned char c) {
    if (p->text_length >= CASM_TEXT_MAX - 1) return casm_reject(p, CASM_RULE_STRING_SIZE, "String exceeds the bounded literal capacity.");
    p->text[p->text_length++] = c;
    return 1;
}
int casm_next(Parser *p) {
    unsigned char c;
    size_t start, count;
    if (p->failed) return 0;
    for (;;) {
        if (p->pos >= p->length) { p->token_line = p->line; p->token = TOK_EOF; return 1; }
        c = p->source[p->pos];
        p->token_line = p->line;
        if (c == ' ' || c == '\t' || c == '\r' || c == '\n') {
            if (c == '\n') p->line++;
            p->pos++; continue;
        }
        if (c == '/' && p->pos + 1 < p->length && p->source[p->pos + 1] == '/') {
            p->pos += 2;
            while (p->pos < p->length && p->source[p->pos] != '\n') p->pos++;
            continue;
        }
        if (c == '/' && p->pos + 1 < p->length && p->source[p->pos + 1] == '*') {
            p->pos += 2;
            while (p->pos + 1 < p->length && !(p->source[p->pos] == '*' && p->source[p->pos + 1] == '/')) {
                if (p->source[p->pos++] == '\n') p->line++;
            }
            if (p->pos + 1 >= p->length) return casm_reject(p, CASM_RULE_COMMENT_END, "Unterminated block comment.");
            p->pos += 2; continue;
        }
        break;
    }
    c = p->source[p->pos++];
    if (letter(c)) {
        start = p->pos - 1;
        while (p->pos < p->length && (letter(p->source[p->pos]) || casm_digit(p->source[p->pos]))) p->pos++;
        count = p->pos - start;
        if (count > CASM_NAME_MAX) return casm_reject(p, CASM_RULE_NAME_SIZE, "Identifier exceeds 63 characters.");
        memcpy(p->name, p->source + start, count); p->name[count] = 0;
        p->token = TOK_NAME; return 1;
    }
    if (casm_digit(c)) {
        /* The literal text is kept as written; integer_literal() reads it exactly. */
        start = p->pos - 1;
        while (p->pos < p->length && (casm_digit(p->source[p->pos]) || letter(p->source[p->pos]))) p->pos++;
        count = p->pos - start;
        if (count >= CASM_TEXT_MAX) return casm_reject(p, CASM_RULE_INT_LITERAL, "Integer literal is too long.");
        memcpy(p->text, p->source + start, count); p->text[count] = 0; p->text_length = count;
        p->token = TOK_NUMBER; return 1;
    }
    if (c == '"') {
        p->text_length = 0;
        while (p->pos < p->length) {
            c = p->source[p->pos++];
            if (c == '"') {
                if (!append(p, 0)) return 0;
                p->token = TOK_STRING; return 1;
            }
            if (c == '\\') {
                if (p->pos >= p->length) return casm_reject(p, CASM_RULE_STRING_END, "Unterminated escape.");
                c = p->source[p->pos++];
                if (c == 'n') c = '\n';
                else if (c == 'r') c = '\r';
                else if (c != '\\' && c != '"') return casm_reject(p, CASM_RULE_STRING_ESCAPE, "Only \\n, \\r, \\\\ and \\\" escapes are supported.");
            } else if (c < 32 || c > 126) return casm_reject(p, CASM_RULE_STRING_ASCII, "Use printable ASCII and explicit CR/LF escapes.");
            if (!append(p, c)) return 0;
        }
        return casm_reject(p, CASM_RULE_STRING_END, "Unterminated string literal.");
    }
    if (c == 0 || c > 127) return casm_reject(p, CASM_RULE_SOURCE_ASCII, "NUL and non-ASCII source bytes are not supported.");
    if (strchr("(){}[]=;+-*/%", c)) { p->token = c; return 1; }
    return casm_reject(p, CASM_RULE_TOKEN_UNSUPPORTED, "Token is outside the implemented C subset; nothing will be emitted.");
}
int casm_expect(Parser *p, int token) {
    if (p->failed) return 0;
    if (p->token != token) return casm_reject(p, CASM_RULE_SYNTAX, "Unexpected token in the supported grammar.");
    return casm_next(p);
}
int casm_is_name(Parser *p, const char *name) { return p->token == TOK_NAME && !strcmp(p->name, name); }
int casm_word(Parser *p, const char *name) {
    if (!casm_is_name(p, name)) return casm_reject(p, CASM_RULE_C_SUBSET, "Expected a supported declaration or statement; see LANGUAGE.md.");
    return casm_next(p);
}
