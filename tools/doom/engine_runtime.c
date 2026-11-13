#include <ctype.h>
#include <errno.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <sys/stat.h>

#include "guest_invoke.h"

int errno;
static char console[2];
FILE *stdout = (FILE *)&console[0];
FILE *stderr = (FILE *)&console[1];

int toupper(int c) { return c >= 'a' && c <= 'z' ? c - 'a' + 'A' : c; }
int abs(int n) { return n < 0 ? -n : n; }
double fabs(double n) { return __builtin_fabs(n); }

static int space(int c) { return c == ' ' || (c >= '\t' && c <= '\r'); }
static int digit(int c) {
    if (c >= '0' && c <= '9') return c - '0';
    c = toupper(c);
    return c >= 'A' && c <= 'F' ? c - 'A' + 10 : 16;
}

static unsigned long integer(const char **input, int base) {
    const char *s = *input;
    while (space(*s)) ++s;
    int negative = *s == '-';
    if (*s == '-' || *s == '+') ++s;
    if (!base) base = *s == '0' ? 8 : 10;
    if ((base == 8 || base == 16) && *s == '0' && toupper(s[1]) == 'X') {
        base = 16;
        s += 2;
    }
    const char *first = s;
    unsigned long value = 0;
    while (digit(*s) < base) value = value * base + digit(*s++);
    if (s != first) *input = s;
    return negative ? -value : value;
}

int atoi(const char *s) { return (int)integer(&s, 10); }
double atof(const char *s) {
    while (space(*s)) ++s;
    int negative = *s == '-';
    if (*s == '-' || *s == '+') ++s;
    double value = 0;
    while (digit(*s) < 10) value = value * 10 + digit(*s++);
    if (*s == '.') {
        double fraction = 0.1;
        for (++s; digit(*s) < 10; ++s, fraction *= 0.1) value += digit(*s) * fraction;
    }
    return negative ? -value : value;
}

int sscanf(const char *input, const char *format, ...) {
    while (*format && *format != '%') {
        if (space(*format)) {
            while (space(*input)) ++input;
        } else if (*input++ != *format) {
            return 0;
        }
        ++format;
    }
    if (!*format) return 0;
    char conversion = *++format;
    int base;
    switch (conversion) {
    case 'd': base = 10; break;
    case 'i': base = 0; break;
    case 'o': base = 8; break;
    case 'x': base = 16; break;
    default: return 0;
    }
    const char *start = input;
    unsigned long value = integer(&input, base);
    if (input == start) return 0;
    va_list args;
    va_start(args, format);
    if (conversion == 'd' || conversion == 'i') *va_arg(args, int *) = (int)value;
    else *va_arg(args, unsigned int *) = (unsigned int)value;
    va_end(args);
    return 1;
}

size_t strlen(const char *s) {
    const char *end = s;
    while (*end) ++end;
    return end - s;
}
char *strchr(const char *s, int c) {
    do {
        if ((unsigned char)*s == (unsigned char)c) return (char *)s;
    } while (*s++);
    return NULL;
}
char *strrchr(const char *s, int c) {
    const char *last = NULL;
    do {
        if ((unsigned char)*s == (unsigned char)c) last = s;
    } while (*s++);
    return (char *)last;
}
int strncmp(const char *a, const char *b, size_t n) {
    while (n && *a && *a == *b) { ++a; ++b; --n; }
    return n ? (unsigned char)*a - (unsigned char)*b : 0;
}
int strcmp(const char *a, const char *b) { return strncmp(a, b, (size_t)-1); }
int strncasecmp(const char *a, const char *b, size_t n) {
    while (n && *a && toupper(*a) == toupper(*b)) { ++a; ++b; --n; }
    return n ? toupper((unsigned char)*a) - toupper((unsigned char)*b) : 0;
}
int strcasecmp(const char *a, const char *b) { return strncasecmp(a, b, (size_t)-1); }
char *strstr(const char *s, const char *needle) {
    size_t n = strlen(needle);
    do {
        if (!strncmp(s, needle, n)) return (char *)s;
    } while (*s++);
    return NULL;
}
char *strncpy(char *out, const char *s, size_t n) {
    size_t i = 0;
    for (; i < n && s[i]; ++i) out[i] = s[i];
    for (; i < n; ++i) out[i] = 0;
    return out;
}
char *strdup(const char *s) {
    size_t n = strlen(s) + 1;
    char *copy = malloc(n);
    return copy ? memcpy(copy, s, n) : NULL;
}

int putchar(int c) {
    return doom_invoke(5, 7, (unsigned char)c, 0) ? EOF : (unsigned char)c;
}
int puts(const char *s) {
    while (*s) if (putchar(*s++) == EOF) return EOF;
    return putchar('\n');
}
int fflush(FILE *stream) { return !stream || stream == stdout || stream == stderr ? 0 : EOF; }
size_t fwrite(const void *data, size_t bytes, size_t count, FILE *stream) {
    if (!bytes || (stream != stdout && stream != stderr)) return 0;
    const unsigned char *s = data;
    size_t done = 0;
    for (; done < count; ++done) {
        for (size_t i = 0; i < bytes; ++i) if (putchar(*s++) == EOF) return done;
    }
    return done;
}
int mkdir(const char *path, unsigned mode) { (void)path; (void)mode; errno = ENOENT; return -1; }
int remove(const char *path) { (void)path; errno = ENOENT; return -1; }
int rename(const char *a, const char *b) { (void)b; return remove(a); }
int system(const char *command) { return command ? -1 : 0; }
_Noreturn void exit(int code) {
    fprintf(stderr, "\nBMO DOOM EXIT %d\n", code);
    extern void DG_SleepMs(unsigned int);
    for (;;) DG_SleepMs(1000);
}
