#include "internal.h"
#include <stdio.h>
#include <string.h>

int casm_reserved(const char *name) {
    static const char *names[] = {"auto","break","case","char","const","continue","default","do","double","else","enum","extern","float","for","goto","if","inline","int","long","register","restrict","return","short","signed","sizeof","static","struct","switch","typedef","union","unsigned","void","volatile","while","_Alignas","_Alignof","_Atomic","_Bool","_Complex","_Generic","_Imaginary","_Noreturn","_Static_assert","_Thread_local","metal_main","metal_puts","metal_put_int",
        "uint8_t","uint16_t","uint32_t","uint64_t","int8_t","int16_t","int32_t","int64_t"};
    size_t i;
    for (i = 0; i < sizeof(names)/sizeof(names[0]); i++) if (!strcmp(name, names[i])) return 1;
    return name[0] == '_';
}
int casm_type_index(const char *name) {
    int i;
    for (i = 0; i < 8; i++) if (!strcmp(name, casm_int_types[i].name)) return i;
    return -1;
}
int casm_name_taken(const CasmProgram *program, const char *name) {
    size_t i;
    for (i = 0; i < program->constant_count; i++) if (!strcmp(program->constants[i].name, name)) return 1;
    for (i = 0; i < program->integer_count; i++) if (!strcmp(program->integers[i].name, name)) return 1;
    return 0;
}
