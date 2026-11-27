#pragma once

#include <stdint.h>

namespace BmoNvidia {
// This is a serial transport for the bounded, read-only diagnostic capability.
inline constexpr unsigned trace_bytes = 17 * 4096;
inline constexpr unsigned trace_selector = 17;
inline constexpr unsigned row_bytes = 64;

struct InitReceipt {
    uint32_t revision, link, pcie, console, cl, crc;
};

template<typename Read>
bool read_init_receipt(Read read, InitReceipt& receipt) {
    constexpr unsigned selector = 0x2400;
    constexpr unsigned words = 544 / 8;
    if (read(selector) != words * 8) return false;
    uint64_t frame[words];
    uint32_t crc = 0xffffffffu;
    for (unsigned index = 0; index < words; ++index) {
        auto value = frame[index] = read(selector + 1 + index);
        for (unsigned byte = 0; byte < 8; ++byte, value >>= 8) {
            crc ^= static_cast<uint8_t>(value);
            for (unsigned bit = 0; bit < 8; ++bit) {
                crc = (crc >> 1) ^ (0xedb88320u & (0u - (crc & 1u)));
            }
        }
    }
    if (uint32_t(frame[10]) != 3 || uint32_t(frame[32]) != 0x52 ||
        frame[41] != 0x120001000ull || frame[23] != 0x120001031ull ||
        frame[42] >> 32 || frame[24] >> 32 ||
        frame[66] != 0x120001033ull || frame[67] >> 32) return false;
    receipt = {uint32_t(frame[10] >> 32), uint32_t(frame[32] >> 32),
               uint32_t(frame[42]), uint32_t(frame[24]), uint32_t(frame[67]), crc ^ 0xffffffffu};
    return true;
}

template<typename Read, typename Write>
void export_gsp_trace(Read read, Write write) {
    constexpr char hex[] = "0123456789ABCDEF";
    uint32_t crc = 0xffffffffu;
    write("BMO_GSP_BEGIN=1 11000\n");
    for (unsigned offset = 0; offset < trace_bytes; offset += row_bytes) {
        char line[5 + 5 + 1 + row_bytes * 2 + 2] = {'G', 'S', 'P', 'D', '='};
        for (unsigned digit = 0; digit < 5; ++digit) {
            line[5 + digit] = hex[(offset >> ((4 - digit) * 4)) & 15];
        }
        line[10] = ':';
        for (unsigned word = 0; word < row_bytes / 8; ++word) {
            auto value = read(trace_selector + offset / 8 + word);
            for (unsigned byte = 0; byte < 8; ++byte, value >>= 8) {
                const auto pos = 11 + word * 16 + byte * 2;
                line[pos] = hex[(value >> 4) & 15];
                line[pos + 1] = hex[value & 15];
                crc ^= static_cast<uint8_t>(value);
                for (unsigned bit = 0; bit < 8; ++bit) {
                    crc = (crc >> 1) ^ (0xedb88320u & (0u - (crc & 1u)));
                }
            }
        }
        line[sizeof(line) - 2] = '\n';
        write(line);
    }
    char end[] = "BMO_GSP_END=1 11000 00000000\n";
    crc ^= 0xffffffffu;
    for (unsigned digit = 0; digit < 8; ++digit) {
        end[sizeof(end) - 10 + digit] = hex[(crc >> ((7 - digit) * 4)) & 15];
    }
    write(end);
}
}
