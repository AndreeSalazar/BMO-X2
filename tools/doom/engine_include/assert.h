#ifndef BMO_DOOM_ASSERT_H
#define BMO_DOOM_ASSERT_H
#define assert(condition) ((condition) ? (void)0 : __builtin_trap())
#endif
