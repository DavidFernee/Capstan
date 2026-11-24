#!/usr/bin/env python3
"""Independent reference semantics for Capstan grant argument binding."""
from dataclasses import dataclass


class SpecError(ValueError):
    pass


@dataclass(frozen=True)
class Ty:
    name: str


@dataclass(frozen=True)
class Ref:
    identity: object


@dataclass(frozen=True)
class Secret:
    identity: object


@dataclass(frozen=True)
class Opt:
    present: bool
    value: object = None


@dataclass(frozen=True)
class Enum:
    name: str
    variant: str
    payload: tuple = ()


def roles(policy_types, function_types):
    """Map kth function occurrence of T to kth policy occurrence of T."""
    counts = {}
    used = {}
    for t in policy_types:
        counts[t] = counts.get(t, 0) + 1
    for t in function_types:
        used[t] = used.get(t, 0) + 1
        if t not in counts:
            raise SpecError("unbound protected parameter type: " + t.name)
    for t, n in used.items():
        if counts[t] > 1 and n not in (0, counts[t]):
            raise SpecError("partial repeated-type mapping: " + t.name)
    result, seen = [], {}
    for t in function_types:
        n = seen.get(t, 0)
        positions = [i for i, p in enumerate(policy_types) if p == t]
        if n >= len(positions):
            raise SpecError("no policy role for " + t.name)
        result.append(positions[n])
        seen[t] = n + 1
    return tuple(result)


def equivalent(ty, issued, supplied, enum_fields):
    """Independent type-directed equivalence relation."""
    k = ty.name
    if k in ("int", "bool"):
        return type(issued) is type(supplied) and issued == supplied
    if k == "string":
        return isinstance(issued, bytes) and isinstance(supplied, bytes) and issued == supplied
    if k in ("struct", "list", "map"):
        return isinstance(issued, Ref) and isinstance(supplied, Ref) and issued.identity is supplied.identity
    if k == "Secret":
        return isinstance(issued, Secret) and isinstance(supplied, Secret) and issued.identity is supplied.identity
    if k.startswith("optional<") and k.endswith(">"):
        inner = Ty(k[9:-1])
        return (isinstance(issued, Opt) and isinstance(supplied, Opt)
                and issued.present == supplied.present
                and (not issued.present or equivalent(inner, issued.value, supplied.value, enum_fields)))
    if k.startswith("enum:"):
        name = k[5:]
        if not isinstance(issued, Enum) or not isinstance(supplied, Enum):
            return False
        variants = enum_fields.get(name, {})
        if (issued.name != name or supplied.name != name or issued.variant != supplied.variant
                or issued.variant not in variants):
            return False
        fields = variants[issued.variant]
        if len(fields) != len(issued.payload) or len(fields) != len(supplied.payload):
            return False
        return all(equivalent(t, a, b, enum_fields)
                   for t, a, b in zip(fields, issued.payload, supplied.payload))
    raise SpecError("missing equivalence rule: " + k)


@dataclass(frozen=True)
class Grant:
    policy: str
    original: tuple


def may_enter(grant, policy, ptypes, ftypes, supplied, predicate, enum_fields):
    """Decide protected-call entry; predicate sees original args/current state."""
    if grant.policy != policy or len(supplied) != len(ftypes) or len(grant.original) != len(ptypes):
        return False
    try:
        mapping = roles(ptypes, ftypes)
    except SpecError:
        return False
    for fi, pi in enumerate(mapping):
        if not equivalent(ftypes[fi], grant.original[pi], supplied[fi], enum_fields):
            return False
    return bool(predicate(*grant.original))


def self_test():
    A, I = Ty("struct"), Ty("int")
    shapes = {"Debit": {"Amount": (I,), "Other": (Ty("string"),)}}
    checks = []
    checks.append(roles((A, A, I), (A, A, I)) == (0, 1, 2))
    checks.append(roles((A, A), ()) == ())
    try:
        roles((A, A), (A,))
        checks.append(False)
    except SpecError:
        checks.append(True)
    try:
        roles((A,), (I,))
        checks.append(False)
    except SpecError:
        checks.append(True)
    checks += [equivalent(I, 4, 4, shapes), not equivalent(I, 4, 5, shapes)]
    checks += [equivalent(Ty("string"), b"x", bytes(bytearray(b"x")), shapes),
               not equivalent(Ty("string"), b"x", b"y", shapes)]
    token = object()
    checks += [equivalent(A, Ref(token), Ref(token), shapes),
               not equivalent(A, Ref(token), Ref(object()), shapes)]
    checks += [equivalent(Ty("Secret"), Secret(token), Secret(token), shapes),
               not equivalent(Ty("Secret"), Secret(token), Secret(object()), shapes)]
    O = Ty("optional<int>")
    checks += [equivalent(O, Opt(False), Opt(False), shapes),
               not equivalent(O, Opt(False), Opt(True, 0), shapes),
               not equivalent(O, Opt(True, 1), Opt(True, 2), shapes)]
    E = Ty("enum:Debit")
    checks += [equivalent(E, Enum("Debit", "Amount", (10,)), Enum("Debit", "Amount", (10,)), shapes),
               not equivalent(E, Enum("Debit", "Amount", (10,)), Enum("Debit", "Amount", (500,)), shapes),
               not equivalent(E, Enum("Debit", "Amount", (10,)), Enum("Debit", "Other", (b"x",)), shapes),
               not equivalent(E, Enum("Debit", "Amount", (10,)), Enum("Debit", "Amount", (10, 11)), shapes)]
    account = Ref(token)
    pred = lambda amount, obj: amount > 0 and obj.identity is token
    g = Grant("CanDebit", (10, account))
    ptypes = (I, A)
    checks += [may_enter(g, "CanDebit", ptypes, ptypes, (10, account), pred, shapes),
               not may_enter(g, "CanDebit", ptypes, ptypes, (500, account), pred, shapes),
               not may_enter(g, "Other", ptypes, ptypes, (10, account), pred, shapes),
               not may_enter(g, "CanDebit", ptypes, ptypes, (10, account), lambda *_: False, shapes)]
    if not all(checks):
        raise AssertionError("grant reference self-check failed: %d/%d" % (checks.count(True), len(checks)))
    print("grant reference semantics: %d specification self-checks passed" % len(checks))


if __name__ == "__main__":
    self_test()
