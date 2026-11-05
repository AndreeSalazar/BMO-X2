#include "internal.h"
#include <stdio.h>
#include <string.h>

typedef struct { int64_t s; uint64_t u; } Value;

static int fits_signed(int64_t v, unsigned bits) {
    int64_t lo, hi;
    if (bits == 64) return 1;
    hi = (int64_t)((UINT64_C(1) << (bits - 1)) - 1); lo = -hi - 1;
    return v >= lo && v <= hi;
}
static int fits_unsigned(uint64_t v, unsigned bits) { return bits == 64 || v <= ((UINT64_C(1) << bits) - 1); }
static int overflow(Parser *p, const CasmIntType *t, const char *what) {
    char reason[160];
    snprintf(reason, sizeof reason, "%s does not fit in %s: CASM never wraps silently.", what, t->name);
    return casm_reject(p, CASM_RULE_INT_OVERFLOW, reason);
}
static int rpn(Parser *p, CasmProgram *program, CasmInteger *n, const char *token) {
    size_t length = strlen(token);
    if (n->rpn_tokens >= CASM_EXPR_TOKENS || n->rpn_length + length + 2 > CASM_RPN_TEXT)
        return casm_reject(p, CASM_RULE_EXPR_SIZE, "Expression exceeds 256 operations.");
    if (!casm_store_rpn(program, n, token))
        return casm_reject(p, CASM_RULE_HOST_MEMORY, "Bounded compiler workspace exhausted.");
    return 1;
}
/* Exact magnitude of the current number token: decimal without leading zeros, or 0x hex. */
static int integer_literal(Parser *p, uint64_t *out) {
    const unsigned char *t = p->text;
    size_t i = 0, base = 10;
    uint64_t v = 0;
    if (t[0] == '0' && (t[1] == 'x' || t[1] == 'X')) { base = 16; i = 2; if (!t[2]) return casm_reject(p, CASM_RULE_INT_LITERAL, "Hexadecimal literal without digits."); }
    else if (t[0] == '0' && t[1]) return casm_reject(p, CASM_RULE_INT_LITERAL, "Leading zero: CASM has no octal literals (010 is not 8).");
    for (; t[i]; i++) {
        unsigned d;
        if (casm_digit(t[i])) d = (unsigned)(t[i] - '0');
        else if (base == 16 && t[i] >= 'a' && t[i] <= 'f') d = (unsigned)(t[i] - 'a' + 10);
        else if (base == 16 && t[i] >= 'A' && t[i] <= 'F') d = (unsigned)(t[i] - 'A' + 10);
        else return casm_reject(p, CASM_RULE_INT_LITERAL, "Malformed integer literal (no suffixes; digits only).");
        if (__builtin_mul_overflow(v, (uint64_t)base, &v) || __builtin_add_overflow(v, (uint64_t)d, &v))
            return casm_reject(p, CASM_RULE_INT_LITERAL, "Integer literal exceeds 18446744073709551615.");
    }
    *out = v;
    return 1;
}
static int decimal_text(uint64_t magnitude, int negative, char *out) {
    char digits[24];
    int n = 0, k = 0;
    do { digits[n++] = (char)('0' + magnitude % 10); magnitude /= 10; } while (magnitude);
    if (negative) out[k++] = '-';
    while (n) out[k++] = digits[--n];
    out[k] = 0;
    return k;
}
static int expression(Parser *p, CasmProgram *program, CasmInteger *n, Value *v, int depth);

static int primary(Parser *p, CasmProgram *program, CasmInteger *n, Value *v, int depth) {
    const CasmIntType *t = &casm_int_types[n->type];
    size_t i;
    if (p->token == '(') {
        if (depth >= CASM_EXPR_DEPTH) return casm_reject(p, CASM_RULE_EXPR_DEPTH, "Expression nests deeper than 32 levels.");
        return casm_next(p) && expression(p, program, n, v, depth + 1) && casm_expect(p, ')');
    }
    if (p->token == TOK_NUMBER) {
        uint64_t m;
        char text[24];
        if (!integer_literal(p, &m)) return 0;
        decimal_text(m, 0, text);
        if (t->is_signed ? (m > (uint64_t)INT64_MAX || !fits_signed((int64_t)m, t->bits)) : !fits_unsigned(m, t->bits)) return overflow(p, t, "The literal");
        if (t->is_signed) v->s = (int64_t)m; else v->u = m;
        return rpn(p, program, n, text) && casm_next(p);
    }
    if (p->token == TOK_NAME) {
        CasmInteger *r = 0;
        char token[CASM_NAME_MAX + 2];
        for (i = 0; i < program->integer_count; i++) if (!strcmp(program->integers[i].name, p->name)) r = &program->integers[i];
        for (i = 0; i < program->constant_count; i++) if (!strcmp(program->constants[i].name, p->name)) return casm_reject(p, CASM_RULE_TYPE_INT, "A string cannot take part in integer arithmetic.");
        if (!r) return casm_reject(p, CASM_RULE_NAME_UNDEFINED, "Integer must be declared before use.");
        r->used = 1;
        /* The referenced exact value must be representable in this declaration's type. */
        if (t->is_signed) {
            if (r->negative ? r->magnitude > (uint64_t)INT64_MAX + 1 : r->magnitude > (uint64_t)INT64_MAX) return overflow(p, t, r->name);
            v->s = r->negative ? (int64_t)(0 - r->magnitude) : (int64_t)r->magnitude;
            if (!fits_signed(v->s, t->bits)) return overflow(p, t, r->name);
        } else {
            if (r->negative && r->magnitude) return overflow(p, t, r->name);
            v->u = r->magnitude;
            if (!fits_unsigned(v->u, t->bits)) return overflow(p, t, r->name);
        }
        token[0] = '@'; memcpy(token + 1, r->name, strlen(r->name) + 1);
        return rpn(p, program, n, token) && casm_next(p);
    }
    return casm_reject(p, CASM_RULE_SYNTAX, "Expected an integer literal, a declared integer or (.");
}
static int unary(Parser *p, CasmProgram *program, CasmInteger *n, Value *v, int depth) {
    const CasmIntType *t = &casm_int_types[n->type];
    if (p->token != '-') return primary(p, program, n, v, depth);
    if (depth >= CASM_EXPR_DEPTH) return casm_reject(p, CASM_RULE_EXPR_DEPTH, "Expression nests deeper than 32 levels.");
    if (!casm_next(p)) return 0;
    if (p->token == TOK_NUMBER) {
        /* -literal is one exact value, so int64_t can hold -9223372036854775808. */
        uint64_t m;
        char text[24];
        if (!integer_literal(p, &m)) return 0;
        if (t->is_signed) {
            if (m > (uint64_t)INT64_MAX + 1) return overflow(p, t, "The literal");
            v->s = m == (uint64_t)INT64_MAX + 1 ? INT64_MIN : -(int64_t)m;
            if (!fits_signed(v->s, t->bits)) return overflow(p, t, "The literal");
        } else {
            if (m) return overflow(p, t, "A negative literal");
            v->u = 0;
        }
        decimal_text(m, m != 0, text);
        return rpn(p, program, n, text) && casm_next(p);
    }
    if (!unary(p, program, n, v, depth + 1)) return 0;
    if (t->is_signed) { if (v->s == INT64_MIN || !fits_signed(-v->s, t->bits)) return overflow(p, t, "The negation"); v->s = -v->s; }
    else { if (v->u) return overflow(p, t, "The negation"); }
    return rpn(p, program, n, "neg");
}
static int term(Parser *p, CasmProgram *program, CasmInteger *n, Value *v, int depth) {
    const CasmIntType *t = &casm_int_types[n->type];
    if (!unary(p, program, n, v, depth)) return 0;
    while (p->token == '*' || p->token == '/' || p->token == '%') {
        int op = p->token;
        Value b;
        if (!casm_next(p) || !unary(p, program, n, &b, depth)) return 0;
        if (op != '*' && (t->is_signed ? b.s == 0 : b.u == 0)) return casm_reject(p, CASM_RULE_INT_DIV_ZERO, "Division or remainder by zero.");
        if (t->is_signed) {
            if (op == '*') { if (__builtin_mul_overflow(v->s, b.s, &v->s) || !fits_signed(v->s, t->bits)) return overflow(p, t, "The product"); }
            else if (op == '/') { if (v->s == INT64_MIN && b.s == -1) return overflow(p, t, "The quotient"); v->s /= b.s; if (!fits_signed(v->s, t->bits)) return overflow(p, t, "The quotient"); }
            else v->s = b.s == -1 ? 0 : v->s % b.s;
        } else {
            if (op == '*') { if (__builtin_mul_overflow(v->u, b.u, &v->u) || !fits_unsigned(v->u, t->bits)) return overflow(p, t, "The product"); }
            else if (op == '/') v->u /= b.u;
            else v->u %= b.u;
        }
        if (!rpn(p, program, n, op == '*' ? "*" : op == '/' ? "/" : "%")) return 0;
    }
    return 1;
}
static int expression(Parser *p, CasmProgram *program, CasmInteger *n, Value *v, int depth) {
    const CasmIntType *t = &casm_int_types[n->type];
    if (!term(p, program, n, v, depth)) return 0;
    while (p->token == '+' || p->token == '-') {
        int op = p->token;
        Value b;
        if (!casm_next(p) || !term(p, program, n, &b, depth)) return 0;
        if (t->is_signed) {
            if ((op == '+' ? __builtin_add_overflow(v->s, b.s, &v->s) : __builtin_sub_overflow(v->s, b.s, &v->s)) || !fits_signed(v->s, t->bits))
                return overflow(p, t, op == '+' ? "The sum" : "The difference");
        } else {
            if ((op == '+' ? __builtin_add_overflow(v->u, b.u, &v->u) : __builtin_sub_overflow(v->u, b.u, &v->u)) || !fits_unsigned(v->u, t->bits))
                return overflow(p, t, op == '+' ? "The sum" : "The difference");
        }
        if (!rpn(p, program, n, op == '+' ? "+" : "-")) return 0;
    }
    return 1;
}
/* const <int type> name = expression; */
int casm_integer_declaration(Parser *p, CasmProgram *program, int type, unsigned line) {
    CasmInteger *n;
    Value v;
    if (program->integer_count >= CASM_ITEMS_MAX) return casm_reject(p, CASM_RULE_INTEGER_LIMIT, "Too many integer constants.");
    if (!casm_next(p)) return 0;
    if (p->token != TOK_NAME) return casm_reject(p, CASM_RULE_DECL_NAME, "Expected an integer identifier.");
    if (casm_reserved(p->name)) return casm_reject(p, CASM_RULE_NAME_RESERVED, "C keywords, underscore names and runtime names cannot be declared.");
    if (casm_name_taken(program, p->name)) return casm_reject(p, CASM_RULE_NAME_DUPLICATE, "Identifier already declared in this scope.");
    n = &program->integers[program->integer_count];
    memset(n, 0, sizeof(*n));
    memcpy(n->name, p->name, strlen(p->name) + 1);
    n->line = line; n->type = type; n->decimal = -1;
    if (!casm_next(p) || !casm_expect(p, '=')) return 0;
    if (p->token == TOK_STRING) return casm_reject(p, CASM_RULE_TYPE_INT, "An integer requires an integer expression, not a string.");
    memset(&v, 0, sizeof v);
    if (!expression(p, program, n, &v, 0)) return 0;
    if (casm_int_types[type].is_signed) { n->negative = v.s < 0; n->magnitude = v.s < 0 ? 0 - (uint64_t)v.s : (uint64_t)v.s; }
    else { n->negative = 0; n->magnitude = v.u; }
    program->integer_count++;
    return casm_expect(p, ';');
}
/* metal_put_int(name); prints the exact decimal value, like COBOL's DISPLAY. */
int casm_put_int(Parser *p, CasmProgram *program) {
    size_t i;
    unsigned line = p->token_line;
    CasmInteger *n = 0;
    if (program->call_count >= CASM_ITEMS_MAX) return casm_reject(p, CASM_RULE_CALL_LIMIT, "Too many service calls.");
    if (!casm_next(p) || !casm_expect(p, '(')) return 0;
    if (p->token != TOK_NAME) return casm_reject(p, CASM_RULE_TYPE_INT, "metal_put_int requires a declared integer.");
    for (i = 0; i < program->integer_count; i++) if (!strcmp(program->integers[i].name, p->name)) n = &program->integers[i];
    for (i = 0; i < program->constant_count; i++) if (program->constants[i].kind == CASM_ASCII && !strcmp(program->constants[i].name, p->name)) return casm_reject(p, CASM_RULE_TYPE_INT, "metal_put_int prints integers; use metal_puts for strings.");
    if (!n) return casm_reject(p, CASM_RULE_NAME_UNDEFINED, "Integer must be declared before use.");
    n->used = 1;
    if (n->decimal < 0) {
        /* Its decimal rendering is data, emitted once and shared by every call. */
        CasmConstant *c;
        char text[24];
        int length;
        if (program->constant_count >= CASM_ITEMS_MAX) return casm_reject(p, CASM_RULE_CONSTANT_LIMIT, "Too many constants.");
        c = &program->constants[program->constant_count];
        memset(c, 0, sizeof(*c));
        c->name[0] = '#'; memcpy(c->name + 1, n->name, strlen(n->name) + 1);
        length = decimal_text(n->magnitude, n->negative, text);
        c->bytes = casm_store_data(program, (const unsigned char *)text, (size_t)length + 1);
        if (!c->bytes) return casm_reject(p, CASM_RULE_HOST_MEMORY, "Bounded compiler workspace exhausted.");
        c->length = (size_t)length + 1;
        c->line = n->line; c->kind = CASM_DECIMAL; c->integer = (size_t)(n - program->integers);
        n->decimal = (long)program->constant_count++;
    }
    program->calls[program->call_count].constant = (size_t)n->decimal;
    program->calls[program->call_count++].line = line;
    return casm_next(p) && casm_expect(p, ')') && casm_expect(p, ';');
}

