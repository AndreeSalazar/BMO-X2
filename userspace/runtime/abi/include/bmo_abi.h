#ifndef BMO_ABI_H
#define BMO_ABI_H

#define BMO_ABI_VERSION 1
#define BMO_INVOKE 0
#define BMO_WAIT 1
#define BMO_OP_ECHO 1

typedef unsigned long long bmo_word;
typedef struct {
    long long status;
    bmo_word value;
} bmo_result;

enum {
    BMO_OK = 0,
    BMO_BAD_GATE = -1,
    BMO_BAD_CAP = -2,
    BMO_BAD_ARG = -3,
    BMO_NOT_READY = -4,
    BMO_BAD_OP = -5,
    BMO_TIMED_OUT = -6
};

#ifdef __cplusplus
extern "C" {
#endif
bmo_result bmo_invoke(bmo_word capability, bmo_word operation, bmo_word arg0,
                      bmo_word arg1, bmo_word arg2);
bmo_result bmo_wait(bmo_word capability, bmo_word sequence, bmo_word deadline);
#ifdef __cplusplus
}
#endif

#endif
