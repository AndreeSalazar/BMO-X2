#ifndef CASM_KERNEL_STOP_H
#define CASM_KERNEL_STOP_H
#include <stddef.h>
int casm_stop(const unsigned char *source, size_t length, const char *hex, const char *ir);
#endif
