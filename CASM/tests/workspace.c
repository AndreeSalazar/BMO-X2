/* Invariants of the host workspace, independent of parsing or emission. */
#include "../src/casm.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CHECK(condition) do { if (!(condition)) { fprintf(stderr, "workspace check failed at line %d\n", __LINE__); free(p); return 1; } } while (0)

int main(void) {
    CasmProgram *p = calloc(1, sizeof(*p));
    CasmInteger first = {0}, second = {0}, edge = {0};
    static unsigned char payload[CASM_DATA_CAPACITY];
    const unsigned char *stored;
    size_t before;
    if (!p) return 2;
    payload[CASM_DATA_CAPACITY - 1] = 0x5a;
    CHECK(casm_store_data(p, payload, CASM_DATA_CAPACITY + 1) == NULL && p->data_used == 0);
    stored = casm_store_data(p, payload, CASM_DATA_CAPACITY);
    CHECK(stored == p->data_storage && stored[CASM_DATA_CAPACITY - 1] == 0x5a);
    CHECK(casm_store_data(p, payload, 1) == NULL && p->data_used == CASM_DATA_CAPACITY);
    p->data_used = CASM_DATA_CAPACITY + 1;
    CHECK(casm_store_data(p, payload, 1) == NULL);

    CHECK(casm_store_rpn(p, &first, "1") && casm_store_rpn(p, &first, "2") && casm_store_rpn(p, &first, "+"));
    CHECK(!strcmp(first.rpn, "1 2 +") && first.rpn_length == 5 && first.rpn_tokens == 3);
    CHECK(casm_store_rpn(p, &second, "17") && !strcmp(first.rpn, "1 2 +"));
    before = p->rpn_used;
    CHECK(!casm_store_rpn(p, &first, "3") && p->rpn_used == before && !strcmp(first.rpn, "1 2 +"));
    p->rpn_used = CASM_RPN_CAPACITY - 2;
    CHECK(casm_store_rpn(p, &edge, "0") && p->rpn_used == CASM_RPN_CAPACITY);
    CHECK(!casm_store_rpn(p, &edge, "1") && !strcmp(edge.rpn, "0") && edge.rpn_length == 1);
    p->rpn_used = CASM_RPN_CAPACITY + 1;
    CHECK(!casm_store_rpn(p, &edge, "1"));

    printf("{\"program_bytes\":%zu,\"constant_bytes\":%zu,\"integer_bytes\":%zu,"
           "\"data_capacity\":%d,\"rpn_capacity\":%d,\"invariant_checks\":11}\n",
           sizeof(CasmProgram), sizeof(CasmConstant), sizeof(CasmInteger), CASM_DATA_CAPACITY, CASM_RPN_CAPACITY);
    free(p);
    return 0;
}
