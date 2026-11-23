"""K0 classifier: assign a weakness class (and CWE) to a Linux kernel CVE from its fix description.

The kernel's CNA publishes each CVE with the fix commit's message as its description, and almost
never assigns a CWE. This module reads that text and the crash signatures quoted in it (KASAN,
UBSAN, KMSAN, lockdep, kmemleak, KCSAN reports) and returns the most specific class it can.

Rules are tried in order; the first match wins. Memory-safety consequences come before their
causes, so "a race leads to a use-after-free" is a use-after-free: that is the class a language
would have to stop. The order and every pattern are part of the method and are published with
the study (docs/K0-KERNEL-CVES.md).
"""
import re

# (class, CWE, patterns). Patterns are case-insensitive regular expressions.
RULES = [
    ("double or invalid free", "CWE-415", [r"double[- ]free", r"invalid free", r"bad free", r"kfree\(\)\s+\w*\s*(devres|devm)", r"free\w* (an? )?(active|static|stack|non-heap)", r"mismatched (free|alloc)", r"freed twice", r"double kfree", r"double put"]),
    ("use-after-free", "CWE-416", [
        r"use[- ]after[- ]free", r"\buaf\b", r"slab-use-after-free", r"use-after-scope",
        r"dangling pointer", r"access(es|ing)? (already )?freed", r"dereferenc\w* (the )?freed",
        r"after (it|they|the \w+) (has|have|had|was|were) (been )?freed", r"stale pointer", r"(has|have|had|was|were) (already )?(been )?(released|freed)\b",
    ]),
    ("out-of-bounds write", "CWE-787", [
        r"out[- ]of[- ]bounds write", r"oob write", r"buffer overflow", r"heap overflow",
        r"stack overflow", r"buffer overrun", r"overwrit\w+ (beyond|past)", r"write (beyond|past) the end",
        r"memory corruption", r"skb_(under|over)_panic", r"slab-out-of-bounds in \w*(write|copy|memcpy|memset)",
    ]),
    ("out-of-bounds read", "CWE-125", [
        r"out[- ]of[- ]bounds?", r"\boob\b", r"off[- ]by[- ]one", r"array-index-out-of-bounds", r"index out of range",
        r"over-?read", r"read (beyond|past) the end", r"beyond the end of", r"past the end of",
        r"out of range (array )?index", r"exceed\w* the (array|buffer)", r"buffer over",
        r"invalid (array )?index", r"access\w* outside (of )?(the )?\w*", r"nul-terminat", r"null-terminat", r"check\w* (the )?\w* ?index", r"\bindex\b.{0,30}\b(check|bound|range|valid)", r"bounds check", r"array overflow",
    ]),
    ("NULL dereference", "CWE-476", [
        r"null[- ]pointer", r"null check", r"check\w* .{0,40}before derefer", r"null-?check", r"\bnpd\b", r"null vs\.? is_err", r"is_err\(\)", r"err(or)?[_ ]ptr", r"error pointer", r"null-ptr-deref", r"null dereference", r"null deref",
        r"dereferenc\w* (a |the )?null", r"null ptr", r"\bnull\b.{0,40}\bderef",
        r"deref\w*.{0,40}\bnull\b", r"is_err_or_null", r"unable to handle kernel null",
    ]),
    ("uninitialised memory", "CWE-908", [
        r"uninit-value", r"^\S+(: \S+)*: initiali[sz]e ", r"uninitiali[sz]ed", r"un-initiali[sz]ed", r"kernel-infoleak",
        r"info(rmation)?[- ]?leak", r"not initiali[sz]ed", r"without initiali[sz]", r"kmsan",
        r"leak\w* (kernel |stack |uninit\w* )?(memory|data|bytes|contents) to user",
    ]),
    ("integer overflow", "CWE-190", [
        r"integer (overflow|underflow|wrap)", r"signed-integer-overflow", r"\boverflows?\b.{0,30}\b(u8|u16|u32|u64|int|integer|size|multiplication|addition)",
        r"\bwrap(s|ped)? ?around", r"\bunderflow", r"arithmetic overflow", r"overflow in (the )?(calculation|multiplication|addition)",
        r"check_(add|mul|sub)_overflow", r"truncat\w+ (to|of) (u8|u16|u32|int)", r"\boverflow\b",
    ]),
    ("divide by zero", "CWE-369", [r"divi(de|sion)[- ]by[- ]zero", r"divide error", r"div(ision)? by 0", r"zero divisor"]),
    ("shift out of bounds", "CWE-1335", [r"shift-out-of-bounds", r"shift exponent", r"undefined shift", r"shift (is )?too large"]),
    ("type confusion", "CWE-843", [r"type confusion", r"wrong type", r"incorrect type", r"misinterpret\w* as"]),
    ("unbounded recursion", "CWE-674", [r"(?<!lock )recursion", r"recursive\w* (call|loop)", r"stack exhaustion"]),
    ("unchecked error", "CWE-252", [r"(missing|add|unchecked|ignor\w+|check\w*) (\w+ )?(error|return)[- ](value|code|check)s?", r"error (handling|check)", r"return value", r"not check\w* (the )?(return|result|error)"]),
    ("speculative execution", "CWE-1037", [r"speculat", r"spectre", r"side[- ]channel", r"retbleed", r"\bmds\b"]),
    ("deadlock", "CWE-833", [r"dead-?lock", r"\babba\b", r"recursive locking", r"lock recursion", r"circular locking", r"lock inversion", r"self-?lock"]),
    ("improper locking", "CWE-667", [
        r"lockdep", r"under (the )?[\w ]{0,20}(lock|semaphore|mutex|spinlock)", r"(lock|mutex|semaphore) (ordering|order)", r"sleeping function called from invalid context", r"scheduling while atomic",
        r"lock (imbalance|leak)", r"unbalanced (lock|unlock)", r"missing (un)?lock", r"without (holding|taking) (the )?\w*\s?lock",
        r"(spin|mutex|rcu|lock)\w* (is )?(not )?held", r"suspicious rcu", r"rcu_read_lock", r"rcu protection", r"\brcu\b", r"bad unlock",
        r"\block(ing)?\b.{0,30}\b(wrong|missing|incorrect)",
    ]),
    ("race condition", "CWE-362", [r"\brac(e|es|y|ing)\b", r"data-race", r"memory barrier", r"\bsmp_[rw]?mb\b", r"(kill|cancel|disable|flush|stop)\w* (the )?(\w+ )?(timer|work|works|workqueue)", r"kcsan", r"concurrent", r"read_once", r"write_once", r"toctou", r"time-of-check"]),
    ("memory leak", "CWE-401", [r"memory leak", r"kmemleak", r"leak\w* (the )?(memory|allocat|buffer|skb|page)", r"\bleak(s|ed|ing)?\b.{0,40}\b(kfree|free|alloc)"]),
    ("resource leak", "CWE-772", [r"refcount", r"reference (count )?leak", r"\bleak", r"missing (\w+ )?(put|release|free)", r"not (released|freed)"]),
    ("hang or infinite loop", "CWE-835", [r"infinite loop", r"cond_resched", r"don't spin", r"busy[- ]loop", r"endless loop", r"soft lockup", r"hung task", r"livelock", r"\bhang", r"stall", r"loops? forever", r"never (terminates|ends|exits)"]),
    ("missing authorisation", "CWE-862", [r"capab", r"permission check", r"privilege", r"cap_sys_admin", r"\bcap_\w+", r"unprivileged"]),
    ("insufficient validation", "CWE-20", [r"validat", r"sanity[- ]check", r"\bcheck (the |for )?\w+ (length|size|value|count)", r"untrusted", r"type mismatch", r"endpoint (type )?check", r"malicious", r"crafted", r"bogus", r"invalid (input|value|length|size)"]),
    ("assertion or warning reached", "CWE-617", [r"kernel bug at", r"assertion", r"\bbug_on\b", r"\bwarn(_on|ing:)", r"\bbug:", r"\bpanic", r"\boops\b", r"crash", r"page fault", r"general protection fault"]),
]

_COMPILED = [(c, w, [re.compile(p, re.I) for p in ps]) for c, w, ps in RULES]
_SPLIT = [c for c, _, _ in RULES].index("deadlock")
_BOILER = re.compile(r"^In the Linux kernel, the following vulnerability has been resolved:\s*", re.I)


def clean(desc):
    """Drop the CNA's fixed preamble and the trailing links."""
    return re.sub(r"\s+", " ", _BOILER.sub("", desc or ""))


def classify(title, desc):
    """Return (class, CWE, evidence) for one CVE, or ("unclassified", "", "")."""
    subject = title or ""
    body = clean(desc)
    # Within a group the commit subject (the author's one-line statement of the bug) is tried
    # before the whole message and the sanitiser reports quoted in it.
    # Memory-safety classes are tried on both texts before any other class, so a consequence named
    # anywhere outranks a cause named in the subject.
    for group in (_COMPILED[:_SPLIT], _COMPILED[_SPLIT:]):
        for text in (subject, body):
            for cls, cwe, pats in group:
                for p in pats:
                    m = p.search(text)
                    if m:
                        return cls, cwe, m.group(0)
    return "unclassified", "", ""
