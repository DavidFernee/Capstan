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
 *  - Roots: the machine stack, callee-saved registers (spilled with setjmp),
 *    and global variables registered by the generated code. The stack and
 *    object contents are scanned conservatively.
 *
 * Environment:
 *   CAPSTAN_GC_STATS=1    print collector statistics on exit
 *   CAPSTAN_GC_STRESS=N   collect every N allocations (for testing)
 */
#ifndef CAPSTAN_GC_H
#define CAPSTAN_GC_H

#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <setjmp.h>
#include <pthread.h>
#include <signal.h>
#include <unistd.h>

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

static const uint32_t cap_class_size[CAP_NCLASS] =
    {16, 32, 48, 64, 96, 128, 192, 256, 384, 512, 768, 1024, 1536, 2048};

typedef struct CapPage {
    char *base;
    uint32_t objsize, nobj;
    int atomic;
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
    void *freelist[2][CAP_NCLASS];
    CapLarge *large; size_t nlarge, caplarge;
    void ***roots; size_t nroots, caproots;
    uintptr_t lo, hi;
    size_t since, threshold, live, heap, peak_heap, total, collections;
    void **mstack; size_t msp, mcap;
} cap_gc;

static void cap_gc_oom(void) {
    fprintf(stderr, "capstan: out of memory\n");
    exit(102);
}

static void *cap_gc_meta(size_t n) {
    void *p = calloc(1, n ? n : 1);
    if (!p) cap_gc_oom();
    return p;
}

static void cap_gc_report(void) {
    fprintf(stderr, "gc: collections=%zu total_allocated=%zu live=%zu heap=%zu peak_heap=%zu\n",
            cap_gc.collections, cap_gc.total, cap_gc.live, cap_gc.heap, cap_gc.peak_heap);
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

static void cap_gc_init(void) {
    if (cap_gc.inited) return;
    cap_gc.inited = 1;
    cap_gc.threshold = CAP_MIN_THRESHOLD;
    cap_gc.lo = UINTPTR_MAX;
    const char *s = getenv("CAPSTAN_GC_STRESS");
    if (s) cap_gc.stress = atol(s);
    if (getenv("CAPSTAN_GC_STATS")) { cap_gc.stats = 1; atexit(cap_gc_report); }
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
    if ((cap_gc.npages + 1) * 2 > cap_gc.ptab_cap) {
        size_t nc = cap_gc.ptab_cap ? cap_gc.ptab_cap * 2 : 64;
        CapPage **nt = (CapPage **)cap_gc_meta(sizeof(CapPage *) * nc);
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

static void cap_gc_new_page(int atomic, int cls) {
    void *mem = NULL;
    if (posix_memalign(&mem, CAP_PAGE_SIZE, CAP_PAGE_SIZE) != 0) cap_gc_oom();
    CapPage *pg = (CapPage *)cap_gc_meta(sizeof(CapPage));
    pg->base = (char *)mem;
    pg->objsize = cap_class_size[cls];
    pg->nobj = (uint32_t)(CAP_PAGE_SIZE / pg->objsize);
    pg->atomic = atomic;
    pg->alloc = (uint8_t *)cap_gc_meta(pg->nobj);
    pg->mark = (uint8_t *)cap_gc_meta(pg->nobj);
    for (uint32_t i = pg->nobj; i-- > 0;) {
        void **slot = (void **)(pg->base + (size_t)i * pg->objsize);
        *slot = cap_gc.freelist[atomic][cls];
        cap_gc.freelist[atomic][cls] = slot;
    }
    if (cap_gc.npages == cap_gc.cappages) {
        size_t nc = cap_gc.cappages ? cap_gc.cappages * 2 : 16;
        CapPage **np = (CapPage **)cap_gc_meta(sizeof(CapPage *) * nc);
        if (cap_gc.npages) memcpy(np, cap_gc.pages, sizeof(CapPage *) * cap_gc.npages);
        free(cap_gc.pages);
        cap_gc.pages = np;
        cap_gc.cappages = nc;
    }
    cap_gc_ptab_insert(pg);
    cap_gc.pages[cap_gc.npages++] = pg;
    cap_gc.heap += CAP_PAGE_SIZE;
    cap_gc_range((uintptr_t)pg->base, (uintptr_t)pg->base + CAP_PAGE_SIZE);
}

/* ---- marking ------------------------------------------------------------ */

static void cap_gc_push(void *p, size_t n) {
    if (cap_gc.msp + 2 > cap_gc.mcap) {
        size_t nc = cap_gc.mcap ? cap_gc.mcap * 2 : 1024;
        void **ns = (void **)cap_gc_meta(sizeof(void *) * nc);
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
    for (int a = 0; a < 2; a++) for (int c = 0; c < CAP_NCLASS; c++) cap_gc.freelist[a][c] = NULL;
    for (size_t i = 0; i < cap_gc.npages; i++) {
        CapPage *pg = cap_gc.pages[i];
        int cls = 0;
        while (cap_class_size[cls] != pg->objsize) cls++;
        for (uint32_t j = pg->nobj; j-- > 0;) {
            if (pg->mark[j]) {
                pg->mark[j] = 0;
                live += pg->objsize;
            } else {
                pg->alloc[j] = 0;
                void **slot = (void **)(pg->base + (size_t)j * pg->objsize);
                *slot = cap_gc.freelist[pg->atomic][cls];
                cap_gc.freelist[pg->atomic][cls] = slot;
            }
        }
    }
    size_t keep = 0;
    for (size_t i = 0; i < cap_gc.nlarge; i++) {
        CapLarge l = cap_gc.large[i];
        if (l.mark) {
            l.mark = 0;
            live += l.size;
            cap_gc.large[keep++] = l;
        } else {
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
    if (n == 0) n = 1;
    cap_gc.since += n;
    cap_gc.total += n;
    if (cap_gc.stress > 0) {
        if (++cap_gc.stress_count >= cap_gc.stress) { cap_gc.stress_count = 0; cap_gc_collect(); }
    } else if (cap_gc.since > cap_gc.threshold) {
        cap_gc_collect();
    }
    if (n > cap_class_size[CAP_NCLASS - 1]) {
        void *p = calloc(1, n);
        if (!p) cap_gc_oom();
        if (cap_gc.nlarge == cap_gc.caplarge) {
            size_t nc = cap_gc.caplarge ? cap_gc.caplarge * 2 : 64;
            CapLarge *nl = (CapLarge *)cap_gc_meta(sizeof(CapLarge) * nc);
            if (cap_gc.nlarge) memcpy(nl, cap_gc.large, sizeof(CapLarge) * cap_gc.nlarge);
            free(cap_gc.large);
            cap_gc.large = nl;
            cap_gc.caplarge = nc;
        }
        CapLarge l = {(char *)p, n, atomic, 0};
        size_t at = cap_gc.nlarge++;
        while (at > 0 && (uintptr_t)cap_gc.large[at - 1].base > (uintptr_t)p) { cap_gc.large[at] = cap_gc.large[at - 1]; at--; }
        cap_gc.large[at] = l;
        cap_gc.heap += n;
        if (cap_gc.heap > cap_gc.peak_heap) cap_gc.peak_heap = cap_gc.heap;
        cap_gc_range((uintptr_t)p, (uintptr_t)p + n);
        return p;
    }
    int cls = 0;
    while (cap_class_size[cls] < n) cls++;
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
    if (cap_gc.nroots == cap_gc.caproots) {
        size_t nc = cap_gc.caproots ? cap_gc.caproots * 2 : 64;
        void ***nr = (void ***)cap_gc_meta(sizeof(void **) * nc);
        if (cap_gc.nroots) memcpy(nr, cap_gc.roots, sizeof(void **) * cap_gc.nroots);
        free(cap_gc.roots);
        cap_gc.roots = nr;
        cap_gc.caproots = nc;
    }
    cap_gc.roots[cap_gc.nroots++] = addr;
}

#endif
