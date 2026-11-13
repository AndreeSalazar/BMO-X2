#include <stdio.h>

#include "guest_invoke.h"

struct BmoFile {
    unsigned long length;
    unsigned long position;
    int open;
    int eof;
};

/* The initial profile grants a single read-only IWAD handle. */
static FILE wad_file;

static int equal(const char *left, const char *right) {
    while (*left == *right && *left) {
        ++left;
        ++right;
    }
    return *left == *right;
}

FILE *fopen(const char *name, const char *mode) {
    if (wad_file.open || (!equal(name, "doom1.wad") && !equal(name, "./doom1.wad")) ||
            (!equal(mode, "rb") && !equal(mode, "r"))) {
        return NULL;
    }
    unsigned long length = doom_invoke(4, 5, 0, 0);
    if (length < 12 || length > 0x1000000) {
        return NULL;
    }
    wad_file = (FILE){.length = length, .open = 1};
    return &wad_file;
}

int fclose(FILE *stream) {
    if (stream != &wad_file || !stream->open) {
        return EOF;
    }
    stream->open = 0;
    return 0;
}

int fseek(FILE *stream, long offset, int origin) {
    if (stream != &wad_file || !stream->open) {
        return -1;
    }
    long base;
    switch (origin) {
    case SEEK_SET: base = 0; break;
    case SEEK_CUR: base = (long)stream->position; break;
    case SEEK_END: base = (long)stream->length; break;
    default: return -1;
    }
    if (offset < -base || offset > (long)stream->length - base) {
        return -1;
    }
    stream->position = (unsigned long)(base + offset);
    stream->eof = 0;
    return 0;
}

long ftell(FILE *stream) {
    return stream == &wad_file && stream->open ? (long)stream->position : -1;
}

size_t fread(void *buffer, size_t size, size_t count, FILE *stream) {
    if (stream != &wad_file || !stream->open || !size || !count) {
        return 0;
    }
    unsigned long available = stream->length - stream->position;
    int short_read = count > available / size;
    size_t bytes = short_read ? available : size * count;
    unsigned char *out = buffer;
    size_t copied = 0;
    while (copied < bytes) {
        unsigned long offset = stream->position;
        if (offset > stream->length - 4) {
            offset = stream->length - 4;
        }
        unsigned long word = doom_invoke(4, 4, offset, 0);
        if (word == ~0ul) {
            break;
        }
        for (unsigned long i = stream->position - offset; i < 4 && copied < bytes; ++i) {
            out[copied++] = (unsigned char)(word >> (i * 8));
            ++stream->position;
        }
    }
    stream->eof |= short_read && copied == bytes;
    return copied / size;
}

int feof(FILE *stream) {
    return stream == &wad_file && stream->open && stream->eof;
}
