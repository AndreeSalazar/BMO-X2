#ifndef CASM_KERNEL_STOP_H
#define CASM_KERNEL_STOP_H
#include <stddef.h>
typedef enum {
    KERNEL_STOP, KERNEL_CPU, KERNEL_CONTEXT, KERNEL_FAULT,
    KERNEL_MEMORY, KERNEL_FRAME_CYCLE, KERNEL_PAGING, KERNEL_USER_FAULT, KERNEL_ABI_PROBE
} KernelProfile;
int casm_stop(const unsigned char *source, size_t length, const char *hex, const char *ir, KernelProfile profile);
#endif
