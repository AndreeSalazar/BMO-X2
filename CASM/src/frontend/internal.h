#ifndef CASM_FRONTEND_INTERNAL_H
#define CASM_FRONTEND_INTERNAL_H
#include "../casm.h"

enum { TOK_EOF = 256, TOK_NAME, TOK_STRING, TOK_NUMBER };
typedef struct {
    const unsigned char *source;
    size_t length, pos;
    unsigned line, token_line;
    int token, failed;
    char name[CASM_NAME_MAX + 1];
    unsigned char text[CASM_TEXT_MAX];
    size_t text_length;
} Parser;


typedef enum {
    CASM_RULE_AFTER_RETURN,
    CASM_RULE_C_SUBSET,
    CASM_RULE_CALL_LIMIT,
    CASM_RULE_COMMENT_END,
    CASM_RULE_CONSTANT_LIMIT,
    CASM_RULE_DECL_NAME,
    CASM_RULE_EXPR_DEPTH,
    CASM_RULE_EXPR_SIZE,
    CASM_RULE_HOST_MEMORY,
    CASM_RULE_INT_DIV_ZERO,
    CASM_RULE_INT_LITERAL,
    CASM_RULE_INT_OVERFLOW,
    CASM_RULE_INTEGER_LIMIT,
    CASM_RULE_NAME_DUPLICATE,
    CASM_RULE_NAME_RESERVED,
    CASM_RULE_NAME_SIZE,
    CASM_RULE_NAME_UNDEFINED,
    CASM_RULE_RETURN_REQUIRED,
    CASM_RULE_SOURCE_ASCII,
    CASM_RULE_SOURCE_SIZE,
    CASM_RULE_STRING_ASCII,
    CASM_RULE_STRING_END,
    CASM_RULE_STRING_ESCAPE,
    CASM_RULE_STRING_SIZE,
    CASM_RULE_SYNTAX,
    CASM_RULE_TOKEN_UNSUPPORTED,
    CASM_RULE_TRAILING_SOURCE,
    CASM_RULE_TYPE_INT,
    CASM_RULE_TYPE_STRING,
} CasmRule;

int casm_reject(Parser *p, CasmRule rule, const char *reason);
int casm_digit(unsigned char c);
int casm_next(Parser *p);
int casm_expect(Parser *p, int token);
int casm_is_name(Parser *p, const char *name);
int casm_word(Parser *p, const char *name);
int casm_reserved(const char *name);
int casm_type_index(const char *name);
int casm_name_taken(const CasmProgram *program, const char *name);
int casm_integer_declaration(Parser *p, CasmProgram *program, int type, unsigned line);
int casm_put_int(Parser *p, CasmProgram *program);
int casm_parse_tokens(const unsigned char *source, size_t length, CasmProgram *program);
#endif
