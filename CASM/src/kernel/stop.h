#ifndef CASM_KERNEL_STOP_H
#define CASM_KERNEL_STOP_H
#include <stddef.h>
typedef enum { KERNEL_STOP, KERNEL_CPU, KERNEL_CONTEXT, KERNEL_FAULT, KERNEL_MEMORY, KERNEL_FRAME_CYCLE } KernelProfile;
int casm_stop(const unsigned char *source, size_t length, const char *hex, const char *ir, KernelProfile profile);
#endif
