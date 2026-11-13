#include <stdio.h>
#include <string.h>

typedef struct {
    char *buffer;
    size_t capacity;
    size_t length;
} Output;

static void emit(Output *out, char c) {
    if (out->capacity && out->length < out->capacity - 1) out->buffer[out->length] = c;
    ++out->length;
}

int vsnprintf(char *buffer, size_t capacity, const char *format, va_list args) {
    Output out = {buffer, capacity, 0};
    while (*format) {
        if (*format != '%') {
            emit(&out, *format++);
            continue;
        }
        ++format;
        int left = *format == '-';
        if (left) ++format;
        int zero = *format == '0';
        if (zero) ++format;
        unsigned width = 0;
        while (*format >= '0' && *format <= '9') {
            if (width < 1024) width = width * 10 + *format - '0';
            ++format;
        }
        unsigned precision = (unsigned)-1;
        if (*format == '.') {
            ++format;
            precision = 0;
            while (*format >= '0' && *format <= '9') {
                if (precision < 1024) precision = precision * 10 + *format - '0';
                ++format;
            }
        }
        unsigned longs = 0;
        while (*format == 'l' && longs < 2) { ++longs; ++format; }
        if (!*format) {
            if (capacity) buffer[out.length < capacity ? out.length : capacity - 1] = 0;
            return -1;
        }
        char conversion = *format++;
        char digits[32];
        char *start = digits + sizeof(digits);
        const char *value = start;
        size_t length = 0;
        unsigned leading_zeroes = 0;
        int negative = 0;
        int pointer = conversion == 'p';
        switch (conversion) {
        case '%': case 'c':
            *--start = conversion == '%' ? '%' : (char)va_arg(args, int);
            value = start;
            length = 1;
            break;
        case 's':
            value = va_arg(args, const char *);
            if (!value) value = "(null)";
            while (length < precision && value[length]) ++length;
            break;
        case 'd': case 'i': case 'u': case 'o': case 'x': case 'X': case 'p': {
            unsigned long long number;
            if (pointer) {
                number = (unsigned long)va_arg(args, void *);
            } else if (conversion == 'd' || conversion == 'i') {
                long long n = longs == 2 ? va_arg(args, long long)
                            : longs == 1 ? va_arg(args, long) : va_arg(args, int);
                negative = n < 0;
                number = negative ? -(unsigned long long)n : (unsigned long long)n;
            } else {
                number = longs == 2 ? va_arg(args, unsigned long long)
                       : longs == 1 ? va_arg(args, unsigned long) : va_arg(args, unsigned int);
            }
            unsigned base = conversion == 'o' ? 8 : conversion == 'x' || conversion == 'X' || pointer ? 16 : 10;
            const char *alphabet = conversion == 'X' ? "0123456789ABCDEF" : "0123456789abcdef";
            if (number || precision != 0) {
                do {
                    *--start = alphabet[number % base];
                    ++length;
                    number /= base;
                } while (number);
            }
            if (precision != (unsigned)-1) {
                if (precision > length) leading_zeroes = precision - (unsigned)length;
                zero = 0;
            }
            value = start;
            break;
        }
        default:
            if (capacity) buffer[out.length < capacity ? out.length : capacity - 1] = 0;
            return -1;
        }
        size_t printed = length + leading_zeroes + negative + 2 * pointer;
        unsigned padding = width > printed ? width - (unsigned)printed : 0;
        if (!left && !zero) for (unsigned i = 0; i < padding; ++i) emit(&out, ' ');
        if (negative) emit(&out, '-');
        if (pointer) { emit(&out, '0'); emit(&out, 'x'); }
        if (!left && zero) leading_zeroes += padding;
        for (unsigned i = 0; i < leading_zeroes; ++i) emit(&out, '0');
        for (size_t i = 0; i < length; ++i) emit(&out, value[i]);
        if (left) for (unsigned i = 0; i < padding; ++i) emit(&out, ' ');
    }
    if (capacity) buffer[out.length < capacity ? out.length : capacity - 1] = 0;
    return (int)out.length;
}

int snprintf(char *buffer, size_t capacity, const char *format, ...) {
    va_list args;
    va_start(args, format);
    int length = vsnprintf(buffer, capacity, format, args);
    va_end(args);
    return length;
}

int vfprintf(FILE *stream, const char *format, va_list args) {
    char buffer[512] = {0};
    int length = vsnprintf(buffer, sizeof(buffer), format, args);
    size_t bytes = strlen(buffer);
    return fwrite(buffer, 1, bytes, stream) == bytes ? length : -1;
}

int fprintf(FILE *stream, const char *format, ...) {
    va_list args;
    va_start(args, format);
    int length = vfprintf(stream, format, args);
    va_end(args);
    return length;
}

int printf(const char *format, ...) {
    va_list args;
    va_start(args, format);
    int length = vfprintf(stdout, format, args);
    va_end(args);
    return length;
}
