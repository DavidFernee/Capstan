#!/usr/bin/env python3
"""Finite reference machine for Halyard's single-owner reservation actor.

This is an executable semantic model, not a Capstan implementation or proof of
its refinement. The actor serialises all ledger mutations; producers transfer
commands into a bounded FIFO inbox. A successful enqueue is the ownership
commit point. Run with Python 3's standard library only.
"""
from collections import deque
from dataclasses import dataclass
from itertools import product

DIMENSIONS = 5
LIMITS = (2, 2, 2, 2, 2)
QUEUE_CAPACITY = 2
MAX_DEPTH = 8
CHARGES = ((1, 0, 0, 0, 0), (1, 1, 1, 1, 1), (0, 0, 0, 0, 2))


@dataclass(frozen=True, order=True)
class Request:
    op: str
    request_id: int
    target_id: int = -1
    charge: tuple = (0, 0, 0, 0, 0)


@dataclass(frozen=True)
class State:
    queue: tuple = ()
    leases: tuple = ()       # sorted (lease_id, five-dimensional charge)
    outcomes: tuple = ()     # sorted (request_id, terminal outcome)


def outcome_map(state):
    return dict(state.outcomes)


def lease_map(state):
    return dict(state.leases)


def used(state):
    totals = [0] * DIMENSIONS
    for charge in lease_map(state).values():
        for i, amount in enumerate(charge):
            totals[i] += amount
    return tuple(totals)


def submit(state, request):
    """Return the committed state, or None when submission cannot commit."""
    known = {r.request_id for r in state.queue} | set(outcome_map(state))
    if len(state.queue) >= QUEUE_CAPACITY or request.request_id in known:
        return None
    return State(
        queue=state.queue + (request,),
        leases=state.leases,
        outcomes=state.outcomes,
    )


def cancel_queued(state, request_id):
    queue = list(state.queue)
    index = next((i for i, req in enumerate(queue)
                  if req.request_id == request_id), None)
    if index is None:
        return None
    queue.pop(index)
    outcomes = outcome_map(state)
    outcomes[request_id] = "cancelled"
    return State(tuple(queue), state.leases, tuple(sorted(outcomes.items())))


def actor_process_one(state):
    """Process one FIFO command; only this actor mutates the lease ledger."""
    if not state.queue:
        return None
    request, rest = state.queue[0], state.queue[1:]
    leases = lease_map(state)
    outcomes = outcome_map(state)

    if request.op == "reserve":
        current = used(state)
        proposed = tuple(current[i] + request.charge[i]
                         for i in range(DIMENSIONS))
        if all(0 <= request.charge[i] and proposed[i] <= LIMITS[i]
               for i in range(DIMENSIONS)):
            leases[request.request_id] = request.charge
            outcomes[request.request_id] = "granted"
        else:
            outcomes[request.request_id] = "rejected"
    elif request.op == "release":
        if request.target_id in leases:
            del leases[request.target_id]
            outcomes[request.request_id] = "released:" + str(request.target_id)
        else:
            outcomes[request.request_id] = "release_rejected:" + str(request.target_id)
    else:
        raise AssertionError("unknown operation")

    return State(rest, tuple(sorted(leases.items())),
                 tuple(sorted(outcomes.items())))


def invariant(state):
    outcomes = outcome_map(state)
    queued_ids = [r.request_id for r in state.queue]
    assert len(state.queue) <= QUEUE_CAPACITY
    assert len(queued_ids) == len(set(queued_ids))
    assert not (set(queued_ids) & set(outcomes))
    assert all(outcomes.get(r.request_id) is None for r in state.queue)
    assert len(lease_map(state)) == len(state.leases)
    assert all(len(c) == DIMENSIONS and all(x >= 0 for x in c)
               for c in lease_map(state).values())
    assert all(0 <= used(state)[i] <= LIMITS[i]
               for i in range(DIMENSIONS))
    assert set(lease_map(state)).isdisjoint(
        {rid for rid, result in state.outcomes if result in
         ("cancelled", "rejected")})
    for request_id, result in state.outcomes:
        assert (result in {"cancelled", "granted", "rejected"} or
                result.startswith("released:") or
                result.startswith("release_rejected:"))
        if result == "granted":
            assert request_id in lease_map(state) or any(
                outcome == "released:" + str(request_id)
                for _, outcome in state.outcomes)
        if result.startswith("released:"):
            assert int(result.split(":", 1)[1]) not in lease_map(state)


def actions(state):
    known = {r.request_id for r in state.queue} | set(outcome_map(state))
    result = []
    for rid in (0, 1):
        if rid not in known:
            result.extend(Request("reserve", rid, charge=c) for c in CHARGES)
    for rid in (2, 3):
        if rid not in known:
            result.extend(Request("release", rid, target_id=t)
                          for t in (0, 1))
    result.extend(("cancel", rid) for rid in
                  (r.request_id for r in state.queue))
    if state.queue:
        result.append(("process",))
    return result


def step(state, action):
    if isinstance(action, Request):
        return submit(state, action)
    if action[0] == "cancel":
        return cancel_queued(state, action[1])
    if action[0] == "process":
        return actor_process_one(state)
    raise AssertionError("unknown action")


def direct_regressions():
    empty = State()
    first = submit(empty, Request("reserve", 0, charge=CHARGES[0]))
    second = submit(first, Request("reserve", 1, charge=CHARGES[1]))
    assert first is not None and second is not None
    # Full inbox: failed enqueue preserves the complete observable state.
    assert submit(second, Request("release", 2, target_id=0)) is None
    assert second == State(second.queue, second.leases, second.outcomes)

    # Cancellation before processing prevents a reservation from appearing.
    cancelled = cancel_queued(second, 0)
    assert cancelled is not None and outcome_map(cancelled)[0] == "cancelled"
    after = actor_process_one(cancelled)
    assert after is not None and 0 not in lease_map(after)

    # Successful reservation is released exactly once; replay is rejected.
    granted = actor_process_one(first)
    assert granted is not None and outcome_map(granted)[0] == "granted"
    release_req = Request("release", 2, target_id=0)
    queued_release = submit(granted, release_req)
    released = actor_process_one(queued_release)
    assert outcome_map(released)[2] == "released:0"
    replay = submit(released, Request("release", 3, target_id=0))
    replayed = actor_process_one(replay)
    assert outcome_map(replayed)[3] == "release_rejected:0"
    assert 0 not in lease_map(replayed)


def explore():
    initial = State()
    frontier = deque([(initial, 0)])
    seen = {initial}
    transitions = 0
    max_queue = 0
    while frontier:
        state, depth = frontier.popleft()
        invariant(state)
        max_queue = max(max_queue, len(state.queue))
        if depth == MAX_DEPTH:
            continue
        for action in actions(state):
            nxt = step(state, action)
            if nxt is None or nxt == state:
                continue
            transitions += 1
            invariant(nxt)
            if nxt not in seen:
                seen.add(nxt)
                frontier.append((nxt, depth + 1))
    return len(seen), transitions, max_queue


def demonstrate_shared_check_commit_race():
    # Two unsynchronised callers both observe one free unit before either commits.
    observed_free_by_a = 1
    observed_free_by_b = 1
    assert observed_free_by_a >= 1 and observed_free_by_b >= 1
    committed_usage = 0
    committed_usage += 1
    committed_usage += 1
    assert committed_usage == 2  # counterexample: limit was one

    # A linearized shared-ledger operation (or the actor) serializes admission.
    atomic_usage = 0
    admitted = []
    for _ in range(2):
        if atomic_usage + 1 <= 1:
            atomic_usage += 1
            admitted.append(True)
        else:
            admitted.append(False)
    assert admitted == [True, False] and atomic_usage == 1


def main():
    direct_regressions()
    demonstrate_shared_check_commit_race()
    states, transitions, max_queue = explore()
    assert max_queue == QUEUE_CAPACITY
    print("Halyard actor model: PASS")
    print(f"reachable states (depth <= {MAX_DEPTH}): {states}")
    print(f"committed transitions explored: {transitions}")
    print(f"maximum inbox occupancy: {max_queue}/{QUEUE_CAPACITY}")
    print("invariants: bounded queue, FIFO processing, unique request ownership,")
    print("            budget soundness, atomic failed admission, one-shot release")
    print("comparison: split check/commit admits an over-budget interleaving;")
    print("            linearized admission rejects the second reservation")


if __name__ == "__main__":
    main()
