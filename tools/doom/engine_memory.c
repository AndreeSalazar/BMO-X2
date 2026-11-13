#include <stdint.h>
#include <stdlib.h>
#include <string.h>

typedef struct Block Block;
struct Block {
    size_t bytes;
    Block *next;
    int available;
};

_Alignas(16) static unsigned char arena[8 * 1024 * 1024];
static Block *head;
#define HEADER ((sizeof(Block) + 15u) & ~(size_t)15u)

void *memcpy(void *destination, const void *source, size_t bytes) {
    unsigned char *out = destination;
    const unsigned char *in = source;
    while (bytes--) *out++ = *in++;
    return destination;
}

void *memset(void *destination, int value, size_t bytes) {
    unsigned char *out = destination;
    while (bytes--) *out++ = (unsigned char)value;
    return destination;
}

void *malloc(size_t bytes) {
    if (!bytes || bytes > sizeof(arena) - HEADER) return NULL;
    bytes = (bytes + 15u) & ~(size_t)15u;
    if (!head) {
        head = (Block *)arena;
        *head = (Block){sizeof(arena) - HEADER, NULL, 1};
    }
    for (Block *block = head; block; block = block->next) {
        if (!block->available || block->bytes < bytes) continue;
        unsigned char *payload = (unsigned char *)block + HEADER;
        if (block->bytes - bytes >= HEADER + 16) {
            Block *tail = (Block *)(payload + bytes);
            *tail = (Block){block->bytes - bytes - HEADER, block->next, 1};
            block->next = tail;
            block->bytes = bytes;
        }
        block->available = 0;
        return payload;
    }
    return NULL;
}

void free(void *payload) {
    if (!payload) return;
    Block *block = (Block *)((unsigned char *)payload - HEADER);
    block->available = 1;
    for (Block *current = head; current && current->next;) {
        Block *next = current->next;
        if (current->available && next->available) {
            current->bytes += HEADER + next->bytes;
            current->next = next->next;
        } else {
            current = next;
        }
    }
}

void *calloc(size_t count, size_t bytes) {
    if (bytes && count > SIZE_MAX / bytes) return NULL;
    void *payload = malloc(count * bytes);
    if (payload) memset(payload, 0, count * bytes);
    return payload;
}

void *realloc(void *payload, size_t bytes) {
    if (!payload) return malloc(bytes);
    if (!bytes) {
        free(payload);
        return NULL;
    }
    Block *block = (Block *)((unsigned char *)payload - HEADER);
    if (bytes <= block->bytes) return payload;
    void *replacement = malloc(bytes);
    if (replacement) {
        memcpy(replacement, payload, block->bytes);
        free(payload);
    }
    return replacement;
}
