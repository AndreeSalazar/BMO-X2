#include "casm.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "kernel/stop.h"
#include "kernel/splash.h"

int main(int argc, char **argv) {
    unsigned char *source;
    CasmProgram *program;
    FILE *file;
    size_t length;
    int ok;
    int explicit_profile = argc == 6 && !strcmp(argv[1], "--profile");
    int identify = explicit_profile && !strcmp(argv[2], "ring0-cpu-0.1");
    int context = explicit_profile && !strcmp(argv[2], "ring0-context-0.1");
    int memory = explicit_profile && !strcmp(argv[2], "ring0-memory-0.1");
    int frame_cycle = explicit_profile && !strcmp(argv[2], "ring0-frame-cycle-0.1");
    int paging = explicit_profile && !strcmp(argv[2], "ring0-paging-0.1");
    int user_fault = explicit_profile && !strcmp(argv[2], "ring0-user-fault-0.1");
    int fault = explicit_profile && !strcmp(argv[2], "ring0-fault-0.1");
    int splash_hd = explicit_profile && !strcmp(argv[2], "ring0-splash-hd-0.1");
    int splash = splash_hd || (explicit_profile && !strcmp(argv[2], "ring0-splash-0.1"));
    int stop = identify || context || fault || memory || frame_cycle || paging || user_fault ||
               (explicit_profile && !strcmp(argv[2], "ring0-stop-0.1"));
    if (stop || splash) { argc -= 2; argv += 2; }
    if (argc != 4) {
        fprintf(stderr, "Usage: casmc SOURCE OUTPUT.hex OUTPUT.ir.json\n");
        return 2;
    }
    file = fopen(argv[1], "rb");
    if (!file) { fprintf(stderr, "RED [HOST-READ] Cannot open source.\n"); return 1; }
    source = calloc(CASM_SOURCE_MAX + 1, 1);
    program = stop || splash ? NULL : calloc(1, sizeof(*program));
    if (!source || (!stop && !splash && !program)) {
        fprintf(stderr, "RED [HOST-MEMORY] Allocation failed.\n");
        fclose(file); free(source); free(program); return 1;
    }
    length = fread(source, 1, CASM_SOURCE_MAX + 1, file);
    ok = !ferror(file) && length <= CASM_SOURCE_MAX;
    fclose(file);
    if (!ok) fprintf(stderr, "RED [SOURCE-SIZE] Source exceeds 65536 bytes or cannot be read.\n");
    if (ok && splash) ok = casm_splash(source, length, argv[2], argv[3], splash_hd);
    else if (ok && stop) ok = casm_stop(source, length, argv[2], argv[3],
                                    user_fault ? KERNEL_USER_FAULT : paging ? KERNEL_PAGING : frame_cycle ? KERNEL_FRAME_CYCLE :
                                    memory ? KERNEL_MEMORY : fault ? KERNEL_FAULT :
                                    context ? KERNEL_CONTEXT : identify ? KERNEL_CPU : KERNEL_STOP);
    else {
        if (ok) ok = casm_parse(source, length, program);
        if (ok) ok = casm_emit(program, argv[2], argv[3]);
    }
    free(program); free(source);
    return ok ? 0 : 1;
}
