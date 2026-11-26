# Capability, effect and information-flow systems: comparative survey

**Status:** targeted literature and repository-design review; recommendation for a first experiment, not a normative language decision  
**Issue:** [#222](https://github.com/DavidFernee/Capstan/issues/222)  
**Reviewed:** 2026-11-26  
**Repository baseline:** `main` after PR #438 (merge commit `95e3492588de11169714e45c5ad7b5509a8235a2`)  
**Coordinates:** [F1 language contract](../F1-LANGUAGE-CONTRACT.md), [concurrency guarantee calculus](CONCURRENCY-GUARANTEE-CALCULUS.md), [ECE obligations](EVIDENCE-CARRYING-EXECUTION-OBLIGATIONS.md), [Anchor capability-I/O requirements](../ANCHOR-CAPABILITY-IO-REQUIREMENTS.md), [language extension roadmap](../architecture/LANGUAGE-EXTENSIONS.md)

## 1. Executive recommendation

Capstan should treat **authority, effects and information flow as distinct but mutually checked dimensions** of one compositional contract. It should not collapse them into a single generic effect or permission label.

- A **capability** answers: *which specific authority does this component possess, for which resource and operations, and how can it be transferred, attenuated or revoked?*
- An **effect** answers: *which kinds of externally relevant operation may this computation perform, and which handler/adapter is responsible for interpreting them?*
- An **information-flow policy** answers: *what may be inferred from or done with the data this computation observes or produces?*

The distinction is not cosmetic. An effect annotation must not grant authority; possession of a capability must not imply that every use of it is semantically permitted; and a data label must not be mistaken for an OS access-control decision.

This conclusion is already consistent with Capstan's current research drafts: the concurrency guarantee calculus explicitly separates required authority (A) from effect set (E), and the Anchor capability-I/O requirements say that effects describe what an operation may do while capabilities describe which authority is required. The F1 draft proposes a factored but mutually checked guarantee derivation. This survey supplies prior-art context and a narrow experiment, not new syntax or an approved semantic change.

**Recommended first slice:** a small, explicit filesystem-read boundary with (1) a scoped, unforgeable directory-read capability, (2) a statically checked `fs.read` effect, and (3) an information-flow label on returned bytes. The host adapter must perform the actual path confinement and resource checks. The first slice should prove fail-closed authority inclusion and exercise tainted/secret data flow; it should not attempt general capability revocation, distributed delegation, a universal effect-handler runtime or full non-interference for arbitrary programs.

## 2. Review method and scope

This is a targeted review of primary papers, formal models, language specifications and official platform documentation located on 2026-11-26. It is not a systematic literature review: no exhaustive database search, formal screening protocol or independent bibliography audit was performed. Sources were selected for direct relevance to object-capability semantics, practical OS enforcement, formal capability models, effect typing/handlers and language-based information-flow control.

The review prioritises original papers/specifications where located. Official project documentation is used to establish the current documented design of Jif and WASI, not as independent evidence of all implementation properties. The cited literature is not evidence that Capstan has implemented or proved any of these mechanisms.

## 3. Comparison taxonomy

| Family | Core abstraction | What it can establish | What it does not establish by itself |
|---|---|---|---|
| Object-capability languages | Unforgeable object references convey authority; authority is passed explicitly | Least-authority object graphs, local authority reasoning, confinement under language/runtime assumptions | Data confidentiality/non-interference; OS isolation; correctness of every host adapter |
| Kernel capability systems | Kernel objects and operations are accessed through rights-bearing capabilities | Kernel-enforced object authority, derivation/attenuation and controlled delegation/revocation | Source-level effect summaries or high-level data-flow policy |
| Capability-oriented sandbox APIs | Existing OS handles are constrained and passed into compartments | Practical reduction of ambient OS authority and compartmentalisation | A capability type system or end-to-end language proof |
| Effect systems | Types record computational effects; handlers interpret or delimit effects | Static effect summaries, effect polymorphism and explicit handling structure | Permission to perform an effect; secure host mediation unless all paths are controlled |
| Information-flow type systems | Labels/policies track confidentiality and integrity through computation | Restricted flows, explicit declassification and scoped non-interference results | Filesystem/network authority, arbitrary covert-channel elimination or host isolation |
| Language-level taint/context systems | Values retain provenance/context through transformations and sinks | Prevention of specified unsafe data-to-sink flows | General confidentiality policy or external resource authority |
| Wasm/WASI-style host interfaces | Sandbox execution plus explicitly imported host functions/resources | A restricted guest/host interface with authority controlled by the embedding | Correctness of embedder policy, absence of all side channels or source-language effect checking |

These families solve related but non-identical problems. A design that borrows terminology from each without preserving the semantic distinctions risks giving the appearance of compositional security while leaving a bypass between the layers.

## 4. Object-capability and kernel capability systems

### 4.1 Object-capability model

Miller, Yee and Shapiro's *Capability Myths Demolished* (2003) is important because it distinguishes object-capability systems from looser uses of the word capability. It analyses authority in terms of object references and the propagation of those references, and argues that least authority and avoidance of confused-deputy problems depend on the actual model, not merely on representing permissions as tokens. It also treats confinement and revocation as designable properties rather than universal impossibilities.

The practical consequence for Capstan is that a string naming a resource, a boolean permission, a global policy lookup or a bearer identifier is not automatically an object capability. The security argument needs an unforgeable reference/handle whose possession is necessary to perform the operation, with a well-defined authority graph and no ambient fallback.

Mettler, Wagner and Close's Joe-E work (2010; specification 2008) is a language-level example. Joe-E restricts Java constructs and library behaviour so object references can support capability-style reasoning. Its verifier checks the subset; its security properties rely on memory-safe object semantics and removal/taming of ambient-authority facilities. Joe-E is not a general theorem that arbitrary Java code is capability-safe, nor does its subset alone provide a confidentiality type system.

### 4.2 Kernel and OS capability systems

The seL4 work provides a stronger, lower-level authority model. Capabilities refer to kernel objects and carry rights; capability derivation can create a restricted-rights capability, and authority can be transferred through controlled IPC. The verified shared-capability model demonstrates machine-checked reasoning about authority confinement and shared capability storage. The seL4 verification literature also makes clear that the access-control model is an abstraction whose relation to implementation and hardware must be stated.

Capsicum demonstrates a pragmatic UNIX integration: capability mode restricts ambient namespace access, and file descriptors can be used as capabilities. It extends rather than replaces conventional UNIX APIs. The paper's contribution is a usable compartmentalisation mechanism, not a source-language capability type system.

WASI's design principles make the host-boundary point explicit: external resources are exposed through capabilities/handles, and the design aims to avoid ambient authority. This is a useful contemporary interface reference, but a WebAssembly module still relies on its embedder to decide which imports/resources to provide. A guest sandbox cannot establish that the embedder granted only the correct authority.

### 4.3 Authority operations and limitations

| Operation | Typical model | Required semantic question |
|---|---|---|
| Creation | Trusted root/host or object constructor | Who is authorised to mint initial authority, and what prevents guest forgery? |
| Attenuation | Derived capability with subset of rights/scope | Is the derived authority provably no stronger than its parent? |
| Delegation | Explicit transfer/pass to another object/task | Is the recipient and transfer boundary visible? Can authority escape through shared state? |
| Revocation | Revocation object/indirection, kernel derivation tree, epoch or lease | What is revoked: one reference, all descendants, future use, or already-running operations? |
| Confinement | Closed authority graph and controlled capability propagation | Are ambient namespaces, reflection, global registries and FFI escape routes excluded? |
| Lifetime | Owned handle, region, lease or explicit close | What happens on cancellation, failure, task termination and partial completion? |

Revocation is not free. A raw immutable object reference is difficult to revoke after arbitrary copying unless the design introduces indirection, revocation lists/trees, epochs, leases or another mediation point. The first Capstan slice should therefore avoid claiming general revocation. It should specify a narrow lifetime and use model, then introduce revocation only when a real host-service requirement justifies its costs and semantics.

## 5. Effect systems and handlers

Bauer and Pretnar's formal work on effect systems for algebraic effects and handlers (2014) gives a typed account of operations and handlers, with a safety result for the core language. Their Eff work presents effects as algebraic operations and handlers as interpretations that can be composed. The central advantage is modularity: code can state which operations it may perform without committing to a single implementation of those operations.

Later work continues to address expressiveness and implementation cost. The 2023 OOPSLA paper *From Capabilities to Regions: Enabling Efficient Compilation of Lexical Effect Handlers* studies compilation strategies for lexical handlers, including the runtime costs associated with handler abstractions. A 2024 framework for higher-order effects and handlers extends the modelling of effect classes. These works show that effects/handlers are an active language-design and implementation area; they do not imply that a handler is an access-control boundary.

**Critical distinction:** an effect such as `fs.read` describes a possible operation. It does not prove that the caller is authorised to read a particular directory. If an effect handler can call a global filesystem API or consult ambient process state, it may remain a confused deputy. Conversely, possessing a directory capability does not mean a function actually performs I/O; it may simply pass the capability to another component.

A robust composition rule therefore needs both:

- effect inclusion: the callee's possible effects are accounted for in the caller's declared effect contract; and
- authority inclusion: every operation's required capability is explicitly available, with no implicit escalation.

Handlers must be treated as trusted interpreters at the boundary where they acquire OS or device authority. A user-level handler can provide deterministic testing or an in-memory interpretation, but it is not a sandbox if code can bypass it.

Effect handlers also raise continuation and resource questions. If a handler can capture, duplicate or resume a continuation more than once, effect execution may be repeated and resource accounting becomes more complex. The initial Capstan experiment should use a simple effect row and direct adapter call, not general multi-shot algebraic handlers.

## 6. Information-flow control and taint

### 6.1 Static information-flow type systems

Jif/JFlow (Myers, 1999 onward) extends Java with security labels and principals. Its type system tracks information flow and supports label polymorphism, inference, explicit declassification and selected runtime checks. It demonstrates that confidentiality/integrity policies can be part of ordinary typing, including control-flow dependencies.

Flow Caml (Simonet) brings information-flow tracking to Objective Caml, showing that a security type system can be layered over an existing language and compile to ordinary OCaml. Both are important prior art: Capstan cannot claim novelty merely for attaching labels to values and rejecting illegal flows.

Jif's documentation is explicit about limitations: not every covert channel is controlled, including timing channels, and its supported concurrency model is restricted. Zhang, Askarov and Myers (2012) separately study language-based mitigation of timing channels, illustrating that timing leakage requires a stronger model than ordinary termination-insensitive information-flow checking.

The 2025 paper *Structural Information Flow: A Fresh Look at Types for Non-interference* identifies adoption and annotation complexity as continuing problems for information-flow systems. It is directly relevant to Capstan's usability question: an expressive policy calculus can be formally attractive but impractical if simple programs require brittle, pervasive annotations.

### 6.2 Taint, confidentiality and integrity are not interchangeable

Capstan's existing `Tainted` and context-specific output types are closer to provenance/integrity tracking than to a complete confidentiality lattice. A value derived from untrusted input should not flow to a sensitive sink without validation/encoding; a secret value should not flow to a public output unless a permitted declassification policy applies. Those are different directions and require different rules.

A single undifferentiated label such as `untrusted` or `secret` is insufficient for both. The model should distinguish at least:

- **integrity/provenance:** whether input is trusted, validated or attacker-controlled;
- **confidentiality:** which principals may observe a value;
- **context:** which output grammar/sink a value has been encoded for;
- **declassification/endorsement:** the explicit, audited transition that changes a policy label.

Information-flow tracking must include implicit flows through control dependencies, calls, containers, exceptions/traps and serialization. It must also state whether timing, termination, resource-consumption and concurrency channels are included or excluded.

## 7. Comparative matrix

| System / source | Authority model | Effects | Information flow | Main assurance boundary / limitation |
|---|---|---|---|---|
| E / object-capability tradition; Miller et al. | Object references as authority; explicit propagation | Not a general typed effect system | Not a general IFC type system | Depends on object-language/runtime discipline and host boundary |
| Joe-E | Object-capability subset of Java; verifier rejects unsafe language constructs | Not a general effect calculus | Not a general IFC lattice | Static subset verification plus JVM/standard-library trust |
| seL4 capability model | Kernel-managed object capabilities, derivation and revocation | Kernel operations are capability-mediated | Formal access-control/confidentiality models at kernel level | Kernel/boot/hardware assumptions and model-to-implementation refinement |
| Capsicum | OS sandbox/capability mode and descriptor capabilities | OS API calls are mediated by process mode/handles | Not source-level data-flow control | UNIX-specific OS enforcement; not a language type system |
| WASI / Wasm | Imported host resources/handles; no intended ambient guest access | Imports define callable host surface | No general source-language IFC | Embedder selects imports; host correctness remains trusted |
| Eff / algebraic effects | No inherent authority model | First-class effect operations and handlers | No inherent IFC policy | Handler implementation and continuation/resource semantics |
| Jif / JFlow | Principals and access-control policy integrated with labels | Some runtime checks; not general authority mediation | Static labels, implicit-flow tracking, declassification | Timing/covert channels and runtime/Java boundary limitations |
| Flow Caml | No general object-capability model | ML computation effects not the central abstraction | Static information-flow type system | Language subset and specified flow model |
| Structural Information Flow (2025) | Not an OS capability model | Type-based structural policy mechanism | New type-oriented non-interference approach | Research contribution; adoption/usability and scope need evaluation |

## 8. Capstan baseline and design implications

The current repository documents a promising direction but does not yet implement a complete capability type system:

- `docs/F1-LANGUAGE-CONTRACT.md` treats authority, effects, information flow and resource use as distinct contract dimensions and states a conservative fail-closed rule.
- `docs/research/CONCURRENCY-GUARANTEE-CALCULUS.md` explicitly distinguishes the effect set (E) from required authority (A); its conceptual judgment also includes information-flow labels and environmental assumptions.
- `docs/ANCHOR-CAPABILITY-IO-REQUIREMENTS.md` identifies the current path-string filesystem interface as ambient path authority and calls for a public directory capability and owned file handle. It also says that the precise type/effect integration is still a research question.
- `docs/architecture/LANGUAGE-EXTENSIONS.md` places information-flow types, policies/grants and explicit capability/effect signatures in separate stages.
- `docs/research/EVIDENCE-CARRYING-EXECUTION-OBLIGATIONS.md` leaves capability algebra, effect summaries, call-site authority inclusion and attenuation/no-escalation as open obligations.

The current `Grant<P>`/policy mechanisms must not be relabelled as a complete object-capability system. The repository itself records that policy meaning remains developer-defined and that the public filesystem API still uses path strings. The present compiler/runtime is C-backed; host mediation and the C/OS boundary remain part of the trusted computing base.

### 8.1 Proposed conceptual contract

For a small first experiment, use a conceptual judgment:

`Γ ; A ; Λ ⊢ e : τ ! E`

where `Γ` is the typing/ownership environment, `A` is the explicitly available authority, `Λ` is the information-flow environment, and `E` is the possible effect set. This is notation for a research model, not source syntax.

For each external operation `op`, define a requirement relation:

- `effect(op) ∈ E`: the computation may perform this kind of operation;
- `required(op) ⊆ A`: the caller must possess authority scoped to the target and operation;
- `flow(op, Λ)`: input/output labels are propagated according to the operation contract;
- `adapter(op)`: the named trusted host adapter performs the OS action and enforces residual path/handle/byte/deadline constraints.

At a call boundary, the caller must cover the callee's effect set and provide the callee's required capabilities. Neither set is inferred from the other. Missing authority, unknown effect summaries or an unmodelled foreign call must fail closed in the Safe profile.

## 9. Recommended minimal experiment

### 9.1 Filesystem read capability

Implement one narrow operation, conceptually:

`read_bytes(directory_cap, relative_path, max_bytes)`

The public capability should be opaque and unforgeable, identify a directory root and permitted operations, and be passed explicitly. It should not be reconstructed from an arbitrary path string. The adapter should resolve paths relative to the directory handle, reject traversal/symlink escape according to a documented policy, enforce the byte ceiling before unbounded allocation, and return a structured error.

The function contract should declare a filesystem-read effect and a required directory-read authority. Returned bytes should retain an untrusted-input/integrity label unless a separate validator establishes a more specific property. The experiment should not treat a validated byte format as trusted for every downstream context.

### 9.2 Required positive and negative cases

| Case | Expected result |
|---|---|
| Caller has a read capability scoped to the target directory and declares the effect | Accepted; adapter reads within the scope |
| Caller declares `fs.read` but has no directory capability | Rejected before execution |
| Caller has a capability but function effect contract omits `fs.read` | Rejected or effect summary widened by a sound checker; never silently hidden |
| Capability is attenuated to a subdirectory/read-only scope | Access outside that scope is rejected |
| Caller passes a path with traversal or symlink escape | Adapter rejects according to the frozen path-resolution contract |
| Input exceeds `max_bytes` | Bounded rejection without publishing partial data |
| Callee requires stronger rights than caller possesses | Call-site authority inclusion fails |
| Unmodelled FFI/host call can access filesystem ambiently | Safe-profile admission rejects it or requires a separately declared trusted boundary |
| Bytes are written to a context-sensitive output sink without validation/encoding | Existing integrity/context rules reject the flow |
| A secret-labelled value is returned or logged through the same operation | Confidentiality policy rejects unauthorised observation/output |

### 9.3 First properties to formalise

1. **Authority non-escalation:** derived/delegated authority is no stronger than the source capability.
2. **Call-site authority inclusion:** every callee requirement is covered by explicitly available caller authority.
3. **Effect soundness:** every observable external operation is included in the declared effect summary.
4. **No ambient fallback:** an operation cannot succeed through an implicit path/environment/global namespace when the explicit capability is absent.
5. **Adapter confinement:** a successful read is within the capability's root and operation scope, under explicit OS/filesystem assumptions.
6. **Flow preservation:** returned bytes retain their integrity/provenance label through the supported operations until a justified validation transition.

Do not initially claim general non-interference, side-channel freedom, arbitrary revocation correctness or FFI safety. Those require separate semantics and evidence.

## 10. What Capstan should not attempt in the first increment

- Do not merge capabilities and effects into a single `Effect<Permission>` concept that lets an annotation confer authority.
- Do not treat a global policy query, path allowlist or bearer token as equivalent to an unforgeable object capability.
- Do not build a universal capability algebra for every OS, network, process, device and distributed-service resource before one vertical slice is proven.
- Do not add general-purpose multi-shot effect handlers or implicit handler inheritance to solve filesystem authority.
- Do not promise immediate revocation of copied capabilities without an explicit indirection/revocation mechanism.
- Do not claim full non-interference while timing, termination, resource and concurrency channels are outside the model.
- Do not infer that the host adapter is safe merely because the source-level type checker accepts its signature.
- Do not allow an FFI call or C runtime helper to bypass the declared authority/effect boundary.
- Do not make policy syntax normative until the capability and effect semantics, call-site composition and adapter contract have been reviewed together.

## 11. Novelty and contribution risk

The individual ingredients are well established: object capabilities and least authority, capability derivation and confinement, effect typing/handlers, and language-based information-flow control all have substantial prior art. A claim such as "Capstan combines capabilities, effects and taint" is therefore not a defensible novelty statement.

A potentially useful engineering/research contribution would need to demonstrate a specific integration property that is not merely juxtaposition: for example, a small compositional judgment in which effect summaries, explicit authority requirements and information-flow labels are independently tracked but jointly checked across source calls, a canonical intermediate representation and a host adapter, with an implementation-linked proof or executable conformance corpus. The novelty question is whether that exact cross-layer composition adds something beyond known capability/effect/IFC systems, not whether each term appears in the same language.

A publishable hypothesis might be:

> A factored, mutually checked contract can reject authority escalation and prohibited information flows across module and host-adapter boundaries while retaining more modular effect handling than a single undifferentiated permission/effect system.

This is falsifiable only after competing designs are implemented on the same bounded task and measured for expressiveness, rejected bypasses, annotation burden, checker complexity and runtime overhead. It remains a hypothesis.

## 12. Bibliography and primary references

1. Mark S. Miller, Ka-Ping Yee and Jonathan S. Shapiro. **Capability Myths Demolished.** Johns Hopkins University Systems Research Laboratory Technical Report SRL-2003-02 (2003). [Paper](https://cgi.cse.unsw.edu.au/~cs9242/papers/Miller_YS_03.pdf).
2. Adrian Mettler, David Wagner and Tyler Close. **Joe-E: A Security-Oriented Subset of Java.** Network and Distributed System Security Symposium (2010). [Paper](https://people.eecs.berkeley.edu/~daw/papers/joe-e-ndss10.pdf).
3. Adrian Mettler and David Wagner. **The Joe-E Language Specification, Version 1.0.** UC Berkeley Technical Report UCB/EECS-2008-91 (2008). [Specification](https://www2.eecs.berkeley.edu/Pubs/TechRpts/2008/EECS-2008-91.pdf).
4. Robert N. M. Watson, Jonathan Anderson, Ben Laurie and Kris Kennaway. **Capsicum: Practical Capabilities for UNIX.** USENIX Security Symposium (2010). [Paper and publication page](https://www.usenix.org/conference/usenixsecurity10/capsicum-practical-capabilities-unix).
5. Andrew Boyton. **A Verified Shared Capability Model.** Systems Software Verification (2009), pp. 25–44. [Paper](https://trustworthy.systems/publications/nicta_full_text/1810.pdf).
6. Gerwin Klein et al. **Comprehensive Formal Verification of an OS Microkernel.** ACM Transactions on Computer Systems 32(1), 2014. [Paper](https://www.cs.cmu.edu/~15811/papers/seL4-journal.pdf).
7. WebAssembly/WASI. **WASI Design Principles.** Official project documentation, accessed 2026-11-26. [Design principles](https://github.com/WebAssembly/WASI/blob/main/docs/DesignPrinciples.md); see also the [WebAssembly security model](https://webassembly.org/docs/security/).
8. Andrej Bauer and Matija Pretnar. **An Effect System for Algebraic Effects and Handlers.** Logical Methods in Computer Science 10(4:9), 2014. [Paper](https://lmcs.episciences.org/1153).
9. Andrej Bauer and Matija Pretnar. **Programming with Algebraic Effects and Handlers.** Journal of Logical and Algebraic Methods in Programming 84(1), 2015. [Paper](https://doi.org/10.1016/j.jlamp.2014.02.001).
10. Marius Müller, Philipp Schuster, Jonathan Lindegaard Starup, Klaus Ostermann and Jonathan Immanuel Brachthäuser. **From Capabilities to Regions: Enabling Efficient Compilation of Lexical Effect Handlers.** PACMPL OOPSLA2 (2023). [Paper](https://doi.org/10.1145/3622831).
11. Andrew C. Myers. **JFlow: Practical Mostly-Static Information Flow Control.** POPL (1999), pp. 228–241. [Jif language documentation and historical reference](https://www.cs.cornell.edu/jif/doc/jif-3.3.0/overview.html).
12. Vincent Simonet. **Flow Caml in a Nutshell.** (2003). [Paper](https://people.cs.nott.ac.uk/pszgmh/appsem-papers/simonet.pdf).
13. Danfeng Zhang, Aslan Askarov and Andrew C. Myers. **Language-Based Control and Mitigation of Timing Channels.** PLDI (2012), pp. 99–110. [Paper](https://doi.org/10.1145/2345156.2254078).
14. Hemant Gouni, Frank Pfenning and Jonathan Aldrich. **Structural Information Flow: A Fresh Look at Types for Non-interference.** PACMPL OOPSLA2 9 (2025), Article 414. [Paper](https://doi.org/10.1145/3764116).
15. Andrew C. Myers and Barbara Liskov. **A Decentralized Model for Information Flow Control.** SOSP (1997). [Jif/JFlow historical reference](https://www.cs.cornell.edu/jif/doc/jif-2.0.0/jif_programming.html).

## 13. Conclusion

The strongest direction is not to invent a new umbrella term for permissions, effects and labels. It is to preserve their distinct semantics and make their composition explicit and fail-closed. Capstan's existing drafts already point in this direction. The next useful evidence is a small filesystem capability/effect/flow vertical slice, with a concrete host adapter, adversarial path and resource tests, a reference model, and a proof or executable conformance argument for authority inclusion and non-escalation.

Until that work is completed, the capability/effect/IFC integration remains a design hypothesis. This review establishes prior-art risks and a proposed experiment; it does not establish implementation, proof, novelty or production readiness.
