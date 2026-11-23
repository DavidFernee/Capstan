/*
 * Unit tests for the Capstan runtime (runtime/capstan_rt.h, capstan_gc.h).
 *
 * Cryptographic expectations are published test vectors:
 *   SHA-256       FIPS 180-2 / NIST CAVP examples
 *   HMAC-SHA256   RFC 4231 test cases 1, 2 and 6
 *   PBKDF2-SHA256 RFC 7914 section 11
 */
#include "capstan_rt.h"

static int failures = 0, checks = 0;
static const char *unit_files[] = {"unit"};

#define CHECK(cond) do { checks++; if (!(cond)) { failures++; \
    fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); } } while (0)

static void hexof(const unsigned char *p, size_t n, char *out) { cap_hex(p, n, out); }

static int sha_hex_is(const void *data, size_t n, const char *want) {
    CapSha256 s;
    unsigned char d[32];
    char h[65];
    cap_sha256_init(&s);
    cap_sha256_update(&s, (const unsigned char *)data, n);
    cap_sha256_final(&s, d);
    hexof(d, 32, h);
    return strcmp(h, want) == 0;
}

static void test_sha256(void) {
    CHECK(sha_hex_is("", 0, "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"));
    CHECK(sha_hex_is("abc", 3, "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"));
    const char *m448 = "abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq";
    CHECK(sha_hex_is(m448, strlen(m448), "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1"));
    char *million = (char *)malloc(1000000);
    memset(million, 'a', 1000000);
    CHECK(sha_hex_is(million, 1000000, "cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0"));
    /* the same million bytes fed in uneven pieces */
    CapSha256 s; unsigned char d[32]; char h[65]; size_t off = 0, step = 1;
    cap_sha256_init(&s);
    while (off < 1000000) { size_t n = step > 1000000 - off ? 1000000 - off : step; cap_sha256_update(&s, (unsigned char *)million + off, n); off += n; step = step * 3 % 977 + 1; }
    cap_sha256_final(&s, d); hexof(d, 32, h);
    CHECK(strcmp(h, "cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0") == 0);
    free(million);
    CHECK(strcmp(cap_hash(CAP_LIT("abc", 3))->data, "cap1$sha256$ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad") == 0);
}

static int hmac_is(const void *k, size_t kn, const void *m, size_t mn, const char *want) {
    unsigned char out[32];
    char h[65];
    cap_hmac_sha256((const unsigned char *)k, kn, (const unsigned char *)m, mn, out);
    hexof(out, 32, h);
    return strcmp(h, want) == 0;
}

static void test_hmac(void) {
    unsigned char k1[20], k6[131];
    memset(k1, 0x0b, sizeof k1);
    memset(k6, 0xaa, sizeof k6);
    CHECK(hmac_is(k1, 20, "Hi There", 8, "b0344c61d8db38535ca8afceaf0bf12b881dc200c9833da726e9376c2e32cff7"));
    CHECK(hmac_is("Jefe", 4, "what do ya want for nothing?", 28, "5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843"));
    const char *m6 = "Test Using Larger Than Block-Size Key - Hash Key First";
    CHECK(hmac_is(k6, 131, m6, strlen(m6), "60e431591ee0b67f0d8a26aacbf5b77f8e0bc6213728c5140546040f0ee37f54"));
}

static void test_pbkdf2(void) {
    unsigned char dk[32];
    char h[65];
    cap_pbkdf2("passwd", 6, (const unsigned char *)"salt", 4, 1, dk);
    hexof(dk, 32, h);
    CHECK(strcmp(h, "55ac046e56e3089fec1691c22544b605f94185216dde0465e68b9d57c20dacbc") == 0);
    cap_pbkdf2("Password", 8, (const unsigned char *)"NaCl", 4, 80000, dk);
    hexof(dk, 32, h);
    CHECK(strcmp(h, "4ddcd8f60b98be21830cee5ef22701f9641a4418d04c0414aeff08876b34ab56") == 0);
}

static void test_passwords(void) {
    CapStr *pw = CAP_LIT("correct horse", 13);
    CapStr *h1 = cap_hash_password(pw);
    CapStr *h2 = cap_hash_password(pw);
    CHECK(!cap_str_eq(h1, h2));                         /* random salt */
    CHECK(cap_verify_password(pw, h1));
    CHECK(cap_verify_password(pw, h2));
    CHECK(!cap_verify_password(CAP_LIT("correct horsf", 13), h1));
    CHECK(!cap_needs_rehash(h1));
    CHECK(cap_needs_rehash(CAP_LIT("cap1$pbkdf2-sha256$1000$00$00", 30)));
    CHECK(cap_needs_rehash(CAP_LIT("md5$abc", 7)));
    /* tampering with any field must fail closed */
    CapStr *t = cap_str_new(h1->data, h1->len);
    t->data[t->len - 1] = t->data[t->len - 1] == '0' ? '1' : '0';
    CHECK(!cap_verify_password(pw, t));
    CHECK(!cap_verify_password(pw, CAP_LIT("", 0)));
    CHECK(!cap_verify_password(pw, CAP_LIT("cap1$pbkdf2-sha256$", 19)));
    CHECK(!cap_verify_password(pw, CAP_LIT("cap1$pbkdf2-sha256$0$x$y", 24)));
    CHECK(!cap_verify_password(pw, CAP_LIT("cap1$pbkdf2-sha256$999999999999$00$00", 37)));
    CHECK(!cap_hash_verify(CAP_LIT("abc", 3), CAP_LIT("md5$900150983cd24fb0d6963f7d28e17f72", 36)));
}

static void test_validators(void) {
    int64_t *v;
    v = cap_validate_int(CAP_LIT("9223372036854775807", 19)); CHECK(v && *v == INT64_MAX);
    v = cap_validate_int(CAP_LIT("-9223372036854775808", 20)); CHECK(v && *v == INT64_MIN);
    CHECK(cap_validate_int(CAP_LIT("9223372036854775808", 19)) == NULL);
    CHECK(cap_validate_int(CAP_LIT("-9223372036854775809", 20)) == NULL);
    CHECK(cap_validate_int(CAP_LIT("", 0)) == NULL);
    CHECK(cap_validate_int(CAP_LIT("-", 1)) == NULL);
    CHECK(cap_validate_int(CAP_LIT("+1", 2)) == NULL);
    CHECK(cap_validate_int(CAP_LIT("1 ", 2)) == NULL);
    CHECK(cap_validate_int(CAP_LIT("0x10", 4)) == NULL);
    v = cap_validate_int(CAP_LIT("-0", 2)); CHECK(v && *v == 0);
    CHECK(cap_validate_ident(CAP_LIT("_a9", 3)) != NULL);
    CHECK(cap_validate_ident(CAP_LIT("9a", 2)) == NULL);
    CHECK(cap_validate_ident(CAP_LIT("a-b", 3)) == NULL);
    CHECK(cap_validate_ident(CAP_LIT("", 0)) == NULL);
    CHECK(cap_validate_ident(cap_str_new("a\0b", 3)) == NULL);
    char longid[300]; memset(longid, 'x', 300);
    CHECK(cap_validate_ident(cap_str_new(longid, 256)) == NULL);
    CHECK(cap_validate_ident(cap_str_new(longid, 255)) != NULL);
}

static void test_escapers(void) {
    CHECK(strcmp(cap_escape_html(CAP_LIT("<a href=\"x\">'&'</a>", 19))->data,
                 "&lt;a href=&quot;x&quot;&gt;&#39;&amp;&#39;&lt;/a&gt;") == 0);
    CHECK(strcmp(cap_escape_log(cap_str_new("a\nb\r\x1b[31m\x7f", 10))->data, "a\\x0ab\\x0d\\x1b[31m\\x7f") == 0);
    CHECK(strcmp(cap_escape_c(CAP_LIT("?\?=", 3))->data, "\\?\\?=") == 0);   /* no trigraphs */
    /* every byte value survives escape_c; checked end to end by tests/unit/escape_roundtrip.sh */
    char all[256];
    for (int i = 0; i < 256; i++) all[i] = (char)i;
    CapStr *e = cap_escape_c(cap_str_new(all, 256));
    for (int64_t i = 0; i < e->len; i++) {
        unsigned char c = (unsigned char)e->data[i];
        CHECK(c >= 32 && c < 127);
        if (c == '"') CHECK(i > 0 && e->data[i - 1] == '\\');
    }
}

static void test_collections(void) {
    CapMap *m = cap_map_new();
    for (int i = 0; i < 100000; i++) cap_map_set(m, cap_int_to_str(i), cap_vi(i));
    for (int i = 0; i < 100000; i += 997) cap_map_set(m, cap_int_to_str(i), cap_vi(-i));
    CHECK(m->len == 100000);
    int ok = 1;
    for (int i = 0; i < 100000; i++) {
        int64_t *v = cap_map_get_i(m, cap_int_to_str(i));
        if (!v || *v != (i % 997 == 0 ? -i : i)) ok = 0;
    }
    CHECK(ok);
    CHECK(cap_map_get_i(m, CAP_LIT("nope", 4)) == NULL);
    CapList *keys = cap_map_keys(m);
    CHECK(keys->len == 100000 && cap_str_eq((CapStr *)keys->items[0].p, CAP_LIT("0", 1))
          && cap_str_eq((CapStr *)keys->items[99999].p, CAP_LIT("99999", 5)));
    CapList *l = cap_list_new();
    for (int i = 0; i < 1000; i++) cap_list_push(l, cap_vi(i));
    CHECK(l->len == 1000 && cap_list_get(l, 999, 0).i == 999);
    CapList *parts = cap_list_new();
    cap_list_push(parts, cap_vp(CAP_LIT("a", 1)));
    cap_list_push(parts, cap_vp(CAP_LIT("", 0)));
    cap_list_push(parts, cap_vp(CAP_LIT("c", 1)));
    CHECK(strcmp(cap_join(parts, CAP_LIT("--", 2), 0)->data, "a----c") == 0);
    CHECK(cap_join(cap_list_new(), CAP_LIT(",", 1), 0)->len == 0);
    CHECK(cap_str_slice(CAP_LIT("hello", 5), 5, 5, 0)->len == 0);
}

static void test_arithmetic(void) {
    CHECK(cap_add(INT64_MAX - 1, 1, 0) == INT64_MAX);
    CHECK(cap_sub(INT64_MIN + 1, 1, 0) == INT64_MIN);
    CHECK(cap_mul(-4611686018427387904LL, 2, 0) == INT64_MIN);
    CHECK(cap_div(-7, 2, 0) == -3 && cap_mod(-7, 2, 0) == -1 && cap_mod(7, -2, 0) == 1);
    CHECK(cap_mod(INT64_MIN, -1, 0) == 0);
    CHECK(strcmp(cap_int_to_str(INT64_MIN)->data, "-9223372036854775808") == 0);
    CHECK(cap_ct_eq("abc", 3, "abc", 3) && !cap_ct_eq("abc", 3, "abd", 3) && !cap_ct_eq("abc", 3, "ab", 2));
}

/* The collector must keep objects reachable only through interior pointers,
   large objects, registered globals, and nested structures. */
static CapStr *global_root;
static void test_gc(void) {
    cap_gc_root((void **)&global_root);
    global_root = cap_str_new("global", 6);
    CapStr *s = cap_str_new("interior-pointer", 16);
    char *volatile interior = s->data + 5;
    s = NULL;
    CapList *big = cap_list_new();
    for (int i = 0; i < 10000; i++) cap_list_push(big, cap_vp(cap_int_to_str(i)));
    for (int round = 0; round < 50; round++) {
        for (int i = 0; i < 2000; i++) cap_str_new("garbage garbage garbage", 23);
        cap_gc_collect();
    }
    CHECK(memcmp(interior - 5, "interior-pointer", 16) == 0);
    CHECK(strcmp(global_root->data, "global") == 0);
    int ok = 1;
    for (int i = 0; i < 10000; i++) if (!cap_str_eq((CapStr *)big->items[i].p, cap_int_to_str(i))) ok = 0;
    CHECK(ok);
    size_t before = cap_gc.heap;
    for (int i = 0; i < 200000; i++) cap_str_new("x", 1);
    cap_gc_collect();
    CHECK(cap_gc.heap <= before + (size_t)8 * 65536);   /* garbage is reused, not accumulated */
    CHECK(cap_gc.live < (size_t)4 << 20);
}

/* Collected secrets must be wiped (CWE-244). The test keeps only disguised
   addresses, so the collector cannot see references to the secrets. A conservative
   collector may retain a few through stale register values, so the test creates
   many and requires nearly all to be wiped once collected. */
#define CAP_DISGUISE ((uintptr_t)0x5a5a5a5a5a5a5a5aULL)
#define CAP_NSECRETS 200
static uintptr_t secret_addrs[CAP_NSECRETS];
__attribute__((noinline)) static void make_secrets(void) {
    setenv("CAPSTAN_UNIT_SECRET", "correct-horse-battery-staple", 1);
    for (int i = 0; i < CAP_NSECRETS; i++) {
        CapStr *sec = cap_secret_env(CAP_LIT("CAPSTAN_UNIT_SECRET", 19));
        secret_addrs[i] = (uintptr_t)sec->data ^ CAP_DISGUISE;
    }
    unsetenv("CAPSTAN_UNIT_SECRET");
}
__attribute__((noinline)) static void scrub_stack(int depth) {
    volatile char pad[4096];
    memset((char *)pad, 0, sizeof pad);
    if (depth > 0) scrub_stack(depth - 1);
}
static void test_secret_wipe(void) {
    make_secrets();
    scrub_stack(16);
    for (int i = 0; i < 3; i++) cap_gc_collect();
    int wiped = 0;
    for (int i = 0; i < CAP_NSECRETS; i++) {
        const volatile char *where = (const volatile char *)(secret_addrs[i] ^ CAP_DISGUISE);
        int clean = 1;
        for (int j = 0; j < 28; j++) if (where[j] != 0) clean = 0;
        wiped += clean;
    }
    CHECK(wiped >= CAP_NSECRETS - 4);
}

int main(void) {
    cap_gc_init();
    cap_files = unit_files;
    test_sha256();
    test_hmac();
    test_pbkdf2();
    test_passwords();
    test_validators();
    test_escapers();
    test_collections();
    test_arithmetic();
    test_gc();
    test_secret_wipe();
    printf("runtime unit tests: %d checks, %d failed\n", checks, failures);
    return failures ? 1 : 0;
}
