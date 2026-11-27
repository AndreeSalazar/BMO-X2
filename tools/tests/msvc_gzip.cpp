#include "../../userspace/runtime/abi/include/bmo_abi.h"
#include "zlib.h"

extern "C" {
__declspec(dllimport) void* GetProcessHeap(void);
__declspec(dllimport) void* HeapAlloc(void*, unsigned long, size_t);
__declspec(dllimport) int HeapFree(void*, unsigned long, void*);
__declspec(dllimport) void* CreateFileW(const wchar_t*, unsigned long, unsigned long,
                                      void*, unsigned long, unsigned long, void*);
__declspec(dllimport) int ReadFile(void*, void*, unsigned long, unsigned long*, void*);
__declspec(dllimport) int CloseHandle(void*);
__declspec(dllimport) unsigned long GetLastError(void);
__declspec(dllimport) void* GetStdHandle(unsigned long);
__declspec(dllimport) int WriteFile(void*, const void*, unsigned long, unsigned long*, void*);
void* memset(void*, int, size_t);
#ifdef BMO_MINIGZIP_CLI
const char* bmo_package_argv(size_t*);
#endif
}

#ifdef _MSC_VER
#pragma function(memset)
#endif
extern "C" void* memset(void* destination, int value, size_t size) {
    auto* bytes = static_cast<volatile unsigned char*>(destination);
    for (size_t index = 0; index < size; ++index) {
        bytes[index] = static_cast<unsigned char>(value);
    }
    return destination;
}

namespace {
constexpr unsigned long buffer_limit = 4096;
constexpr unsigned window_bits = 15;

struct Output {
    unsigned char* bytes;
    unsigned long size;
};

voidpf allocate(voidpf heap, uInt count, uInt size) {
    return HeapAlloc(heap, 8, static_cast<size_t>(count) * size);
}

void release(voidpf heap, voidpf block) {
    HeapFree(heap, 0, block);
}

unsigned no_more_input(void*, z_const unsigned char**) {
    return 0;
}

int append(void* output, unsigned char* data, unsigned count) {
    auto& sink = *static_cast<Output*>(output);
    if (count > buffer_limit - sink.size) return 1;
    for (unsigned index = 0; index < count; ++index) {
        static_cast<volatile unsigned char*>(sink.bytes)[sink.size + index] = data[index];
    }
    sink.size += count;
    return 0;
}

unsigned long word(const unsigned char* bytes) {
    return static_cast<unsigned long>(bytes[0]) |
        (static_cast<unsigned long>(bytes[1]) << 8) |
        (static_cast<unsigned long>(bytes[2]) << 16) |
        (static_cast<unsigned long>(bytes[3]) << 24);
}

unsigned long crc32_gzip(const Output& output) {
    unsigned long crc = 0xffffffff;
    for (unsigned long index = 0; index < output.size; ++index) {
        crc ^= output.bytes[index];
        for (unsigned bit = 0; bit < 8; ++bit) {
            crc = (crc >> 1) ^ (0xedb88320 & (0ul - (crc & 1)));
        }
    }
    return crc ^ 0xffffffff;
}

bool gunzip(void* heap, unsigned char* input, unsigned long size, unsigned char* window, Output& output) {
    // This probe consumes a single gzip member with no optional header fields.
    if (size < 18 || input[0] != 0x1f || input[1] != 0x8b || input[2] != 8 || input[3] != 0) return false;
    z_stream stream{};
    stream.zalloc = allocate;
    stream.zfree = release;
    stream.opaque = heap;
    stream.next_in = input + 10;
    stream.avail_in = size - 18;
    if (inflateBackInit(&stream, window_bits, window) != Z_OK) return false;
    output.size = 0;
    int result = inflateBack(&stream, no_more_input, nullptr, append, &output);
    bool consumed = stream.avail_in == 0;
    bool released = inflateBackEnd(&stream) == Z_OK;
    return result == Z_STREAM_END && consumed && released &&
        output.size == word(input + size - 4) && crc32_gzip(output) == word(input + size - 8);
}

bool gzip(void* heap, const Output& input, Output& output, int level = 6) {
    z_stream stream{};
    stream.zalloc = allocate;
    stream.zfree = release;
    stream.opaque = heap;
    // A 1 KiB window and memLevel 1 keep zlib inside the 64 KiB fixture heap.
    if (deflateInit2(&stream, level, Z_DEFLATED, 16 + 10, 1, Z_DEFAULT_STRATEGY) != Z_OK) return false;
    stream.next_in = input.bytes;
    stream.avail_in = input.size;
    stream.next_out = output.bytes;
    stream.avail_out = buffer_limit;
    const int result = deflate(&stream, Z_FINISH);
    const bool consumed = stream.avail_in == 0;
    output.size = buffer_limit - stream.avail_out;
    const bool released = deflateEnd(&stream) == Z_OK;
    return result == Z_STREAM_END && consumed && released;
}

#ifndef BMO_MINIGZIP_CLI
bool persist(const Output& output, unsigned char* recovered) {
    constexpr unsigned long generic_read = 0x80000000, generic_write = 0x40000000;
    constexpr unsigned long create_always = 2, open_existing = 3;
    const auto invalid = reinterpret_cast<void*>(static_cast<size_t>(-1));
    auto open = [](unsigned long access, unsigned long disposition) {
        return CreateFileW(L"output.bin", access, 1, nullptr, disposition, 0, nullptr);
    };
    if (open(generic_read, open_existing) != invalid || GetLastError() != 2) return false;
    void* file = open(generic_write, create_always);
    unsigned long count = 0;
    const auto half = output.size / 2;
    if (file == invalid || !WriteFile(file, output.bytes, half, &count, nullptr) || count != half ||
        WriteFile(file, output.bytes, buffer_limit + 1, &count, nullptr) || count || GetLastError() != 112 ||
        !WriteFile(file, output.bytes + half, output.size - half, &count, nullptr) ||
        count != output.size - half || !CloseHandle(file) ||
        WriteFile(file, output.bytes, 1, &count, nullptr) || count || GetLastError() != 6) return false;
    file = open(generic_read, open_existing);
    if (file == invalid || WriteFile(file, output.bytes, 1, &count, nullptr) || count || GetLastError() != 5 ||
        !ReadFile(file, recovered, buffer_limit, &count, nullptr) || count != output.size ||
        !ReadFile(file, recovered, 1, &count, nullptr) || count || !CloseHandle(file)) return false;
    for (unsigned long index = 0; index < output.size; ++index) {
        if (recovered[index] != output.bytes[index]) return false;
    }
    file = open(generic_write, create_always);
    if (file == invalid || !CloseHandle(file)) return false;
    file = open(generic_read, open_existing);
    return file != invalid && ReadFile(file, recovered, 1, &count, nullptr) && !count && CloseHandle(file);
}
#endif

bool read_input(Output& input) {
    void* file = CreateFileW(L"input.bin", 0x80000000, 1, nullptr, 3, 0, nullptr);
    if (file == reinterpret_cast<void*>(static_cast<size_t>(-1))) return false;
    unsigned char extra = 0;
    unsigned long count = 0;
    const bool read = ReadFile(file, input.bytes, buffer_limit, &input.size, nullptr);
    const bool eof = read && ReadFile(file, &extra, 1, &count, nullptr) && count == 0;
    return CloseHandle(file) && eof;
}

bool write_stdout(const Output& output) {
    unsigned long written = 0;
    return WriteFile(GetStdHandle(static_cast<unsigned long>(-11)), output.bytes, output.size,
                     &written, nullptr) && written == output.size;
}

#ifndef BMO_MINIGZIP_CLI
int run_gzip() {
    void* heap = GetProcessHeap();
    auto* input = static_cast<unsigned char*>(HeapAlloc(heap, 0, buffer_limit));
    auto* decoded = static_cast<unsigned char*>(HeapAlloc(heap, 0, buffer_limit));
    auto* window = static_cast<unsigned char*>(HeapAlloc(heap, 0, 1u << window_bits));
    if (!input || !decoded || !window) return 1;
    Output source{input, 0};
    if (!read_input(source)) return 3;
    const auto size = source.size;
    Output output{decoded, 0};
    if (!gunzip(heap, input, size, window, output)) return 4;
    input[size - 8] ^= 1;
    if (gunzip(heap, input, size, window, output)) return 5;
    if (!HeapFree(heap, 0, window)) return 7;
    Output compressed{input, 0};
    if (!gzip(heap, output, compressed)) return 8;
    if (!persist(compressed, decoded)) return 9;
    if (!write_stdout({decoded, compressed.size})) return 6;
    return HeapFree(heap, 0, decoded) && HeapFree(heap, 0, input) ? 0 : 7;
}
#else
bool equals(const char* first, const char* second) {
    while (*first && *first == *second) {
        ++first;
        ++second;
    }
    return *first == *second;
}

#ifdef BMO_MINIGZIP_DISK
#ifdef BMO_MINIGZIP_FAT
#include "msvc_gzip_fat.h"
#else
constexpr bmo_word disk_signature = 0x314f4d42;
constexpr unsigned disk_payload_limit = 504;

bool write_disk(const Output& output, bool) {
    if (output.size > disk_payload_limit) return false;
    const bmo_word header = disk_signature | (static_cast<bmo_word>(output.size) << 32);
    if (bmo_invoke(4, 3, header, 0, 0).status) return false;
    for (unsigned word_index = 1; word_index < 64; ++word_index) {
        bmo_word value = 0;
        for (unsigned byte = 0; byte < 8; ++byte) {
            const unsigned offset = (word_index - 1) * 8 + byte;
            if (offset < output.size) value |= static_cast<bmo_word>(output.bytes[offset]) << (8 * byte);
        }
        if (bmo_invoke(4, 3, value, word_index, 0).status) return false;
    }
    return bmo_invoke(4, 4, 1, 0, 0).status == BMO_OK;
}

bool read_disk(Output& input) {
    if (bmo_invoke(4, 4, 0, 0, 0).status) return false;
    const auto header = bmo_invoke(4, 5, 0, 0, 0);
    input.size = static_cast<unsigned long>(header.value >> 32);
    if (header.status || static_cast<unsigned long>(header.value) != disk_signature ||
        input.size < 18 || input.size > disk_payload_limit) return false;
    for (unsigned offset = 0; offset < input.size; offset += 8) {
        const auto block = bmo_invoke(4, 5, 0, offset / 8 + 1, 0);
        if (block.status) return false;
        for (unsigned byte = 0; byte < 8 && offset + byte < input.size; ++byte) {
            input.bytes[offset + byte] = static_cast<unsigned char>(block.value >> (8 * byte));
        }
    }
    return true;
}
#endif

int disk_main(bool reading, bool replace = false) {
    void* heap = GetProcessHeap();
    Output input{static_cast<unsigned char*>(HeapAlloc(heap, 0, buffer_limit)), 0};
    Output output{static_cast<unsigned char*>(HeapAlloc(heap, 0, buffer_limit)), 0};
    bool ok = input.bytes && output.bytes;
    if (ok && reading) {
        auto* window = static_cast<unsigned char*>(HeapAlloc(heap, 0, 1u << window_bits));
        ok = window && read_disk(input) && gunzip(heap, input.bytes, input.size, window, output)
            && write_stdout(output);
        ok = HeapFree(heap, 0, window) && ok;
    } else if (ok) {
        ok = read_input(input) && gzip(heap, input, output, 9) && write_disk(output, replace);
    }
    const bool freed_input = HeapFree(heap, 0, input.bytes);
    const bool freed_output = HeapFree(heap, 0, output.bytes);
    return ok && freed_input && freed_output ? 0 : 1;
}
#endif

int minigzip_main(size_t argc, const char* const* argv) {
#ifdef BMO_MINIGZIP_DISK
    if (argc == 2 && equals(argv[1], "--disk-write")) return disk_main(false);
    if (argc == 2 && equals(argv[1], "--disk-read")) return disk_main(true);
#ifdef BMO_MINIGZIP_FAT
    if (argc == 2 && equals(argv[1], "--disk-replace")) return disk_main(false, true);
#endif
#endif
    bool decode = false, copyout = false;
    int level = 6;
    for (size_t index = 1; index < argc; ++index) {
        const char* option = argv[index];
        if (equals(option, "-c")) copyout = true;
        else if (equals(option, "-d")) decode = true;
        else if (option[0] == '-' && option[1] >= '1' && option[1] <= '9' && !option[2]) {
            level = option[1] - '0';
        } else if (!equals(option, "input.bin") || index + 1 != argc) {
            return 2;
        }
    }
    if (!copyout) return 2;

    void* heap = GetProcessHeap();
    Output input{static_cast<unsigned char*>(HeapAlloc(heap, 0, buffer_limit)), 0};
    Output output{static_cast<unsigned char*>(HeapAlloc(heap, 0, buffer_limit)), 0};
    bool ok = input.bytes && output.bytes && read_input(input);
    if (ok && decode) {
        auto* window = static_cast<unsigned char*>(HeapAlloc(heap, 0, 1u << window_bits));
        ok = window && gunzip(heap, input.bytes, input.size, window, output);
        ok = HeapFree(heap, 0, window) && ok;
    } else if (ok) {
        ok = gzip(heap, input, output, level);
    }
    if (ok) ok = write_stdout(output);
    const bool freed_input = HeapFree(heap, 0, input.bytes);
    const bool freed_output = HeapFree(heap, 0, output.bytes);
    return ok && freed_input && freed_output ? 0 : 1;
}

int run_gzip() {
    const char* argv[8];
    size_t size = 0, argc = 0;
    const char* cursor = bmo_package_argv(&size);
    const char* end = cursor + size;
    while (cursor != end && argc < sizeof(argv) / sizeof(*argv)) {
        argv[argc++] = cursor;
        while (cursor != end && *cursor) ++cursor;
        if (cursor == end) return 2;
        ++cursor;
    }
    return argc && cursor == end && equals(argv[0], "minigzip") ? minigzip_main(argc, argv) : 2;
}
#endif
}

extern "C" void bmo_main(void) {
    bmo_invoke(4, 2, run_gzip(), 0, 0);
}
