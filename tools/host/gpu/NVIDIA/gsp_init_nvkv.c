/* HOST-only bounds check for the OpenRM 615 GSP_INIT NVKV wire format. */
#include <stddef.h>
#include <stdint.h>

static inline uint32_t read_le32(const uint8_t *bytes)
{
    return (uint32_t)bytes[0] | ((uint32_t)bytes[1] << 8) |
           ((uint32_t)bytes[2] << 16) | ((uint32_t)bytes[3] << 24);
}

/* Zero means valid. An error returns the offending byte offset plus one. */
__attribute__((ms_abi, section(".text.gsp_nvkv")))
size_t gsp_validate_nvkv(const uint8_t *bytes, size_t length)
{
    if (length == 0 || length > 65536)
        return 1;

    size_t offset = 0;
    while (offset < length) {
        const size_t entry = offset;
        if (length - offset < 8)
            return entry + 1;

        const uint32_t tag = read_le32(bytes + offset);
        const uint32_t count = read_le32(bytes + offset + 4);
        const uint32_t opcode = tag >> 28;
        offset += 8;
        if (opcode == 0)
            continue;
        if (opcode > 5 || count == 0)
            return entry + 1;
        if (opcode <= 2 && count > 0x10000u - (tag & 0xffffu))
            return entry + 1;

        const size_t width = opcode == 3 ? 1 : (opcode == 1 || opcode == 4 ? 4 : 8);
        const size_t available = (length - offset) & ~(size_t)7;
        if (count > available / width)
            return entry + 1;
        offset += (width * count + 7) & ~(size_t)7;
    }
    return 0;
}
