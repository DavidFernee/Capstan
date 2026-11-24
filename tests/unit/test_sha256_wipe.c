/*
 * Focused regression test for SHA-256 compression scratch erasure.
 *
 * The observer is compiled only into this test translation unit. It reads
 * each scratch region through volatile bytes immediately after cap_wipe().
 * The normal runtime has no observer call or additional runtime behaviour.
 */
#define CAP_SHA256_TEST_HOOK 1
#include "capstan_rt.h"

static unsigned observer_calls;
static unsigned observer_bytes;
static unsigned observer_nonzero;

void cap_sha256_test_wipe_observer(const volatile void *p, size_t n) {
    const volatile unsigned char *bytes = (const volatile unsigned char *)p;
    observer_calls++;
    observer_bytes += (unsigned)n;
    for (size_t i = 0; i < n; i++) {
        if (bytes[i] != 0) observer_nonzero++;
    }
}

int main(void) {
    CapSha256 state;
    unsigned char block[64] = {0};

    cap_sha256_init(&state);
    cap_sha256_block(&state, block);

    /* One compression call wipes w[64] plus eight uint32_t working words. */
    if (observer_calls != 9) return 1;
    if (observer_bytes != 64u * sizeof(uint32_t) + 8u * sizeof(uint32_t)) return 2;
    if (observer_nonzero != 0) return 3;

    return 0;
}
