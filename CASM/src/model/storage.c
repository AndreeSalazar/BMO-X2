/* Host-only bounded storage. No allocator and no target-runtime dependency. */
#include "../casm.h"
#include <string.h>

const unsigned char *casm_store_data(CasmProgram *program, const unsigned char *bytes, size_t length) {
    unsigned char *target;
    if (program->data_used > CASM_DATA_CAPACITY || length > CASM_DATA_CAPACITY - program->data_used)
        return NULL;
    target = program->data_storage + program->data_used;
    if (length) memcpy(target, bytes, length);
    program->data_used += length;
    return target;
}

int casm_store_rpn(CasmProgram *program, CasmInteger *integer, const char *token) {
    size_t length = strlen(token), extra = length + (integer->rpn_tokens ? 1u : 0u);
    size_t terminator = integer->rpn ? 0u : 1u;
    if (program->rpn_used > CASM_RPN_CAPACITY || terminator > CASM_RPN_CAPACITY - program->rpn_used
        || extra > CASM_RPN_CAPACITY - program->rpn_used - terminator)
        return 0;
    /* Only the current expression may append. Completed expressions stay stable. */
    if (integer->rpn && integer->rpn + integer->rpn_length + 1 != program->rpn_storage + program->rpn_used)
        return 0;
    if (!integer->rpn) {
        integer->rpn = program->rpn_storage + program->rpn_used;
        program->rpn_used++;
    }
    if (integer->rpn_tokens) integer->rpn[integer->rpn_length++] = ' ';
    memcpy(integer->rpn + integer->rpn_length, token, length + 1);
    integer->rpn_length += length;
    integer->rpn_tokens++;
    program->rpn_used += extra;
    return 1;
}
