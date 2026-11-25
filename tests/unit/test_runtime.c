/*
 * Unit tests for the Capstan runtime (runtime/capstan_rt.h, capstan_gc.h).
 *
 * Cryptographic expectations are published test vectors:
 *   SHA-256       FIPS 180-2 / NIST CAVP examples
 *   HMAC-SHA256   RFC 4231 test cases 1, 2 and 6
 *   PBKDF2-SHA256 RFC 7914 section 11
 */
#define CAP_GC_TESTING 1
#define CAP_PBKDF2_TEST_HOOK 1
#define CAP_SECRET_SCRATCH_TEST_HOOK 1
#define CAP_SIPHASH_TEST_HOOK 1
#define CAP_SHA256_WIPE_TEST_HOOK 1
#include <stddef.h>
static void cap_sha256_wipe_test_observe(const volatile unsigned char *p, size_t n);
#include "capstan_rt.h"
#include <sys/wait.h>

static unsigned sha256_wipe_observations = 0;
static unsigned sha256_wipe_failures = 0;
static void cap_sha256_wipe_test_observe(const volatile unsigned char *p, size_t n) {
    sha256_wipe_observations++;
    for (size_t i = 0; i < n; i++) if (p[i] != 0) sha256_wipe_failures++;
}

static int failures = 0, checks = 0;
static const char *unit_files[] = {"unit"};

#define CHECK(cond) do { checks++; if (!(cond)) { failures++; \
    fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); } } while (0)

static unsigned siphash_wipe_regions;
static unsigned siphash_wipe_failures;

static void observe_siphash_wipe(const void *memory, size_t n) {
    const volatile unsigned char *p = (const volatile unsigned char *)memory;
    siphash_wipe_regions++;
    for (size_t i = 0; i < n; i++) if (p[i] != 0) siphash_wipe_failures++;
}

static void test_siphash_wipe(void) {
    unsigned char key_bytes[16], message[1] = {0};
    for (int i = 0; i < 16; i++) key_bytes[i] = (unsigned char)i;
    uint64_t k0 = 0, k1 = 0;
    for (int i = 7; i >= 0; i--) {
        k0 = (k0 << 8) | key_bytes[i];
        k1 = (k1 << 8) | key_bytes[8 + i];
    }
    siphash_wipe_regions = siphash_wipe_failures = 0;
    cap_siphash_test_wipe_hook = observe_siphash_wipe;
    uint64_t got = cap_siphash(message, 0, k0, k1, 2, 4);
    cap_siphash_test_wipe_hook = NULL;
    CHECK(got == UINT64_C(0x726fdb47dd0e0e31));
    CHECK(siphash_wipe_regions == 6);
    CHECK(siphash_wipe_failures == 0);
}

static size_t secret_scratch_wipe_calls;
static size_t secret_scratch_wipe_last_len;
static int secret_scratch_wipe_clean;

static void observe_secret_scratch_wipe(const void *memory, size_t n) {
    const volatile unsigned char *bytes = (const volatile unsigned char *)memory;
    for (size_t i = 0; i < n; i++) if (bytes[i] != 0) secret_scratch_wipe_clean = 0;
    secret_scratch_wipe_last_len = n;
    secret_scratch_wipe_calls++;
}

static void test_secret_scratch_lifecycle(void) {
    CapSecretScratch scratch = {0};
    secret_scratch_wipe_calls = 0;
    secret_scratch_wipe_clean = 1;
    cap_secret_scratch_test_wipe_hook = observe_secret_scratch_wipe;

    CHECK(cap_secret_scratch_init(&scratch, 97));
    CHECK(scratch.active && scratch.data != NULL && scratch.len == 97);
    memset(scratch.data, 0xa5, scratch.len);
    CHECK(!cap_secret_scratch_init(&scratch, 8));
    cap_secret_scratch_destroy(&scratch);
    CHECK(!scratch.active && scratch.data == NULL && scratch.len == 0);
    CHECK(secret_scratch_wipe_calls == 1 && secret_scratch_wipe_clean);
    cap_secret_scratch_destroy(&scratch); /* repeated destroy is a no-op */
    CHECK(secret_scratch_wipe_calls == 1);

    CHECK(cap_secret_scratch_init(&scratch, 0));
    CHECK(scratch.active && scratch.data == NULL && scratch.len == 0);
    cap_secret_scratch_destroy(&scratch);
    CHECK(!scratch.active && secret_scratch_wipe_calls == 1);
    cap_secret_scratch_destroy(&scratch);
    CHECK(secret_scratch_wipe_calls == 1);

    /* PBKDF2 intermediates are wiped as one region immediately before free. */
    unsigned char salt[16] = {0}, derived[32];
    secret_scratch_wipe_calls = 0;
    secret_scratch_wipe_last_len = 0;
    secret_scratch_wipe_clean = 1;
    cap_pbkdf2("pw", 2, salt, sizeof salt, 1, derived);
    CHECK(secret_scratch_wipe_calls == 1 && secret_scratch_wipe_clean);
    CHECK(secret_scratch_wipe_last_len == sizeof(CapPbkdf2Scratch));
    cap_wipe(derived, sizeof derived);

    CHECK(!cap_secret_scratch_init(NULL, 8));
    CHECK(!cap_secret_scratch_init(&scratch, CAP_MAX_LEN + (size_t)1));
    cap_secret_scratch_test_wipe_hook = NULL;
}

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
    unsigned wipe_observations_before = sha256_wipe_observations;
    unsigned wipe_failures_before = sha256_wipe_failures;
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
    CapSha256 state;
    unsigned char state_digest[32];
    cap_sha256_init(&state);
    cap_sha256_update(&state, (const unsigned char *)"secret-derived-state", 20);
    cap_sha256_final(&state, state_digest);
    int state_wiped = 1;
    const volatile unsigned char *state_bytes = (const volatile unsigned char *)&state;
    for (size_t i = 0; i < sizeof state; i++) if (state_bytes[i] != 0) state_wiped = 0;
    CHECK(state_wiped);
    CHECK(sha256_wipe_observations > wipe_observations_before);
    CHECK(sha256_wipe_failures == wipe_failures_before);
    cap_wipe(state_digest, sizeof state_digest);
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
    unsigned prepared = cap_pbkdf2_prepare_calls;
    cap_pbkdf2("passwd", 6, (const unsigned char *)"salt", 4, 1, dk);
    CHECK(cap_pbkdf2_prepare_calls == prepared + 1);
    hexof(dk, 32, h);
    CHECK(strcmp(h, "55ac046e56e3089fec1691c22544b605f94185216dde0465e68b9d57c20dacbc") == 0);
    cap_pbkdf2("Password", 8, (const unsigned char *)"NaCl", 4, 80000, dk);
    CHECK(cap_pbkdf2_prepare_calls == prepared + 2);
    hexof(dk, 32, h);
    CHECK(strcmp(h, "4ddcd8f60b98be21830cee5ef22701f9641a4418d04c0414aeff08876b34ab56") == 0);
    char long_password[100];
    memset(long_password, 'p', sizeof long_password);
    cap_pbkdf2(long_password, sizeof long_password, (const unsigned char *)"salt", 4, 20, dk);
    CHECK(cap_pbkdf2_prepare_calls == prepared + 3);
    hexof(dk, 32, h);
    CHECK(strcmp(h, "2eb89ef29f89f8343421877ca538a4bc793824f7b375aaafbb53b46a352d75c8") == 0);
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
    CHECK(!cap_verify_password(pw, NULL));
    CHECK(!cap_verify_password(NULL, h1));
    char current_record[124];
    const char current_prefix[] = "cap1$pbkdf2-sha256$600000$";
    memcpy(current_record, current_prefix, sizeof current_prefix - 1);
    memset(current_record + 26, '0', 32);
    current_record[58] = '$';
    memset(current_record + 59, '0', 64);
    current_record[123] = '\0';
    CapStr *canonical = cap_str_new(current_record, 123);
    CHECK(!cap_needs_rehash(canonical));
    unsigned calls_before_rejected_records = cap_pbkdf2_test_calls;
    char noncanonical[124];
    memcpy(noncanonical, current_record, sizeof noncanonical);
    noncanonical[19] = '0';
    CHECK(cap_needs_rehash(cap_str_new(noncanonical, 123)));
    CHECK(!cap_verify_password(pw, cap_str_new(noncanonical, 123)));
    memcpy(noncanonical, current_record, sizeof noncanonical);
    noncanonical[26] = 'A';
    CHECK(cap_needs_rehash(cap_str_new(noncanonical, 123)));
    CHECK(!cap_verify_password(pw, cap_str_new(noncanonical, 123)));
    char embedded_nul[126];
    memcpy(embedded_nul, current_record, 123);
    embedded_nul[123] = '\0';
    embedded_nul[124] = 'x';
    embedded_nul[125] = '\0';
    CapStr *nul_suffix = cap_str_new(embedded_nul, 125);
    CHECK(cap_needs_rehash(nul_suffix));
    CHECK(!cap_verify_password(pw, nul_suffix));
    char trailing[125];
    memcpy(trailing, current_record, 123);
    trailing[123] = 'x';
    trailing[124] = '\0';
    CapStr *trailing_suffix = cap_str_new(trailing, 124);
    CHECK(cap_needs_rehash(trailing_suffix));
    CHECK(!cap_verify_password(pw, trailing_suffix));
    char excessive[127];
    const char excessive_prefix[] = "cap1$pbkdf2-sha256$100000000$";
    memcpy(excessive, excessive_prefix, sizeof excessive_prefix - 1);
    memset(excessive + 29, '0', 32);
    excessive[61] = '$';
    memset(excessive + 62, '0', 64);
    excessive[126] = '\0';
    CapStr *excessive_record = cap_str_new(excessive, 126);
    CHECK(cap_needs_rehash(excessive_record));
    CHECK(!cap_verify_password(pw, excessive_record));
    CHECK(cap_pbkdf2_test_calls == calls_before_rejected_records);
    CapStr *negative_record = cap_str_new(current_record, 123);
    negative_record->len = -1;
    CHECK(cap_needs_rehash(negative_record));
    CHECK(!cap_verify_password(pw, negative_record));
    CapStr *negative_password = cap_str_new("pw", 2);
    negative_password->len = -1;
    CHECK(!cap_verify_password(negative_password, h1));
    CHECK(cap_pbkdf2_test_calls == calls_before_rejected_records);
    char just_over_limit[124];
    memcpy(just_over_limit, current_record, sizeof just_over_limit);
    just_over_limit[24] = '1';
    CapStr *over_limit_record = cap_str_new(just_over_limit, 123);
    CHECK(cap_needs_rehash(over_limit_record));
    CHECK(!cap_verify_password(pw, over_limit_record));
    CHECK(cap_pbkdf2_test_calls == calls_before_rejected_records);
    char non_ascii_cost[124];
    memcpy(non_ascii_cost, current_record, sizeof non_ascii_cost);
    non_ascii_cost[19] = (char)0xD9;
    CapStr *non_ascii_record = cap_str_new(non_ascii_cost, 123);
    CHECK(cap_needs_rehash(non_ascii_record));
    CHECK(!cap_verify_password(pw, non_ascii_record));
    CHECK(cap_pbkdf2_test_calls == calls_before_rejected_records);

    char overlong_password_bytes[CAP_PASSWORD_MAX_BYTES + 1];
    memset(overlong_password_bytes, 'p', sizeof overlong_password_bytes);
    CapStr *overlong_password = cap_str_new(overlong_password_bytes, sizeof overlong_password_bytes);
    unsigned calls_before_overlong = cap_pbkdf2_test_calls;
    CHECK(!cap_verify_password(overlong_password, canonical));
    CHECK(cap_pbkdf2_test_calls == calls_before_overlong);
    cap_test_mode = 1;
    if (setjmp(cap_test_jmp) == 0) {
        (void)cap_hash_password(overlong_password);
        CHECK(false);
    } else {
        CHECK(true);
    }
    cap_test_mode = 0;
    CHECK(cap_pbkdf2_test_calls == calls_before_overlong);
    CHECK(!cap_hash_verify(CAP_LIT("abc", 3), CAP_LIT("md5$900150983cd24fb0d6963f7d28e17f72", 36)));
}

static bool cap_pbkdf2_rejects(const char *pw, size_t pn,
                                   const unsigned char *salt, size_t sn,
                                   int iter) {
    int old_test_mode = cap_test_mode;
    cap_test_mode = 1;
    if (setjmp(cap_test_jmp) == 0) {
        unsigned char out[32];
        cap_pbkdf2(pw, pn, salt, sn, iter, out);
        cap_test_mode = old_test_mode;
        return false;
    }
    cap_test_mode = old_test_mode;
    return true;
}

static void test_pbkdf2_parameter_bounds(void) {
    unsigned char salt[65] = {0};
    char password[CAP_PASSWORD_MAX_BYTES + 1];
    memset(password, 'p', sizeof password);
    unsigned before = cap_pbkdf2_test_calls;
    CHECK(cap_pbkdf2_rejects("pw", 2, salt, 16, 0));
    CHECK(cap_pbkdf2_rejects("pw", 2, salt, 16, CAP_PBKDF2_ITER + 1));
    CHECK(cap_pbkdf2_rejects("pw", 2, salt, sizeof salt, 1));
    CHECK(cap_pbkdf2_rejects(password, sizeof password, salt, 16, 1));
    CHECK(cap_pbkdf2_test_calls == before);
}

static bool cap_sha256_update_rejects(void) {
    CapSha256 state;
    cap_sha256_init(&state);
    state.bits = UINT64_MAX - 7;
    int old_test_mode = cap_test_mode;
    cap_test_mode = 1;
    if (setjmp(cap_test_jmp) == 0) {
        cap_sha256_update(&state, (const unsigned char *)"x", 1);
        cap_test_mode = old_test_mode;
        return false;
    }
    cap_test_mode = old_test_mode;
    return true;
}

static void test_sha256_length_bound(void) {
    CHECK(cap_sha256_update_rejects());
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

static bool str_is(CapStr *s, const char *want, int64_t n) {
    return s && s->len == n && memcmp(s->data, want, (size_t)n) == 0;
}

/* escape_log(): text survives, anything that could forge or disguise a log line does not. */
static void test_escape_log(void) {
    struct { const char *in; int n; const char *out; } cases[] = {
        {"plain text", 10, "plain text"},
        {"caf\xc3\xa9 \xe4\xb8\xad\xe6\x96\x87 \xf0\x9f\x9a\xa2", 17, "caf\xc3\xa9 \xe4\xb8\xad\xe6\x96\x87 \xf0\x9f\x9a\xa2"},  /* é 中文 🚢 */
        {"a\nb", 3, "a\\x0ab"},
        {"\x1b[31m", 5, "\\x1b[31m"},
        {"\xc2\x9b" "31m", 5, "\\xc2\\x9b31m"},                     /* U+009B: C1 CSI */
        {"\x9b" "31m", 4, "\\x9b31m"},                              /* raw 8-bit CSI */
        {"user \xe2\x80\xae" "nimda", 13, "user \\xe2\\x80\\xaenimda"}, /* U+202E: right-to-left override */
        {"\xe2\x81\xa6x", 4, "\\xe2\\x81\\xa6x"},                     /* U+2066 */
        {"a\xe2\x80\xa8" "b", 5, "a\\xe2\\x80\\xa8b"},                 /* U+2028: line separator */
        {"\xef\xbb\xbf" "x", 4, "\\xef\\xbb\\xbfx"},                     /* byte-order mark */
        {"\xff", 1, "\\xff"},                                        /* never valid */
        {"\xc0\xaf", 2, "\\xc0\\xaf"},                                /* overlong '/' */
        {"\xed\xa0\x80", 3, "\\xed\\xa0\\x80"},                        /* surrogate */
        {"\xf4\x90\x80\x80", 4, "\\xf4\\x90\\x80\\x80"},                /* beyond U+10FFFF */
        {"ok\xe2\x80", 4, "ok\\xe2\\x80"},                              /* truncated at the end */
        {"\xe2\x28\xa1", 3, "\\xe2(\\xa1"},                           /* bad continuation */
        {"\x7f\x00", 2, "\\x7f\\x00"},
    };
    for (size_t i = 0; i < sizeof cases / sizeof *cases; i++) {
        CapStr *e = cap_escape_log(cap_str_new(cases[i].in, cases[i].n));
        CHECK(strcmp(e->data, cases[i].out) == 0);
        if (strcmp(e->data, cases[i].out) != 0) fprintf(stderr, "  escape_log case %zu gave %s\n", i, e->data);
    }
    /* every 1- and 2-byte input: the result never contains a control byte, a raw byte
       0x80-0x9F that is not inside a kept sequence, or an escape of printable ASCII */
    for (int a = 0; a < 256; a++) {
        for (int b = 0; b < 256; b++) {
            char in[2] = {(char)a, (char)b};
            CapStr *e = cap_escape_log(cap_str_new(in, 2));
            for (int64_t k = 0; k < e->len; k++) {
                unsigned char c = (unsigned char)e->data[k];
                CHECK(c >= 32 && c != 127);
                if (c == 0xC2 && k + 1 < e->len) CHECK((unsigned char)e->data[k + 1] > 0x9F);
            }
        }
    }
}

/* validate_path(): relative paths of safe segments only (CWE-22, CWE-158). */
static void test_paths(void) {
    const char *good[] = {"a", "dir/file.txt", "a-b_c.d", "x/y/z", "...", "a..b", ".hidden", "v1.2.3/notes"};
    for (size_t i = 0; i < sizeof good / sizeof *good; i++) {
        CapStr *in = cap_str_new(good[i], (int64_t)strlen(good[i]));
        CHECK(str_is(cap_validate_path(in), good[i], in->len));
    }
    const char *bad[] = {"", "/etc/passwd", "..", ".", "../x", "a/../b", "a/..", "a/./b", "./a", "a//b", "a/", "/",
                         "a b", "a\\b", "~root", "C:x", "a;b", "$HOME", "a\nb", "caf\xc3\xa9"};
    for (size_t i = 0; i < sizeof bad / sizeof *bad; i++) CHECK(cap_validate_path(cap_str_new(bad[i], (int64_t)strlen(bad[i]))) == NULL);
    CHECK(cap_validate_path(cap_str_new("a\0b", 3)) == NULL);
    char longp[5000];
    memset(longp, 'p', sizeof longp);
    CHECK(cap_validate_path(cap_str_new(longp, 4096)) != NULL);
    CHECK(cap_validate_path(cap_str_new(longp, 4097)) == NULL);
}

/* validate_range(): an integer inside [lo, hi] (CWE-1284). */
static void test_ranges(void) {
    int64_t *v;
    v = cap_validate_range(CAP_LIT("5", 1), 1, 10); CHECK(v && *v == 5);
    v = cap_validate_range(CAP_LIT("1", 1), 1, 10); CHECK(v && *v == 1);
    v = cap_validate_range(CAP_LIT("10", 2), 1, 10); CHECK(v && *v == 10);
    CHECK(cap_validate_range(CAP_LIT("0", 1), 1, 10) == NULL);
    CHECK(cap_validate_range(CAP_LIT("11", 2), 1, 10) == NULL);
    CHECK(cap_validate_range(CAP_LIT("-1", 2), 0, 10) == NULL);
    CHECK(cap_validate_range(CAP_LIT("5", 1), 10, 1) == NULL);       /* empty range */
    CHECK(cap_validate_range(CAP_LIT("x", 1), 0, 10) == NULL);
    CHECK(cap_validate_range(CAP_LIT("99999999999999999999", 20), INT64_MIN, INT64_MAX) == NULL);
    v = cap_validate_range(CAP_LIT("-9223372036854775808", 20), INT64_MIN, INT64_MAX); CHECK(v && *v == INT64_MIN);
}

/* escape_csv(): one quoted field; formula prefixes neutralised (CWE-1236). */
static void test_csv(void) {
    CHECK(str_is(cap_escape_csv(CAP_LIT("abc", 3)), "\"abc\"", 5));
    CHECK(str_is(cap_escape_csv(CAP_LIT("", 0)), "\"\"", 2));
    CHECK(str_is(cap_escape_csv(CAP_LIT("say \"hi\"", 8)), "\"say \"\"hi\"\"\"", 12));
    CHECK(str_is(cap_escape_csv(CAP_LIT("a,b\nc", 5)), "\"a,b\nc\"", 7));
    const char *formulas[] = {"=SUM(A1)", "+1", "-1", "@cmd", "\tx", "\rx"};
    for (size_t i = 0; i < sizeof formulas / sizeof *formulas; i++) {
        size_t n = strlen(formulas[i]);
        CapStr *e = cap_escape_csv(cap_str_new(formulas[i], (int64_t)n));
        CHECK(e->len == (int64_t)n + 3 && e->data[0] == '"' && e->data[1] == '\'' && memcmp(e->data + 2, formulas[i], n) == 0);
    }
    CHECK(str_is(cap_escape_csv(CAP_LIT("a=b", 3)), "\"a=b\"", 5));   /* only a leading prefix matters */
    CHECK(str_is(cap_escape_csv(cap_str_new("\0=", 2)), "\"\0=\"", 4));
    CHECK(str_is(cap_escape_csv(CAP_LIT("\"=x", 3)), "\"\"\"=x\"", 6));
}

/* secret_eq(): constant-time comparison gives the right answer in every case. */
static void test_secret_eq(void) {
    CHECK(cap_secret_eq(CAP_LIT("hunter2", 7), CAP_LIT("hunter2", 7)));
    CHECK(!cap_secret_eq(CAP_LIT("hunter2", 7), CAP_LIT("hunter3", 7)));
    CHECK(!cap_secret_eq(CAP_LIT("hunter2", 7), CAP_LIT("Hunter2", 7)));
    CHECK(!cap_secret_eq(CAP_LIT("hunter2", 7), CAP_LIT("hunter", 6)));
    CHECK(!cap_secret_eq(CAP_LIT("hunter", 6), CAP_LIT("hunter2", 7)));
    CHECK(!cap_secret_eq(CAP_LIT("", 0), CAP_LIT("x", 1)));
    CHECK(cap_secret_eq(CAP_LIT("", 0), CAP_LIT("", 0)));
    CHECK(!cap_secret_eq(cap_str_new("a\0b", 3), cap_str_new("a\0c", 3)));
    CHECK(!cap_secret_eq(cap_str_new("a\0", 2), cap_str_new("a", 1)));
}

/* read_file(), write_file(), read_line(): every byte survives, and bad paths fail safely. */
static void test_files(void) {
    char dir[] = "/tmp/capstan-unit-XXXXXX";
    CHECK(mkdtemp(dir) != NULL);
    char path[256];
    snprintf(path, sizeof path, "%s/data.bin", dir);
    char all[256];
    for (int i = 0; i < 256; i++) all[i] = (char)i;
    CapStr *p = cap_str_new(path, (int64_t)strlen(path));
    CHECK(cap_write_file(p, cap_str_new(all, 256)));
    CHECK(str_is(cap_read_file(p), all, 256));
    CHECK(cap_write_file(p, CAP_LIT("", 0)));
    CHECK(str_is(cap_read_file(p), "", 0));
    /* larger than the read chunk, so the buffer must grow */
    char *big = (char *)malloc(300000);
    for (int i = 0; i < 300000; i++) big[i] = (char)(i * 7);
    CHECK(cap_write_file(p, cap_str_new(big, 300000)));
    CHECK(str_is(cap_read_file(p), big, 300000));
    free(big);
    CHECK(cap_read_file(cap_str_new(dir, (int64_t)strlen(dir))) == NULL);            /* a directory */
    CHECK(cap_read_file(CAP_LIT("/nonexistent/capstan", 20)) == NULL);
    CHECK(cap_read_file(CAP_LIT("", 0)) == NULL);
    char nul[300];
    int nn = snprintf(nul, sizeof nul, "%s/data.bin", dir);
    nul[strlen(dir)] = 0;                                                              /* "<dir>\0data.bin" */
    CHECK(cap_read_file(cap_str_new(nul, nn)) == NULL);
    CHECK(!cap_write_file(cap_str_new(nul, nn), CAP_LIT("x", 1)));
    CHECK(!cap_write_file(CAP_LIT("/nonexistent/capstan/x", 22), CAP_LIT("x", 1)));
    CHECK(!cap_write_file(cap_str_new(dir, (int64_t)strlen(dir)), CAP_LIT("x", 1)));
    CapStr *proc = cap_read_file(CAP_LIT("/proc/self/status", 17));                   /* size 0 on Linux */
#if defined(__linux__)
    CHECK(proc && proc->len > 0);
#else
    (void)proc;
#endif
    /* read_line(): from a file standing in for standard input */
    char in[256];
    snprintf(in, sizeof in, "%s/stdin.txt", dir);
    FILE *f = fopen(in, "wb");
    fwrite("ab\0cd\n\nx\r\n", 1, 10, f);
    for (int i = 0; i < 10000; i++) fputc('L', f);
    fwrite("\nlast", 1, 5, f);
    fclose(f);
    CHECK(freopen(in, "rb", stdin) != NULL);
    CHECK(str_is(cap_read_line(), "ab\0cd", 5));
    CHECK(str_is(cap_read_line(), "", 0));
    CHECK(str_is(cap_read_line(), "x\r", 2));
    CapStr *longl = cap_read_line();
    CHECK(longl && longl->len == 10000 && longl->data[0] == 'L' && longl->data[9999] == 'L');
    CHECK(str_is(cap_read_line(), "last", 4)); /* EOF without a trailing newline */
    CHECK(cap_read_line() == NULL);
    CHECK(cap_read_line() == NULL);

    /* Exactly the configured maximum is accepted, and the next line remains intact. */
    f = fopen(in, "wb");
    char line_chunk[4096];
    memset(line_chunk, 'Q', sizeof line_chunk);
    for (int i = 0; i < CAP_READ_LINE_MAX / (int64_t)sizeof line_chunk; i++)
        CHECK(fwrite(line_chunk, 1, sizeof line_chunk, f) == sizeof line_chunk);
    fwrite("\nnext\n", 1, 6, f);
    fclose(f);
    CHECK(freopen(in, "rb", stdin) != NULL);
    CapStr *at_limit = cap_read_line();
    CHECK(at_limit && at_limit->len == CAP_READ_LINE_MAX &&
          at_limit->data[0] == 'Q' && at_limit->data[CAP_READ_LINE_MAX - 1] == 'Q');
    CHECK(str_is(cap_read_line(), "next", 4));
    CHECK(cap_read_line() == NULL);

    /* One byte over the limit fails closed without growing the buffer further. */
    f = fopen(in, "wb");
    for (int i = 0; i < CAP_READ_LINE_MAX / (int64_t)sizeof line_chunk; i++)
        CHECK(fwrite(line_chunk, 1, sizeof line_chunk, f) == sizeof line_chunk);
    fputc('X', f);
    fclose(f);
    CHECK(freopen(in, "rb", stdin) != NULL);
    int old_test_mode = cap_test_mode;
    cap_test_mode = 1;
    int rejected = setjmp(cap_test_jmp) != 0;
    if (!rejected) (void)cap_read_line();
    cap_test_mode = old_test_mode;
    CHECK(rejected);
    CHECK(cap_read_line() == NULL);
    remove(in);
    remove(path);
    rmdir(dir);
}

static int expect_runtime_panic(void (*fn)(void));
static void trigger_negative_string_length(void) {
    (void)cap_str_new(NULL, -1);
}
static void trigger_null_string_source(void) {
    (void)cap_str_new(NULL, 1);
}
static void trigger_negative_permanent_string_length(void) {
    (void)cap_str_perm(NULL, -1);
}
static void trigger_string_expansion_overflow(void) {
    (void)cap_rt_checked_string_bytes(INT64_MAX, 6, 1, 0);
}
static void trigger_escape_length_overflow(void) {
    CapStr forged = {.len = INT64_MAX};
    (void)cap_escape_html(&forged);
}
static void trigger_concat_invalid_operand(void) {
    CapStr bad = {.len = -1};
    CapStr good = {.len = 1};
    (void)cap_str_concat(&bad, &good, 0);
}
static void trigger_join_invalid_collection(void) {
    CapList parts = {.len = 2, .cap = 1, .items = NULL};
    (void)cap_join(&parts, CAP_LIT("", 0), 0);
}
static void test_string_allocation_bounds(void) {
    CHECK(expect_runtime_panic(trigger_negative_string_length));
    CHECK(expect_runtime_panic(trigger_null_string_source));
    CHECK(expect_runtime_panic(trigger_negative_permanent_string_length));
    CHECK(expect_runtime_panic(trigger_string_expansion_overflow));
    CHECK(expect_runtime_panic(trigger_escape_length_overflow));
    CHECK(expect_runtime_panic(trigger_concat_invalid_operand));
    CHECK(expect_runtime_panic(trigger_join_invalid_collection));
    size_t max_plain = CAP_MAX_LEN - sizeof(CapStr) - 1;
    CHECK(cap_rt_checked_string_bytes((int64_t)max_plain, 1, 1, 0) == CAP_MAX_LEN);
    size_t max_html = (CAP_MAX_LEN - sizeof(CapStr) - 1) / 6;
    CHECK(cap_rt_checked_string_bytes((int64_t)max_html, 6, 1, 0) ==
          sizeof(CapStr) + max_html * 6 + 1);
    CapStr *plain = cap_str_new("abc", 3);
    CHECK(plain->len == 3 && memcmp(plain->data, "abc", 3) == 0);
}

/* Shifts and wrapping arithmetic at the edges of the 64-bit range (no panics here;
   the stops are covered by tests/runtime/shift_*.cap). */
static int expect_runtime_panic(void (*fn)(void));
static void trigger_gc_add_overflow(void) {
    (void)cap_gc_checked_add(SIZE_MAX, 1);
}
static void trigger_gc_mul_overflow(void) {
    (void)cap_gc_checked_mul(SIZE_MAX, 2);
}
static void trigger_gc_capacity_overflow(void) {
    (void)cap_gc_next_capacity(0, SIZE_MAX, 8, sizeof(CapLarge));
}
static void trigger_gc_heap_invariant(void) {
    (void)cap_gc_heap_would_exceed(0);
}
static void trigger_full_page_table_lookup(void) {
    (void)cap_gc_page_of((uintptr_t)0x30000);
}
static void trigger_null_registered_root(void) {
    cap_gc_root(NULL);
}
static void trigger_full_page_table_insert(void) {
    CapPage pg = {.base = (char *)(uintptr_t)0x30000};
    cap_gc_ptab_insert(&pg);
}
static void trigger_null_page_table_insert(void) {
    cap_gc_ptab_insert(NULL);
}
static void trigger_duplicate_page_table_insert(void) {
    CapPage duplicate = {.base = (char *)(uintptr_t)0x10000};
    cap_gc_ptab_insert(&duplicate);
}
static void trigger_bad_heap_limit_suffix(void) {
    (void)cap_gc_parse_heap_limit("12MB");
}
static void trigger_heap_limit_shift_overflow(void) {
    (void)cap_gc_parse_heap_limit("18446744073709551615G");
}
static void trigger_negative_heap_limit(void) {
    (void)cap_gc_parse_heap_limit("-1");
}
static void trigger_signed_heap_limit(void) {
    (void)cap_gc_parse_heap_limit(" -1");
}
static void trigger_plus_heap_limit(void) {
    (void)cap_gc_parse_heap_limit("+1");
}
static void test_gc_allocator_arithmetic(void) {
    CHECK(expect_runtime_panic(trigger_gc_add_overflow));
    CHECK(expect_runtime_panic(trigger_gc_mul_overflow));
    CHECK(expect_runtime_panic(trigger_gc_capacity_overflow));
    CHECK(expect_runtime_panic(trigger_bad_heap_limit_suffix));
    CHECK(expect_runtime_panic(trigger_heap_limit_shift_overflow));
    CHECK(expect_runtime_panic(trigger_negative_heap_limit));
    CHECK(expect_runtime_panic(trigger_signed_heap_limit));
    CHECK(expect_runtime_panic(trigger_plus_heap_limit));
    CHECK(cap_gc_parse_heap_limit("128K") == ((size_t)128 << 10));
    CHECK(cap_gc_parse_heap_limit("0") == 0);
    CHECK(cap_gc_effective_heap_limit(cap_gc_parse_heap_limit("0")) == CAP_MAX_LEN);
    CHECK(cap_gc_effective_heap_limit((size_t)CAP_MAX_LEN + 1) == CAP_MAX_LEN);
    CHECK(cap_gc_effective_heap_limit((size_t)128 << 20) == ((size_t)128 << 20));
    CHECK(cap_gc_parse_heap_limit("1G") == ((size_t)1 << 30));
    CHECK(cap_gc_physical_heap_limit(1024, 4096) == ((size_t)3 << 20));
    CHECK(cap_gc_physical_heap_limit(SIZE_MAX, 4096) == CAP_MAX_LEN);
    CHECK(cap_gc_physical_heap_limit(0, 4096) == ((size_t)1 << 34));
    size_t saved_heap = cap_gc.heap, saved_limit = cap_gc.max_heap;
    cap_gc.heap = 100;
    cap_gc.max_heap = 101;
    CHECK(!cap_gc_heap_would_exceed(1));
    CHECK(cap_gc_heap_would_exceed(2));
    cap_gc.heap = 1;
    cap_gc.max_heap = 0;
    CHECK(!cap_gc_heap_would_exceed(SIZE_MAX));
    cap_gc.heap = 100;
    cap_gc.max_heap = 99;
    CHECK(expect_runtime_panic(trigger_gc_heap_invariant));
    cap_gc.heap = saved_heap;
    cap_gc.max_heap = saved_limit;
    CHECK(cap_gc_saturating_add(SIZE_MAX - 1, 2) == SIZE_MAX);
    CHECK(cap_gc_next_capacity(64, 128, 64, sizeof(CapPage *)) == 128);
    CHECK(expect_runtime_panic(trigger_null_registered_root));
    CHECK(expect_runtime_panic(trigger_null_page_table_insert));
    {
        size_t saved_cap = cap_gc.ptab_cap, saved_pages = cap_gc.npages;
        cap_gc.ptab_cap = 0; cap_gc.npages = 1;
        CHECK(expect_runtime_panic(trigger_full_page_table_insert));
        cap_gc.ptab_cap = saved_cap; cap_gc.npages = saved_pages;
    }
    {
        CapPage **saved_table = cap_gc.ptab;
        size_t saved_cap = cap_gc.ptab_cap;
        cap_gc.ptab = NULL; cap_gc.ptab_cap = 2;
        CHECK(expect_runtime_panic(trigger_full_page_table_lookup));
        cap_gc.ptab = saved_table; cap_gc.ptab_cap = saved_cap;
    }
    {
        CapPage existing = {.base = (char *)(uintptr_t)0x10000};
        CapPage *table[4] = {&existing, NULL, NULL, NULL};
        CapPage **saved_table = cap_gc.ptab;
        size_t saved_cap = cap_gc.ptab_cap, saved_pages = cap_gc.npages;
        cap_gc.ptab = table; cap_gc.ptab_cap = 4; cap_gc.npages = 1;
        CHECK(expect_runtime_panic(trigger_duplicate_page_table_insert));
        cap_gc.ptab = saved_table; cap_gc.ptab_cap = saved_cap; cap_gc.npages = saved_pages;
    }
    {
        CapPage first = {.base = (char *)(uintptr_t)0x10000};
        CapPage second = {.base = (char *)(uintptr_t)0x20000};
        CapPage *full_table[2] = {&first, &second};
        CapPage **saved_table = cap_gc.ptab;
        size_t saved_cap = cap_gc.ptab_cap, saved_pages = cap_gc.npages;
        cap_gc.ptab = full_table; cap_gc.ptab_cap = 2; cap_gc.npages = 0;
        CHECK(expect_runtime_panic(trigger_full_page_table_lookup));
        CHECK(expect_runtime_panic(trigger_full_page_table_insert));
        cap_gc.ptab = saved_table; cap_gc.ptab_cap = saved_cap; cap_gc.npages = saved_pages;
    }
}

static void test_bitwise(void) {
    CHECK(cap_as_signed(0) == 0 && cap_as_signed(UINT64_MAX) == -1);
    CHECK(cap_as_signed((uint64_t)INT64_MAX) == INT64_MAX && cap_as_signed((uint64_t)INT64_MAX + 1) == INT64_MIN);
    CHECK(cap_shl(1, 62, 0) == (int64_t)1 << 62 && cap_shl(-1, 63, 0) == INT64_MIN && cap_shl(0, 63, 0) == 0);
    CHECK(cap_shl(-3, 61, 0) == -3 * ((int64_t)1 << 61));
    CHECK(cap_sar(INT64_MIN, 63, 0) == -1 && cap_sar(-1, 1, 0) == -1 && cap_sar(-16, 2, 0) == -4 && cap_sar(INT64_MAX, 62, 0) == 1);
    CHECK(cap_sar(-7, 1, 0) == -4);                                 /* rounds toward minus infinity */
    CHECK(cap_shr(-1, 0, 0) == -1 && cap_shr(-1, 1, 0) == INT64_MAX && cap_shr(-1, 63, 0) == 1 && cap_shr(INT64_MIN, 63, 0) == 1);
    CHECK(cap_wrapping_add(INT64_MAX, 1) == INT64_MIN && cap_wrapping_sub(INT64_MIN, 1) == INT64_MAX);
    CHECK(cap_wrapping_mul(INT64_MIN, -1) == INT64_MIN && cap_wrapping_mul(0x100000000LL, 0x100000000LL) == 0);
    CHECK(cap_wrapping_shl(3, 63, 0) == INT64_MIN && cap_wrapping_shl(-1, 63, 0) == INT64_MIN);
    CHECK(cap_shl_proved(5, 3, 0) == 40 && cap_sar_proved(-9, 1, 0) == -5 && cap_shr_proved(-2, 63, 0) == 1);
}

/* Keep the longjmp target in its own frame for deterministic failure tests. */
__attribute__((noinline)) static int expect_runtime_panic(void (*fn)(void)) {
    cap_test_mode = 1;
    if (setjmp(cap_test_jmp) == 0) {
        fn();
        cap_test_mode = 0;
        return 0;
    }
    cap_test_mode = 0;
    return 1;
}

static void trigger_bad_growth(void) {
    (void)cap_rt_growth_capacity(0, INT64_MAX, 8, sizeof(CapVal), 0, 0);
}
static void trigger_bad_buffer_length(void) {
    CapBuf b = cap_buf_new(64);
    b.s->len = INT64_MAX - 1;
    b.cap = INT64_MAX;
    cap_buf_put(&b, "x", 1);
}
static void trigger_negative_buffer_append(void) {
    CapBuf b = cap_buf_new(64);
    cap_buf_put(&b, "x", -1);
}
static void trigger_oversized_initial_buffer(void) {
    (void)cap_buf_new(INT64_MAX);
}
static void trigger_negative_initial_buffer(void) {
    (void)cap_buf_new(-1);
}
static void trigger_non_power_of_two_map_index(void) {
    CapMap m = {0};
    m.index_cap = 3;
    (void)cap_map_find(&m, CAP_LIT("k", 1));
}
static void trigger_out_of_range_map_index_entry(void) {
    CapMap m = {0};
    CapStr *key = cap_str_new("k", 1);
    CapStr *keys[1] = {key};
    CapVal vals[1] = {{.i = 1}};
    int64_t index[2] = {2, 2};
    m.len = 1; m.cap = 1; m.keys = keys; m.vals = vals;
    m.index = index; m.index_cap = 2;
    (void)cap_map_find(&m, key);
}
static void trigger_full_map_index(void) {
    CapMap m = {0};
    CapStr *stored = cap_str_new("stored", 6);
    CapStr *missing = cap_str_new("missing", 7);
    CapStr *keys[1] = {stored};
    CapVal vals[1] = {{.i = 1}};
    int64_t index[2] = {1, 1};
    m.len = 1; m.cap = 1; m.keys = keys; m.vals = vals;
    m.index = index; m.index_cap = 2;
    (void)cap_map_find(&m, missing);
}
static void trigger_missing_list_storage(void) {
    CapList l = {.len = 0, .cap = 1, .items = NULL};
    cap_list_push(&l, cap_vi(1));
}
static void trigger_missing_boolean_list_storage(void) {
    CapBList l = {.len = 0, .cap = 1, .items = NULL};
    cap_blist_push(&l, true);
}

static void test_runtime_growth_arithmetic(void) {
    if (!cap_map_keyed) cap_map_key_init();
    CHECK(cap_rt_growth_capacity(0, 1, 8, sizeof(CapVal), 0, 0) == 8);
    CHECK(cap_rt_growth_capacity(8, 9, 8, sizeof(CapVal), 0, 0) == 16);
    size_t max_items = cap_rt_max_count(sizeof(CapVal), 0, 0);
    CHECK(cap_rt_growth_capacity((int64_t)max_items - 1, (int64_t)max_items,
                                 8, sizeof(CapVal), 0, 0) == (int64_t)max_items);
    CHECK(expect_runtime_panic(trigger_bad_growth));
    CHECK(expect_runtime_panic(trigger_bad_buffer_length));
    CHECK(expect_runtime_panic(trigger_negative_buffer_append));
    CHECK(expect_runtime_panic(trigger_oversized_initial_buffer));
    CHECK(expect_runtime_panic(trigger_negative_initial_buffer));
    CHECK(expect_runtime_panic(trigger_non_power_of_two_map_index));
    CHECK(expect_runtime_panic(trigger_out_of_range_map_index_entry));
    CHECK(expect_runtime_panic(trigger_full_map_index));
    CHECK(expect_runtime_panic(trigger_missing_list_storage));
    CHECK(expect_runtime_panic(trigger_missing_boolean_list_storage));
}

/* noinline: keep its 100,000-key map out of main's conservative root frame. */
__attribute__((noinline)) static void test_collections(void) {
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
    /* int_to_str against snprintf: every power of ten and its neighbours, both
       signs, the 64-bit extremes, and a million pseudo-random values. */
    {
        int bad = 0, n = 0;
        int64_t edges[200];
        int ne = 0;
        int64_t p10 = 1;
        for (int k = 0; k < 19; k++) {
            edges[ne++] = p10 - 1; edges[ne++] = p10; edges[ne++] = p10 + 1;
            edges[ne++] = -p10 + 1; edges[ne++] = -p10; edges[ne++] = -p10 - 1;
            if (k < 18) p10 *= 10;
        }
        edges[ne++] = INT64_MAX; edges[ne++] = INT64_MAX - 1; edges[ne++] = INT64_MIN; edges[ne++] = INT64_MIN + 1;
        uint64_t x = 0x9E3779B97F4A7C15ULL;
        for (int i = 0; i < ne + 1000000; i++) {
            int64_t v;
            if (i < ne) v = edges[i];
            else { x ^= x << 13; x ^= x >> 7; x ^= x << 17; v = (int64_t)(x >> (x % 64)); if (x & 1) v = -v; }
            char want[32];
            snprintf(want, sizeof want, "%lld", (long long)v);
            CapStr *got = cap_int_to_str(v);
            n++;
            if (got->len != (int64_t)strlen(want) || memcmp(got->data, want, strlen(want)) != 0 || got->data[got->len] != 0) bad++;
        }
        CHECK(bad == 0 && n > 1000000);
    }
    CHECK(cap_ct_eq("abc", 3, "abc", 3) && !cap_ct_eq("abc", 3, "abd", 3) && !cap_ct_eq("abc", 3, "ab", 2));
}

/* Zero the stack below the caller, so stale pointers left by earlier tests (the
   collector is conservative) cannot keep their objects alive. */
__attribute__((noinline)) static void scrub_stack(int depth) {
    volatile char pad[4096];
    memset((char *)pad, 0, sizeof pad);
    if (depth > 0) scrub_stack(depth - 1);
}

/* The collector must keep objects reachable only through interior pointers,
   large objects, registered globals, and nested structures. */
#define CAP_DISGUISE_GC ((uintptr_t)0x3c3c3c3c3c3c3c3cULL)
__attribute__((noinline)) static void scrub_stack(int depth);
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

/* Pages a collection leaves empty go back to the operating system beyond a reserve,
   are reused (for any size class) before new memory is requested, and a stale
   pointer into a released page is treated as pointing at nothing. */
static uintptr_t stale_addr;
__attribute__((noinline)) static void fill_and_drop(void) {
    /* About 50 MiB of garbage with no collection in between (the threshold is
       raised for the duration), so one collection then finds it all empty. */
    size_t saved = cap_gc.threshold;
    cap_gc.threshold = (size_t)1 << 40;
    for (int i = 0; i < 600000; i++) {
        CapStr *t = cap_str_new("0123456789012345678901234567890123456789", 40);
        if (i == 1000) stale_addr = (uintptr_t)t ^ CAP_DISGUISE_GC;
    }
    cap_gc.threshold = saved;
}
/* Collect from a fresh frame after clearing the stack and the callee-saved
   registers, so stale copies of dropped pointers do not keep them alive. */
__attribute__((noinline)) static void collect_clean(void) {
    scrub_stack(16);
    __asm__ volatile("" ::: "memory");
#if defined(__x86_64__)
    __asm__ volatile("xor %%r12d, %%r12d\n\txor %%r13d, %%r13d\n\txor %%r14d, %%r14d\n\txor %%r15d, %%r15d\n\txor %%ebx, %%ebx" ::: "r12", "r13", "r14", "r15", "rbx", "memory");
#endif
    cap_gc_collect();
}
static void test_gc_release_accounting(void) {
    CapPage page;
    memset(&page, 0, sizeof page);
    size_t saved_heap = cap_gc.heap;
    size_t saved_released = cap_gc.released_total;
    cap_gc.heap = CAP_PAGE_SIZE;
    cap_gc_account_release(&page, 0); /* simulated madvise failure */
    CHECK(!page.released);
    CHECK(cap_gc.heap == CAP_PAGE_SIZE);
    CHECK(cap_gc.released_total == saved_released);
    cap_gc_account_release(&page, 1); /* confirmed release */
    CHECK(page.released);
    CHECK(cap_gc.heap == 0);
    CHECK(cap_gc.released_total == saved_released + 1);
    cap_gc_account_release(&page, 1); /* repeated release is idempotent */
    CHECK(cap_gc.heap == 0);
    CHECK(cap_gc.released_total == saved_released + 1);
    cap_gc.heap = saved_heap;
    cap_gc.released_total = saved_released;
}

static void test_gc_stack_bounds(void) {
    uintptr_t low = 0, high = 0;
    CHECK(cap_gc_stack_bounds((uintptr_t)0x1000, 0x2000, &low, &high));
    CHECK(low == (uintptr_t)0x1000 && high == (uintptr_t)0x3000);
    CHECK(!cap_gc_stack_bounds((uintptr_t)0x1000, 0, &low, &high));
    CHECK(!cap_gc_stack_bounds(UINTPTR_MAX - 7, 16, &low, &high));
}

#define CAP_NLARGE_SECRETS 16
static uintptr_t large_secret_addrs[CAP_NLARGE_SECRETS];
static uintptr_t large_secret_wiped_addrs[CAP_NLARGE_SECRETS];
static size_t large_secret_wipe_observations;
static int large_secret_wipe_clean;

static void observe_large_secret_wipe(const void *memory, size_t n) {
    uintptr_t address = (uintptr_t)memory;
    const volatile unsigned char *bytes = (const volatile unsigned char *)memory;
    if (n == 0 || n % CAP_PAGE_SIZE != 0) large_secret_wipe_clean = 0;
    for (size_t i = 0; i < n; i++)
        if (bytes[i] != 0) large_secret_wipe_clean = 0;
    size_t records = 0;
    for (size_t i = 0; i < cap_gc.nlarge; i++) {
        if ((uintptr_t)cap_gc.large[i].base == address) {
            records++;
            if (cap_gc.large[i].alloc_size != n || cap_gc.large[i].atomic != 2)
                large_secret_wipe_clean = 0;
        }
    }
    if (records != 1) large_secret_wipe_clean = 0;
    int original = 0;
    for (int i = 0; i < CAP_NLARGE_SECRETS; i++) {
        uintptr_t expected = large_secret_addrs[i] ^ (uintptr_t)0x5a5aa5a55a5aa5a5ULL;
        if (expected == address) original++;
    }
    if (original > 1) large_secret_wipe_clean = 0;
    if (original == 0) return;
    if (n < 8192) large_secret_wipe_clean = 0;
    size_t ordinal = large_secret_wipe_observations++;
    if (ordinal >= CAP_NLARGE_SECRETS) {
        large_secret_wipe_clean = 0;
        return;
    }
    large_secret_wiped_addrs[ordinal] = address;
}

__attribute__((noinline)) static void make_large_secrets_for_wipe(void) {
    for (int i = 0; i < CAP_NLARGE_SECRETS; i++) {
        unsigned char *p = (unsigned char *)cap_gc_alloc(8192, 2);
        memset(p, 0xa5, 8192);
        large_secret_addrs[i] = (uintptr_t)p ^ (uintptr_t)0x5a5aa5a55a5aa5a5ULL;
    }
}

static void test_gc_large_secret_mapping(void) {
    size_t heap_before = cap_gc.heap;
    large_secret_wipe_observations = 0;
    large_secret_wipe_clean = 1;
    cap_gc_test_secret_wipe_hook = observe_large_secret_wipe;
    make_large_secrets_for_wipe();
    collect_clean();
    int retained = 0;
    for (int j = 0; j < CAP_NLARGE_SECRETS; j++) {
        uintptr_t address = large_secret_addrs[j] ^ (uintptr_t)0x5a5aa5a55a5aa5a5ULL;
        int records = 0;
        for (size_t i = 0; i < cap_gc.nlarge; i++)
            if ((uintptr_t)cap_gc.large[i].base == address) records++;
        if (records > 1) large_secret_wipe_clean = 0;
        retained += records;
    }
    for (size_t j = 0; j < large_secret_wipe_observations; j++) {
        int records = 0;
        for (size_t i = 0; i < cap_gc.nlarge; i++)
            if ((uintptr_t)cap_gc.large[i].base == large_secret_wiped_addrs[j]) records++;
        if (records != 0) large_secret_wipe_clean = 0;
    }
    cap_gc_test_secret_wipe_hook = NULL;
    size_t heap_after = cap_gc.heap;
    CHECK(large_secret_wipe_observations >= CAP_NLARGE_SECRETS - 1);
    CHECK(large_secret_wipe_clean);
    CHECK(retained <= 1);
    CHECK(heap_after <= heap_before + CAP_PAGE_SIZE);
    const volatile unsigned char *fresh = (const volatile unsigned char *)cap_gc_alloc(8192, 2);
    int zeroed = 1;
    for (size_t i = 0; i < 8192; i++) if (fresh[i] != 0) zeroed = 0;
    CHECK(zeroed);
}

static void test_gc_secret_free_slots(void) {
    size_t checked = 0;
    int clean = 1;
    uint8_t seen[CAP_PAGE_SIZE / 16];
    for (size_t i = 0; i < cap_gc.npages; i++) {
        CapPage *pg = cap_gc.pages[i];
        if (pg->atomic != 2) continue;
        if (!pg->free_slots || pg->free_count > pg->free_cap ||
            pg->free_cap != pg->nobj || pg->nobj > sizeof seen) {
            clean = 0;
            continue;
        }
        memset(seen, 0, pg->nobj);
        for (uint32_t j = 0; j < pg->free_count; j++) {
            uint32_t slot = pg->free_slots[j];
            if (slot >= pg->nobj || seen[slot] || pg->alloc[slot]) {
                clean = 0;
                continue;
            }
            seen[slot] = 1;
            const volatile unsigned char *bytes =
                (const volatile unsigned char *)(pg->base + (size_t)slot * pg->objsize);
            for (uint32_t k = 0; k < pg->objsize; k++)
                if (bytes[k] != 0) clean = 0;
            checked++;
        }
        for (uint32_t j = 0; j < pg->nobj; j++)
            if (!pg->alloc[j] && !seen[j]) clean = 0;
    }
    CHECK(checked > 0 && clean);
}

enum {
    GC_META_ROOT,
    GC_META_MARK_STACK,
    GC_META_PAGE,
    GC_META_SECRET_PAGE,
    GC_META_SPARE,
    GC_META_LARGE
};

static void reset_gc_page_metadata_for_child(void) {
    cap_gc.spare = NULL;
    cap_gc.nspare = cap_gc.capspare = 0;
    cap_gc.pages = NULL;
    cap_gc.npages = cap_gc.cappages = 0;
    cap_gc.ptab = NULL;
    cap_gc.ptab_cap = 0;
}

static void trigger_gc_metadata_site(int site) {
    void *value = NULL;
    switch (site) {
    case GC_META_ROOT:
        cap_gc.roots = NULL;
        cap_gc.nroots = cap_gc.caproots = 0;
        cap_gc_root(&value);
        break;
    case GC_META_MARK_STACK:
        cap_gc.mstack = NULL;
        cap_gc.msp = cap_gc.mcap = 0;
        cap_gc_push(&value, sizeof value);
        break;
    case GC_META_PAGE:
        reset_gc_page_metadata_for_child();
        cap_gc_new_page(0, 0);
        break;
    case GC_META_SECRET_PAGE:
        reset_gc_page_metadata_for_child();
        cap_gc_new_page(2, 0);
        break;
    case GC_META_SPARE: {
        CapPage page;
        memset(&page, 0, sizeof page);
        cap_gc.spare = NULL;
        cap_gc.nspare = cap_gc.capspare = 0;
        cap_gc_spare_page(&page, 0);
        break;
    }
    case GC_META_LARGE:
        cap_gc.large = NULL;
        cap_gc.nlarge = cap_gc.caplarge = 0;
        cap_gc.since = 0;
        cap_gc.threshold = SIZE_MAX;
        cap_gc.stress = 0;
        cap_gc.max_heap = 0;
        (void)cap_gc_alloc(8192, 2);
        break;
    default:
        _exit(90);
    }
}

static void expect_gc_metadata_oom(int site, long successful_allocations) {
    pid_t pid = fork();
    CHECK(pid >= 0);
    if (pid < 0) return;
    if (pid == 0) {
        (void)freopen("/dev/null", "w", stdout);
        (void)freopen("/dev/null", "w", stderr);
        cap_gc_test_meta_fail_after = successful_allocations;
        trigger_gc_metadata_site(site);
        _exit(0);
    }
    int status = 0;
    pid_t waited;
    do { waited = waitpid(pid, &status, 0); } while (waited < 0 && errno == EINTR);
    CHECK(waited == pid);
    CHECK(waited == pid && WIFEXITED(status) && WEXITSTATUS(status) == 102);
}

static void test_gc_metadata_oom(void) {
    expect_gc_metadata_oom(GC_META_ROOT, 0);
    expect_gc_metadata_oom(GC_META_MARK_STACK, 0);
    expect_gc_metadata_oom(GC_META_SPARE, 0);
    expect_gc_metadata_oom(GC_META_LARGE, 0);
    for (long i = 0; i < 5; i++) expect_gc_metadata_oom(GC_META_PAGE, i);
    for (long i = 0; i < 6; i++) expect_gc_metadata_oom(GC_META_SECRET_PAGE, i);
}

static void test_gc_release(void) {
    cap_gc_collect();
    size_t released_before = cap_gc.released_total, heap_before = cap_gc.heap;
    fill_and_drop();
    collect_clean();
    CHECK(cap_gc.released_total > released_before);          /* memory went back */
    CHECK(cap_gc.heap <= heap_before + ((size_t)32 << 20));  /* at most the reserve stays */
    /* A stale pointer into the released memory must not be followed or kept. */
    volatile uintptr_t stale = stale_addr ^ CAP_DISGUISE_GC;
    cap_gc_collect();
    CHECK(stale != 0);
    /* Reuse: allocations of another size class take the spare pages first. */
    size_t reused_before = cap_gc.reused_total, pages_before = cap_gc.npages;
    CapList *keep = cap_list_new();
    for (int i = 0; i < 20000; i++) cap_list_push(keep, cap_vp(cap_str_new("a much longer string that needs a bigger size class than forty bytes", 68)));
    CHECK(cap_gc.npages == pages_before);                     /* no new memory was requested */
    CHECK(cap_gc.reused_total >= reused_before);
    int ok = 1;
    for (int i = 0; i < 20000; i++) if (((CapStr *)keep->items[i].p)->len != 68) ok = 0;
    cap_gc_collect();
    for (int i = 0; i < 20000; i++) if (((CapStr *)keep->items[i].p)->data[0] != 'a') ok = 0;
    CHECK(ok);
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
static void test_secret_env_name(void) {
    setenv("CAPSTAN_UNIT_SECRET_PREFIX", "prefix-value", 1);
    static const char truncated_name[] = "CAPSTAN_UNIT_SECRET_PREFIX\0SUFFIX";
    CHECK(cap_secret_env(cap_str_new(truncated_name, (int64_t)sizeof truncated_name - 1)) == NULL);
    unsetenv("CAPSTAN_UNIT_SECRET_PREFIX");
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

static void test_collection_slot_clearing(void) {
    CapList *list = cap_list_new();
    CapStr *a = cap_str_new("slot-a", 6);
    CapStr *b = cap_str_new("slot-b", 6);
    CapStr *c = cap_str_new("slot-c", 6);
    cap_list_push(list, cap_vp(a));
    CHECK(cap_list_pop_p(list) == a);
    CHECK(list->len == 0 && list->items[0].p == NULL);
    cap_list_push(list, cap_vi(17));
    int64_t *boxed = cap_list_pop_i(list);
    CHECK(boxed && *boxed == 17);
    CHECK(list->len == 0 && list->items[0].i == 0);
    cap_list_push(list, cap_vp(a));
    cap_list_push(list, cap_vp(b));
    CapVal *slots = list->items;
    cap_list_clear(list);
    CHECK(list->len == 0 && slots[0].p == NULL && slots[1].p == NULL);
    cap_list_push(list, cap_vp(a));
    cap_list_push(list, cap_vp(b));
    cap_list_push(list, cap_vp(c));
    CapVal removed = cap_list_remove(list, 1, 0);
    CHECK(removed.p == b);
    CHECK(list->len == 2 && list->items[0].p == a && list->items[1].p == c);
    CHECK(list->items[2].p == NULL);
    CapMap *map = cap_map_new();
    CapStr *ka = cap_str_new("key-a", 5);
    CapStr *kb = cap_str_new("key-b", 5);
    CapStr *va = cap_str_new("value-a", 7);
    CapStr *vb = cap_str_new("value-b", 7);
    cap_map_set(map, ka, cap_vp(va));
    cap_map_set(map, kb, cap_vp(vb));
    CHECK(cap_map_remove(map, ka));
    CHECK(map->len == 1 && map->keys[0] == kb && map->vals[0].p == vb);
    CHECK(map->keys[1] == NULL && map->vals[1].p == NULL);
}

static void test_secret_page_free_stack(void) {
    void *memory = NULL;
    CHECK(posix_memalign(&memory, CAP_PAGE_SIZE, CAP_PAGE_SIZE) == 0);
    if (!memory) return;
    memset(memory, 0xa5, CAP_PAGE_SIZE);
    CapPage page;
    memset(&page, 0, sizeof page);
    page.base = (char *)memory;
    cap_gc_format_page(&page, 2, 0);
    CHECK(page.free_slots != NULL);
    CHECK(page.free_count == page.nobj && page.free_cap == page.nobj);
    int all_zero = 1;
    const volatile unsigned char *bytes = (const volatile unsigned char *)memory;
    for (size_t i = 0; i < CAP_PAGE_SIZE; i++) if (bytes[i] != 0) all_zero = 0;
    CHECK(all_zero);
    unsigned char *seen = (unsigned char *)calloc(page.nobj, 1);
    CHECK(seen != NULL);
    if (seen) {
        int unique = 1;
        for (uint32_t i = 0; i < page.free_count; i++) {
            uint32_t idx = page.free_slots[i];
            if (idx >= page.nobj || seen[idx]) unique = 0;
            else seen[idx] = 1;
        }
        CHECK(unique);
        free(seen);
    }
    free(page.free_slots);
    free(page.alloc);
    free(page.mark);
    free(memory);
}

int main(void) {
    cap_gc_init();
    cap_files = unit_files;
    test_secret_scratch_lifecycle();
    test_siphash_wipe();
    test_sha256();
    test_hmac();
    test_pbkdf2();
    test_pbkdf2_parameter_bounds();
    test_sha256_length_bound();
    test_passwords();
    test_validators();
    test_escapers();
    test_escape_log();
    test_paths();
    test_ranges();
    test_csv();
    test_secret_eq();
    test_files();
    test_bitwise();
    test_string_allocation_bounds();
    test_gc_allocator_arithmetic();
    test_runtime_growth_arithmetic();
    test_collections();
    test_collection_slot_clearing();
    test_arithmetic();
    scrub_stack(16);    /* the 100,000-key map from test_collections must not look live */
    test_gc();
    test_gc_metadata_oom();
    test_gc_release_accounting();
    test_gc_stack_bounds();
    test_secret_page_free_stack();
    test_gc_release();
    test_secret_env_name();
    test_secret_wipe();
    test_gc_secret_free_slots();
    test_gc_large_secret_mapping();
    printf("runtime unit tests: %d checks, %d failed\n", checks, failures);
    return failures ? 1 : 0;
}
