/* Same algorithm in idiomatic C: snprintf keys, open-addressing hash table. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
typedef struct { char *k; int64_t v; } E;
static uint64_t h(const char *s) { uint64_t x = 1469598103934665603ULL; while (*s) { x ^= (unsigned char)*s++; x *= 1099511628211ULL; } return x; }
int main(void) {
    size_t cap = 16384; E *t = calloc(cap, sizeof(E)); size_t n = 0;
    char buf[32];
    for (int64_t i = 0; i < 2000000; i++) {
        snprintf(buf, sizeof buf, "w%lld", (long long)(i % 5003));
        size_t s = h(buf) & (cap - 1);
        while (t[s].k && strcmp(t[s].k, buf)) s = (s + 1) & (cap - 1);
        if (t[s].k) t[s].v++; else { t[s].k = strdup(buf); t[s].v = 1; n++; }
    }
    int64_t total = 0;
    for (size_t s = 0; s < cap; s++) if (t[s].k) total += t[s].v;
    printf("%zu %lld\n", n, (long long)total);
    return 0;
}
