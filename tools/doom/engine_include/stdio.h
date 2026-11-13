#ifndef BMO_DOOM_STDIO_H
#define BMO_DOOM_STDIO_H
#include <stddef.h>
#include <stdarg.h>
typedef struct BmoFile FILE;
extern FILE *stdin, *stdout, *stderr;
#define EOF (-1)
#define SEEK_SET 0
#define SEEK_CUR 1
#define SEEK_END 2
FILE *fopen(const char *, const char *);
int fclose(FILE *);
int fflush(FILE *);
int feof(FILE *);
int fileno(FILE *);
int fseek(FILE *, long, int);
long ftell(FILE *);
size_t fread(void *, size_t, size_t, FILE *);
size_t fwrite(const void *, size_t, size_t, FILE *);
int printf(const char *, ...);
int puts(const char *);
int putchar(int);
int fprintf(FILE *, const char *, ...);
int vfprintf(FILE *, const char *, va_list);
int snprintf(char *, size_t, const char *, ...);
int vsnprintf(char *, size_t, const char *, va_list);
int fscanf(FILE *, const char *, ...);
int sscanf(const char *, const char *, ...);
int remove(const char *);
int rename(const char *, const char *);
#endif
