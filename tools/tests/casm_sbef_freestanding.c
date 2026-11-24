/* Linux init harness for the audited CASM Native module, used in a diskless VM. */
typedef unsigned long u64;

static long syscall6(long number, long a, long b, long c, long d, long e, long f) {
    register long r10 __asm__("r10") = d;
    register long r8 __asm__("r8") = e;
    register long r9 __asm__("r9") = f;
    __asm__ volatile("syscall" : "+a"(number)
                     : "D"(a), "S"(b), "d"(c), "r"(r10), "r"(r8), "r"(r9)
                     : "rcx", "r11", "memory");
    return number;
}

static long call(long number, long a, long b, long c) {
    return syscall6(number, a, b, c, 0, 0, 0);
}

static long read_file(const char *name, unsigned char *dest, long limit) {
    long fd = call(2, (long)name, 0, 0);
    if (fd < 0) return -1;
    long used = 0;
    while (used < limit) {
        long count = call(0, fd, (long)(dest + used), limit - used);
        if (count < 0) {
            call(3, fd, 0, 0);
            return -1;
        }
        if (count == 0) break;
        used += count;
    }
    unsigned char extra;
    long tail = call(0, fd, (long)&extra, 1);
    call(3, fd, 0, 0);
    return tail == 0 ? used : -1;
}

static int map_region(const char *name, u64 address, u64 memory, u64 file, int permissions) {
    /* MAP_FIXED_NOREPLACE | MAP_PRIVATE | MAP_ANONYMOUS. Stage with RW/NX. */
    if (syscall6(9, address, memory, 3, 0x100022, -1, 0) != (long)address) return 1;
    if (read_file(name, (unsigned char *)address, file) != (long)file) return 1;
    return call(10, address, memory, permissions) != 0;
}

static void print_value(const char *prefix, long length, u64 value) {
    char digits[21];
    char *start = &digits[20];
    *start = '\n';
    do {
        *--start = '0' + value % 10;
        value /= 10;
    } while (value);
    call(1, 1, (long)prefix, length);
    call(1, 1, (long)start, digits + sizeof digits - start);
}

__attribute__((force_align_arg_pointer)) void _start(void) {
    u64 stack_limits[2];
    u64 resident = 0;
    unsigned char pages[DATA_MEMORY / 4096];
    volatile u64 *input = (void *)(DATA_ADDRESS + 24);
    u64 (*validate)(void) = (void *)ENTRY;
    unsigned char buffer[296];
    if (call(97, 3, (long)stack_limits, 0) || stack_limits[0] < STACK_BYTES) goto done;
    if (map_region("/text", TEXT_ADDRESS, TEXT_BYTES, TEXT_BYTES, 5) ||
        map_region("/data", DATA_ADDRESS, DATA_MEMORY, DATA_BYTES, 3)) goto done;
    if (input[sizeof buffer] != INPUT_MARKER) goto done;
    for (unsigned index = 0; index < CASE_COUNT; ++index) {
        char name[] = "/case00";
        name[5] = '0' + index / 10;
        name[6] = '0' + index % 10;
        long size = read_file(name, buffer, sizeof buffer);
        if (size < 0) goto done;
        for (long offset = 0; offset < size; ++offset) input[offset] = buffer[offset];
        input[sizeof buffer] = (u64)size;
        /* SysV requires DF clear and a 16-byte aligned stack before call. */
        __asm__ volatile("cld" ::: "cc");
        print_value("BMO_SBEF ", 9, validate());
    }
    if (call(27, DATA_ADDRESS, DATA_MEMORY, (long)pages)) goto done;
    for (u64 index = 0; index < sizeof pages; ++index) resident += pages[index] & 1;
    print_value("BMO_RW_RESIDENT ", 16, resident);
    call(1, 1, (long)"BMO_COMPLETE\n", 13);
done:
    call(169, 0xfee1dead, 672274793, 0x4321fedc);
    for (;;) call(34, 0, 0, 0);
}
