#include <stdio.h>
#include <stdint.h>
static int64_t leaf(int64_t i) { return (i * 7 + 3) % 11; }
static int64_t split_sum(int64_t lo, int64_t hi) {
    if (hi - lo == 1) return leaf(lo);
    int64_t mid = lo + (hi - lo) / 2;
    return split_sum(lo, mid) + split_sum(mid, hi);
}
int main(void) { printf("%lld\n", (long long)split_sum(0, 16777216)); return 0; }
