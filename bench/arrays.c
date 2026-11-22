#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
int main(void) {
    int64_t n = 5000000, count = 0;
    bool *c = calloc(n + 1, 1);
    for (int64_t p = 2; p <= n; p++) if (!c[p]) { count++; for (int64_t m = p * p; m <= n; m += p) c[m] = true; }
    printf("%lld\n", (long long)count);
    return 0;
}
