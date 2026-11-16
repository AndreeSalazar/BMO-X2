/* Single-owner Ring 3 heap. No kernel allocator, locks or hidden fallback. */
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
extern _Noreturn void bmo_native_fail(const char *);
typedef struct Block { size_t span; struct Block *next; int available; } Block;
typedef struct User { Block *owner; size_t requested; } User;
_Alignas(64) static unsigned char arena[4*1024*1024];
static Block *head;
size_t bmo_heap_live, bmo_heap_peak;
#define HEADER ((sizeof(Block)+15)&~(size_t)15)

static void *allocate(size_t alignment, size_t bytes) {
    if (!bytes) bytes=1;
    if (alignment<16) alignment=16;
    if ((alignment&(alignment-1)) || alignment>sizeof(arena) || bytes>sizeof(arena)) {
        errno=ENOMEM; return NULL;
    }
    if (!head) {head=(Block *)arena; *head=(Block){sizeof(arena),NULL,1};}
    for (Block *b=head;b;b=b->next) {
        uintptr_t start=(uintptr_t)b+HEADER+sizeof(User);
        uintptr_t payload=(start+alignment-1)&~(uintptr_t)(alignment-1);
        size_t used=((payload-(uintptr_t)b)+bytes+15)&~(size_t)15;
        if (!b->available || used>b->span) continue;
        if (b->span-used>=HEADER+sizeof(User)+16) {
            Block *next=(Block *)((unsigned char *)b+used);
            *next=(Block){b->span-used,b->next,1}; b->span=used;b->next=next;
        }
        b->available=0;
        User *u=(User *)payload-1; *u=(User){b,bytes};
        bmo_heap_live+=b->span;
        if(bmo_heap_live>bmo_heap_peak) bmo_heap_peak=bmo_heap_live;
        return (void *)payload;
    }
    errno=ENOMEM; return NULL;
}
void *malloc(size_t bytes) {return allocate(16,bytes);}
void *aligned_alloc(size_t alignment,size_t bytes) {
    if(!alignment || (alignment&(alignment-1)) || bytes%alignment) {errno=EINVAL;return NULL;}
    return allocate(alignment,bytes);
}
static User *owned(void *p) {
    uintptr_t address=(uintptr_t)p;
    if (address<(uintptr_t)arena+HEADER+sizeof(User) || address>=(uintptr_t)arena+sizeof(arena) || address%16)
        bmo_native_fail("heap pointer");
    User *u=(User *)p-1;
    for(Block *b=head;b;b=b->next) if(b==u->owner && !b->available &&
        address>=(uintptr_t)b+HEADER+sizeof(User) && address<(uintptr_t)b+b->span &&
        u->requested<=(uintptr_t)b+b->span-address) return u;
    bmo_native_fail("heap ownership");
}
void free(void *p) {
    if(!p) return;
    User *u=owned(p); Block *b=u->owner;
    bmo_heap_live-=b->span;b->available=1;
    for(b=head;b && b->next;) {
        if(b->available && b->next->available) {b->span+=b->next->span;b->next=b->next->next;}
        else b=b->next;
    }
}
void *calloc(size_t n,size_t bytes) {
    if(bytes && n>SIZE_MAX/bytes) {errno=ENOMEM;return NULL;}
    void *p=malloc(n*bytes);if(p) memset(p,0,n*bytes);return p;
}
void *realloc(void *p,size_t bytes) {
    if(!p) return malloc(bytes);
    if(!bytes) {free(p);return NULL;}
    User *u=owned(p);
    if(bytes<=u->requested) {u->requested=bytes;return p;}
    void *next=malloc(bytes);
    if(next) {memcpy(next,p,u->requested);free(p);}return next;
}
