# The Capstan Challenge (draft)

> **Status: draft. The challenge is not open and no prize is offered.** It will open only when it
> is announced with its funding, judges and final rules ([DESIGN-MAP.md](DESIGN-MAP.md), section 8).
> Until then, report findings through [SECURITY.md](../SECURITY.md): every confirmed one is fixed,
> credited and listed in the hall of fame below.

Capstan claims that the weaknesses its [CWE atlas](CWE-ATLAS.md) marks as prevented cannot be
written in it. The Capstan Challenge puts money behind that claim: each year, a prize for anyone
who writes a vulnerability Capstan says is impossible.

A successful entry is the most useful thing that can happen to the language. Every winner gets a
public write-up, a fix, and a regression test that would have caught it, so each payout makes
Capstan measurably stronger.

## What wins

An entry must work against the latest Capstan release at the time it is submitted, built from a
clean checkout of its tag, with no use of `trust()` unless the tier says otherwise.

| Tier | What it takes | Prize |
|---|---|---|
| **1. Wrong verdict** | A program Capstan compiles that contains a weakness the atlas marks *prevented at compile time*, *inexpressible* or *no effect*, shown by a test that demonstrates the weakness | *to be set* |
| **2. Broken safe stop** | A program in which a check the atlas marks *stopped safely at run time* fails to stop: memory corruption, undefined behaviour, or execution continuing past a violated check | *to be set* |
| **3. Exploit** | A tier 1 or tier 2 entry turned into a working attack on a Capstan program: code execution, disclosure of data the program protects, or bypass of a grant, policy or taint check | *to be set* |
| **4. Broken proof** | Once proof against a specification exists (K1.10): a module at the `refined` level that does something its specification forbids, or a proof the independent checker accepts that is false | *to be set: the largest prize* |

Bugs in Capstan's own compiler, runtime, standard library or bootstrap count, in the tier their
effect matches. A code-generation error that turns a correct program into an exploitable one is a
tier 3 entry, and arguably the most valuable kind.

Suggested proportions, when funded: tier 2 at twice tier 1, tier 3 at five times, and tier 4 at
twenty times. An unclaimed prize carries over and grows the next year.

## What does not win

- **Documented gaps.** A weakness the atlas lists as a gap, or as possible only through an escape
  hatch, on the day the entry is received. These are known; reports of practical exploits are
  still welcome through SECURITY.md and are credited.
- **Logic and specification errors.** Code that does what it says when what it says is wrong (the
  atlas's "beyond any language" list), and a specification that permits what it should forbid.
- **Misuse of `trust()`.** Declaring unvalidated input trusted and then misusing it, except where
  `trust()` itself fails to be reported by the build as Capstan promises.
- **A safe stop.** A program that halts with a run-time error at a check is the guarantee working.
- **The platform.** Faults in the processor, firmware, operating system, or the C compiler and C
  library while they remain in Capstan's trusted base, unless the fault is triggered by code
  Capstan generated in breach of its own rules. Speculative-execution attacks beyond what K1.8
  covers.
- **Resource exhaustion** that stops a program safely (out of memory, a deadline reached).
- **Older or experimental code**: releases before the latest, and features documented as
  experimental.
- Anything that needs social engineering, stolen credentials, or attacks on the project's or
  anyone else's infrastructure.

## How to enter

1. Report privately through GitHub's private vulnerability reporting, as described in
   [SECURITY.md](../SECURITY.md), with **Challenge entry** and the tier in the title.
2. Include the smallest program that shows the problem, the release and platform, the exact build
   and run commands, and a test that demonstrates the weakness (for tier 3, the attack).
3. The first valid report of a given flaw wins. Reports of the same root cause share the prize
   only if received within the same 72 hours.

## Judging

- An entry is acknowledged within 5 working days, and a decision with reasons follows within
  30 days.
- The maintainer judges first. An entrant who disagrees can appeal to an independent panel of at
  least two security researchers with no stake in Capstan, named when the challenge opens; the
  panel's decision is final.
- Every decision, accepted or not, is published with its reasoning after the fix is released.
  Where the rules are unclear, the entrant gets the benefit of the doubt and the rules are fixed for
  the next year.

## Payment, disclosure and credit

- Prizes are paid within 30 days of acceptance, in Australian dollars unless agreed otherwise.
- The flaw is fixed with a regression test, an advisory is published, and the atlas is corrected.
  Disclosure is coordinated: the entrant may publish 90 days after acceptance, or when the fix is
  released if sooner.
- Winners are credited in the advisory, the changelog and the hall of fame, unless they prefer to
  stay anonymous.

## Safe harbour

Good-faith research under these rules, on your own copy of Capstan and your own programs, is
authorised: the project will not pursue legal action against it or ask anyone else to. Do not test
against systems you do not own, and do not access, change or keep other people's data.

## Eligibility

- Anyone may enter where the law allows them to receive the prize. People subject to sanctions, and
  maintainers and contributors with commit access (who are credited but not paid), are not eligible.
- Prizes are decided by skill alone, not chance. Before cash prizes are offered, the final rules
  will be reviewed by a lawyer for the jurisdictions involved, including Australian state rules on
  trade promotions and competitions; that review may change these terms.
- Entrants are responsible for any tax on a prize.

## The yearly cycle

Each challenge year begins with a release and ends twelve months later with a public report
alongside the [K0 study](K0-KERNEL-CVES.md): entries received, entries accepted, prizes paid,
fixes made, and the rule changes for the next year.

## Before the challenge opens

- [ ] Funding held separately for the full prize pool, so every prize can be paid at once
- [ ] Prize amounts set for each tier
- [ ] Independent appeals panel named
- [ ] Legal review of the final rules
- [ ] Reference programs published as suggested targets (a records service with grants and
      policies, a parser of untrusted input, a cryptographic tool)
- [ ] Payment method that works across countries

## Hall of fame

Everyone whose report found a flaw in Capstan's guarantees, prize or not.

*No entries yet.*
