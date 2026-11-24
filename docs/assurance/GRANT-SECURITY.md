# Grant security: reference semantics and assurance

**Status:** independent reference specification with executable self-checks. This is
not a proof of the compiler or runtime and does not justify calling Capstan formally
verified.

## Protected-call invariant

A protected call may enter its body only if:

1. The grant was issued by the exact policy named by the protected function.
2. Each non-grant function argument maps to one unambiguous policy parameter.
3. Each supplied argument is equivalent to the value authorised in that policy role.
4. The original policy is re-evaluated over the original authorisation tuple against
   current state at protected-call entry, and still returns true.

A grant records which policy request was authorised; it is not general permission
to invoke every function associated with that policy.

## Argument-role mapping

Let P be the policy parameter sequence and F the protected function's non-grant
parameter sequence. The kth occurrence of type T in F maps to the kth occurrence
of T in P.

A function parameter whose type does not occur in P is invalid. If T occurs more
than once in P, the function may accept all occurrences or none. Accepting only a
subset makes ordinal matching ambiguous and is invalid. The grant parameter is
excluded from F.

This enforces structural correspondence, not business correctness. It cannot prove
that a policy expresses the organisation's intended authorisation decision.

## Type-directed value equivalence

| Type | Required equivalence |
|---|---|
| int, bool | Same value and scalar type |
| string | Same byte content |
| Struct, list, map | Same object identity |
| Secret | Same opaque identity; never inspect secret contents |
| T? | Same presence; recursively compare payload when present |
| Enum | Same enum type and active variant; recursively compare active payload fields |

Only active enum fields are compared. The discriminant must denote a declared
variant and payload arity must match. Tag-only comparison is insufficient:
Amount(10) must not authorise Amount(500).

The independent model is tests/unit/grant_reference.py. It uses a separate
algebraic representation and imports no compiler, generated-C or runtime code.
Its self-checks run as part of the standard tests/run.sh unit section. They cover
role ordering, repeated and unbound types, scalar type confusion, string byte
semantics, object and secret identity, nested optional presence and payload,
enum identity/tag/payload shape, protected-call arity, policy identity, and policy
re-evaluation.

## Assurance status

| Claim | Evidence now | Level | Remaining work |
|---|---|---|---|
| Argument roles are unambiguous | Static-rule specification and independent model self-checks | Specified; model self-tested | Differentially compare compiler accept/reject decisions |
| Runtime values cannot be substituted across roles | Type-directed relation and grant-branch regression fixtures | Specified; regression-tested on implementation branch | Generated differential cases for every type and nested combination |
| Enum payload substitution is rejected | Recursive enum relation and payload-substitution fixture | Specified; regression-tested on implementation branch | Invalid discriminants and malformed representation tests |
| Policy identity is enforced | Protected-call precondition | Specified; implementation evidence to attach after integration | Cross-policy substitution, including no-struct policies |
| Policy conditions are re-evaluated | Original tuple is rechecked at protected-call entry | Specified; implementation evidence to attach after integration | State mutation matrix and stateful differential tests |

The self-checks establish only that this Python model matches the rules written
here. They do not establish that the compiler, code generator, runtime or generated
machine code implements those rules.

## Assumptions and limits

- Execution is sequential. Re-evaluation occurs at protected-call entry; it is not
  an atomic transaction spanning the function body.
- A concurrent writer could invalidate a condition after the check and before or
  during use. No concurrency safety or check-and-use atomicity is claimed.
- Policy correctness remains a developer/organisation responsibility.
- Runtime, C compiler, operating system and platform remain in the trusted computing
  base documented in THREAT-MODEL.md.
- The reference model is Python and is not itself verified.

## Differential verification plan

After the grant implementation is integrated on main, add a harness that generates
small Capstan programs and compares observed outcomes with this oracle. Vary:

1. Policy/function type sequences, especially repeated types and omitted groups.
2. Scalar values, including boundaries and one-unit substitutions.
3. String bytes, including equal content in separate allocations, embedded NUL
   bytes and empty strings.
4. Struct/list/map identities, aliases and distinct equal-looking values.
5. Optional presence and recursively varied payloads.
6. Every enum variant, nested payload and optional payload.
7. Policy identity, stale grants after state mutation, and policies without structs.

Expected verdicts must come from this model, not compiler helpers or generated-C
equality routines. Preserve each counterexample as a fixed regression fixture.
Mutate the specification (tag-only enum comparison, omitted scalar comparison,
ignored role order, skipped policy re-evaluation) and require the differential
suite to detect each mutation.

## Threshold for stronger claims

"Mechanically proved" is justified only when a proof covers the implementation
actually shipped, the proof checker and assumptions are stated, and the proof is
reproducible from a pinned revision. Proving this reference model alone is not
compiler-correctness proof. Until then, use specified, model self-tested and—where
CI confirms—implementation regression-tested.
