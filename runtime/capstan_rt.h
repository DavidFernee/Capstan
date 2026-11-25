/*
 * Capstan runtime, v0.1
 *
 * Every program the Capstan compiler produces is C code that calls into this
 * header. The compiler's type checker rules out most weakness classes before a
 * program ever runs; the checks here catch the ones that can only be decided at
 * run time (an index computed from input, an overflowing sum), and stop the
 * program safely instead of letting it continue in a corrupted state.
 *
 * Each check names the CWE weakness it prevents.
 *
 * Memory model: values are allocated by the garbage collector in
 * capstan_gc.h and freed automatically. Programs never free memory
 * themselves, so use-after-free and double-free cannot occur.
 */
#ifndef CAPSTAN_RT_H
#define CAPSTAN_RT_H

#if defined(__linux__) && !defined(_GNU_SOURCE)
#define _GNU_SOURCE   /* pthread_getattr_np, used to find the stack bounds */
#endif

#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <setjmp.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include "capstan_gc.h"

/* ------------------------------------------------------------------ */
/* Locations and panics                                               */
/* ------------------------------------------------------------------ */

static const char **cap_files = NULL;   /* set by generated code */
static int cap_test_mode = 0;
static jmp_buf cap_test_jmp;
static int cap_argc = 0;
static char **cap_argv = NULL;

#define CAP_UNLIKELY(x) __builtin_expect(!!(x), 0)
#define CAP_LOC_FILE(loc) ((int)((loc) / 1000000))
#define CAP_LOC_LINE(loc) ((long long)((loc) % 1000000))

__attribute__((noreturn, cold, noinline)) static void cap_panic(const char *what, const char *cwe, int64_t loc) {
    const char *file = cap_files ? cap_files[CAP_LOC_FILE(loc)] : "?";
    fprintf(stderr, "%s:%lld: runtime check failed: %s [%s prevented]\n",
            file, CAP_LOC_LINE(loc), what, cwe);
    if (cap_test_mode) longjmp(cap_test_jmp, 1);
    exit(101);
}

/* Memory that may contain pointers (structs, lists, maps, grants). */
__attribute__((noreturn, cold)) static void cap_unreachable(int64_t loc) {
    cap_panic("match reached an impossible value (internal error)", "CWE-617", loc);
}

static void *cap_alloc(size_t n) { return cap_gc_alloc(n, 0); }
/* Memory that never contains pointers (string bytes, boxed integers). */
static void *cap_alloc_atomic(size_t n) { return cap_gc_alloc(n, 1); }
/* Memory for secrets: pointer-free, and zeroed when collected. */
static void *cap_alloc_secret(size_t n) { return cap_gc_alloc(n, 2); }

static void cap_assert(bool ok, int64_t loc) {
    if (!ok) cap_panic("assertion failed", "test", loc);
}

/* ------------------------------------------------------------------ */
/* Checked integer arithmetic (CWE-190, CWE-191, CWE-369)             */
/* ------------------------------------------------------------------ */

static inline int64_t cap_add(int64_t a, int64_t b, int64_t loc) {
    int64_t r;
    if (CAP_UNLIKELY(__builtin_add_overflow(a, b, &r))) cap_panic("integer overflow in +", "CWE-190", loc);
    return r;
}
static inline int64_t cap_sub(int64_t a, int64_t b, int64_t loc) {
    int64_t r;
    if (CAP_UNLIKELY(__builtin_sub_overflow(a, b, &r))) cap_panic("integer overflow in -", "CWE-191", loc);
    return r;
}
static inline int64_t cap_mul(int64_t a, int64_t b, int64_t loc) {
    int64_t r;
    if (CAP_UNLIKELY(__builtin_mul_overflow(a, b, &r))) cap_panic("integer overflow in *", "CWE-190", loc);
    return r;
}
static inline int64_t cap_div(int64_t a, int64_t b, int64_t loc) {
    if (b == 0) cap_panic("division by zero", "CWE-369", loc);
    if (a == INT64_MIN && b == -1) cap_panic("integer overflow in /", "CWE-190", loc);
    return a / b;
}
static inline int64_t cap_mod(int64_t a, int64_t b, int64_t loc) {
    if (b == 0) cap_panic("division by zero", "CWE-369", loc);
    if (a == INT64_MIN && b == -1) return 0;
    return a % b;
}
static inline int64_t cap_neg(int64_t a, int64_t loc) {
    if (a == INT64_MIN) cap_panic("integer overflow in unary -", "CWE-190", loc);
    return -a;
}

/* Bitwise shifts (CWE-1335): the count must be 0..63. << is checked like
   multiplication (no bit may be lost, CWE-190); >> keeps the sign, >>> fills with
   zeros. Written so that every case is defined behaviour in C. */
static inline int64_t cap_shift_count(int64_t n, int64_t loc) {
    if (CAP_UNLIKELY(n < 0 || n > 63)) cap_panic("shift count outside 0..63", "CWE-1335", loc);
    return n;
}
/* uint64_t to int64_t without relying on implementation-defined conversion. */
static inline int64_t cap_as_signed(uint64_t u) {
    return u <= (uint64_t)INT64_MAX ? (int64_t)u : -(int64_t)(~u) - 1;
}
static inline int64_t cap_shl(int64_t a, int64_t n, int64_t loc) {
    cap_shift_count(n, loc);
    int64_t r = cap_as_signed((uint64_t)a << n);
    int64_t back = r < 0 ? ~(int64_t)((uint64_t)~r >> n) : (int64_t)((uint64_t)r >> n);
    if (CAP_UNLIKELY(back != a)) cap_panic("integer overflow in <<", "CWE-190", loc);
    return r;
}
static inline int64_t cap_sar(int64_t a, int64_t n, int64_t loc) {
    cap_shift_count(n, loc);
    return a < 0 ? ~(int64_t)((uint64_t)~a >> n) : (int64_t)((uint64_t)a >> n);
}
static inline int64_t cap_shr(int64_t a, int64_t n, int64_t loc) {
    cap_shift_count(n, loc);
    return cap_as_signed((uint64_t)a >> n);
}
/* Explicit modular arithmetic, for hashing and cryptography. */
static inline int64_t cap_wrapping_add(int64_t a, int64_t b) { return cap_as_signed((uint64_t)a + (uint64_t)b); }
static inline int64_t cap_wrapping_sub(int64_t a, int64_t b) { return cap_as_signed((uint64_t)a - (uint64_t)b); }
static inline int64_t cap_wrapping_mul(int64_t a, int64_t b) { return cap_as_signed((uint64_t)a * (uint64_t)b); }
static inline int64_t cap_wrapping_shl(int64_t a, int64_t n, int64_t loc) {
    cap_shift_count(n, loc);
    return cap_as_signed((uint64_t)a << n);
}

/* Proved forms: used only where the compiler's range analysis has proved that the
   check cannot fail (compiler/ranges.cap), so the check is done at compile time
   instead of at run time. Same arguments, so evaluation is unchanged. */
static inline int64_t cap_add_proved(int64_t a, int64_t b, int64_t loc) { (void)loc; return a + b; }
static inline int64_t cap_sub_proved(int64_t a, int64_t b, int64_t loc) { (void)loc; return a - b; }
static inline int64_t cap_mul_proved(int64_t a, int64_t b, int64_t loc) { (void)loc; return a * b; }
static inline int64_t cap_div_proved(int64_t a, int64_t b, int64_t loc) { (void)loc; return a / b; }
static inline int64_t cap_mod_proved(int64_t a, int64_t b, int64_t loc) { (void)loc; return a % b; }
static inline int64_t cap_neg_proved(int64_t a, int64_t loc) { (void)loc; return -a; }
static inline int64_t cap_shl_proved(int64_t a, int64_t n, int64_t loc) { (void)loc; return cap_as_signed((uint64_t)a << n); }
static inline int64_t cap_sar_proved(int64_t a, int64_t n, int64_t loc) { (void)loc; return a < 0 ? ~(int64_t)((uint64_t)~a >> n) : (int64_t)((uint64_t)a >> n); }
static inline int64_t cap_shr_proved(int64_t a, int64_t n, int64_t loc) { (void)loc; return cap_as_signed((uint64_t)a >> n); }

/* Optional int/bool are boxed; none is NULL. */
static int64_t *cap_box_int(int64_t v) {
    int64_t *p = (int64_t *)cap_alloc_atomic(sizeof(int64_t));
    *p = v;
    return p;
}

/* ------------------------------------------------------------------ */
/* Strings: immutable, length-prefixed, always bounds-checked          */
/* ------------------------------------------------------------------ */

typedef struct CapStr { int64_t len; char data[]; } CapStr;

/* All string allocation sizes are checked before converting a signed length
   to size_t or multiplying for an escaping expansion. */
static size_t cap_rt_checked_string_bytes(int64_t len, size_t expansion,
                                          size_t extra, int64_t loc) {
    if (len < 0 || !expansion || extra > CAP_MAX_LEN ||
        sizeof(CapStr) > CAP_MAX_LEN - extra ||
        sizeof(CapStr) > SIZE_MAX - extra)
        cap_panic("invalid string allocation length", "CWE-682", loc);
    size_t available = CAP_MAX_LEN - sizeof(CapStr) - extra;
    size_t size_available = SIZE_MAX - sizeof(CapStr) - extra;
    if ((uint64_t)len > available / expansion ||
        (uint64_t)len > size_available / expansion)
        cap_panic("string allocation exceeds runtime limit", "CWE-789", loc);
    return sizeof(CapStr) + (size_t)len * expansion + extra;
}

static CapStr *cap_str_new(const char *s, int64_t n) {
    if (n > 0 && !s)
        cap_panic("null source for non-empty string", "CWE-476", 0);
    CapStr *r = (CapStr *)cap_alloc_atomic(cap_rt_checked_string_bytes(n, 1, 1, 0));
    r->len = n;
    if (n > 0) memcpy(r->data, s, (size_t)n);
    r->data[n] = 0;
    return r;
}

/* String literals are allocated once per site, outside the collected heap. */
static CapStr *cap_str_perm(const char *s, int64_t n) {
    if (n > 0 && !s)
        cap_panic("null source for non-empty permanent string", "CWE-476", 0);
    CapStr *r = (CapStr *)malloc(cap_rt_checked_string_bytes(n, 1, 1, 0));
    if (!r) cap_gc_oom();
    r->len = n;
    if (n > 0) memcpy(r->data, s, (size_t)n);
    r->data[n] = 0;
    return r;
}
#define CAP_LIT(s, n) ({ static CapStr *_cap_lit = NULL; \
    if (!_cap_lit) { _cap_lit = cap_str_perm((s), (n)); } _cap_lit; })

static CapStr *cap_str_concat(CapStr *a, CapStr *b, int64_t loc) {
    if (!a || !b || a->len < 0 || b->len < 0)
        cap_panic("invalid string operand", "CWE-682", loc);
    int64_t n = cap_add(a->len, b->len, loc);
    CapStr *r = (CapStr *)cap_alloc_atomic(cap_rt_checked_string_bytes(n, 1, 1, loc));
    r->len = n;
    memcpy(r->data, a->data, (size_t)a->len);
    memcpy(r->data + a->len, b->data, (size_t)b->len);
    r->data[n] = 0;
    return r;
}

static bool cap_str_eq(CapStr *a, CapStr *b) {
    return a->len == b->len && memcmp(a->data, b->data, (size_t)a->len) == 0;
}

static inline int64_t cap_str_at(CapStr *s, int64_t i, int64_t loc) {
    if (CAP_UNLIKELY((uint64_t)i >= (uint64_t)s->len)) cap_panic("string index out of bounds", "CWE-125", loc);
    return (int64_t)(unsigned char)s->data[i];
}
static inline int64_t cap_str_at_proved(CapStr *s, int64_t i, int64_t loc) { (void)loc; return (int64_t)(unsigned char)s->data[i]; }

static CapStr *cap_str_slice(CapStr *s, int64_t a, int64_t b, int64_t loc) {
    if (a < 0 || b < a || b > s->len) cap_panic("string slice out of bounds", "CWE-125", loc);
    return cap_str_new(s->data + a, b - a);
}

/* Decimal text of v, written right to left: no printf machinery (part of T4's aim of
   leaving libc's formatting functions out of the trusted base). The magnitude is taken
   in unsigned arithmetic, so INT64_MIN needs no special case. */
static CapStr *cap_int_to_str(int64_t v) {
    char buf[24];
    int i = (int)sizeof buf;
    uint64_t u = v < 0 ? (uint64_t)0 - (uint64_t)v : (uint64_t)v;
    do {
        buf[--i] = (char)('0' + (int)(u % 10));
        u /= 10;
    } while (u != 0);
    if (v < 0) buf[--i] = '-';
    return cap_str_new(buf + i, (int64_t)sizeof buf - i);
}

static CapStr *cap_char_str(int64_t c, int64_t loc) {
    if (c < 0 || c > 255) cap_panic("char_str value outside 0..255", "CWE-704", loc);
    char ch = (char)c;
    return cap_str_new(&ch, 1);
}

/* ------------------------------------------------------------------ */
/* Lists: growable, bounds-checked                                     */
/* ------------------------------------------------------------------ */

/* Checked container/buffer sizing. The collector caps individual managed
   allocations at CAP_MAX_LEN; include the object header when sizing payloads. */
static size_t cap_rt_max_count(size_t element_size, size_t overhead, int64_t loc) {
    if (!element_size || overhead > CAP_MAX_LEN)
        cap_panic("invalid allocation element size", "CWE-190", loc);
    size_t max_bytes = CAP_MAX_LEN - overhead;
    size_t count = max_bytes / element_size;
    return count > (size_t)INT64_MAX ? (size_t)INT64_MAX : count;
}

static int64_t cap_rt_growth_capacity(int64_t current, int64_t required,
                                      int64_t initial, size_t element_size,
                                      size_t overhead, int64_t loc) {
    size_t max_count = cap_rt_max_count(element_size, overhead, loc);
    if (current < 0 || required < 0 || initial <= 0 ||
        (uint64_t)current > max_count || (uint64_t)required > max_count)
        cap_panic("container capacity exceeds allocation limit", "CWE-789", loc);
    size_t cap = current ? (size_t)current : (size_t)initial;
    if (cap > max_count)
        cap_panic("initial container capacity exceeds allocation limit", "CWE-789", loc);
    while (cap < (size_t)required) {
        if (cap > max_count / 2) cap = max_count;
        else cap *= 2;
        if (cap == 0)
            cap_panic("container capacity growth overflow", "CWE-190", loc);
    }
    return (int64_t)cap;
}

static size_t cap_rt_checked_bytes(size_t count, size_t element_size,
                                   size_t overhead, int64_t loc) {
    if (!element_size || overhead > CAP_MAX_LEN ||
        count > (CAP_MAX_LEN - overhead) / element_size ||
        count > (SIZE_MAX - overhead) / element_size)
        cap_panic("allocation size exceeds runtime limit", "CWE-789", loc);
    return overhead + count * element_size;
}

typedef union CapVal { int64_t i; void *p; } CapVal;
static inline CapVal cap_vi(int64_t i) { CapVal v; v.i = i; return v; }
static inline CapVal cap_vp(void *p) { CapVal v; v.p = p; return v; }

typedef struct CapList { int64_t len, cap; CapVal *items; } CapList;

static CapList *cap_list_new(void) {
    return (CapList *)cap_alloc(sizeof(CapList));
}

static inline void cap_list_push(CapList *l, CapVal v) {
    if (CAP_UNLIKELY(!l || l->len < 0 || l->cap < 0 || l->len > l->cap ||
                     (l->cap > 0 && !l->items)))
        cap_panic("invalid list length/capacity", "CWE-682", 0);
    if (CAP_UNLIKELY(l->len == l->cap)) {
        if (l->len == INT64_MAX)
            cap_panic("list length exceeds allocation limit", "CWE-789", 0);
        int64_t nc = cap_rt_growth_capacity(l->cap, l->len + 1, 8, sizeof(CapVal), 0, 0);
        size_t bytes = cap_rt_checked_bytes((size_t)nc, sizeof(CapVal), 0, 0);
        CapVal *ni = (CapVal *)cap_alloc(bytes);
        if (l->len) memcpy(ni, l->items, cap_rt_checked_bytes((size_t)l->len, sizeof(CapVal), 0, 0));
        l->items = ni;
        l->cap = nc;
    }
    l->items[l->len++] = v;
}

static inline CapVal cap_list_get(CapList *l, int64_t i, int64_t loc) {
    if (CAP_UNLIKELY((uint64_t)i >= (uint64_t)l->len)) cap_panic("list index out of bounds", "CWE-125", loc);
    return l->items[i];
}

static inline void cap_list_set(CapList *l, int64_t i, CapVal v, int64_t loc) {
    if (CAP_UNLIKELY((uint64_t)i >= (uint64_t)l->len)) cap_panic("list index out of bounds", "CWE-787", loc);
    l->items[i] = v;
}
static inline CapVal cap_list_get_proved(CapList *l, int64_t i, int64_t loc) { (void)loc; return l->items[i]; }
static inline void cap_list_set_proved(CapList *l, int64_t i, CapVal v, int64_t loc) { (void)loc; l->items[i] = v; }

static void *cap_list_pop_p(CapList *l) {
    if (l->len == 0) return NULL;
    int64_t last = --l->len;
    void *value = l->items[last].p;
    l->items[last] = cap_vp(NULL);
    return value;
}

static int64_t *cap_list_pop_i(CapList *l) {
    if (l->len == 0) return NULL;
    int64_t last = --l->len;
    int64_t value = l->items[last].i;
    l->items[last] = cap_vi(0);
    return cap_box_int(value);
}

/* Unboxed form for `if (let v = xs.pop())`, read immediately (see cap_map_peek_i). */
static int64_t *cap_list_pop_peek_i(CapList *l) {
    if (l->len == 0) return NULL;
    return &l->items[--l->len].i;
}

static void cap_list_clear(CapList *l) {
    if (l->len > 0) memset(l->items, 0, (size_t)l->len * sizeof(CapVal));
    l->len = 0;
}

static CapVal cap_list_remove(CapList *l, int64_t i, int64_t loc) {
    if (CAP_UNLIKELY((uint64_t)i >= (uint64_t)l->len)) cap_panic("list index out of bounds", "CWE-125", loc);
    CapVal v = l->items[i];
    memmove(l->items + i, l->items + i + 1, sizeof(CapVal) * (size_t)(l->len - i - 1));
    l->len--;
    l->items[l->len] = cap_vp(NULL);
    return v;
}

static void cap_list_insert(CapList *l, int64_t i, CapVal v, int64_t loc) {
    if (CAP_UNLIKELY((uint64_t)i > (uint64_t)l->len)) cap_panic("list insert position out of bounds", "CWE-787", loc);
    cap_list_push(l, v);
    memmove(l->items + i + 1, l->items + i, sizeof(CapVal) * (size_t)(l->len - 1 - i));
    l->items[i] = v;
}

/* Stable merge sort, so equal elements keep their order on every platform. */
static int cap_cmp_i(CapVal a, CapVal b) { return a.i < b.i ? -1 : a.i > b.i; }
static int cap_cmp_s(CapVal a, CapVal b) {
    CapStr *x = (CapStr *)a.p, *y = (CapStr *)b.p;
    int64_t n = x->len < y->len ? x->len : y->len;
    int c = memcmp(x->data, y->data, (size_t)n);
    if (c) return c;
    return x->len < y->len ? -1 : x->len > y->len;
}

static void cap_merge_sort(CapVal *a, CapVal *tmp, int64_t n, int (*cmp)(CapVal, CapVal)) {
    if (n < 2) return;
    int64_t h = n / 2;
    cap_merge_sort(a, tmp, h, cmp);
    cap_merge_sort(a + h, tmp, n - h, cmp);
    int64_t i = 0, j = h, k = 0;
    while (i < h && j < n) tmp[k++] = cmp(a[j], a[i]) < 0 ? a[j++] : a[i++];
    while (i < h) tmp[k++] = a[i++];
    while (j < n) tmp[k++] = a[j++];
    memcpy(a, tmp, sizeof(CapVal) * (size_t)n);
}

static void cap_list_sort_i(CapList *l) {
    CapVal *tmp = (CapVal *)cap_alloc_atomic(sizeof(CapVal) * (size_t)(l->len ? l->len : 1));
    cap_merge_sort(l->items, tmp, l->len, cap_cmp_i);
}

static void cap_list_sort_s(CapList *l) {
    CapVal *tmp = (CapVal *)cap_alloc(sizeof(CapVal) * (size_t)(l->len ? l->len : 1));
    cap_merge_sort(l->items, tmp, l->len, cap_cmp_s);
}

/* Packed List<bool>: one byte per element instead of eight. */
/* Elements are stored as bool, not uint8_t: a store through a character type may
   alias anything, which forced the C compiler to reload len and items after every
   write in a loop; bool stores cannot alias the int64_t fields. */
typedef struct CapBList { int64_t len, cap; bool *items; } CapBList;

static CapBList *cap_blist_new(void) { return (CapBList *)cap_alloc(sizeof(CapBList)); }

static inline void cap_blist_push(CapBList *l, bool v) {
    if (CAP_UNLIKELY(!l || l->len < 0 || l->cap < 0 || l->len > l->cap ||
                     (l->cap > 0 && !l->items)))
        cap_panic("invalid boolean-list length/capacity", "CWE-682", 0);
    if (CAP_UNLIKELY(l->len == l->cap)) {
        if (l->len == INT64_MAX)
            cap_panic("boolean-list length exceeds allocation limit", "CWE-789", 0);
        int64_t nc = cap_rt_growth_capacity(l->cap, l->len + 1, 16, sizeof(bool), 0, 0);
        size_t bytes = cap_rt_checked_bytes((size_t)nc, sizeof(bool), 0, 0);
        bool *ni = (bool *)cap_alloc_atomic(bytes);
        if (l->len) memcpy(ni, l->items, cap_rt_checked_bytes((size_t)l->len, sizeof(bool), 0, 0));
        l->items = ni;
        l->cap = nc;
    }
    l->items[l->len++] = v;
}

static inline bool cap_blist_get(CapBList *l, int64_t i, int64_t loc) {
    if (CAP_UNLIKELY((uint64_t)i >= (uint64_t)l->len)) cap_panic("list index out of bounds", "CWE-125", loc);
    return l->items[i];
}

static inline void cap_blist_set(CapBList *l, int64_t i, bool v, int64_t loc) {
    if (CAP_UNLIKELY((uint64_t)i >= (uint64_t)l->len)) cap_panic("list index out of bounds", "CWE-787", loc);
    l->items[i] = v;
}
static inline bool cap_blist_get_proved(CapBList *l, int64_t i, int64_t loc) { (void)loc; return l->items[i]; }
static inline void cap_blist_set_proved(CapBList *l, int64_t i, bool v, int64_t loc) { (void)loc; l->items[i] = v; }

static int64_t *cap_blist_pop(CapBList *l) {
    if (l->len == 0) return NULL;
    return cap_box_int(l->items[--l->len]);
}

static void cap_blist_clear(CapBList *l) { l->len = 0; }

static bool cap_blist_remove(CapBList *l, int64_t i, int64_t loc) {
    if (CAP_UNLIKELY((uint64_t)i >= (uint64_t)l->len)) cap_panic("list index out of bounds", "CWE-125", loc);
    bool v = l->items[i];
    memmove(l->items + i, l->items + i + 1, (size_t)(l->len - i - 1) * sizeof(bool));
    l->len--;
    return v;
}

static void cap_blist_insert(CapBList *l, int64_t i, bool v, int64_t loc) {
    if (CAP_UNLIKELY((uint64_t)i > (uint64_t)l->len)) cap_panic("list insert position out of bounds", "CWE-787", loc);
    cap_blist_push(l, v);
    memmove(l->items + i + 1, l->items + i, (size_t)(l->len - 1 - i) * sizeof(bool));
    l->items[i] = v;
}

static CapStr *cap_join(CapList *parts, CapStr *sep, int64_t loc) {
    if (!parts || !sep || parts->len < 0 || parts->cap < 0 ||
        parts->len > parts->cap || sep->len < 0 ||
        (parts->cap > 0 && !parts->items))
        cap_panic("invalid string join operands", "CWE-682", loc);
    int64_t total = 0;
    for (int64_t i = 0; i < parts->len; i++) {
        CapStr *part = (CapStr *)parts->items[i].p;
        if (!part || part->len < 0)
            cap_panic("invalid string in join parts", "CWE-682", loc);
        total = cap_add(total, part->len, loc);
        if (i > 0) total = cap_add(total, sep->len, loc);
    }
    CapStr *r = (CapStr *)cap_alloc_atomic(cap_rt_checked_string_bytes(total, 1, 1, loc));
    r->len = total;
    char *w = r->data;
    for (int64_t i = 0; i < parts->len; i++) {
        if (i > 0) { memcpy(w, sep->data, (size_t)sep->len); w += sep->len; }
        CapStr *p = (CapStr *)parts->items[i].p;
        memcpy(w, p->data, (size_t)p->len);
        w += p->len;
    }
    *w = 0;
    return r;
}

/* ------------------------------------------------------------------ */
/* Maps: string keys, insertion-ordered (deterministic iteration)      */
/* ------------------------------------------------------------------ */

typedef struct CapMap {
    int64_t len, cap;
    CapStr **keys;
    CapVal *vals;
    int64_t *index;     /* open addressing: slot -> position+1, 0 = empty */
    int64_t index_cap;
} CapMap;

/* Map keys are hashed with SipHash-1-3 under a random key chosen once per process
   (as Rust and Python do), so an attacker who chooses the keys cannot make them
   collide and turn every lookup into a scan of the table (hash flooding, CWE-407).
   cap_siphash is the generic SipHash-c-d; tests check it against the published
   SipHash-2-4 vectors and an independent implementation. */
#define CAP_ROTL64(x, b) (uint64_t)(((x) << (b)) | ((x) >> (64 - (b))))
#define CAP_SIPROUND do { \
    v0 += v1; v1 = CAP_ROTL64(v1, 13); v1 ^= v0; v0 = CAP_ROTL64(v0, 32); \
    v2 += v3; v3 = CAP_ROTL64(v3, 16); v3 ^= v2; \
    v0 += v3; v3 = CAP_ROTL64(v3, 21); v3 ^= v0; \
    v2 += v1; v1 = CAP_ROTL64(v1, 17); v1 ^= v2; v2 = CAP_ROTL64(v2, 32); } while (0)

static uint64_t cap_siphash(const unsigned char *in, size_t len, uint64_t k0, uint64_t k1, int c, int d) {
    uint64_t v0 = 0x736f6d6570736575ULL ^ k0, v1 = 0x646f72616e646f6dULL ^ k1;
    uint64_t v2 = 0x6c7967656e657261ULL ^ k0, v3 = 0x7465646279746573ULL ^ k1;
    size_t full = len - len % 8;
    for (size_t i = 0; i < full; i += 8) {
        uint64_t m = 0;
        for (int j = 7; j >= 0; j--) m = (m << 8) | in[i + (size_t)j];
        v3 ^= m;
        for (int r = 0; r < c; r++) CAP_SIPROUND;
        v0 ^= m;
    }
    uint64_t b = (uint64_t)len << 56;
    for (size_t j = 0; j < len % 8; j++) b |= (uint64_t)in[full + j] << (8 * j);
    v3 ^= b;
    for (int r = 0; r < c; r++) CAP_SIPROUND;
    v0 ^= b;
    v2 ^= 0xff;
    for (int r = 0; r < d; r++) CAP_SIPROUND;
    return v0 ^ v1 ^ v2 ^ v3;
}

static uint64_t cap_map_k0, cap_map_k1;
static bool cap_map_keyed;

/* The SipHash key remains process-global; clear its temporary stack copy. */
static void cap_wipe(void *p, size_t n);

static void cap_map_key_init(void) {
    unsigned char k[16] = {0};
    FILE *r = fopen("/dev/urandom", "rb");
    if (!r) {
        cap_wipe(k, sizeof k);
        fprintf(stderr, "capstan: no secure randomness available\n");
        exit(103);
    }
    size_t got = fread(k, 1, sizeof k, r);
    fclose(r);
    if (got != sizeof k) {
        cap_wipe(k, sizeof k);
        fprintf(stderr, "capstan: no secure randomness available\n");
        exit(103);
    }
    cap_map_k0 = cap_map_k1 = 0;
    for (int i = 7; i >= 0; i--) { cap_map_k0 = (cap_map_k0 << 8) | k[i]; cap_map_k1 = (cap_map_k1 << 8) | k[8 + i]; }
    cap_wipe(k, sizeof k);
    cap_map_keyed = true;
}

static uint64_t cap_hash_str(CapStr *s) {
    return cap_siphash((const unsigned char *)s->data, (size_t)s->len, cap_map_k0, cap_map_k1, 1, 3);
}

static CapMap *cap_map_new(void) {
    if (!cap_map_keyed) cap_map_key_init();
    return (CapMap *)cap_alloc(sizeof(CapMap));
}

static int64_t cap_map_find(CapMap *m, CapStr *k) {
    /* Validate the complete probe invariant before deriving an index or
       dereferencing any backing array. A corrupt index entry must not turn a
       lookup into an out-of-bounds read. */
    if (!m || !k || m->len < 0 || m->cap < 0 || m->len > m->cap ||
        (m->cap > 0 && (!m->keys || !m->vals)) ||
        (m->len > 0 && (!m->keys || !m->vals)) ||
        m->index_cap < 0 ||
        (m->index_cap != 0 && (m->index_cap & (m->index_cap - 1)) != 0) ||
        (m->index_cap > 0 && !m->index) ||
        (m->index_cap == 0 && m->len != 0) ||
        (m->index_cap > 0 && m->len > m->index_cap / 2))
        cap_panic("invalid map lookup invariants", "CWE-682", 0);
    if (m->index_cap == 0) return -1;
    uint64_t mask = (uint64_t)m->index_cap - 1;
    uint64_t s = cap_hash_str(k) & mask;
    for (int64_t probes = 0; probes < m->index_cap; probes++) {
        int64_t entry = m->index[s];
        if (entry == 0) return -1;
        if (entry < 1 || entry > m->len)
            cap_panic("map index entry outside live range", "CWE-125", 0);
        int64_t pos = entry - 1;
        if (!m->keys[pos])
            cap_panic("null key in live map entry", "CWE-476", 0);
        if (cap_str_eq(m->keys[pos], k)) return pos;
        s = (s + 1) & mask;
    }
    cap_panic("map index has no empty slot", "CWE-400", 0);
}

static void cap_map_reindex(CapMap *m, int64_t newcap) {
    if (newcap <= 0 || (newcap & (newcap - 1)) != 0)
        cap_panic("invalid map index capacity", "CWE-682", 0);
    size_t bytes = cap_rt_checked_bytes((size_t)newcap, sizeof(int64_t), 0, 0);
    int64_t *new_index = (int64_t *)cap_alloc_atomic(bytes);
    m->index = new_index;
    m->index_cap = newcap;
    uint64_t mask = (uint64_t)newcap - 1;
    for (int64_t pos = 0; pos < m->len; pos++) {
        uint64_t s = cap_hash_str(m->keys[pos]) & mask;
        while (m->index[s]) s = (s + 1) & mask;
        m->index[s] = pos + 1;
    }
}

static void cap_map_set(CapMap *m, CapStr *k, CapVal v) {
    int64_t pos = cap_map_find(m, k);
    if (pos >= 0) { m->vals[pos] = v; return; }
    if (CAP_UNLIKELY(m->len < 0 || m->cap < 0 || m->len > m->cap ||
                     m->index_cap < 0 ||
                     (m->index_cap != 0 && (m->index_cap & (m->index_cap - 1)) != 0)))
        cap_panic("invalid map length/capacity", "CWE-682", 0);
    if (m->len == m->cap) {
        if (m->len == INT64_MAX)
            cap_panic("map length exceeds allocation limit", "CWE-789", 0);
        int64_t nc = cap_rt_growth_capacity(m->cap, m->len + 1, 8,
                                            sizeof(CapVal) > sizeof(CapStr *) ? sizeof(CapVal) : sizeof(CapStr *),
                                            0, 0);
        CapStr **nk = (CapStr **)cap_alloc(cap_rt_checked_bytes((size_t)nc, sizeof(CapStr *), 0, 0));
        CapVal *nv = (CapVal *)cap_alloc(cap_rt_checked_bytes((size_t)nc, sizeof(CapVal), 0, 0));
        if (m->len) {
            size_t key_bytes = cap_rt_checked_bytes((size_t)m->len, sizeof(CapStr *), 0, 0);
            size_t val_bytes = cap_rt_checked_bytes((size_t)m->len, sizeof(CapVal), 0, 0);
            memcpy(nk, m->keys, key_bytes);
            memcpy(nv, m->vals, val_bytes);
        }
        m->keys = nk; m->vals = nv; m->cap = nc;
    }
    if (m->len == INT64_MAX)
        cap_panic("map length exceeds allocation limit", "CWE-789", 0);
    int64_t new_len = m->len + 1;
    if (m->index_cap == 0 || new_len > m->index_cap / 2) {
        if (new_len > INT64_MAX / 2)
            cap_panic("map index capacity overflow", "CWE-190", 0);
        int64_t required = new_len * 2;
        int64_t newcap = cap_rt_growth_capacity(m->index_cap, required, 16,
                                                sizeof(int64_t), 0, 0);
        /* Publish the entry before allocation: a collection during index
           growth must see the new key/value through the map's traced arrays. */
        m->keys[m->len] = k;
        m->vals[m->len] = v;
        m->len = new_len;
        cap_map_reindex(m, newcap);
    } else {
        m->keys[m->len] = k;
        m->vals[m->len] = v;
        m->len = new_len;
        uint64_t mask = (uint64_t)m->index_cap - 1;
        uint64_t s = cap_hash_str(k) & mask;
        while (m->index[s]) s = (s + 1) & mask;
        m->index[s] = m->len;
    }
}

static bool cap_map_has(CapMap *m, CapStr *k) { return cap_map_find(m, k) >= 0; }

static void *cap_map_get_p(CapMap *m, CapStr *k) {
    int64_t pos = cap_map_find(m, k);
    return pos < 0 ? NULL : m->vals[pos].p;
}

static int64_t *cap_map_get_i(CapMap *m, CapStr *k) {
    int64_t pos = cap_map_find(m, k);
    return pos < 0 ? NULL : cap_box_int(m->vals[pos].i);
}

/* Unboxed form for `if (let v = m.get(k))`: a pointer into the entry itself, valid
   until the map next changes. The generated code reads it immediately. */
static int64_t *cap_map_peek_i(CapMap *m, CapStr *k) {
    int64_t pos = cap_map_find(m, k);
    return pos < 0 ? NULL : &m->vals[pos].i;
}

/* Remove a key, keeping the remaining keys in insertion order. */
static bool cap_map_remove(CapMap *m, CapStr *k) {
    int64_t pos = cap_map_find(m, k);
    if (pos < 0) return false;
    memmove(m->keys + pos, m->keys + pos + 1, sizeof(CapStr *) * (size_t)(m->len - pos - 1));
    memmove(m->vals + pos, m->vals + pos + 1, sizeof(CapVal) * (size_t)(m->len - pos - 1));
    m->len--;
    /* Clear vacated traced slots before reindexing can allocate and collect. */
    m->keys[m->len] = NULL;
    m->vals[m->len] = cap_vp(NULL);
    cap_map_reindex(m, m->index_cap);
    return true;
}

static CapList *cap_map_keys(CapMap *m) {
    CapList *l = cap_list_new();
    for (int64_t i = 0; i < m->len; i++) cap_list_push(l, cap_vp(m->keys[i]));
    return l;
}

/* ------------------------------------------------------------------ */
/* Authorisation grants (CWE-862, CWE-639)                             */
/* ------------------------------------------------------------------ */

#define CAP_GRANT_MAX 8
/* A grant also keeps the policy's arguments and a function that evaluates the policy on them
   again, so a protected call fails if what the policy checked has changed since (CWE-367). */
typedef struct CapGrant {
    int64_t policy; int64_t n; void *bound[CAP_GRANT_MAX];
    bool (*recheck)(void *args); void *args;
} CapGrant;

static CapGrant *cap_grant_new(int64_t policy) {
    CapGrant *g = (CapGrant *)cap_alloc(sizeof(CapGrant));
    g->policy = policy;
    return g;
}

static CapGrant *cap_grant_bind(CapGrant *g, void *obj) {
    if (g->n < CAP_GRANT_MAX) g->bound[g->n++] = obj;
    return g;
}

static void cap_grant_recheck(CapGrant *g, int64_t loc) {
    if (g->recheck && !g->recheck(g->args))
        cap_panic("the policy no longer allows this: what it checked has changed since the grant was issued", "CWE-367", loc);
}

/* Check the policy identity even when a policy has no struct arguments. */
static void cap_grant_policy_check(CapGrant *g, int64_t policy, int64_t loc) {
    if (g->policy != policy) cap_panic("grant issued by a different policy", "CWE-863", loc);
}

/* A grant is only valid for the exact objects and values in their policy-argument roles. */
static void cap_grant_check(CapGrant *g, int64_t policy, int64_t slot, void *obj, int64_t loc) {
    if (g->policy != policy) cap_panic("grant issued by a different policy", "CWE-863", loc);
    if (slot < 0 || slot >= g->n || g->bound[slot] != obj)
        cap_panic("grant used on an object in the wrong policy-argument role", "CWE-639", loc);
}

/* ------------------------------------------------------------------ */
/* I/O                                                                 */
/* ------------------------------------------------------------------ */

static void cap_print(CapStr *s) { fwrite(s->data, 1, (size_t)s->len, stdout); }
static void cap_println(CapStr *s) { cap_print(s); fputc('\n', stdout); }

__attribute__((noreturn)) static void cap_exit(int64_t code) { fflush(stdout); exit((int)code); }

static CapList *cap_args(void) {
    CapList *l = cap_list_new();
    for (int i = 1; i < cap_argc; i++) cap_list_push(l, cap_vp(cap_str_new(cap_argv[i], (int64_t)strlen(cap_argv[i]))));
    return l;
}

/* A path is passed to the C library as a NUL-terminated string, so a path that
   contains a NUL byte would silently name a different file (CWE-158). */
static bool cap_path_ok(CapStr *path) {
    return path->len > 0 && memchr(path->data, 0, (size_t)path->len) == NULL;
}

/* A growable byte buffer on the collected heap, so the heap limit applies to input
   of any size. */
typedef struct CapBuf { CapStr *s; int64_t cap; } CapBuf;

static void cap_buf_put(CapBuf *b, const char *p, int64_t n) {
    if (!b || !b->s || n < 0 || b->s->len < 0 || b->cap < 1 ||
        b->s->len >= b->cap || (n > 0 && !p))
        cap_panic("invalid byte-buffer state or append length", "CWE-682", 0);
    if (n > INT64_MAX - b->s->len - 1)
        cap_panic("byte-buffer length overflow", "CWE-190", 0);
    int64_t required = b->s->len + n + 1;
    if (required > (int64_t)(CAP_MAX_LEN - sizeof(CapStr)))
        cap_panic("byte-buffer exceeds allocation limit", "CWE-789", 0);
    if (required > b->cap) {
        int64_t nc = cap_rt_growth_capacity(b->cap, required, 64, 1,
                                            sizeof(CapStr), 0);
        size_t bytes = cap_rt_checked_bytes((size_t)nc, 1, sizeof(CapStr), 0);
        CapStr *ns = (CapStr *)cap_alloc_atomic(bytes);
        ns->len = b->s->len;
        memcpy(ns->data, b->s->data, (size_t)b->s->len);
        b->s = ns;
        b->cap = nc;
    }
    if (n) memcpy(b->s->data + b->s->len, p, (size_t)n);
    b->s->len = required - 1;
    b->s->data[b->s->len] = 0;
}

static CapBuf cap_buf_new(int64_t cap) {
    CapBuf b;
    if (cap < 0)
        cap_panic("negative byte-buffer initial capacity", "CWE-682", 0);
    int64_t requested = cap < 64 ? 64 : cap;
    b.cap = cap_rt_growth_capacity(0, requested, 64, 1, sizeof(CapStr), 0);
    size_t bytes = cap_rt_checked_bytes((size_t)b.cap, 1, sizeof(CapStr), 0);
    b.s = (CapStr *)cap_alloc_atomic(bytes);
    b.s->len = 0;
    b.s->data[0] = 0;
    return b;
}

/* File contents are untrusted input: returned as Tainted. Reads until end of file
   rather than trusting the reported size, so pipes and /proc files work. Gives none
   for a directory, an unreadable file, or a file longer than max bytes (default
   2^30), so /dev/zero or an endless pipe cannot exhaust memory (CWE-400). Opening
   never blocks: a FIFO with no writer reads as empty instead of hanging. */
#define CAP_READ_FILE_DEFAULT ((int64_t)1 << 30)
static CapStr *cap_read_file_max(CapStr *path, int64_t max, int64_t loc) {
    if (CAP_UNLIKELY(max < 0 || max > CAP_READ_FILE_DEFAULT)) cap_panic("read_file() limit outside 0..2^30", "CWE-789", loc);
    if (!cap_path_ok(path)) return NULL;
    int fd = open(path->data, O_RDONLY | O_NONBLOCK | O_NOCTTY | O_CLOEXEC);
    if (fd < 0) return NULL;
    struct stat st;
    if (fstat(fd, &st) != 0 || S_ISDIR(st.st_mode)) { close(fd); return NULL; }
    int fl = fcntl(fd, F_GETFL);
    if (fl < 0 || fcntl(fd, F_SETFL, fl & ~O_NONBLOCK) < 0) { close(fd); return NULL; }
    FILE *f = fdopen(fd, "rb");
    if (!f) { close(fd); return NULL; }
    int64_t hint = S_ISREG(st.st_mode) && st.st_size > 0 && st.st_size <= max ? (int64_t)st.st_size + 1 : 4096;
    CapBuf b = cap_buf_new(hint);
    char chunk[65536];
    size_t got;
    int64_t total = 0;
    bool too_long = false;
    while ((got = fread(chunk, 1, sizeof chunk, f)) > 0) {
        if ((int64_t)got > max - total) { too_long = true; break; }
        cap_buf_put(&b, chunk, (int64_t)got);
        total += (int64_t)got;
    }
    int failed = ferror(f);
    fclose(f);
    return failed || too_long ? NULL : b.s;
}
static CapStr *cap_read_file(CapStr *path) { return cap_read_file_max(path, CAP_READ_FILE_DEFAULT, 0); }

/* One line of standard input without its newline, or none at end of input. Every
   byte is kept, including NUL bytes. Lines are capped at 1 MiB (CWE-789). */
#define CAP_READ_LINE_MAX ((int64_t)1 << 20)
static CapStr *cap_read_line(void) {
    CapBuf b = cap_buf_new(128);
    int c, got = 0;
    while ((c = getc(stdin)) != EOF) {
        got = 1;
        if (c == '\n') break;
        if (b.s->len >= CAP_READ_LINE_MAX)
            cap_panic("read_line() input exceeds 1 MiB", "CWE-789", 0);
        char ch = (char)c;
        cap_buf_put(&b, &ch, 1);
    }
    if (!got) return NULL;
    return b.s;
}

/* Up to n bytes of standard input: exactly n unless the input ends first, or none
   at end of input. Each byte is kept. n must be 0..2^30 (CWE-789); memory grows
   with the bytes actually read, not with n. */
#define CAP_READ_BYTES_MAX ((int64_t)1 << 30)
static CapStr *cap_read_bytes(int64_t n, int64_t loc) {
    if (CAP_UNLIKELY(n < 0 || n > CAP_READ_BYTES_MAX)) cap_panic("read_bytes() count outside 0..2^30", "CWE-789", loc);
    CapBuf b = cap_buf_new(n < 65536 ? n + 1 : 65536);
    char chunk[65536];
    int64_t left = n;
    bool any = n == 0;
    while (left > 0) {
        size_t want = left < (int64_t)sizeof chunk ? (size_t)left : sizeof chunk;
        size_t got = fread(chunk, 1, want, stdin);
        if (got == 0) break;
        any = true;
        cap_buf_put(&b, chunk, (int64_t)got);
        left -= (int64_t)got;
    }
    if (!any) return NULL;
    return b.s;
}

/* Everything printed so far is written out now (for programs that talk to
   another process through a pipe). */
static void cap_flush(void) { fflush(stdout); }

static bool cap_write_file(CapStr *path, CapStr *data) {
    if (!cap_path_ok(path)) return false;
    FILE *f = fopen(path->data, "wb");
    if (!f) return false;
    size_t w = fwrite(data->data, 1, (size_t)data->len, f);
    return fclose(f) == 0 && w == (size_t)data->len;
}

/* ------------------------------------------------------------------ */
/* Validators: the only ways out of Tainted (CWE-20)                   */
/* ------------------------------------------------------------------ */

static CapStr *cap_validate_ident(CapStr *t) {
    if (t->len == 0 || t->len > 255) return NULL;
    for (int64_t i = 0; i < t->len; i++) {
        unsigned char c = (unsigned char)t->data[i];
        int alpha = (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || c == '_';
        int digit = c >= '0' && c <= '9';
        if (!(alpha || (digit && i > 0))) return NULL;
    }
    return cap_str_new(t->data, t->len);
}

static int64_t *cap_validate_int(CapStr *t) {
    int64_t i = 0, v = 0;
    int neg = 0;
    if (t->len == 0) return NULL;
    if (t->data[0] == '-') { neg = 1; i = 1; if (t->len == 1) return NULL; }
    for (; i < t->len; i++) {
        unsigned char c = (unsigned char)t->data[i];
        if (c < '0' || c > '9') return NULL;
        if (__builtin_mul_overflow(v, 10, &v)) return NULL;
        if (neg ? __builtin_sub_overflow(v, c - '0', &v) : __builtin_add_overflow(v, c - '0', &v)) return NULL;
    }
    return cap_box_int(v);
}

/* Escape arbitrary bytes into the body of a C string literal. */
static CapStr *cap_escape_c(CapStr *t) {
    if (!t) cap_panic("null string passed to cap_escape_c", "CWE-476", 0);
    CapStr *r = (CapStr *)cap_alloc_atomic(cap_rt_checked_string_bytes(t->len, 4, 1, 0));
    char *w = r->data;
    for (int64_t i = 0; i < t->len; i++) {
        unsigned char c = (unsigned char)t->data[i];
        if (c == '\\') { *w++ = '\\'; *w++ = '\\'; }
        else if (c == '"') { *w++ = '\\'; *w++ = '"'; }
        else if (c == '?') { *w++ = '\\'; *w++ = '?'; }
        else if (c >= 32 && c < 127) *w++ = (char)c;
        else { w += sprintf(w, "\\%03o", c); }
    }
    *w = 0;
    r->len = (int64_t)(w - r->data);
    return r;
}

static CapStr *cap_escape_html(CapStr *t) {
    if (!t) cap_panic("null string passed to cap_escape_html", "CWE-476", 0);
    CapStr *r = (CapStr *)cap_alloc_atomic(cap_rt_checked_string_bytes(t->len, 6, 1, 0));
    char *w = r->data;
    for (int64_t i = 0; i < t->len; i++) {
        char c = t->data[i];
        switch (c) {
            case '&': memcpy(w, "&amp;", 5); w += 5; break;
            case '<': memcpy(w, "&lt;", 4); w += 4; break;
            case '>': memcpy(w, "&gt;", 4); w += 4; break;
            case '"': memcpy(w, "&quot;", 6); w += 6; break;
            case '\'': memcpy(w, "&#39;", 5); w += 5; break;
            default: *w++ = c;
        }
    }
    *w = 0;
    r->len = (int64_t)(w - r->data);
    return r;
}

/* A relative path inside the current directory tree: segments of letters, digits,
   '_', '-' and '.', never "." or "..", never absolute (CWE-22). */
static CapStr *cap_validate_path(CapStr *t) {
    /* A leading '-' would be read as an option by most programs (CWE-88). */
    if (t->len == 0 || t->len > 4096 || t->data[0] == '/' || t->data[0] == '-') return NULL;
    int64_t seg = 0;
    for (int64_t i = 0; i <= t->len; i++) {
        if (i == t->len || t->data[i] == '/') {
            int64_t n = i - seg;
            if (n == 0) return NULL;
            if (n == 1 && t->data[seg] == '.') return NULL;
            if (n == 2 && t->data[seg] == '.' && t->data[seg + 1] == '.') return NULL;
            seg = i + 1;
        } else {
            unsigned char c = (unsigned char)t->data[i];
            int ok = (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '_' || c == '-' || c == '.';
            if (!ok) return NULL;
        }
    }
    return cap_str_new(t->data, t->len);
}

static int64_t *cap_validate_range(CapStr *t, int64_t lo, int64_t hi) {
    int64_t *v = cap_validate_int(t);
    if (!v || *v < lo || *v > hi) return NULL;
    return v;
}

/* One CSV field: always quoted, quotes doubled, and a leading = + - @ tab or CR
   neutralised with an apostrophe so spreadsheets do not run it (CWE-1236). */
static CapStr *cap_escape_csv(CapStr *t) {
    if (!t) cap_panic("null string passed to cap_escape_csv", "CWE-476", 0);
    CapStr *r = (CapStr *)cap_alloc_atomic(cap_rt_checked_string_bytes(t->len, 2, 4, 0));
    char *w = r->data;
    *w++ = '"';
    if (t->len > 0 && t->data[0] != 0 && strchr("=+-@\t\r", t->data[0])) *w++ = '\'';
    for (int64_t i = 0; i < t->len; i++) {
        if (t->data[i] == '"') *w++ = '"';
        *w++ = t->data[i];
    }
    *w++ = '"';
    *w = 0;
    r->len = (int64_t)(w - r->data);
    return r;
}

/* Neutralise line breaks and control bytes so input cannot forge log lines (CWE-117). */
/* Length of the valid UTF-8 sequence at p (n bytes available), or 0 if invalid;
   overlong forms and surrogates are invalid. *cp receives the code point. */
static int cap_utf8_seq(const unsigned char *p, int64_t n, uint32_t *cp) {
    unsigned char c = p[0];
    int len;
    uint32_t v, lo = 0x80, hi = 0xBF;
    if (c >= 0xC2 && c <= 0xDF) { len = 2; v = c & 0x1F; }
    else if (c >= 0xE0 && c <= 0xEF) { len = 3; v = c & 0x0F; if (c == 0xE0) lo = 0xA0; if (c == 0xED) hi = 0x9F; }
    else if (c >= 0xF0 && c <= 0xF4) { len = 4; v = c & 0x07; if (c == 0xF0) lo = 0x90; if (c == 0xF4) hi = 0x8F; }
    else return 0;
    if (n < len) return 0;
    for (int k = 1; k < len; k++) {
        unsigned char d = p[k];
        if (d < (k == 1 ? lo : 0x80) || d > (k == 1 ? hi : 0xBF)) return 0;
        v = (v << 6) | (d & 0x3F);
    }
    *cp = v;
    return len;
}

/* Code points that steer a terminal or a log viewer rather than display text:
   C1 controls (0x9B is a CSI introducer), bidirectional controls (log lines that
   display differently from what they contain), line and paragraph separators,
   and the byte-order mark. */
static bool cap_log_hostile(uint32_t cp) {
    return (cp >= 0x80 && cp <= 0x9F) || cp == 0x061C || cp == 0x200E || cp == 0x200F ||
           (cp >= 0x2028 && cp <= 0x202E) || (cp >= 0x2066 && cp <= 0x2069) || cp == 0xFEFF;
}

/* Neutralise anything that could forge or disguise a log line (CWE-117, CWE-150):
   ASCII controls, invalid UTF-8, and the hostile code points above become \xNN
   escapes, one per byte. Printable ASCII and other valid UTF-8 text are kept. */
static CapStr *cap_escape_log(CapStr *t) {
    if (!t) cap_panic("null string passed to cap_escape_log", "CWE-476", 0);
    CapStr *r = (CapStr *)cap_alloc_atomic(cap_rt_checked_string_bytes(t->len, 4, 1, 0));
    char *w = r->data;
    const unsigned char *s = (const unsigned char *)t->data;
    int64_t i = 0;
    while (i < t->len) {
        unsigned char c = s[i];
        if (c >= 32 && c < 127) { *w++ = (char)c; i++; continue; }
        uint32_t cp = 0;
        int len = c >= 0x80 ? cap_utf8_seq(s + i, t->len - i, &cp) : 0;
        if (len > 0 && !cap_log_hostile(cp)) {
            memcpy(w, s + i, (size_t)len);
            w += len;
            i += len;
            continue;
        }
        if (len == 0) len = 1;
        for (int k = 0; k < len; k++) w += sprintf(w, "\\x%02x", s[i + k]);
        i += len;
    }
    *w = 0;
    r->len = (int64_t)(w - r->data);
    return r;
}

/* The contents of a JSON string literal (without the quotes) for any bytes
   (CWE-116): '"' and '\\' are escaped; controls, DEL, '<', '>', '&' and the line
   separators U+2028/U+2029 become \uXXXX (safe inside an HTML <script> too, CWE-79);
   valid UTF-8 is kept; each invalid byte becomes U+FFFD, so the output is always
   valid JSON. */
static CapStr *cap_escape_json(CapStr *t) {
    if (!t) cap_panic("null string passed to cap_escape_json", "CWE-476", 0);
    CapStr *r = (CapStr *)cap_alloc_atomic(cap_rt_checked_string_bytes(t->len, 6, 1, 0));
    char *w = r->data;
    const unsigned char *s = (const unsigned char *)t->data;
    int64_t i = 0;
    while (i < t->len) {
        unsigned char c = s[i];
        if (c == '"' || c == '\\') { *w++ = '\\'; *w++ = (char)c; i++; continue; }
        if (c == '\n') { *w++ = '\\'; *w++ = 'n'; i++; continue; }
        if (c == '\t') { *w++ = '\\'; *w++ = 't'; i++; continue; }
        if (c == '\r') { *w++ = '\\'; *w++ = 'r'; i++; continue; }
        if (c < 32 || c == 127 || c == '<' || c == '>' || c == '&') { w += sprintf(w, "\\u%04x", c); i++; continue; }
        if (c < 128) { *w++ = (char)c; i++; continue; }
        uint32_t cp = 0;
        int len = cap_utf8_seq(s + i, t->len - i, &cp);
        if (len == 0) { memcpy(w, "\\ufffd", 6); w += 6; i++; continue; }
        if (cp == 0x2028 || cp == 0x2029) { w += sprintf(w, "\\u%04x", (unsigned)cp); i += len; continue; }
        memcpy(w, s + i, (size_t)len);
        w += len;
        i += len;
    }
    *w = 0;
    r->len = (int64_t)(w - r->data);
    return r;
}

/* A one-byte string that stays untrusted: decoding escapes in untrusted text
   (%41, \u0041) cannot launder it, because the result is Tainted. */
static CapStr *cap_taint_char(int64_t c, int64_t loc) {
    if (CAP_UNLIKELY(c < 0 || c > 255)) cap_panic("taint_char() byte outside 0..255", "CWE-704", loc);
    CapStr *r = (CapStr *)cap_alloc_atomic(sizeof(CapStr) + 2);
    r->data[0] = (char)c;
    r->data[1] = 0;
    r->len = 1;
    return r;
}

/* ------------------------------------------------------------------ */
/* Injection-safe sinks (v0.1 demonstration stubs)                     */
/* The query/program text is always a compile-time literal; untrusted  */
/* values travel separately as bound parameters / argv entries.        */
/* ------------------------------------------------------------------ */

static void cap_sql_query(CapStr *tmpl, CapList *params) {
    printf("[sql] %s", tmpl->data);
    for (int64_t i = 0; i < params->len; i++)
        printf(" $%lld=%s", (long long)(i + 1), cap_escape_log((CapStr *)params->items[i].p)->data);
    printf("\n");
}

static void cap_run(CapStr *prog, CapList *argv) {
    printf("[run] %s", prog->data);
    for (int64_t i = 0; i < argv->len; i++)
        printf(" argv[%lld]=%s", (long long)(i + 1), cap_escape_log((CapStr *)argv->items[i].p)->data);
    printf("\n");
}

/* ------------------------------------------------------------------ */
/* Secrets (CWE-798, CWE-208, CWE-532)                                 */
/* ------------------------------------------------------------------ */

static CapStr *cap_secret_env(CapStr *name) {
    /* getenv() accepts a NUL-terminated name, while CapStr is length-delimited.
       Reject embedded NULs rather than silently resolving a truncated name. */
    if (!name || name->len < 0 ||
        memchr(name->data, '\0', (size_t)name->len) != NULL) return NULL;
    const char *v = getenv(name->data);
    if (!v) return NULL;
    size_t value_len = strlen(v);
    if (value_len > INT64_MAX)
        cap_panic("secret environment value exceeds string length range", "CWE-789", 0);
    int64_t n = (int64_t)value_len;
    CapStr *r = (CapStr *)cap_alloc_secret(cap_rt_checked_string_bytes(n, 1, 1, 0));
    r->len = n;
    memcpy(r->data, v, (size_t)n);
    r->data[n] = 0;
    return r;
}

static void cap_wipe(void *p, size_t n) { volatile unsigned char *w = (volatile unsigned char *)p; while (n--) *w++ = 0; }

/* Explicit-lifetime scratch for native cryptographic code. Unlike cap_alloc_secret,
   this storage is not GC-managed: the owner must destroy it on every exit path.
   Do not copy this descriptor or retain aliases to data after destruction. */
typedef struct CapSecretScratch {
    unsigned char *data;
    size_t len;
    bool active;
} CapSecretScratch;

#ifdef CAP_SECRET_SCRATCH_TEST_HOOK
static void (*cap_secret_scratch_test_wipe_hook)(const void *, size_t);
#endif

static bool cap_secret_scratch_init(CapSecretScratch *scratch, size_t n) {
    if (!scratch || scratch->active || scratch->data || scratch->len != 0 || n > CAP_MAX_LEN)
        return false;
    unsigned char *memory = NULL;
    if (n != 0) {
        memory = (unsigned char *)malloc(n);
        if (!memory) return false;
        memset(memory, 0, n);
    }
    scratch->data = memory;
    scratch->len = n;
    scratch->active = true;
    return true;
}

static void cap_secret_scratch_destroy(CapSecretScratch *scratch) {
    if (!scratch || !scratch->active) return;
    if (scratch->data) {
        cap_wipe(scratch->data, scratch->len);
#ifdef CAP_SECRET_SCRATCH_TEST_HOOK
        if (cap_secret_scratch_test_wipe_hook)
            cap_secret_scratch_test_wipe_hook(scratch->data, scratch->len);
#endif
        free(scratch->data);
    }
    cap_wipe(scratch, sizeof *scratch);
}

static bool cap_ct_eq(const char *a, int64_t an, const char *b, int64_t bn) {
    unsigned char d = (unsigned char)(an != bn);
    int64_t n = an < bn ? an : bn;
    for (int64_t i = 0; i < n; i++) d |= (unsigned char)(a[i] ^ b[i]);
    return d == 0;
}

static bool cap_secret_eq(CapStr *a, CapStr *b) { return cap_ct_eq(a->data, a->len, b->data, b->len); }

/* ------------------------------------------------------------------ */
/* Cryptography: algorithm-agile, self-describing outputs (CWE-327/916) */
/* Every output carries its algorithm tag, so a later Capstan version   */
/* can change the default while still verifying older values.           */
/* ------------------------------------------------------------------ */

typedef struct { uint32_t h[8]; uint64_t bits; unsigned char buf[64]; size_t n; } CapSha256;

/* One contiguous, explicitly destroyed region for native PBKDF2 intermediates. */
typedef struct CapPbkdf2Scratch {
    unsigned char msg[64 + 4];
    unsigned char u[32];
    unsigned char t[32];
    CapSha256 inner;
    CapSha256 outer;
} CapPbkdf2Scratch;

static const uint32_t cap_k256[64] = {
    0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
    0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
    0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
    0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
    0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
    0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
    0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
    0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};

#define CAP_ROR(x, n) (((x) >> (n)) | ((x) << (32 - (n))))

static void cap_sha256_block(CapSha256 *s, const unsigned char *p) {
    uint32_t w[64], a, b, c, d, e, f, g, h;
    for (int i = 0; i < 16; i++) w[i] = (uint32_t)p[4*i] << 24 | (uint32_t)p[4*i+1] << 16 | (uint32_t)p[4*i+2] << 8 | p[4*i+3];
    for (int i = 16; i < 64; i++) {
        uint32_t s0 = CAP_ROR(w[i-15], 7) ^ CAP_ROR(w[i-15], 18) ^ (w[i-15] >> 3);
        uint32_t s1 = CAP_ROR(w[i-2], 17) ^ CAP_ROR(w[i-2], 19) ^ (w[i-2] >> 10);
        w[i] = w[i-16] + s0 + w[i-7] + s1;
    }
    a = s->h[0]; b = s->h[1]; c = s->h[2]; d = s->h[3]; e = s->h[4]; f = s->h[5]; g = s->h[6]; h = s->h[7];
    for (int i = 0; i < 64; i++) {
        uint32_t t1 = h + (CAP_ROR(e, 6) ^ CAP_ROR(e, 11) ^ CAP_ROR(e, 25)) + ((e & f) ^ (~e & g)) + cap_k256[i] + w[i];
        uint32_t t2 = (CAP_ROR(a, 2) ^ CAP_ROR(a, 13) ^ CAP_ROR(a, 22)) + ((a & b) ^ (a & c) ^ (b & c));
        h = g; g = f; f = e; e = d + t1; d = c; c = b; b = a; a = t1 + t2;
    }
    s->h[0] += a; s->h[1] += b; s->h[2] += c; s->h[3] += d; s->h[4] += e; s->h[5] += f; s->h[6] += g; s->h[7] += h;
    /* The message schedule and working state contain password-derived material. */
    cap_wipe(w, sizeof w);
    cap_wipe(&a, sizeof a); cap_wipe(&b, sizeof b);
    cap_wipe(&c, sizeof c); cap_wipe(&d, sizeof d);
    cap_wipe(&e, sizeof e); cap_wipe(&f, sizeof f);
    cap_wipe(&g, sizeof g); cap_wipe(&h, sizeof h);
#ifdef CAP_SHA256_WIPE_TEST_HOOK
    cap_sha256_wipe_test_observe((const volatile unsigned char *)w, sizeof w);
    cap_sha256_wipe_test_observe((const volatile unsigned char *)&a, sizeof a);
    cap_sha256_wipe_test_observe((const volatile unsigned char *)&b, sizeof b);
    cap_sha256_wipe_test_observe((const volatile unsigned char *)&c, sizeof c);
    cap_sha256_wipe_test_observe((const volatile unsigned char *)&d, sizeof d);
    cap_sha256_wipe_test_observe((const volatile unsigned char *)&e, sizeof e);
    cap_sha256_wipe_test_observe((const volatile unsigned char *)&f, sizeof f);
    cap_sha256_wipe_test_observe((const volatile unsigned char *)&g, sizeof g);
    cap_sha256_wipe_test_observe((const volatile unsigned char *)&h, sizeof h);
#endif
}

static void cap_sha256_init(CapSha256 *s) {
    static const uint32_t iv[8] = {0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
    memcpy(s->h, iv, sizeof iv); s->bits = 0; s->n = 0;
}

static void cap_sha256_update(CapSha256 *s, const unsigned char *p, size_t n) {
    if (n > (UINT64_MAX - s->bits) / 8)
        cap_panic("SHA-256 message length overflow", "CWE-190", 0);
    for (size_t i = 0; i < n; i++) {
        s->buf[s->n++] = p[i];
        if (s->n == 64) { cap_sha256_block(s, s->buf); s->n = 0; }
    }
    s->bits += (uint64_t)n * 8;
}

static void cap_sha256_final(CapSha256 *s, unsigned char out[32]) {
    uint64_t bits = s->bits;
    unsigned char pad = 0x80, zero = 0, len[8];
    cap_sha256_update(s, &pad, 1);
    while (s->n != 56) cap_sha256_update(s, &zero, 1);
    for (int i = 0; i < 8; i++) len[i] = (unsigned char)(bits >> (56 - 8 * i));
    cap_sha256_update(s, len, 8);
    for (int i = 0; i < 8; i++) { out[4*i] = s->h[i] >> 24; out[4*i+1] = s->h[i] >> 16; out[4*i+2] = s->h[i] >> 8; out[4*i+3] = s->h[i]; }
    cap_wipe(len, sizeof len);
    cap_wipe(s, sizeof *s);
    cap_wipe(&bits, sizeof bits);
    cap_wipe(&pad, sizeof pad);
    cap_wipe(&zero, sizeof zero);
}

static void cap_hmac_sha256(const unsigned char *key, size_t kn, const unsigned char *msg, size_t mn, unsigned char out[32]) {
    unsigned char k[64] = {0}, ipad[64], opad[64], inner[32];
    CapSha256 s;
    if (kn > 64) { cap_sha256_init(&s); cap_sha256_update(&s, key, kn); cap_sha256_final(&s, k); }
    else memcpy(k, key, kn);
    for (int i = 0; i < 64; i++) { ipad[i] = k[i] ^ 0x36; opad[i] = k[i] ^ 0x5c; }
    cap_sha256_init(&s); cap_sha256_update(&s, ipad, 64); cap_sha256_update(&s, msg, mn); cap_sha256_final(&s, inner);
    cap_sha256_init(&s); cap_sha256_update(&s, opad, 64); cap_sha256_update(&s, inner, 32); cap_sha256_final(&s, out);
    cap_wipe(k, sizeof k); cap_wipe(ipad, sizeof ipad); cap_wipe(opad, sizeof opad); cap_wipe(inner, sizeof inner); cap_wipe(&s, sizeof s);
}

#ifdef CAP_PBKDF2_TEST_HOOK
static unsigned cap_pbkdf2_test_calls;
static unsigned cap_pbkdf2_prepare_calls;
#endif

/* Prepare the keyed SHA-256 states once for a PBKDF2 derivation. Each state
   includes exactly one 64-byte HMAC pad block (512 bits). Per-message calls
   copy these states, finish the inner/outer hashes, and wipe the copies. */
static void cap_hmac_sha256_prepare(const unsigned char *key, size_t kn,
                                    CapSha256 *inner, CapSha256 *outer) {
#ifdef CAP_PBKDF2_TEST_HOOK
    cap_pbkdf2_prepare_calls++;
#endif
    unsigned char k[64] = {0}, ipad[64], opad[64];
    CapSha256 s;
    if (kn > 64) {
        cap_sha256_init(&s);
        cap_sha256_update(&s, key, kn);
        cap_sha256_final(&s, k);
    } else {
        memcpy(k, key, kn);
    }
    for (int i = 0; i < 64; i++) {
        ipad[i] = k[i] ^ 0x36;
        opad[i] = k[i] ^ 0x5c;
    }
    cap_sha256_init(inner);
    cap_sha256_update(inner, ipad, sizeof ipad);
    cap_sha256_init(outer);
    cap_sha256_update(outer, opad, sizeof opad);
    cap_wipe(k, sizeof k);
    cap_wipe(ipad, sizeof ipad);
    cap_wipe(opad, sizeof opad);
    cap_wipe(&s, sizeof s);
}

static void cap_hmac_sha256_prepared(const CapSha256 *inner_state,
                                     const CapSha256 *outer_state,
                                     const unsigned char *msg, size_t mn,
                                     unsigned char out[32]) {
    CapSha256 inner = *inner_state, outer = *outer_state;
    unsigned char digest[32];
    cap_sha256_update(&inner, msg, mn);
    cap_sha256_final(&inner, digest);
    cap_sha256_update(&outer, digest, sizeof digest);
    cap_sha256_final(&outer, out);
    cap_wipe(digest, sizeof digest);
    cap_wipe(&inner, sizeof inner);
    cap_wipe(&outer, sizeof outer);
}

static void cap_hex(const unsigned char *p, size_t n, char *out) {
    static const char *d = "0123456789abcdef";
    for (size_t i = 0; i < n; i++) { out[2*i] = d[p[i] >> 4]; out[2*i+1] = d[p[i] & 15]; }
    out[2*n] = 0;
}

static CapStr *cap_hash(CapStr *data) {
    unsigned char dg[32];
    char out[12 + 65];
    CapSha256 s;
    cap_sha256_init(&s); cap_sha256_update(&s, (const unsigned char *)data->data, (size_t)data->len); cap_sha256_final(&s, dg);
    memcpy(out, "cap1$sha256$", 12);
    cap_hex(dg, 32, out + 12);
    cap_wipe(dg, sizeof dg);
    cap_wipe(&s, sizeof s);
    return cap_str_new(out, (int64_t)strlen(out));
}

static bool cap_hash_verify(CapStr *data, CapStr *tagged) {
    if (tagged->len > 12 && memcmp(tagged->data, "cap1$sha256$", 12) == 0) {
        CapStr *h = cap_hash(data);
        return cap_ct_eq(h->data, h->len, tagged->data, tagged->len);
    }
    return false;   /* unknown or retired algorithm tag */
}

#define CAP_PBKDF2_ITER 600000
#define CAP_PASSWORD_MAX_BYTES 256
#define CAP_PASSWORD_RECORD_LEN 123

static void cap_pbkdf2(const char *pw, size_t pn, const unsigned char *salt, size_t sn, int iter, unsigned char out[32]) {
    if (!pw || !salt || !out || pn > CAP_PASSWORD_MAX_BYTES || sn > 64 ||
        iter < 1 || iter > CAP_PBKDF2_ITER)
        cap_panic("invalid PBKDF2 parameters", "CWE-789", 0);
#ifdef CAP_PBKDF2_TEST_HOOK
    cap_pbkdf2_test_calls++;
#endif
    CapSecretScratch allocation = {0};
    if (!cap_secret_scratch_init(&allocation, sizeof(CapPbkdf2Scratch)))
        cap_panic("unable to allocate PBKDF2 secret scratch", "CWE-400", 0);
    CapPbkdf2Scratch *work = (CapPbkdf2Scratch *)allocation.data;
    cap_hmac_sha256_prepare((const unsigned char *)pw, pn, &work->inner, &work->outer);
    memcpy(work->msg, salt, sn);
    work->msg[sn] = 0; work->msg[sn+1] = 0; work->msg[sn+2] = 0; work->msg[sn+3] = 1;
    cap_hmac_sha256_prepared(&work->inner, &work->outer, work->msg, sn + 4, work->u);
    memcpy(work->t, work->u, 32);
    for (int i = 1; i < iter; i++) {
        cap_hmac_sha256_prepared(&work->inner, &work->outer, work->u, 32, work->u);
        for (int j = 0; j < 32; j++) work->t[j] ^= work->u[j];
    }
    memcpy(out, work->t, 32);
    cap_secret_scratch_destroy(&allocation);
}

static CapStr *cap_hash_password(CapStr *pw) {
    if (!pw || pw->len < 0)
        cap_panic("invalid password input", "CWE-476", 0);
    if (pw->len > CAP_PASSWORD_MAX_BYTES)
        cap_panic("password exceeds the 256-byte limit", "CWE-789", 0);
    unsigned char salt[16], dk[32];
    char shex[33], dhex[65], out[128];
    FILE *r = fopen("/dev/urandom", "rb");
    if (!r || fread(salt, 1, 16, r) != 16) { fprintf(stderr, "capstan: no secure randomness available\n"); exit(103); }
    fclose(r);
    cap_pbkdf2(pw->data, (size_t)pw->len, salt, 16, CAP_PBKDF2_ITER, dk);
    cap_hex(salt, 16, shex); cap_hex(dk, 32, dhex);
    cap_wipe(dk, sizeof dk);
    int n = snprintf(out, sizeof out, "cap1$pbkdf2-sha256$%d$%s$%s", CAP_PBKDF2_ITER, shex, dhex);
    /* dhex is a second stack copy of the password-derived verifier key. */
    cap_wipe(dhex, sizeof dhex);
    CapStr *record = cap_str_new(out, n);
    /* The returned CapStr owns the persistent record; clear temporary stack copies. */
    cap_wipe(salt, sizeof salt);
    cap_wipe(shex, sizeof shex);
    cap_wipe(out, sizeof out);
    return record;
}

static int cap_unhex(const char *h, size_t n, unsigned char *out) {
    for (size_t i = 0; i < n; i++) {
        int v = 0;
        for (int k = 0; k < 2; k++) {
            char c = h[2*i+k];
            v <<= 4;
            if (c >= '0' && c <= '9') v |= c - '0';
            else if (c >= 'a' && c <= 'f') v |= c - 'a' + 10;
            else return 0;
        }
        out[i] = (unsigned char)v;
    }
    return 1;
}

/* Parse the complete, canonical current password-record format. Stored records
   are untrusted input: no C-string operation may read beyond CapStr.len, and
   the cost is fixed to the current generation profile until a legacy migration
   policy is explicitly approved. */
static bool cap_parse_password_record(CapStr *tagged,
                                      unsigned char salt[16],
                                      unsigned char want[32]) {
    static const char prefix[] = "cap1$pbkdf2-sha256$";
    const size_t prefix_len = sizeof prefix - 1;
    if (!tagged || tagged->len != CAP_PASSWORD_RECORD_LEN) return false;
    size_t n = CAP_PASSWORD_RECORD_LEN;
    if (memcmp(tagged->data, prefix, prefix_len) != 0) return false;
    size_t i = prefix_len;
    if (tagged->data[i] < '1' || tagged->data[i] > '9') return false;
    unsigned iter = 0;
    while (i < n && tagged->data[i] >= '0' && tagged->data[i] <= '9') {
        unsigned digit = (unsigned)(tagged->data[i] - '0');
        if (iter > ((unsigned)CAP_PBKDF2_ITER - digit) / 10u) return false;
        iter = iter * 10u + digit;
        i++;
    }
    if (iter != (unsigned)CAP_PBKDF2_ITER) return false;
    if (i >= n || tagged->data[i++] != '$') return false;
    if (n - i != 32 + 1 + 64 || tagged->data[i + 32] != '$') return false;
    if (!cap_unhex(tagged->data + i, 16, salt)) return false;
    if (!cap_unhex(tagged->data + i + 33, 32, want)) return false;
    return true;
}

static bool cap_verify_password(CapStr *pw, CapStr *tagged) {
    if (!pw || pw->len < 0 || pw->len > CAP_PASSWORD_MAX_BYTES) return false;
    unsigned char salt[16] = {0}, want[32] = {0}, got[32] = {0};
    if (!cap_parse_password_record(tagged, salt, want)) {
        cap_wipe(salt, sizeof salt);
        cap_wipe(want, sizeof want);
        return false;
    }
    cap_pbkdf2(pw->data, (size_t)pw->len, salt, 16, CAP_PBKDF2_ITER, got);
    bool ok = cap_ct_eq((const char *)got, 32, (const char *)want, 32);
    cap_wipe(salt, sizeof salt);
    cap_wipe(want, sizeof want);
    cap_wipe(got, sizeof got);
    return ok;
}

static bool cap_needs_rehash(CapStr *tagged) {
    unsigned char salt[16] = {0}, want[32] = {0};
    bool current = cap_parse_password_record(tagged, salt, want);
    cap_wipe(salt, sizeof salt);
    cap_wipe(want, sizeof want);
    return !current;
}

/* ------------------------------------------------------------------ */
/* Test harness                                                        */
/* ------------------------------------------------------------------ */

static int cap_tests_run = 0, cap_tests_failed = 0;

static void cap_run_test(const char *name, void (*fn)(void)) {
    cap_tests_run++;
    cap_test_mode = 1;
    if (setjmp(cap_test_jmp) == 0) {
        fn();
        printf("  pass  %s\n", name);
    } else {
        cap_tests_failed++;
        printf("  FAIL  %s\n", name);
    }
    cap_test_mode = 0;
}

static int cap_test_summary(void) {
    printf("%d test(s), %d failed\n", cap_tests_run, cap_tests_failed);
    return cap_tests_failed ? 1 : 0;
}

#endif
