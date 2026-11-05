#include "internal.h"
#include <stdio.h>
#include <string.h>

static int declaration(Parser *p, CasmProgram *program) {
    CasmConstant *constant;
    unsigned line = p->token_line;
    if (!casm_word(p,"const")) return 0;
    if (p->token == TOK_NAME && casm_type_index(p->name) >= 0) return casm_integer_declaration(p, program, casm_type_index(p->name), line);
    if (program->constant_count >= CASM_ITEMS_MAX) return casm_reject(p, CASM_RULE_CONSTANT_LIMIT, "Too many constants.");
    if (!casm_word(p,"char")) return 0;
    if (p->token == '*') return casm_reject(p, CASM_RULE_TOKEN_UNSUPPORTED,"Pointers are not part of CASM: declare const char name[] = \"...\";");
    if (p->token != TOK_NAME) return casm_reject(p, CASM_RULE_DECL_NAME,"Expected an array identifier.");
    if (casm_reserved(p->name)) return casm_reject(p, CASM_RULE_NAME_RESERVED,"C keywords, underscore names and runtime names cannot be declared.");
    if (casm_name_taken(program, p->name)) return casm_reject(p, CASM_RULE_NAME_DUPLICATE,"Identifier already declared in this scope.");
    constant = &program->constants[program->constant_count];
    memset(constant, 0, sizeof(*constant));
    memcpy(constant->name, p->name, strlen(p->name)+1); constant->line = line;
    if (!casm_next(p) || !casm_expect(p,'[') || !casm_expect(p,']') || !casm_expect(p,'=')) return 0;
    if (p->token != TOK_STRING) return casm_reject(p, CASM_RULE_TYPE_STRING,"A const char array requires a string literal initializer.");
    constant->bytes = casm_store_data(program, p->text, p->text_length);
    if (!constant->bytes) return casm_reject(p, CASM_RULE_HOST_MEMORY, "Bounded compiler workspace exhausted.");
    constant->length=p->text_length;
    program->constant_count++;
    return casm_next(p) && casm_expect(p,';');
}
static int call(Parser *p, CasmProgram *program) {
    size_t i;
    unsigned line=p->token_line;
    if (program->call_count >= CASM_ITEMS_MAX) return casm_reject(p, CASM_RULE_CALL_LIMIT,"Too many service calls.");
    if (!casm_word(p,"metal_puts") || !casm_expect(p,'(')) return 0;
    if (p->token != TOK_NAME) return casm_reject(p, CASM_RULE_TYPE_STRING,"metal_puts requires a declared immutable char array.");
    for (i=0; i<program->integer_count; i++) if (!strcmp(p->name,program->integers[i].name)) return casm_reject(p, CASM_RULE_TYPE_STRING,"metal_puts prints strings; use metal_put_int for integers.");
    for (i=0; i<program->constant_count; i++) if (program->constants[i].kind == CASM_ASCII && !strcmp(p->name,program->constants[i].name)) break;
    if (i == program->constant_count) return casm_reject(p, CASM_RULE_NAME_UNDEFINED,"String must be declared before use.");
    program->calls[program->call_count].constant=i;
    program->calls[program->call_count++].line=line;
    return casm_next(p) && casm_expect(p,')') && casm_expect(p,';');
}
int casm_parse_tokens(const unsigned char *source, size_t length, CasmProgram *program) {
    Parser p;
    size_t i;
    memset(&p,0,sizeof(p)); p.source=source; p.length=length; p.line=1; p.token_line=1;
    /* Even comments must not silently conceal unsupported byte encodings. */
    for (i=0;i<length;i++) if (!source[i] || source[i]>127) return casm_reject(&p, CASM_RULE_SOURCE_ASCII,"Source must be ASCII without NUL bytes or a UTF-8 BOM.");
    if (!casm_next(&p) || !casm_word(&p,"void") || !casm_word(&p,"metal_main") || !casm_expect(&p,'(') || !casm_word(&p,"void") || !casm_expect(&p,')') || !casm_expect(&p,'{')) return 0;
    while (!p.failed && p.token != '}' && p.token != TOK_EOF) {
        if (program->return_line) return casm_reject(&p, CASM_RULE_AFTER_RETURN,"Statements after return are not permitted.");
        if (casm_is_name(&p,"const")) { if (!declaration(&p,program)) return 0; }
        else if (casm_is_name(&p,"metal_puts")) { if (!call(&p,program)) return 0; }
        else if (casm_is_name(&p,"metal_put_int")) { if (!casm_put_int(&p,program)) return 0; }
        else if (casm_is_name(&p,"return")) {
            program->return_line=p.token_line;
            if (!casm_next(&p) || !casm_expect(&p,';')) return 0;
        } else return casm_reject(&p, CASM_RULE_C_SUBSET,"Unsupported C construct; no fallback or ignored statements.");
    }
    if (!program->return_line) return casm_reject(&p, CASM_RULE_RETURN_REQUIRED,"The entry must end with an explicit return;.");
    if (!casm_expect(&p,'}')) return 0;
    if (p.token != TOK_EOF) return casm_reject(&p, CASM_RULE_TRAILING_SOURCE,"Only one entry definition is supported.");
    printf("GREEN [SEMANTIC] Immutable strings, exact integers and service calls validated.\n");
    return 1;
}
