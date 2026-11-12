#include "casm.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "kernel/stop.h"

int main(int argc, char **argv) {
    unsigned char *source;
    CasmProgram *program;
    FILE *file;
    size_t length;
    int ok;
    int explicit_profile = argc == 6 && !strcmp(argv[1], "--profile");
    int identify = explicit_profile && !strcmp(argv[2], "ring0-cpu-0.1");
    int stop = identify || (explicit_profile && !strcmp(argv[2], "ring0-stop-0.1"));
    if (stop) { argc -= 2; argv += 2; }
    if (argc != 4) {
        fprintf(stderr, "Usage: casmc SOURCE OUTPUT.hex OUTPUT.ir.json\n");
        return 2;
    }
    file = fopen(argv[1], "rb");
    if (!file) { fprintf(stderr, "RED [HOST-READ] Cannot open source.\n"); return 1; }
    source = calloc(CASM_SOURCE_MAX + 1, 1);
    program = stop ? NULL : calloc(1, sizeof(*program));
    if (!source || (!stop && !program)) {
        fprintf(stderr, "RED [HOST-MEMORY] Allocation failed.\n");
        fclose(file); free(source); free(program); return 1;
    }
    length = fread(source, 1, CASM_SOURCE_MAX + 1, file);
    ok = !ferror(file) && length <= CASM_SOURCE_MAX;
    fclose(file);
    if (!ok) fprintf(stderr, "RED [SOURCE-SIZE] Source exceeds 65536 bytes or cannot be read.\n");
    if (ok && stop) ok = casm_stop(source, length, argv[2], argv[3], identify);
    else {
        if (ok) ok = casm_parse(source, length, program);
        if (ok) ok = casm_emit(program, argv[2], argv[3]);
    }
    free(program); free(source);
    return ok ? 0 : 1;
}
