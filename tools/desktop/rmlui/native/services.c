/* Explicit native services; default disk/environment access is denied. */
#include <errno.h>
#include <stdarg.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <time.h>
#include <wchar.h>
#include "stdio_impl.h"
#include "guest_invoke.h"
static int error_number;
int *__errno_location(void) {return &error_number;}
int *___errno_location(void) {return &error_number;}
size_t __ctype_get_mb_cur_max(void) {return 4;}
static void serial(const char *text) {while(*text) doom_invoke(5,7,(unsigned char)*text++,0);}
_Noreturn void bmo_native_fail(const char *text) {
    serial("BMO UI FAIL: ");serial(text);serial("\n");__asm__ volatile("ud2");__builtin_unreachable();
}
extern size_t bmo_heap_live,bmo_heap_peak;
_Noreturn void bmo_native_oom(size_t requested) {
    size_t values[]={requested,bmo_heap_live,bmo_heap_peak};
    serial("BMO UI OOM request/live/peak:");
    for(size_t i=0;i<3;++i) {char digits[17];for(int n=15;n>=0;--n) {digits[n]="0123456789abcdef"[values[i]&15];values[i]>>=4;}digits[16]=0;serial(" ");serial(digits);}
    serial("\n");bmo_native_fail("bounded C++ heap exhausted");
}
_Noreturn void abort(void) {bmo_native_fail("abort");}
static void (*exit_handlers[128])(void);
static size_t exits;
int atexit(void (*fn)(void)) {if(exits==128)return -1;exit_handlers[exits++]=fn;return 0;}
void bmo_native_exit_handlers(void) {while(exits)exit_handlers[--exits]();}
static uint64_t monotonic_ns;
void bmo_native_clock(uint64_t ns) {if(ns<monotonic_ns)bmo_native_fail("clock reversed");monotonic_ns=ns;}
int clock_gettime(clockid_t id,struct timespec *ts) {
    if(id!=CLOCK_MONOTONIC || !ts) {errno=EINVAL;return -1;}
    ts->tv_sec=monotonic_ns/1000000000;ts->tv_nsec=monotonic_ns%1000000000;return 0;
}
char *getenv(const char *name) {(void)name;return NULL;}
int isatty(int fd) {(void)fd;errno=ENOTTY;return 0;}
int fileno(FILE *f) {(void)f;errno=EBADF;return -1;}
FILE *fopen(const char *path,const char *mode) {(void)path;(void)mode;errno=EACCES;return NULL;}
int fclose(FILE *f) {(void)f;errno=EBADF;return EOF;}
size_t fread(void *p,size_t a,size_t b,FILE *f) {(void)p;(void)a;(void)b;(void)f;errno=EBADF;return 0;}
int fseek(FILE *f,long offset,int whence) {(void)f;(void)offset;(void)whence;errno=EBADF;return -1;}
long ftell(FILE *f) {(void)f;errno=EBADF;return -1;}
char *strerror(int n) {(void)n;return "BMO native service error";}
int __lockfile(FILE *f) {(void)f;bmo_native_fail("threaded FILE");}
void __unlockfile(FILE *f) {(void)f;bmo_native_fail("threaded FILE unlock");}
void __stdio_exit_needed(void) {}
static size_t log_write(FILE *f,const unsigned char *s,size_t n) {
    for(unsigned char *p=f->wbase;p && p<f->wpos;++p)doom_invoke(5,7,*p,0);
    for(size_t i=0;i<n;++i)doom_invoke(5,7,s[i],0);
    f->wpos=f->wbase=f->buf;return n;
}
FILE __stderr_FILE={.lock=-1,.lbf=EOF,.write=log_write};
#undef stderr
FILE *const stderr=&__stderr_FILE;
int fprintf(FILE *f,const char *format,...) {va_list ap;va_start(ap,format);int n=vfprintf(f,format,ap);va_end(ap);return n;}
/* Used by RmlUi's non-security UI effects only. Never a capability source. */
int rand(void) {static uint32_t state=1;state=state*1103515245+12345;return (state>>1)&0x7fffffff;}
