/* Real diagnostic dispatch: keeps the rule catalogue visible to the existing
 * SUPER GRAFO Taller. The message and source location come from the caller.
 * To inspect the original condition, follow the frontend modules in the graph. */
#include "frontend/internal.h"
#include <stdio.h>

static int fail(Parser *p, const char *rule, const char *reason) {
    if (!p->failed) fprintf(stderr, "RED [%s] line %u: %s\n", rule, p->token_line, reason);
    p->failed = 1;
    return 0;
}
int casm_reject(Parser *p, CasmRule rule, const char *reason) {
    switch (rule) {
    case CASM_RULE_AFTER_RETURN: return fail(p, "AFTER-RETURN", reason);
    case CASM_RULE_C_SUBSET: return fail(p, "C-SUBSET", reason);
    case CASM_RULE_CALL_LIMIT: return fail(p, "CALL-LIMIT", reason);
    case CASM_RULE_COMMENT_END: return fail(p, "COMMENT-END", reason);
    case CASM_RULE_CONSTANT_LIMIT: return fail(p, "CONSTANT-LIMIT", reason);
    case CASM_RULE_DECL_NAME: return fail(p, "DECL-NAME", reason);
    case CASM_RULE_EXPR_DEPTH: return fail(p, "EXPR-DEPTH", reason);
    case CASM_RULE_EXPR_SIZE: return fail(p, "EXPR-SIZE", reason);
    case CASM_RULE_HOST_MEMORY: return fail(p, "HOST-MEMORY", reason);
    case CASM_RULE_INT_DIV_ZERO: return fail(p, "INT-DIV-ZERO", reason);
    case CASM_RULE_INT_LITERAL: return fail(p, "INT-LITERAL", reason);
    case CASM_RULE_INT_OVERFLOW: return fail(p, "INT-OVERFLOW", reason);
    case CASM_RULE_INTEGER_LIMIT: return fail(p, "INTEGER-LIMIT", reason);
    case CASM_RULE_NAME_DUPLICATE: return fail(p, "NAME-DUPLICATE", reason);
    case CASM_RULE_NAME_RESERVED: return fail(p, "NAME-RESERVED", reason);
    case CASM_RULE_NAME_SIZE: return fail(p, "NAME-SIZE", reason);
    case CASM_RULE_NAME_UNDEFINED: return fail(p, "NAME-UNDEFINED", reason);
    case CASM_RULE_RETURN_REQUIRED: return fail(p, "RETURN-REQUIRED", reason);
    case CASM_RULE_SOURCE_ASCII: return fail(p, "SOURCE-ASCII", reason);
    case CASM_RULE_SOURCE_SIZE: return fail(p, "SOURCE-SIZE", reason);
    case CASM_RULE_STRING_ASCII: return fail(p, "STRING-ASCII", reason);
    case CASM_RULE_STRING_END: return fail(p, "STRING-END", reason);
    case CASM_RULE_STRING_ESCAPE: return fail(p, "STRING-ESCAPE", reason);
    case CASM_RULE_STRING_SIZE: return fail(p, "STRING-SIZE", reason);
    case CASM_RULE_SYNTAX: return fail(p, "SYNTAX", reason);
    case CASM_RULE_TOKEN_UNSUPPORTED: return fail(p, "TOKEN-UNSUPPORTED", reason);
    case CASM_RULE_TRAILING_SOURCE: return fail(p, "TRAILING-SOURCE", reason);
    case CASM_RULE_TYPE_INT: return fail(p, "TYPE-INT", reason);
    case CASM_RULE_TYPE_STRING: return fail(p, "TYPE-STRING", reason);

    }
    return fail(p, "C-SUBSET", "Unknown internal diagnostic.");
}

int casm_parse(const unsigned char *source, size_t length, CasmProgram *program) {
    if (length > CASM_SOURCE_MAX) {
        Parser p = {0};
        p.token_line = 1;
        return casm_reject(&p, CASM_RULE_SOURCE_SIZE, "Source exceeds 65536 bytes.");
    }
    return casm_parse_tokens(source, length, program);
}
