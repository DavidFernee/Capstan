/*
 * Capstan garbage collector (v0.2)
 *
 * A non-moving mark-sweep collector. Memory is freed automatically, and use
 * after free and double free stay impossible because programs never free
 * memory themselves.
 *
 *  - Small objects (<= 2 KiB) live in 64 KiB pages, one size class per page,
 *    so any address can be mapped to its object in constant time. Pointers
 *    into the middle of an object keep it alive.
 *  - Large objects are allocated individually and found by binary search.
 *  - "Atomic" allocations (strings, boxed integers, hash indexes) hold no
 *    pointers and are never scanned, so text cannot keep objects alive.
 *  - Secrets live in their own pages and are zeroed when collected, so a
 *    credential does not linger in freed memory (CWE-244).
 *  - The heap has a limit (CAPSTAN_MAX_HEAP, default three quarters of
 *    physical memory). Exceeding it stops the program safely (CWE-400).
 *  - Pages left empty by a collection are returned to the operating system
 *    (madvise), beyond a reserve kept for reuse, and are reused before new
 *    memory is requested. Their addresses stay reserved, so a stale pointer
 *    into one is still recognised as pointing at nothing.
 *  - Roots: the machine stack, callee-saved registers (spilled with setjmp),
 *    and global variables registered by the generated code. The stack and
 *    object contents are scanned conservatively.
 *
 * Environment:
 *   CAPSTAN_GC_STATS=1    print collector statistics on exit
 *   CAPSTAN_GC_STRESS=N   collect every N allocations (for testing)
 *   CAPSTAN_MAX_HEAP=N    heap limit in bytes; K, M and G suffixes accepted
 */
#ifndef CAPSTAN_GC_H
#define CAPSTAN_GC_H

#include <stdint.h>
#include <errno.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <setjmp.h>
#include <pthread.h>
#include <signal.h>
#include <unistd.h>
#include <sys/mman.h>
#if !defined(MAP_ANONYMOUS) && defined(MAP_ANON)
#define MAP_ANONYMOUS MAP_ANON
#endif

/* Upper bound on any length (see the heap limit below). */
#define CAP_MAX_LEN ((size_t)1 << 48)

#if defined(__clang__)
#define CAP_NO_SANITIZE __attribute__((no_sanitize("address"), noinline))
#elif defined(__GNUC__)
#define CAP_NO_SANITIZE __attribute__((no_sanitize_address, noinline))
#else
#define CAP_NO_SANITIZE
#endif

#if defined(__SANITIZE_ADDRESS__)
#define CAP_ASAN 1
#elif defined(__has_feature)
#if __has_feature(address_sanitizer)
#define CAP_ASAN 1
#endif
#endif

#define CAP_PAGE_SHIFT 16
#define CAP_PAGE_SIZE ((uintptr_t)1 << CAP_PAGE_SHIFT)
#define CAP_NCLASS 14
#define CAP_MIN_THRESHOLD ((size_t)8 << 20)
#define CAP_KINDS 3          /* 0: may hold pointers, 1: pointer-free, 2: secret (pointer-free, wiped) */

__attribute__((noreturn, cold, noinline)) static void cap_panic(const char *what, const char *cwe, int64_t loc);

static const uint32_t cap_class_size[CAP_NCLASS] =
    {16, 32, 48, 64, 96, 128, 192, 256, 384, 512, 768, 1024, 1536, 2048};

typedef struct CapPage {
    char *base;
    uint32_t objsize, nobj;
    int atomic;
    int spare;               /* empty and in the spare list, not in any free list */
    int released;            /* spare, and its memory has been returned to the OS */
    uint8_t *alloc;
    uint8_t *mark;
    uint32_t *free_slots;       /* out-of-line free stack for secret pages */
    uint32_t free_count, free_cap;
} CapPage;

typedef struct { char *base; size_t size, alloc_size; int atomic, mark; } CapLarge;

static struct {
    int inited, stats;
    long stress, stress_count;
    char *stack_top;
    CapPage **pages; size_t npages, cappages;
    CapPage **ptab; size_t ptab_cap;          /* hash table keyed by page number */
    void *freelist[CAP_KINDS][CAP_NCLASS];
    size_t max_heap;
    CapLarge *large; size_t nlarge, caplarge;
    void ***roots; size_t nroots, caproots;
    uintptr_t lo, hi;
    size_t since, threshold, live, heap, peak_heap, total, collections;
    void **mstack; size_t msp, mcap;
    CapPage **spare; size_t nspare, capspare;  /* empty pages, reused before new ones */
    size_t released_total, reused_total;
} cap_gc;

static __attribute__((noreturn)) void cap_gc_oom(void) {
    fprintf(stderr, "capstan: out of memory\n");
    exit(102);
}

/* Checked sizing helpers for collector-owned metadata. */
static int cap_gc_size_add(size_t a, size_t b, size_t *out) {
    if (b > SIZE_MAX - a) return 0;
    *out = a + b;
    return 1;
}
static int cap_gc_size_mul(size_t a, size_t b, size_t *out) {
    if (a && b > SIZE_MAX / a) return 0;
    *out = a * b;
    return 1;
}
static size_t cap_gc_next_capacity(size_t current, size_t required, size_t initial) {
    size_t n = current ? current : initial;
    if (!n) n = 1;
    while (n < required) {
        if (n > SIZE_MAX / 2) cap_gc_oom();
        n *= 2;
    }
    return n;
}
static void *cap_gc_meta(size_t n) {
    void *p = calloc(1, n ? n : 1);
    if (!p) cap_gc_oom();
    return p;
}

static void *cap_gc_meta_array(size_t count, size_t element_size) {
    size_t bytes;
    if (!cap_gc_size_mul(count, element_size, &bytes)) cap_gc_oom();
    return cap_gc_meta(bytes);
}
static size_t cap_gc_account_add(size_t current, size_t amount) {
    size_t result;
    if (!cap_gc_size_add(current, amount, &result))
        cap_panic("runtime allocation accounting overflow", "CWE-190", 0);
    return result;
}
static int cap_gc_would_exceed_heap(size_t amount) {
    return cap_gc.max_heap &&
           (cap_gc.heap > cap_gc.max_heap || amount > cap_gc.max_heap - cap_gc.heap);
}

/* Volatile stores prevent the compiler from deleting a wipe whose only purpose
   is to erase data before the storage is reused or released. */
static void cap_gc_wipe(void *memory, size_t n) {
    volatile unsigned char *p = (volatile unsigned char *)memory;
    while (n--) *p++ = 0;
}

static void cap_gc_report(void) {
    fprintf(stderr, "gc: collections=%zu total_allocated=%zu live=%zu heap=%zu peak_heap=%zu pages_released=%zu pages_reused=%zu\n",
            cap_gc.collections, cap_gc.total, cap_gc.live, cap_gc.heap, cap_gc.peak_heap,
            cap_gc.released_total, cap_gc.reused_total);
}

/* ---- stack overflow guard (CWE-674) -----------------------------------------
 * Deep or infinite recursion runs into the guard page below the stack. Instead
 * of crashing, the program stops with a named runtime check, like any other. */
static char *cap_stack_low = NULL;
static char cap_altstack[65536];

static void cap_segv_handler(int sig, siginfo_t *si, void *uc) {
    (void)sig; (void)uc;
    uintptr_t address = (uintptr_t)si->si_addr;
    uintptr_t low = (uintptr_t)cap_stack_low;
    uintptr_t lower = low > ((uintptr_t)1 << 24) ? low - ((uintptr_t)1 << 24) : 0;
    uintptr_t upper = low > UINTPTR_MAX - 65536 ? UINTPTR_MAX : low + 65536;
    static const char overflow_msg[] =
        "runtime check failed: stack overflow, recursion too deep [CWE-674 prevented]\n";
    static const char fault_msg[] =
        "capstan: internal error: invalid memory access; please report this as a bug\n";
    const char *msg = fault_msg;
    size_t msg_len = sizeof fault_msg - 1;
    int code = 105;
    if (cap_stack_low && address >= lower && address < upper) {
        msg = overflow_msg;
        msg_len = sizeof overflow_msg - 1;
        code = 101;
    }
    ssize_t written = write(2, msg, msg_len);
    (void)written;
    _exit(code);
}

static void cap_install_stack_guard(char *low) {
    cap_stack_low = low;
    stack_t ss;
    ss.ss_sp = cap_altstack;
    ss.ss_size = sizeof cap_altstack;
    ss.ss_flags = 0;
    if (sigaltstack(&ss, NULL) != 0)
        cap_panic("unable to install stack overflow signal stack", "CWE-674", 0);
    struct sigaction sa;
    memset(&sa, 0, sizeof sa);
    sa.sa_sigaction = cap_segv_handler;
    sa.sa_flags = SA_SIGINFO | SA_ONSTACK;
    sigemptyset(&sa.sa_mask);
    if (sigaction(SIGSEGV, &sa, NULL) != 0 || sigaction(SIGBUS, &sa, NULL) != 0)
        cap_panic("unable to install stack overflow signal handler", "CWE-674", 0);
}

static void cap_gc_init(void) {
    if (cap_gc.inited) return;
    cap_gc.inited = 1;
    cap_gc.threshold = CAP_MIN_THRESHOLD;
    cap_gc.lo = UINTPTR_MAX;
    const char *s = getenv("CAPSTAN_GC_STRESS");
    if (s) {
        char *end;
        errno = 0;
        long value = strtol(s, &end, 10);
        if (s == end || *end != '\0' || errno == ERANGE || value < 0)
            cap_panic("invalid CAPSTAN_GC_STRESS value", "CWE-20", 0);
        cap_gc.stress = value;
    }
    if (getenv("CAPSTAN_GC_STATS")) { cap_gc.stats = 1; atexit(cap_gc_report); }
    const char *mh = getenv("CAPSTAN_MAX_HEAP");
    if (mh) {
        char *end;
        errno = 0;
        unsigned long long v = strtoull(mh, &end, 10);
        if (mh == end || errno == ERANGE || mh[0] == '-')
            cap_panic("invalid CAPSTAN_MAX_HEAP value", "CWE-20", 0);
        unsigned shift = 0;
        if (*end == 'K' || *end == 'k') shift = 10;
        else if (*end == 'M' || *end == 'm') shift = 20;
        else if (*end == 'G' || *end == 'g') shift = 30;
        if (shift) {
            if (v > ((unsigned long long)CAP_MAX_LEN >> shift))
                v = CAP_MAX_LEN;
            else
                v <<= shift;
            end++;
        }
        if (*end != '\0')
            cap_panic("invalid CAPSTAN_MAX_HEAP value", "CWE-20", 0);
        cap_gc.max_heap = v > CAP_MAX_LEN ? CAP_MAX_LEN : (size_t)v;
    } else {
        long pages = sysconf(_SC_PHYS_PAGES), psize = sysconf(_SC_PAGESIZE);
        if (pages > 0 && psize > 0) {
            size_t physical_quarters = (size_t)pages / 4 * 3, total;
            cap_gc.max_heap = cap_gc_size_mul(physical_quarters, (size_t)psize, &total)
                ? total : CAP_MAX_LEN;
        } else {
            cap_gc.max_heap = (size_t)1 << 34;
        }
    }
    /* Never more than 2^48 bytes: every string and collection is then shorter than
       2^48 elements, a bound the compiler's range analysis relies on. */
    if (cap_gc.max_heap == 0 || cap_gc.max_heap > CAP_MAX_LEN) cap_gc.max_heap = CAP_MAX_LEN;
    char *low = NULL;
#if defined(__APPLE__)
    cap_gc.stack_top = (char *)pthread_get_stackaddr_np(pthread_self());
    low = cap_gc.stack_top - pthread_get_stacksize_np(pthread_self());
#elif defined(__linux__)
    pthread_attr_t attr;
    void *addr; size_t size;
    if (pthread_getattr_np(pthread_self(), &attr) == 0 && pthread_attr_getstack(&attr, &addr, &size) == 0) {
        cap_gc.stack_top = (char *)addr + size;
        low = (char *)addr;
        pthread_attr_destroy(&attr);
    }
#endif
#ifndef CAP_ASAN
    if (low) cap_install_stack_guard(low);   /* AddressSanitizer installs its own */
#endif
    if (!cap_gc.stack_top) cap_gc.stack_top = (char *)__builtin_frame_address(0) + 4096;
}

/* ---- page table ------------------------------------------------------ */

static size_t cap_gc_slot(uintptr_t pageno, size_t cap) {
    return (size_t)((pageno * 11400714819323198485ULL) >> 7) & (cap - 1);
}

static void cap_gc_ptab_insert(CapPage *pg) {
    size_t entries, needed;
    if (!cap_gc_size_add(cap_gc.npages, 1, &entries) ||
        !cap_gc_size_mul(entries, 2, &needed)) cap_gc_oom();
    if (needed > cap_gc.ptab_cap) {
        size_t nc = cap_gc_next_capacity(cap_gc.ptab_cap, needed, 64);
        CapPage **nt = (CapPage **)cap_gc_meta_array(nc, sizeof(CapPage *));
        for (size_t i = 0; i < cap_gc.ptab_cap; i++) {
            CapPage *p = cap_gc.ptab[i];
            if (!p) continue;
            size_t s = cap_gc_slot((uintptr_t)p->base >> CAP_PAGE_SHIFT, nc);
            while (nt[s]) s = (s + 1) & (nc - 1);
            nt[s] = p;
        }
        free(cap_gc.ptab);
        cap_gc.ptab = nt;
        cap_gc.ptab_cap = nc;
    }
    size_t s = cap_gc_slot((uintptr_t)pg->base >> CAP_PAGE_SHIFT, cap_gc.ptab_cap);
    while (cap_gc.ptab[s]) s = (s + 1) & (cap_gc.ptab_cap - 1);
    cap_gc.ptab[s] = pg;
}

static CapPage *cap_gc_page_of(uintptr_t addr) {
    if (!cap_gc.ptab_cap) return NULL;
    uintptr_t pageno = addr >> CAP_PAGE_SHIFT;
    size_t s = cap_gc_slot(pageno, cap_gc.ptab_cap);
    while (cap_gc.ptab[s]) {
        if (((uintptr_t)cap_gc.ptab[s]->base >> CAP_PAGE_SHIFT) == pageno) return cap_gc.ptab[s];
        s = (s + 1) & (cap_gc.ptab_cap - 1);
    }
    return NULL;
}

static void cap_gc_range(uintptr_t a, uintptr_t b) {
    if (a < cap_gc.lo) cap_gc.lo = a;
    if (b > cap_gc.hi) cap_gc.hi = b;
}

/* Move an empty page to the spare list, from which any size class can take it.
   With `release`, its memory also goes back to the operating system. Either
   way the address range stays reserved and the page stays in the page table
   with nothing allocated, so a stale pointer into it still maps to nothing. */
/* Account a page as released only after the OS confirms the advice. Kept
   separate from the syscall so failure accounting is directly unit-testable. */
static void cap_gc_account_release(CapPage *pg, int advice_succeeded) {
    if (pg->released || !advice_succeeded) return;
    if (cap_gc.heap < CAP_PAGE_SIZE)
        cap_panic("collector heap accounting underflow", "CWE-682", 0);
    pg->released = 1;
    cap_gc.heap -= CAP_PAGE_SIZE;
    cap_gc.released_total++;
}

static void cap_gc_release(CapPage *pg) {
    if (pg->released) return;
    int advised = 0;
#if defined(__APPLE__)
    advised = madvise(pg->base, CAP_PAGE_SIZE, MADV_FREE) == 0;
#elif defined(MADV_DONTNEED)
    advised = madvise(pg->base, CAP_PAGE_SIZE, MADV_DONTNEED) == 0;
#endif
    /* Unsupported advice and OS errors both leave the mapping counted. */
    cap_gc_account_release(pg, advised);
}

static void cap_gc_spare_page(CapPage *pg, int release) {
    pg->spare = 1;
    if (release) cap_gc_release(pg);
    if (cap_gc.nspare == cap_gc.capspare) {
        size_t needed;
        if (!cap_gc_size_add(cap_gc.nspare, 1, &needed)) cap_gc_oom();
        size_t nc = cap_gc_next_capacity(cap_gc.capspare, needed, 16);
        CapPage **ns = (CapPage **)cap_gc_meta_array(nc, sizeof(CapPage *));
        if (cap_gc.nspare) memcpy(ns, cap_gc.spare, cap_gc.nspare * sizeof(CapPage *));
        free(cap_gc.spare);
        cap_gc.spare = ns;
        cap_gc.capspare = nc;
    }
    cap_gc.spare[cap_gc.nspare] = pg;
    cap_gc.nspare++;
}

/* Set up a page's metadata for size class `cls` and thread its slots onto the free list. */
static void cap_gc_format_page(CapPage *pg, int atomic, int cls) {
    uint32_t nobj = (uint32_t)(CAP_PAGE_SIZE / cap_class_size[cls]);
    if (pg->alloc && pg->nobj != nobj) {
        free(pg->alloc);
        free(pg->mark);
        pg->alloc = NULL;
    }
    if (!pg->alloc) {
        pg->alloc = (uint8_t *)cap_gc_meta(nobj);
        pg->mark = (uint8_t *)cap_gc_meta(nobj);
    } else {
        memset(pg->alloc, 0, nobj);
        memset(pg->mark, 0, nobj);
    }
    if (pg->free_slots && (atomic != 2 || pg->free_cap != nobj)) {
        free(pg->free_slots);
        pg->free_slots = NULL;
        pg->free_cap = pg->free_count = 0;
    }
    if (atomic == 2 && !pg->free_slots) {
        pg->free_slots = (uint32_t *)cap_gc_meta_array(nobj, sizeof(uint32_t));
        pg->free_cap = nobj;
    }
    pg->objsize = cap_class_size[cls];
    pg->nobj = nobj;
    pg->atomic = atomic;
    if (atomic == 2) cap_gc_wipe(pg->base, CAP_PAGE_SIZE);
    pg->spare = 0;
    pg->released = 0;
    pg->free_count = 0;
    for (uint32_t i = pg->nobj; i-- > 0;) {
        if (atomic == 2) {
            pg->free_slots[pg->free_count++] = i;
        } else {
            void **slot = (void **)(pg->base + (size_t)i * pg->objsize);
            *slot = cap_gc.freelist[atomic][cls];
            cap_gc.freelist[atomic][cls] = slot;
        }
    }
}

static void cap_gc_new_page(int atomic, int cls) {
    if (cap_gc.nspare) {
        CapPage *pg = cap_gc.spare[--cap_gc.nspare];
        if (pg->released) {
            cap_gc.heap = cap_gc_account_add(cap_gc.heap, CAP_PAGE_SIZE);
            cap_gc.reused_total++;
        }
        cap_gc_format_page(pg, atomic, cls);
        return;
    }
    void *mem = NULL;
    if (posix_memalign(&mem, CAP_PAGE_SIZE, CAP_PAGE_SIZE) != 0) cap_gc_oom();
    CapPage *pg = (CapPage *)cap_gc_meta(sizeof(CapPage));
    pg->base = (char *)mem;
    cap_gc_format_page(pg, atomic, cls);
    if (cap_gc.npages == cap_gc.cappages) {
        size_t needed;
        if (!cap_gc_size_add(cap_gc.npages, 1, &needed)) cap_gc_oom();
        size_t nc = cap_gc_next_capacity(cap_gc.cappages, needed, 16);
        CapPage **np = (CapPage **)cap_gc_meta_array(nc, sizeof(CapPage *));
        if (cap_gc.npages) memcpy(np, cap_gc.pages, cap_gc.npages * sizeof(CapPage *));
        free(cap_gc.pages);
        cap_gc.pages = np;
        cap_gc.cappages = nc;
    }
    cap_gc_ptab_insert(pg);
    cap_gc.pages[cap_gc.npages] = pg;
    cap_gc.npages++;
    cap_gc.heap = cap_gc_account_add(cap_gc.heap, CAP_PAGE_SIZE);
    cap_gc_range((uintptr_t)pg->base, (uintptr_t)pg->base + CAP_PAGE_SIZE);
}

/* ---- marking ------------------------------------------------------------ */

static CapPage *cap_gc_find_secret_page(int cls) {
    for (size_t i = 0; i < cap_gc.npages; i++) {
        CapPage *pg = cap_gc.pages[i];
        if (!pg->spare && pg->atomic == 2 && pg->objsize == cap_class_size[cls] && pg->free_count)
            return pg;
    }
    return NULL;
}

static int cap_gc_has_free(int atomic, int cls) {
    return atomic == 2 ? cap_gc_find_secret_page(cls) != NULL : cap_gc.freelist[atomic][cls] != NULL;
}

static void cap_gc_push(void *p, size_t n) {
    size_t needed;
    if (!cap_gc_size_add(cap_gc.msp, 2, &needed)) cap_gc_oom();
    if (needed > cap_gc.mcap) {
        size_t nc = cap_gc_next_capacity(cap_gc.mcap, needed, 1024);
        void **ns = (void **)cap_gc_meta_array(nc, sizeof(void *));
        if (cap_gc.msp) memcpy(ns, cap_gc.mstack, cap_gc.msp * sizeof(void *));
        free(cap_gc.mstack);
        cap_gc.mstack = ns;
        cap_gc.mcap = nc;
    }
    cap_gc.mstack[cap_gc.msp++] = p;
    cap_gc.mstack[cap_gc.msp++] = (void *)n;
}

static void cap_gc_consider(uintptr_t v) {
    if (v < cap_gc.lo || v >= cap_gc.hi) return;
    CapPage *pg = cap_gc_page_of(v);
    if (pg) {
        uint32_t idx = (uint32_t)((v - (uintptr_t)pg->base) / pg->objsize);
        if (idx >= pg->nobj || !pg->alloc[idx] || pg->mark[idx]) return;
        pg->mark[idx] = 1;
        if (!pg->atomic) cap_gc_push(pg->base + (size_t)idx * pg->objsize, pg->objsize);
        return;
    }
    size_t lo = 0, hi = cap_gc.nlarge;
    while (lo < hi) {
        size_t mid = (lo + hi) / 2;
        CapLarge *l = &cap_gc.large[mid];
        if (v < (uintptr_t)l->base) hi = mid;
        else if (v - (uintptr_t)l->base >= l->size) lo = mid + 1;
        else {
            if (!l->mark) {
                l->mark = 1;
                if (!l->atomic) cap_gc_push(l->base, l->size);
            }
            return;
        }
    }
}

CAP_NO_SANITIZE static void cap_gc_scan(char *a, char *b) {
    uintptr_t p = (uintptr_t)a, end = (uintptr_t)b;
    uintptr_t misalignment = p & (sizeof(void *) - 1);
    if (misalignment) {
        uintptr_t adjust = sizeof(void *) - misalignment;
        if (adjust > UINTPTR_MAX - p) return;
        p += adjust;
    }
    for (; p <= end && end - p >= sizeof(void *); p += sizeof(void *))
        cap_gc_consider(*(uintptr_t *)p);
}

static void cap_gc_drain(void) {
    while (cap_gc.msp) {
        size_t n = (size_t)cap_gc.mstack[--cap_gc.msp];
        char *p = (char *)cap_gc.mstack[--cap_gc.msp];
        cap_gc_scan(p, p + n);
    }
}

CAP_NO_SANITIZE static void cap_gc_scan_stack(void) {
    volatile char here = 0;
    cap_gc_scan((char *)&here, cap_gc.stack_top);
}

static int cap_gc_large_cmp(const void *a, const void *b) {
    uintptr_t x = (uintptr_t)((const CapLarge *)a)->base, y = (uintptr_t)((const CapLarge *)b)->base;
    return x < y ? -1 : x > y;
}

CAP_NO_SANITIZE static void cap_gc_collect(void) {
    jmp_buf regs;                       /* spill callee-saved registers onto the stack */
    __builtin_unwind_init();
    setjmp(regs);
    cap_gc.collections++;
    if (cap_gc.nlarge) qsort(cap_gc.large, cap_gc.nlarge, sizeof(CapLarge), cap_gc_large_cmp);
    for (size_t i = 0; i < cap_gc.nroots; i++) {
        cap_gc_consider((uintptr_t)*cap_gc.roots[i]);
        cap_gc_drain();
    }
    cap_gc_scan((char *)&regs, (char *)&regs + sizeof regs);
    cap_gc_scan_stack();
    cap_gc_drain();

    /* sweep */
    size_t live = 0;
    for (int a = 0; a < CAP_KINDS; a++) for (int c = 0; c < CAP_NCLASS; c++) cap_gc.freelist[a][c] = NULL;
    /* Pages left empty are kept, up to a reserve, for the next allocations; the
       rest go back to the OS. The reserve covers what the program will allocate
       before the next collection (the new threshold), so a program in a steady
       state neither releases nor re-requests memory. It is decided after the
       sweep, once the live size is known. */
    size_t nempty = 0;
    for (size_t i = 0; i < cap_gc.npages; i++) {
        CapPage *pg = cap_gc.pages[i];
        if (pg->spare) continue;
        int cls = 0;
        while (cap_class_size[cls] != pg->objsize) cls++;
        int any = 0;
        void *head = cap_gc.freelist[pg->atomic][cls];
        if (pg->atomic == 2) pg->free_count = 0;
        for (uint32_t j = pg->nobj; j-- > 0;) {
            if (pg->mark[j]) {
                pg->mark[j] = 0;
                live += pg->objsize;
                any = 1;
            } else {
                if (pg->atomic == 2) {
                    if (pg->alloc[j]) cap_gc_wipe(pg->base + (size_t)j * pg->objsize, pg->objsize);
                    pg->alloc[j] = 0;
                    if (pg->free_count >= pg->free_cap)
                        cap_panic("secret-page free-slot metadata overflow", "CWE-682", 0);
                    pg->free_slots[pg->free_count++] = j;
                } else {
                    pg->alloc[j] = 0;
                    void **slot = (void **)(pg->base + (size_t)j * pg->objsize);
                    *slot = cap_gc.freelist[pg->atomic][cls];
                    cap_gc.freelist[pg->atomic][cls] = slot;
                }
            }
        }
        if (!any) {
            /* Unthread this page's slots again: they were pushed last, so the free
               list resumes at the head it had before this page. */
            if (pg->atomic != 2) cap_gc.freelist[pg->atomic][cls] = head;
            /* Gather empty pages at the front by swapping (page order does not matter). */
            cap_gc.pages[i] = cap_gc.pages[nempty];
            cap_gc.pages[nempty] = pg;
            nempty++;
        }
    }
    {
        size_t next_threshold = live > CAP_MIN_THRESHOLD ? live : CAP_MIN_THRESHOLD;
        /* Twice the threshold: rounding up to size classes can use up to twice the
           bytes requested. */
        size_t reserve = 2 * next_threshold / CAP_PAGE_SIZE;
        /* Unreleased spares from earlier collections count towards the reserve;
           any beyond it (the program's live size has fallen) are released now. */
        size_t kept = 0;
        for (size_t i = cap_gc.nspare; i-- > 0;) {
            CapPage *sp = cap_gc.spare[i];
            if (sp->released) continue;
            if (kept < reserve) kept++; else cap_gc_release(sp);
        }
        /* Release the excess first and keep the reserve last, so the spare list
           (taken from the end) hands out pages that are still in memory first. */
        size_t keep_now = reserve > kept ? reserve - kept : 0;
        if (keep_now > nempty) keep_now = nempty;
        for (size_t i = keep_now; i < nempty; i++) cap_gc_spare_page(cap_gc.pages[i], 1);
        for (size_t i = 0; i < keep_now; i++) cap_gc_spare_page(cap_gc.pages[i], 0);
    }
    size_t keep = 0;
    for (size_t i = 0; i < cap_gc.nlarge; i++) {
        CapLarge l = cap_gc.large[i];
        if (l.mark) {
            l.mark = 0;
            live += l.alloc_size;
            cap_gc.large[keep++] = l;
        } else {
            if (l.atomic == 2) {
                cap_gc_wipe(l.base, l.alloc_size);
                if (munmap(l.base, l.alloc_size) != 0)
                    cap_panic("unable to release wiped secret mapping", "CWE-244", 0);
            } else {
                free(l.base);
            }
            if (cap_gc.heap < l.alloc_size) cap_panic("collector heap accounting underflow", "CWE-682", 0);
            cap_gc.heap -= l.alloc_size;
        }
    }
    cap_gc.nlarge = keep;
    cap_gc.live = live;
    cap_gc.since = 0;
    cap_gc.threshold = live > CAP_MIN_THRESHOLD ? live : CAP_MIN_THRESHOLD;
}

/* ---- allocation ------------------------------------------------------------ */

static void *cap_gc_alloc(size_t n, int atomic) {
    if (!cap_gc.inited) cap_gc_init();
    if (atomic < 0 || atomic >= CAP_KINDS)
        cap_panic("invalid collector allocation kind", "CWE-843", 0);
    if (n == 0) n = 1;
    if (n > CAP_MAX_LEN)
        cap_panic("allocation exceeds maximum supported length", "CWE-190", 0);
    cap_gc.since = cap_gc_account_add(cap_gc.since, n);
    cap_gc.total = cap_gc_account_add(cap_gc.total, n);
    if (cap_gc.stress > 0) {
        if (++cap_gc.stress_count >= cap_gc.stress) { cap_gc.stress_count = 0; cap_gc_collect(); }
    } else if (cap_gc.since > cap_gc.threshold) {
        cap_gc_collect();
    }
    if (n > cap_class_size[CAP_NCLASS - 1]) {
        size_t alloc_size = n;
        if (atomic == 2) {
            size_t rounded;
            if (!cap_gc_size_add(n, (size_t)CAP_PAGE_SIZE - 1, &rounded))
                cap_panic("secret mapping size overflow", "CWE-190", 0);
            alloc_size = rounded & ~((size_t)CAP_PAGE_SIZE - 1);
        }
        if (cap_gc.max_heap && cap_gc_would_exceed_heap(alloc_size)) {
            cap_gc_collect();
            if (cap_gc_would_exceed_heap(alloc_size))
                cap_panic("memory limit exceeded (raise it with CAPSTAN_MAX_HEAP)", "CWE-400", 0);
        }
        void *p;
        if (atomic == 2) {
            p = mmap(NULL, alloc_size, PROT_READ | PROT_WRITE,
                     MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
            if (p == MAP_FAILED) cap_gc_oom();
        } else {
            p = calloc(1, n);
            if (!p) cap_gc_oom();
        }
        if (cap_gc.nlarge == cap_gc.caplarge) {
            size_t needed;
            if (!cap_gc_size_add(cap_gc.nlarge, 1, &needed)) cap_gc_oom();
            size_t nc = cap_gc_next_capacity(cap_gc.caplarge, needed, 64);
            CapLarge *nl = (CapLarge *)cap_gc_meta_array(nc, sizeof(CapLarge));
            if (cap_gc.nlarge) memcpy(nl, cap_gc.large, cap_gc.nlarge * sizeof(CapLarge));
            free(cap_gc.large);
            cap_gc.large = nl;
            cap_gc.caplarge = nc;
        }
        CapLarge l = {(char *)p, n, alloc_size, atomic, 0};
        size_t at = cap_gc.nlarge++;
        while (at > 0 && (uintptr_t)cap_gc.large[at - 1].base > (uintptr_t)p) { cap_gc.large[at] = cap_gc.large[at - 1]; at--; }
        cap_gc.large[at] = l;
        cap_gc.heap = cap_gc_account_add(cap_gc.heap, alloc_size);
        if (cap_gc.heap > cap_gc.peak_heap) cap_gc.peak_heap = cap_gc.heap;
        cap_gc_range((uintptr_t)p, (uintptr_t)p + n);
        return p;
    }
    int cls = 0;
    while (cap_class_size[cls] < n) cls++;
    if (!cap_gc_has_free(atomic, cls) && cap_gc.max_heap && cap_gc_would_exceed_heap(CAP_PAGE_SIZE)) {
        cap_gc_collect();
        if (!cap_gc_has_free(atomic, cls) && cap_gc_would_exceed_heap(CAP_PAGE_SIZE))
            cap_panic("memory limit exceeded (raise it with CAPSTAN_MAX_HEAP)", "CWE-400", 0);
    }
    if (!cap_gc_has_free(atomic, cls)) {
        cap_gc_new_page(atomic, cls);
        if (cap_gc.heap > cap_gc.peak_heap) cap_gc.peak_heap = cap_gc.heap;
    }
    if (atomic == 2) {
        CapPage *pg = cap_gc_find_secret_page(cls);
        if (!pg || !pg->free_count)
            cap_panic("secret-page free-slot invariant failed", "CWE-682", 0);
        uint32_t idx = pg->free_slots[--pg->free_count];
        if (idx >= pg->nobj || pg->alloc[idx])
            cap_panic("secret-page allocation bitmap invariant failed", "CWE-682", 0);
        pg->alloc[idx] = 1;
        void *slot = pg->base + (size_t)idx * pg->objsize;
        memset(slot, 0, pg->objsize);
        return slot;
    }
    void **slot = (void **)cap_gc.freelist[atomic][cls];
    cap_gc.freelist[atomic][cls] = *slot;
    CapPage *pg = cap_gc_page_of((uintptr_t)slot);
    pg->alloc[((uintptr_t)slot - (uintptr_t)pg->base) / pg->objsize] = 1;
    memset(slot, 0, cap_class_size[cls]);
    return slot;
}

/* Register the address of a global that may hold a pointer into the heap. */
static void cap_gc_root(void **addr) {
    if (cap_gc.nroots == cap_gc.caproots) {
        size_t needed;
        if (!cap_gc_size_add(cap_gc.nroots, 1, &needed)) cap_gc_oom();
        size_t nc = cap_gc_next_capacity(cap_gc.caproots, needed, 64);
        void ***nr = (void ***)cap_gc_meta_array(nc, sizeof(void **));
        if (cap_gc.nroots) memcpy(nr, cap_gc.roots, cap_gc.nroots * sizeof(void **));
        free(cap_gc.roots);
        cap_gc.roots = nr;
        cap_gc.caproots = nc;
    }
    cap_gc.roots[cap_gc.nroots] = addr;
    cap_gc.nroots++;
}

#endif
