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
#include <stddef.h>
#include <stdlib.h>
#include <errno.h>
#include <string.h>
#include <stdio.h>
#include <setjmp.h>
#include <pthread.h>
#include <signal.h>
#include <unistd.h>
#include <sys/mman.h>

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

/* Collector metadata and accounting are part of the trusted allocator. Never
   let a wrapped capacity or byte counter become an undersized allocation or
   bypass the configured heap limit. */
static size_t cap_gc_checked_add(size_t a, size_t b) {
    if (b > SIZE_MAX - a)
        cap_panic("garbage collector size addition overflow", "CWE-190", 0);
    return a + b;
}

static size_t cap_gc_checked_mul(size_t a, size_t b) {
    if (a && b > SIZE_MAX / a)
        cap_panic("garbage collector size multiplication overflow", "CWE-190", 0);
    return a * b;
}

static size_t cap_gc_next_capacity(size_t current, size_t required,
                                   size_t initial, size_t element_size) {
    if (!element_size)
        cap_panic("zero-sized garbage collector metadata element", "CWE-682", 0);
    size_t max_count = SIZE_MAX / element_size;
    if (required > max_count || current > max_count || !initial)
        cap_panic("garbage collector metadata capacity exceeds SIZE_MAX", "CWE-789", 0);
    size_t cap = current ? current : initial;
    if (cap > max_count)
        cap_panic("initial garbage collector metadata capacity exceeds SIZE_MAX", "CWE-789", 0);
    while (cap < required) {
        cap = cap > max_count / 2 ? max_count : cap * 2;
        if (!cap)
            cap_panic("garbage collector metadata capacity overflow", "CWE-190", 0);
    }
    return cap;
}

static size_t cap_gc_saturating_add(size_t a, size_t b) {
    return b > SIZE_MAX - a ? SIZE_MAX : a + b;
}

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
} CapPage;

typedef struct { char *base; size_t size; int atomic, mark; } CapLarge;

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

static int cap_gc_heap_would_exceed(size_t amount) {
    /* Preserve the existing convention: an explicit zero limit disables the cap. */
    if (cap_gc.max_heap == 0) return 0;
    if (cap_gc.heap > cap_gc.max_heap)
        cap_panic("garbage collector heap accounting invariant violated", "CWE-682", 0);
    return amount > cap_gc.max_heap - cap_gc.heap;
}

static void cap_gc_oom(void) {
    fprintf(stderr, "capstan: out of memory\n");
    exit(102);
}

static void *cap_gc_meta(size_t n) {
    void *p = calloc(1, n ? n : 1);
    if (!p) cap_gc_oom();
    return p;
}

static void *cap_gc_meta_array(size_t count, size_t element_size) {
    return cap_gc_meta(cap_gc_checked_mul(count, element_size));
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
    char *a = (char *)si->si_addr;
    const char *msg;
    int code = 101;
    if (cap_stack_low && a < cap_stack_low + 65536 && a + (1 << 24) > cap_stack_low) {
        msg = "runtime check failed: stack overflow, recursion too deep [CWE-674 prevented]\n";
    } else {
        msg = "capstan: internal error: invalid memory access; please report this as a bug\n";
        code = 105;
    }
    ssize_t w = write(2, msg, strlen(msg));
    (void)w;
    _exit(code);
}

static void cap_install_stack_guard(char *low) {
    cap_stack_low = low;
    stack_t ss;
    ss.ss_sp = cap_altstack;
    ss.ss_size = sizeof cap_altstack;
    ss.ss_flags = 0;
    if (sigaltstack(&ss, NULL) != 0) return;
    struct sigaction sa;
    memset(&sa, 0, sizeof sa);
    sa.sa_sigaction = cap_segv_handler;
    sa.sa_flags = SA_SIGINFO | SA_ONSTACK;
    sigemptyset(&sa.sa_mask);
    sigaction(SIGSEGV, &sa, NULL);
    sigaction(SIGBUS, &sa, NULL);
}

static size_t cap_gc_parse_heap_limit(const char *text) {
    /* Accept decimal digits followed by at most one binary suffix; do not
       let strtoull's permissive whitespace/sign handling normalize bad input. */
    if (!text || text[0] < '0' || text[0] > '9')
        cap_panic("invalid CAPSTAN_MAX_HEAP value", "CWE-1284", 0);
    errno = 0;
    char *end = NULL;
    unsigned long long value = strtoull(text, &end, 10);
    if (errno == ERANGE || end == text)
        cap_panic("invalid CAPSTAN_MAX_HEAP value", "CWE-1284", 0);
    unsigned shift = 0;
    if (*end == 'K' || *end == 'k') shift = 10;
    else if (*end == 'M' || *end == 'm') shift = 20;
    else if (*end == 'G' || *end == 'g') shift = 30;
    if (shift) end++;
    if (*end != '\0' || (shift && value > (~0ULL >> shift)))
        cap_panic("invalid CAPSTAN_MAX_HEAP value", "CWE-1284", 0);
    value <<= shift;
    if (value > CAP_MAX_LEN) value = CAP_MAX_LEN;
    return (size_t)value;
}

static size_t cap_gc_physical_heap_limit(size_t physical_pages, size_t page_size) {
    if (!physical_pages || !page_size) return (size_t)1 << 34;
    if (physical_pages > CAP_MAX_LEN / page_size) return CAP_MAX_LEN;
    size_t physical_bytes = physical_pages * page_size;
    size_t limit = (physical_bytes / 4) * 3 + ((physical_bytes % 4) * 3) / 4;
    return limit ? limit : CAP_MAX_LEN;
}

static void cap_gc_init(void) {
    if (cap_gc.inited) return;
    cap_gc.inited = 1;
    cap_gc.threshold = CAP_MIN_THRESHOLD;
    cap_gc.lo = UINTPTR_MAX;
    const char *s = getenv("CAPSTAN_GC_STRESS");
    if (s) cap_gc.stress = atol(s);
    if (getenv("CAPSTAN_GC_STATS")) { cap_gc.stats = 1; atexit(cap_gc_report); }
    const char *mh = getenv("CAPSTAN_MAX_HEAP");
    if (mh) {
        cap_gc.max_heap = cap_gc_parse_heap_limit(mh);
    } else {
        long pages = sysconf(_SC_PHYS_PAGES), psize = sysconf(_SC_PAGESIZE);
        cap_gc.max_heap = pages > 0 && psize > 0
                        ? cap_gc_physical_heap_limit((size_t)pages, (size_t)psize)
                        : (size_t)1 << 34;
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
    if (!pg || !pg->base)
        cap_panic("invalid page-table insertion record", "CWE-476", 0);
    if (cap_gc.ptab_cap && !cap_gc.ptab)
        cap_panic("page-table storage is missing", "CWE-476", 0);
    if ((!cap_gc.ptab_cap && cap_gc.npages) ||
        (cap_gc.ptab_cap && cap_gc.npages > cap_gc.ptab_cap / 2))
        cap_panic("page-table page-count invariant violated", "CWE-682", 0);
    if (cap_gc.ptab_cap &&
        (cap_gc.ptab_cap & (cap_gc.ptab_cap - 1)) != 0)
        cap_panic("page-table capacity is not a power of two", "CWE-682", 0);
    if (!cap_gc.ptab_cap || cap_gc.npages >= cap_gc.ptab_cap / 2) {
        size_t required = cap_gc.ptab_cap
                        ? cap_gc_checked_mul(cap_gc.ptab_cap, 2) : 64;
        size_t minimum = cap_gc_checked_add(cap_gc.npages, 1);
        if (required < minimum) required = minimum;
        size_t nc = cap_gc_next_capacity(cap_gc.ptab_cap, required,
                                         64, sizeof(CapPage *));
        CapPage **nt = (CapPage **)cap_gc_meta_array(nc, sizeof(CapPage *));
        for (size_t i = 0; i < cap_gc.ptab_cap; i++) {
            CapPage *p = cap_gc.ptab[i];
            if (!p) continue;
            if (!p->base)
                cap_panic("page-table contains a page without a base", "CWE-682", 0);
            uintptr_t page_no = (uintptr_t)p->base >> CAP_PAGE_SHIFT;
            size_t s = cap_gc_slot(page_no, nc);
            size_t probes = 0;
            while (nt[s] && probes < nc) {
                if (!nt[s]->base ||
                    ((uintptr_t)nt[s]->base >> CAP_PAGE_SHIFT) == page_no)
                    cap_panic("page-table contains a duplicate or invalid page", "CWE-682", 0);
                s = (s + 1) & (nc - 1);
                probes++;
            }
            if (probes == nc)
                cap_panic("page-table rehash found no empty slot", "CWE-400", 0);
            nt[s] = p;
        }
        free(cap_gc.ptab);
        cap_gc.ptab = nt;
        cap_gc.ptab_cap = nc;
    }
    uintptr_t page_no = (uintptr_t)pg->base >> CAP_PAGE_SHIFT;
    size_t s = cap_gc_slot(page_no, cap_gc.ptab_cap);
    for (size_t probes = 0; probes < cap_gc.ptab_cap; probes++) {
        CapPage *existing = cap_gc.ptab[s];
        if (!existing) {
            cap_gc.ptab[s] = pg;
            return;
        }
        if (!existing->base ||
            ((uintptr_t)existing->base >> CAP_PAGE_SHIFT) == page_no)
            cap_panic("duplicate or invalid page-table entry", "CWE-682", 0);
        s = (s + 1) & (cap_gc.ptab_cap - 1);
    }
    cap_panic("page table has no insertion slot", "CWE-400", 0);
}

static CapPage *cap_gc_page_of(uintptr_t addr) {
    if (!cap_gc.ptab_cap) return NULL;
    if (!cap_gc.ptab)
        cap_panic("page-table storage is missing", "CWE-476", 0);
    uintptr_t pageno = addr >> CAP_PAGE_SHIFT;
    if ((cap_gc.ptab_cap & (cap_gc.ptab_cap - 1)) != 0)
        cap_panic("page-table capacity is not a power of two", "CWE-682", 0);
    size_t s = cap_gc_slot(pageno, cap_gc.ptab_cap);
    for (size_t probes = 0; probes < cap_gc.ptab_cap; probes++) {
        CapPage *pg = cap_gc.ptab[s];
        if (!pg) return NULL;
        if (!pg->base)
            cap_panic("page-table entry has no base", "CWE-682", 0);
        if (((uintptr_t)pg->base >> CAP_PAGE_SHIFT) == pageno) return pg;
        s = (s + 1) & (cap_gc.ptab_cap - 1);
    }
    cap_panic("page table has no empty slot", "CWE-400", 0);
}

static void cap_gc_range(uintptr_t a, uintptr_t b) {
    if (a < cap_gc.lo) cap_gc.lo = a;
    if (b > cap_gc.hi) cap_gc.hi = b;
}

/* Move an empty page to the spare list, from which any size class can take it.
   With `release`, its memory also goes back to the operating system. Either
   way the address range stays reserved and the page stays in the page table
   with nothing allocated, so a stale pointer into it still maps to nothing. */
static void cap_gc_release(CapPage *pg) {
    if (pg->released) return;
    if (cap_gc.heap < CAP_PAGE_SIZE)
        cap_panic("page release would underflow heap accounting", "CWE-682", 0);
#if defined(__APPLE__)
    madvise(pg->base, CAP_PAGE_SIZE, MADV_FREE);
#elif defined(MADV_DONTNEED)
    madvise(pg->base, CAP_PAGE_SIZE, MADV_DONTNEED);
#endif
    pg->released = 1;
    cap_gc.heap -= CAP_PAGE_SIZE;
    cap_gc.released_total = cap_gc_saturating_add(cap_gc.released_total, 1);
}

static void cap_gc_spare_page(CapPage *pg, int release) {
    pg->spare = 1;
    if (release) cap_gc_release(pg);
    if (cap_gc.nspare > cap_gc.capspare ||
        (cap_gc.capspare > 0 && !cap_gc.spare))
        cap_panic("spare-page metadata invariant violated", "CWE-682", 0);
    if (cap_gc.nspare == cap_gc.capspare) {
        size_t nc = cap_gc_next_capacity(cap_gc.capspare,
                                         cap_gc_checked_add(cap_gc.nspare, 1),
                                         16, sizeof(CapPage *));
        CapPage **ns = (CapPage **)cap_gc_meta_array(nc, sizeof(CapPage *));
        if (cap_gc.nspare) memcpy(ns, cap_gc.spare, sizeof(CapPage *) * cap_gc.nspare);
        free(cap_gc.spare);
        cap_gc.spare = ns;
        cap_gc.capspare = nc;
    }
    cap_gc.spare[cap_gc.nspare++] = pg;
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
    pg->objsize = cap_class_size[cls];
    pg->nobj = nobj;
    pg->atomic = atomic;
    pg->spare = 0;
    pg->released = 0;
    for (uint32_t i = pg->nobj; i-- > 0;) {
        void **slot = (void **)(pg->base + (size_t)i * pg->objsize);
        *slot = cap_gc.freelist[atomic][cls];
        cap_gc.freelist[atomic][cls] = slot;
    }
}

static void cap_gc_new_page(int atomic, int cls) {
    if (cap_gc.nspare > cap_gc.capspare ||
        (cap_gc.nspare > 0 && !cap_gc.spare))
        cap_panic("spare-page storage invariant violated", "CWE-682", 0);
    if (cap_gc.nspare) {
        CapPage *pg = cap_gc.spare[--cap_gc.nspare];
        if (pg->released) {
            if (cap_gc_heap_would_exceed(CAP_PAGE_SIZE))
                cap_panic("memory limit exceeded while reusing a page", "CWE-400", 0);
            cap_gc.heap = cap_gc_checked_add(cap_gc.heap, CAP_PAGE_SIZE);
            cap_gc.reused_total = cap_gc_saturating_add(cap_gc.reused_total, 1);
        }
        cap_gc_format_page(pg, atomic, cls);
        return;
    }
    void *mem = NULL;
    if (posix_memalign(&mem, CAP_PAGE_SIZE, CAP_PAGE_SIZE) != 0) cap_gc_oom();
    CapPage *pg = (CapPage *)cap_gc_meta(sizeof(CapPage));
    pg->base = (char *)mem;
    cap_gc_format_page(pg, atomic, cls);
    if (cap_gc.npages > cap_gc.cappages ||
        (cap_gc.cappages > 0 && !cap_gc.pages))
        cap_panic("page metadata invariant violated", "CWE-682", 0);
    if (cap_gc.npages == cap_gc.cappages) {
        size_t nc = cap_gc_next_capacity(cap_gc.cappages,
                                         cap_gc_checked_add(cap_gc.npages, 1),
                                         16, sizeof(CapPage *));
        CapPage **np = (CapPage **)cap_gc_meta_array(nc, sizeof(CapPage *));
        if (cap_gc.npages) memcpy(np, cap_gc.pages, sizeof(CapPage *) * cap_gc.npages);
        free(cap_gc.pages);
        cap_gc.pages = np;
        cap_gc.cappages = nc;
    }
    cap_gc_ptab_insert(pg);
    cap_gc.pages[cap_gc.npages++] = pg;
    if (cap_gc_heap_would_exceed(CAP_PAGE_SIZE))
        cap_panic("memory limit exceeded while allocating a page", "CWE-400", 0);
    cap_gc.heap = cap_gc_checked_add(cap_gc.heap, CAP_PAGE_SIZE);
    cap_gc_range((uintptr_t)pg->base, (uintptr_t)pg->base + CAP_PAGE_SIZE);
}

/* ---- marking ------------------------------------------------------------ */

static void cap_gc_push(void *p, size_t n) {
    if (cap_gc.msp > cap_gc.mcap ||
        (cap_gc.mcap > 0 && !cap_gc.mstack))
        cap_panic("mark-stack metadata invariant violated", "CWE-682", 0);
    if (cap_gc.mcap - cap_gc.msp < 2) {
        size_t nc = cap_gc_next_capacity(cap_gc.mcap,
                                         cap_gc_checked_add(cap_gc.msp, 2),
                                         1024, sizeof(void *));
        void **ns = (void **)cap_gc_meta_array(nc, sizeof(void *));
        if (cap_gc.msp) memcpy(ns, cap_gc.mstack, sizeof(void *) * cap_gc.msp);
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
        else if (v >= (uintptr_t)l->base + l->size) lo = mid + 1;
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
    uintptr_t p = ((uintptr_t)a + sizeof(void *) - 1) & ~(uintptr_t)(sizeof(void *) - 1);
    for (; p + sizeof(void *) <= (uintptr_t)b; p += sizeof(void *)) cap_gc_consider(*(uintptr_t *)p);
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
    cap_gc.collections = cap_gc_saturating_add(cap_gc.collections, 1);
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
        for (uint32_t j = pg->nobj; j-- > 0;) {
            if (pg->mark[j]) {
                pg->mark[j] = 0;
                live = cap_gc_checked_add(live, pg->objsize);
                any = 1;
            } else {
                if (pg->atomic == 2 && pg->alloc[j]) memset(pg->base + (size_t)j * pg->objsize, 0, pg->objsize);
                pg->alloc[j] = 0;
                void **slot = (void **)(pg->base + (size_t)j * pg->objsize);
                *slot = cap_gc.freelist[pg->atomic][cls];
                cap_gc.freelist[pg->atomic][cls] = slot;
            }
        }
        if (!any) {
            /* Unthread this page's slots again: they were pushed last, so the free
               list resumes at the head it had before this page. */
            cap_gc.freelist[pg->atomic][cls] = head;
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
            live = cap_gc_checked_add(live, l.size);
            cap_gc.large[keep++] = l;
        } else {
            if (l.atomic == 2) { volatile char *w = l.base; for (size_t z = 0; z < l.size; z++) w[z] = 0; }
            if (cap_gc.heap < l.size)
                cap_panic("large-object release would underflow heap accounting", "CWE-682", 0);
            free(l.base);
            cap_gc.heap -= l.size;
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
        cap_panic("invalid allocation kind", "CWE-682", 0);
    if (n == 0) n = 1;
    if (n > CAP_MAX_LEN)
        cap_panic("allocation exceeds maximum object size", "CWE-789", 0);
    cap_gc.since = cap_gc_saturating_add(cap_gc.since, n);
    cap_gc.total = cap_gc_saturating_add(cap_gc.total, n);
    if (cap_gc.stress > 0) {
        if (++cap_gc.stress_count >= cap_gc.stress) { cap_gc.stress_count = 0; cap_gc_collect(); }
    } else if (cap_gc.since > cap_gc.threshold) {
        cap_gc_collect();
    }
    if (n > cap_class_size[CAP_NCLASS - 1]) {
        if (cap_gc_heap_would_exceed(n)) {
            cap_gc_collect();
            if (cap_gc_heap_would_exceed(n)) cap_panic("memory limit exceeded (raise it with CAPSTAN_MAX_HEAP)", "CWE-400", 0);
        }
        void *p = calloc(1, n);
        if (!p) cap_gc_oom();
        if (cap_gc.nlarge > cap_gc.caplarge ||
            (cap_gc.caplarge > 0 && !cap_gc.large))
            cap_panic("large-object metadata invariant violated", "CWE-682", 0);
        if (cap_gc.nlarge == cap_gc.caplarge) {
            size_t nc = cap_gc_next_capacity(cap_gc.caplarge,
                                             cap_gc_checked_add(cap_gc.nlarge, 1),
                                             64, sizeof(CapLarge));
            CapLarge *nl = (CapLarge *)cap_gc_meta_array(nc, sizeof(CapLarge));
            if (cap_gc.nlarge) memcpy(nl, cap_gc.large, sizeof(CapLarge) * cap_gc.nlarge);
            free(cap_gc.large);
            cap_gc.large = nl;
            cap_gc.caplarge = nc;
        }
        CapLarge l = {(char *)p, n, atomic, 0};
        size_t at = cap_gc.nlarge++;
        while (at > 0 && (uintptr_t)cap_gc.large[at - 1].base > (uintptr_t)p) { cap_gc.large[at] = cap_gc.large[at - 1]; at--; }
        cap_gc.large[at] = l;
        cap_gc.heap = cap_gc_checked_add(cap_gc.heap, n);
        if (cap_gc.heap > cap_gc.peak_heap) cap_gc.peak_heap = cap_gc.heap;
        cap_gc_range((uintptr_t)p, (uintptr_t)p + n);
        return p;
    }
    int cls = 0;
    while (cap_class_size[cls] < n) cls++;
    if (cap_gc.nspare > cap_gc.capspare ||
        (cap_gc.nspare > 0 && !cap_gc.spare))
        cap_panic("spare-page storage invariant violated", "CWE-682", 0);
    if (!cap_gc.freelist[atomic][cls]) {
        size_t page_charge = cap_gc.nspare && !cap_gc.spare[cap_gc.nspare - 1]->released
                           ? 0 : (size_t)CAP_PAGE_SIZE;
        if (cap_gc_heap_would_exceed(page_charge)) {
            cap_gc_collect();
            if (!cap_gc.freelist[atomic][cls]) {
                page_charge = cap_gc.nspare && !cap_gc.spare[cap_gc.nspare - 1]->released
                            ? 0 : (size_t)CAP_PAGE_SIZE;
                if (cap_gc_heap_would_exceed(page_charge))
                    cap_panic("memory limit exceeded (raise it with CAPSTAN_MAX_HEAP)", "CWE-400", 0);
            }
        }
    }
    if (!cap_gc.freelist[atomic][cls]) {
        cap_gc_new_page(atomic, cls);
        if (cap_gc.heap > cap_gc.peak_heap) cap_gc.peak_heap = cap_gc.heap;
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
    if (!addr)
        cap_panic("null registered root slot", "CWE-476", 0);
    if (cap_gc.nroots > cap_gc.caproots ||
        (cap_gc.caproots > 0 && !cap_gc.roots))
        cap_panic("root metadata invariant violated", "CWE-682", 0);
    if (cap_gc.nroots == cap_gc.caproots) {
        size_t nc = cap_gc_next_capacity(cap_gc.caproots,
                                         cap_gc_checked_add(cap_gc.nroots, 1),
                                         64, sizeof(void **));
        void ***nr = (void ***)cap_gc_meta_array(nc, sizeof(void **));
        if (cap_gc.nroots) memcpy(nr, cap_gc.roots, sizeof(void **) * cap_gc.nroots);
        free(cap_gc.roots);
        cap_gc.roots = nr;
        cap_gc.caproots = nc;
    }
    if (cap_gc.nroots >= cap_gc.caproots)
        cap_panic("root metadata capacity invariant violated", "CWE-682", 0);
    cap_gc.roots[cap_gc.nroots++] = addr;
}

#endif
