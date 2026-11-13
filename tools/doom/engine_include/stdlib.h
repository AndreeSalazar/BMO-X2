#ifndef BMO_DOOM_STDLIB_H
#define BMO_DOOM_STDLIB_H
#include <stddef.h>
void *malloc(size_t);
void *calloc(size_t, size_t);
void *realloc(void *, size_t);
void free(void *);
_Noreturn void exit(int);
char *getenv(const char *);
int atoi(const char *);
double atof(const char *);
long strtol(const char *, char **, int);
unsigned long strtoul(const char *, char **, int);
int abs(int);
int system(const char *);
#endif
