#include "../../userspace/runtime/abi/include/bmo_abi.h"

unsigned long long bmo_session_tick_ms(void);

volatile unsigned long long phase = 0x424d4f58;
volatile unsigned long long first_ms;
volatile unsigned long long second_ms;
static const unsigned char text[] = "BMO-X2";
volatile unsigned long long index = 1;
volatile unsigned char scratch[6000];

void bmo_main(void) {
    if (first_ms || second_ms || scratch[5999]) for (;;) {}
    scratch[index & 3] = text[index & 3];
    first_ms = bmo_session_tick_ms();
    bmo_wait(2, 1, 3);
    second_ms = bmo_session_tick_ms();
    if (second_ms >= first_ms + 20 && scratch[1] == 'M')
        phase = 0x53454332;
    for (;;) {}
}
