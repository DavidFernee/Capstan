#!/usr/bin/env python3
"""Differential property tests for Keel's bounded exact geometry predicates.

The Capstan implementation is compared with Python's arbitrary-precision integers.
The fixed seed makes every failure reproducible.
"""
import os
import random
import subprocess
import sys
import tempfile
from itertools import permutations

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CAPSTANC, CC, *CFLAGS = sys.argv[1:]
RNG = random.Random(20261125)
LIMIT2 = (1 << 30) - 1
LIMIT3 = (1 << 18) - 1


def sign(n):
    return (n > 0) - (n < 0)


def orient2(a, b, c):
    return sign((b[0] - a[0]) * (c[1] - a[1]) -
                (b[1] - a[1]) * (c[0] - a[0]))


def orient3(a, b, c, d):
    u = [b[i] - a[i] for i in range(3)]
    v = [c[i] - a[i] for i in range(3)]
    w = [d[i] - a[i] for i in range(3)]
    det = (u[0] * (v[1] * w[2] - v[2] * w[1]) -
           u[1] * (v[0] * w[2] - v[2] * w[0]) +
           u[2] * (v[0] * w[1] - v[1] * w[0]))
    return sign(det)


def tetra_relation(a, b, c, d, p):
    base = orient3(a, b, c, d)
    if base == 0:
        return None
    signs = (orient3(p, b, c, d), orient3(a, p, c, d),
             orient3(a, b, p, d), orient3(a, b, c, p))
    if any(value not in (0, base) for value in signs):
        return -1
    return 0 if 0 in signs else 1


def cap_int(n):
    return str(n)


def point2(p):
    return f"keel_point2({p[0]}, {p[1]})"


def point3(p):
    return f"keel_point3({p[0]}, {p[1]}, {p[2]})"


def on_segment(a, b, p):
    return (min(a[0], b[0]) <= p[0] <= max(a[0], b[0]) and
            min(a[1], b[1]) <= p[1] <= max(a[1], b[1]))


def segment_relation(a, b, c, d):
    sa, sb = orient2(a, b, c), orient2(a, b, d)
    sc, sd = orient2(c, d, a), orient2(c, d, b)
    if sa == sb == sc == sd == 0:
        axis = 0 if (a[0] != b[0] or a[0] != c[0] or a[0] != d[0]) else 1
        lo = max(min(a[axis], b[axis]), min(c[axis], d[axis]))
        hi = min(max(a[axis], b[axis]), max(c[axis], d[axis]))
        if hi < lo:
            return -1
        return 0 if hi == lo else 2
    if sa != 0 and sb != 0 and sc != 0 and sd != 0 and sa != sb and sc != sd:
        return 1
    if ((sa == 0 and on_segment(a, b, c)) or
            (sb == 0 and on_segment(a, b, d)) or
            (sc == 0 and on_segment(c, d, a)) or
            (sd == 0 and on_segment(c, d, b))):
        return 0
    return -1


cases2 = []
for i in range(256):
    pts = [tuple(RNG.randint(-LIMIT2, LIMIT2) for _ in range(2)) for _ in range(3)]
    cases2.append((pts, orient2(*pts)))
# Boundary and near-collinear cases.
cases2.extend([
    ([(-LIMIT2, -LIMIT2), (LIMIT2, -LIMIT2), (-LIMIT2, LIMIT2)], 1),
    ([(-LIMIT2, 0), (LIMIT2, 1), (LIMIT2 - 1, 1)], 1),
    ([(0, 0), (1, 1), (2, 2)], 0),
    ([(0, 0), (0, 0), (1, 1)], 0),
    ([(LIMIT2 + 1, 0), (0, 0), (1, 1)], None),
    ([(-LIMIT2 - 1, 0), (0, 0), (1, 1)], None),
])
# Exercise every permutation and every coordinate-validation branch.
base2 = [(-LIMIT2, -LIMIT2), (LIMIT2, -LIMIT2), (-LIMIT2, LIMIT2)]
for order in permutations(range(3)):
    pts = [base2[i] for i in order]
    cases2.append((pts, orient2(*pts)))
for point_index in range(3):
    for axis in range(2):
        for invalid in (LIMIT2 + 1, -LIMIT2 - 1):
            pts = [[0, 0], [1, 0], [0, 1]]
            pts[point_index][axis] = invalid
            pts = [tuple(p) for p in pts]
            cases2.append((pts, None))

cases_seg = []
for i in range(256):
    pts = [tuple(RNG.randint(-LIMIT2, LIMIT2) for _ in range(2)) for _ in range(4)]
    cases_seg.append((pts, segment_relation(*pts)))
cases_seg.extend([
    ([(0, 0), (10, 10), (0, 10), (10, 0)], 1),       # proper crossing
    ([(0, 0), (10, 0), (10, 0), (10, 10)], 0),       # endpoint touch
    ([(0, 0), (10, 0), (5, 0), (15, 0)], 2),         # positive overlap
    ([(0, 0), (0, 10), (0, 5), (0, 15)], 2),         # vertical positive overlap
    ([(0, 0), (5, 0), (6, 0), (10, 0)], -1),         # collinear disjoint
    ([(0, 0), (5, 0), (5, 0), (10, 0)], 0),          # collinear point touch
    ([(0, 0), (10, 0), (0, 1), (10, 1)], -1),        # parallel
    ([(5, 0), (5, 0), (0, 0), (10, 0)], 0),          # point on segment
    ([(11, 0), (11, 0), (0, 0), (10, 0)], -1),        # point off segment
    ([(5, 5), (5, 5), (5, 5), (5, 5)], 0),           # identical point segments
    ([(0, 5), (0, 5), (10, 5), (10, 5)], -1),       # distinct point segments, horizontal
    ([(5, 0), (5, 0), (5, 10), (5, 10)], -1),       # distinct point segments, vertical
    ([(-LIMIT2, 0), (LIMIT2, 0), (0, -1), (0, 1)], 1),
    ([(LIMIT2 + 1, 0), (0, 0), (1, 1), (2, 2)], None),
    ([(-LIMIT2 - 1, 0), (0, 0), (1, 1), (2, 2)], None),
])
# Reversal of either segment and swapping the segment pair must preserve the relation.
base_seg = cases_seg[:]
for pts, want in base_seg:
    a, b, c, d = pts
    for variant in ((b, a, c, d), (a, b, d, c), (c, d, a, b),
                    (d, c, b, a)):
        cases_seg.append((list(variant), want))
# Exercise both signs outside the domain in every coordinate position.
for point_index in range(4):
    for axis in range(2):
        for invalid in (LIMIT2 + 1, -LIMIT2 - 1):
            pts = [[0, 0], [10, 10], [0, 10], [10, 0]]
            pts[point_index][axis] = invalid
            pts = [tuple(p) for p in pts]
            cases_seg.append((pts, None))

cases3 = []
for i in range(256):
    pts = [tuple(RNG.randint(-LIMIT3, LIMIT3) for _ in range(3)) for _ in range(4)]
    cases3.append((pts, orient3(*pts)))
# Exact unit determinant at large magnitudes, coplanarity and domain edges.
cases3.extend([
    ([(0, 0, 0), (LIMIT3, LIMIT3 - 1, 0),
      (LIMIT3 - 1, LIMIT3 - 2, 0), (0, 0, 1)], -1),
    ([(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)], 1),
    ([(0, 0, 0), (0, 1, 0), (1, 0, 0), (0, 0, 1)], -1),
    ([(0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0)], 0),
    ([(LIMIT3 + 1, 0, 0), (0, 0, 0), (1, 0, 0), (0, 1, 0)], None),
    ([(-LIMIT3 - 1, 0, 0), (0, 0, 0), (1, 0, 0), (0, 1, 0)], None),
    ([(-LIMIT3, -LIMIT3, -LIMIT3), (LIMIT3, -LIMIT3, -LIMIT3),
      (-LIMIT3, LIMIT3, -LIMIT3), (-LIMIT3, -LIMIT3, LIMIT3)], 1),
])
# Exercise every vertex permutation and every coordinate-validation branch.
base3 = [(-LIMIT3, -LIMIT3, -LIMIT3), (LIMIT3, -LIMIT3, -LIMIT3),
         (-LIMIT3, LIMIT3, -LIMIT3), (-LIMIT3, -LIMIT3, LIMIT3)]
for order in permutations(range(4)):
    pts = [base3[i] for i in order]
    cases3.append((pts, orient3(*pts)))
for point_index in range(4):
    for axis in range(3):
        for invalid in (LIMIT3 + 1, -LIMIT3 - 1):
            pts = [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]]
            pts[point_index][axis] = invalid
            pts = [tuple(p) for p in pts]
            cases3.append((pts, None))

cases_tet = []
for i in range(256):
    pts = [tuple(RNG.randint(-LIMIT3, LIMIT3) for _ in range(3)) for _ in range(5)]
    cases_tet.append((pts, tetra_relation(*pts)))
# A canonical tetrahedron with strict interior, face, edge, vertex and exterior points.
ta = (0, 0, 0)
tb = (100, 0, 0)
tc = (0, 100, 0)
td = (0, 0, 100)
cases_tet.extend([
    ([ta, tb, tc, td, (10, 10, 10)], 1),
    ([ta, tb, tc, td, (20, 20, 60)], 0),
    ([ta, tb, tc, td, (50, 50, 0)], 0),
    ([ta, tb, tc, td, (0, 0, 0)], 0),
    ([ta, tb, tc, td, (101, 0, 0)], -1),
    ([ta, tb, tc, td, (-1, 1, 1)], -1),
    ([ta, tb, tc, td, (100, 100, 100)], -1),
    ([(0, 0, 0), (10, 0, 0), (0, 10, 0), (10, 10, 0), (1, 1, 0)], None),
    ([(-LIMIT3, -LIMIT3, -LIMIT3), (LIMIT3, -LIMIT3, -LIMIT3),
      (-LIMIT3, LIMIT3, -LIMIT3), (-LIMIT3, -LIMIT3, LIMIT3),
      (-LIMIT3 // 2, -LIMIT3 // 2, -LIMIT3 // 2)], 1),
])
# Reordering tetrahedron vertices must not change point classification.
for order in permutations(range(4)):
    vertices = [ta, tb, tc, td]
    permuted = [vertices[i] for i in order]
    for query, want in (((10, 10, 10), 1), ((20, 20, 60), 0),
                        ((101, 0, 0), -1)):
        cases_tet.append((permuted + [query], want))

# Validate every coordinate of every vertex and the query point before determinants.
base_tet = [(0, 0, 0), (10, 0, 0), (0, 10, 0), (0, 0, 10), (1, 1, 1)]
for point_index in range(5):
    for axis in range(3):
        for invalid in (LIMIT3 + 1, -LIMIT3 - 1):
            pts = [list(p) for p in base_tet]
            pts[point_index][axis] = invalid
            cases_tet.append(([tuple(p) for p in pts], None))

# Bounded 3D vector operations, checked against independent Python integers.
def vec_valid(v):
    return all(-LIMIT3 <= x <= LIMIT3 for x in v)


def vec_expected(operation, a, b=None):
    if not vec_valid(a) or (b is not None and not vec_valid(b)):
        return None
    if operation == "add":
        out = tuple(a[i] + b[i] for i in range(3))
        return out if vec_valid(out) else None
    if operation == "sub":
        out = tuple(a[i] - b[i] for i in range(3))
        return out if vec_valid(out) else None
    if operation == "dot":
        return sum(a[i] * b[i] for i in range(3))
    if operation == "cross":
        out = (a[1] * b[2] - a[2] * b[1],
               a[2] * b[0] - a[0] * b[2],
               a[0] * b[1] - a[1] * b[0])
        return out if vec_valid(out) else None
    if operation == "length":
        return sum(x * x for x in a)
    raise AssertionError(operation)


vec_cases = {name: [] for name in ("add", "sub", "dot", "cross", "length")}
for operation in vec_cases:
    for _ in range(256):
        a = tuple(RNG.randint(-1000, 1000) for _ in range(3))
        b = tuple(RNG.randint(-1000, 1000) for _ in range(3))
        vec_cases[operation].append((a, b, vec_expected(operation, a, b)))
    for _ in range(256):
        a = tuple(RNG.randint(-LIMIT3, LIMIT3) for _ in range(3))
        b = tuple(RNG.randint(-LIMIT3, LIMIT3) for _ in range(3))
        vec_cases[operation].append((a, b, vec_expected(operation, a, b)))
vec_cases["add"].extend([
    ((LIMIT3, 0, 0), (0, 0, 0), (LIMIT3, 0, 0)),
    ((LIMIT3, 0, 0), (1, 0, 0), None),
    ((-LIMIT3, 0, 0), (-1, 0, 0), None),
])
vec_cases["sub"].extend([
    ((-LIMIT3, 0, 0), (0, 0, 0), (-LIMIT3, 0, 0)),
    ((LIMIT3, 0, 0), (-1, 0, 0), None),
    ((-LIMIT3, 0, 0), (1, 0, 0), None),
])
vec_cases["dot"].append(((LIMIT3, LIMIT3, LIMIT3),
                         (LIMIT3, LIMIT3, LIMIT3), 3 * LIMIT3 * LIMIT3))
vec_cases["cross"].extend([
    ((1, 0, 0), (0, 1, 0), (0, 0, 1)),
    ((0, 1, 0), (1, 0, 0), (0, 0, -1)),
    ((LIMIT3, 0, 0), (0, LIMIT3, 0), None),
])
vec_cases["length"].append(((LIMIT3, LIMIT3, LIMIT3), None,
                            3 * LIMIT3 * LIMIT3))
# Both signs of out-of-domain input in every component and operand position.
for operation in ("add", "sub", "dot", "cross"):
    for point_index in range(2):
        for axis in range(3):
            for invalid in (LIMIT3 + 1, -LIMIT3 - 1):
                a, b = [0, 0, 0], [1, 2, 3]
                (a if point_index == 0 else b)[axis] = invalid
                vec_cases[operation].append((tuple(a), tuple(b), None))
for axis in range(3):
    for invalid in (LIMIT3 + 1, -LIMIT3 - 1):
        a = [0, 0, 0]
        a[axis] = invalid
        vec_cases["length"].append((tuple(a), None, None))


def box_valid(box):
    lo, hi = box
    return (vec_valid(lo) and vec_valid(hi) and
            all(lo[i] <= hi[i] for i in range(3)))


def box_expected(operation, a, b=None, point=None):
    if operation == "make":
        return (a, b) if vec_valid(a) and vec_valid(b) and all(a[i] <= b[i] for i in range(3)) else None
    if not box_valid(a):
        return None
    if operation == "contains":
        if not vec_valid(point):
            return None
        lo, hi = a
        return all(lo[i] <= point[i] <= hi[i] for i in range(3))
    if not box_valid(b):
        return None
    alo, ahi = a
    blo, bhi = b
    if operation == "intersects":
        return all(alo[i] <= bhi[i] and ahi[i] >= blo[i] for i in range(3))
    if operation == "union":
        return (tuple(min(alo[i], blo[i]) for i in range(3)),
                tuple(max(ahi[i], bhi[i]) for i in range(3)))
    raise AssertionError(operation)


box_cases = {name: [] for name in ("make", "contains", "intersects", "union")}


def random_box():
    p = [tuple(RNG.randint(-LIMIT3, LIMIT3) for _ in range(3)) for _ in range(2)]
    lo = tuple(min(p[0][i], p[1][i]) for i in range(3))
    hi = tuple(max(p[0][i], p[1][i]) for i in range(3))
    return lo, hi


for _ in range(256):
    lo = tuple(RNG.randint(-LIMIT3, LIMIT3) for _ in range(3))
    hi = tuple(RNG.randint(-LIMIT3, LIMIT3) for _ in range(3))
    box_cases["make"].append((lo, hi, None, box_expected("make", lo, hi)))
    box = random_box()
    point = tuple(RNG.randint(-LIMIT3, LIMIT3) for _ in range(3))
    box_cases["contains"].append((box, None, point, box_expected("contains", box, point=point)))
    other = random_box()
    box_cases["intersects"].append((box, other, None, box_expected("intersects", box, other)))
    box_cases["union"].append((box, other, None, box_expected("union", box, other)))
# Closed-boundary semantics, degenerate boxes, invalid order and invalid coordinates.
unit = ((0, 0, 0), (10, 10, 10))
box_cases["make"].extend([
    ((0, 0, 0), (0, 0, 0), None, ((0, 0, 0), (0, 0, 0))),
    ((1, 0, 0), (0, 0, 0), None, None),
    ((LIMIT3 + 1, 0, 0), (1, 1, 1), None, None),
    ((-LIMIT3 - 1, 0, 0), (1, 1, 1), None, None),
])
box_cases["contains"].extend([
    (unit, None, (0, 10, 5), True),
    (unit, None, (11, 5, 5), False),
    (((5, 5, 5), (5, 5, 5)), None, (5, 5, 5), True),
    (unit, None, (LIMIT3 + 1, 0, 0), None),
    (((1, 0, 0), (0, 1, 1)), None, (0, 0, 0), None),
    (unit, None, (-LIMIT3 - 1, 0, 0), None),
])
box_cases["intersects"].extend([
    (unit, ((10, 10, 10), (20, 20, 20)), None, True),
    (unit, ((11, 0, 0), (20, 10, 10)), None, False),
    (((5, 5, 5), (5, 5, 5)), ((5, 5, 5), (5, 5, 5)), None, True),
    (((1, 0, 0), (0, 1, 1)), unit, None, None),
    (((LIMIT3 + 1, 0, 0), (LIMIT3 + 1, 1, 1)), unit, None, None),
    (unit, ((-LIMIT3 - 1, 0, 0), (0, 1, 1)), None, None),
])
box_cases["union"].extend([
    (unit, ((10, 10, 10), (20, 20, 20)), None, ((0, 0, 0), (20, 20, 20))),
    (((1, 0, 0), (0, 1, 1)), unit, None, None),
    (((LIMIT3 + 1, 0, 0), (LIMIT3 + 1, 1, 1)), unit, None, None),
    (unit, ((-LIMIT3 - 1, 0, 0), (0, 1, 1)), None, None),
])


# Bounded simple-polygon point classification, checked with exact Python integers.
def polygon_valid(vertices):
    n = len(vertices)
    if n < 3 or n > 256:
        return False
    if any(not (-LIMIT2 <= x <= LIMIT2 and -LIMIT2 <= y <= LIMIT2)
           for x, y in vertices):
        return None
    if any(vertices[i] == vertices[(i + 1) % n] for i in range(n)):
        return False
    if not any(orient2(vertices[0], vertices[1], vertices[k]) != 0
               for k in range(2, n)):
        return False
    for i in range(n):
        a, b = vertices[i], vertices[(i + 1) % n]
        for j in range(i + 1, n):
            c, d = vertices[j], vertices[(j + 1) % n]
            relation = segment_relation(a, b, c, d)
            adjacent = (j == i + 1) or (i == 0 and j == n - 1)
            if adjacent:
                if relation != 0:
                    return False
            elif relation != -1:
                return False
    return True


def polygon_expected(vertices, point):
    valid = polygon_valid(vertices)
    if valid is not True or not (-LIMIT2 <= point[0] <= LIMIT2 and
                                 -LIMIT2 <= point[1] <= LIMIT2):
        return None
    winding = 0
    for i in range(len(vertices)):
        a, b = vertices[i], vertices[(i + 1) % len(vertices)]
        side = orient2(a, b, point)
        if side == 0 and on_segment(a, b, point):
            return 0
        if a[1] <= point[1]:
            if b[1] > point[1] and side > 0:
                winding += 1
        elif b[1] <= point[1] and side < 0:
            winding -= 1
    return 1 if winding else -1


polygon_cases = []
for _ in range(192):
    xs = sorted(RNG.sample(range(-10000, 10001), RNG.randint(2, 8)))
    upper = [(x, RNG.randint(20, 10000)) for x in xs]
    lower = [(x, RNG.randint(-10000, -20)) for x in reversed(xs)]
    ring = upper + lower
    query = (RNG.randint(-12000, 12000), RNG.randint(-12000, 12000))
    polygon_cases.append((ring, query, polygon_expected(ring, query)))
square = [(0, 0), (10, 0), (10, 10), (0, 10)]
polygon_cases.extend([
    (square, (5, 5), 1),
    (square, (0, 5), 0),
    (square, (10, 10), 0),
    (square, (11, 5), -1),
    (list(reversed(square)), (5, 5), 1),
    ([(0, 0), (10, 0), (5, 5), (10, 10), (0, 10)], (5, 4), 1), # concave
    ([(0, 0), (10, 10), (0, 10), (10, 0)], (5, 5), None),       # bow-tie
    ([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)], (5, 5), None), # repeated closure
    ([(0, 0), (10, 0), (10, 0), (0, 10)], (5, 5), None),         # zero edge
    ([(0, 0), (5, 0), (10, 0)], (5, 0), None),                   # collinear
    ([(0, 0), (10, 0)], (5, 0), None),
    ([(LIMIT2 + 1, 0), (0, 10), (10, 0)], (1, 1), None),
    (square, (LIMIT2 + 1, 0), None),
])
# Repeated non-adjacent vertex and positive-length adjacent backtracking.
polygon_cases.extend([
    ([(0, 0), (10, 0), (10, 10), (0, 10), (10, 0)], (5, 5), None),
    ([(0, 0), (10, 0), (5, 0), (10, 10), (0, 10)], (5, 5), None),
])
# Enforce the vertex cap before inspecting caller-controlled list contents.
polygon_cases.append(([(i, (i * i) % 997) for i in range(257)],
                      (0, 0), None))
# The inclusive maximum-size valid ring and full 2D coordinate-domain extremes.
xs_max = sorted(RNG.sample(range(-100000, 100001), 128))
max_ring = ([(x, RNG.randint(100, 100000)) for x in xs_max] +
            [(x, RNG.randint(-100000, -100)) for x in reversed(xs_max)])
polygon_cases.append((max_ring, (0, 0), polygon_expected(max_ring, (0, 0))))
extreme_square = [(-LIMIT2, -LIMIT2), (LIMIT2, -LIMIT2),
                  (LIMIT2, LIMIT2), (-LIMIT2, LIMIT2)]
polygon_cases.extend([
    (extreme_square, (0, 0), 1),
    (extreme_square, (LIMIT2, 0), 0),
    (extreme_square, (-LIMIT2, -LIMIT2), 0),
])


# Metamorphic topology checks: every cyclic start and reversed winding must
# preserve both simplicity classification and point classification.
metamorphic_sources = [
    (square, (5, 5)),
    (square, (0, 5)),
    ([(0, 0), (10, 0), (5, 5), (10, 10), (0, 10)], (5, 4)),
    ([(0, 0), (10, 10), (0, 10), (10, 0)], (5, 5)),
    ([(0, 0), (10, 0), (5, 0), (10, 10), (0, 10)], (5, 5)),
    (extreme_square, (0, 0)),
]
for ring, query in metamorphic_sources:
    for direction in (ring, list(reversed(ring))):
        for shift in range(len(direction)):
            transformed = direction[shift:] + direction[:shift]
            polygon_cases.append(
                (transformed, query, polygon_expected(transformed, query)))



source = [
    "void show_sign(int? value) {",
    "    if (let n = value) { println(int_to_str(n)); }",
    '    else { println("none"); }',
    "}",
    "void show_vec3(KVec3? value) {",
    '    if (let v = value) { println(int_to_str(v.x) + "," + int_to_str(v.y) + "," + int_to_str(v.z)); }',
    '    else { println("none"); }',
    "}",
    "void show_bool(bool? value) {",
    '    if (let v = value) { if (v) { println("true"); } else { println("false"); } }',
    '    else { println("none"); }',
    "}",
    "void show_bounds(KBounds3? value) {",
    '    if (let b = value) { println(int_to_str(b.min.x) + "," + int_to_str(b.min.y) + "," + int_to_str(b.min.z) + "," + int_to_str(b.max.x) + "," + int_to_str(b.max.y) + "," + int_to_str(b.max.z)); }',
    '    else { println("none"); }',
    "}",
]
expected = []

def emit_batches(dimension, cases, batch_size=32):
    for batch_start in range(0, len(cases), batch_size):
        batch = cases[batch_start:batch_start + batch_size]
        function_name = f"run_{dimension}_{batch_start // batch_size}"
        source.append(f"void {function_name}() {{")
        for offset, (pts, want) in enumerate(batch):
            index = batch_start + offset
            if dimension == "2d":
                source.append(f"    KPoint2 a{index} = {point2(pts[0])};")
                source.append(f"    KPoint2 b{index} = {point2(pts[1])};")
                source.append(f"    KPoint2 c{index} = {point2(pts[2])};")
                source.append(f"    show_sign(keel_orient2d_sign(a{index}, b{index}, c{index}));")
            else:
                source.append(f"    KPoint3 a3_{index} = {point3(pts[0])};")
                source.append(f"    KPoint3 b3_{index} = {point3(pts[1])};")
                source.append(f"    KPoint3 c3_{index} = {point3(pts[2])};")
                source.append(f"    KPoint3 d3_{index} = {point3(pts[3])};")
                source.append(f"    show_sign(keel_orient3d_sign(a3_{index}, b3_{index}, c3_{index}, d3_{index}));")
            expected.append("none" if want is None else str(want))
        source.append("}")

emit_batches("2d", cases2)
emit_batches("3d", cases3)
for batch_start in range(0, len(cases_seg), 32):
    batch = cases_seg[batch_start:batch_start + 32]
    function_name = f"run_seg_{batch_start // 32}"
    source.append(f"void {function_name}() {{")
    for offset, (pts, want) in enumerate(batch):
        index = batch_start + offset
        source.append(f"    KPoint2 sa{index} = {point2(pts[0])};")
        source.append(f"    KPoint2 sb{index} = {point2(pts[1])};")
        source.append(f"    KPoint2 sc{index} = {point2(pts[2])};")
        source.append(f"    KPoint2 sd{index} = {point2(pts[3])};")
        source.append(f"    show_sign(keel_segment_relation2d(sa{index}, sb{index}, sc{index}, sd{index}));")
        expected.append("none" if want is None else str(want))
    source.append("}")
for batch_start in range(0, len(cases_tet), 32):
    batch = cases_tet[batch_start:batch_start + 32]
    function_name = f"run_tet_{batch_start // 32}"
    source.append(f"void {function_name}() {{")
    for offset, (pts, want) in enumerate(batch):
        index = batch_start + offset
        source.append(f"    KPoint3 ta{index} = {point3(pts[0])};")
        source.append(f"    KPoint3 tb{index} = {point3(pts[1])};")
        source.append(f"    KPoint3 tc{index} = {point3(pts[2])};")
        source.append(f"    KPoint3 td{index} = {point3(pts[3])};")
        source.append(f"    KPoint3 tp{index} = {point3(pts[4])};")
        source.append(f"    show_sign(keel_point_in_tetrahedron3d(ta{index}, tb{index}, tc{index}, td{index}, tp{index}));")
        expected.append("none" if want is None else str(want))
    source.append("}")
# Generate vector-operation cases in small functions to keep compiler test units bounded.
for operation, cases in vec_cases.items():
    for batch_start in range(0, len(cases), 32):
        batch = cases[batch_start:batch_start + 32]
        function_name = f"run_vec_{operation}_{batch_start // 32}"
        source.append(f"void {function_name}() {{")
        for offset, (a, b, want) in enumerate(batch):
            index = batch_start + offset
            source.append(f"    KVec3 va{index} = keel_vec3({a[0]}, {a[1]}, {a[2]});")
            if operation in ("add", "sub", "dot", "cross"):
                source.append(f"    KVec3 vb{index} = keel_vec3({b[0]}, {b[1]}, {b[2]});")
            if operation in ("add", "sub", "dot", "cross"):
                call = f"keel_vec3_{operation}(va{index}, vb{index})"
            else:
                call = f"keel_vec3_length_squared(va{index})"
            show = "show_vec3" if operation in ("add", "sub", "cross") else "show_sign"
            source.append(f"    {show}({call});")
            if operation in ("add", "sub", "cross"):
                expected.append("none" if want is None else ",".join(str(x) for x in want))
            else:
                expected.append("none" if want is None else str(want))
        source.append("}")
# The fit helpers are public functions: test direct calls with arbitrary int64 extremes,
# not only calls reached through already-validated vector operations.
vec_fit_cases = [
    ("keel_vec3_add_fits(0, 0)", True),
    (f"keel_vec3_add_fits({LIMIT3}, 1)", False),
    (f"keel_vec3_add_fits({-LIMIT3}, -1)", False),
    ("keel_vec3_add_fits(0x8000000000000000, 0x7FFFFFFFFFFFFFFF)", False),
    ("keel_vec3_add_fits(0x7FFFFFFFFFFFFFFF, 0x8000000000000000)", False),
    ("keel_vec3_sub_fits(0, 0)", True),
    (f"keel_vec3_sub_fits({LIMIT3}, -1)", False),
    (f"keel_vec3_sub_fits({-LIMIT3}, 1)", False),
    ("keel_vec3_sub_fits(0x8000000000000000, 0x7FFFFFFFFFFFFFFF)", False),
    ("keel_vec3_sub_fits(0x7FFFFFFFFFFFFFFF, 0x8000000000000000)", False),
]
source.append("void run_vec_fit_guards() {")
for expression, want in vec_fit_cases:
    source.append(f"    show_bool({expression});")
    expected.append("true" if want else "false")
source.append("}")


# Generate AABB cases with inclusive faces/edges/corners and explicit invalid-state checks.
for operation, cases in box_cases.items():
    for batch_start in range(0, len(cases), 32):
        batch = cases[batch_start:batch_start + 32]
        function_name = f"run_bounds_{operation}_{batch_start // 32}"
        source.append(f"void {function_name}() {{")
        for offset, (a, b, point, want) in enumerate(batch):
            index = batch_start + offset
            if operation == "make":
                source.append(f"    KPoint3 lo{index} = {point3(a)};")
                source.append(f"    KPoint3 hi{index} = {point3(b)};")
                call = f"keel_bounds3_make(lo{index}, hi{index})"
            elif operation == "contains":
                source.append(f"    KBounds3 box{index} = new KBounds3{{min: {point3(a[0])}, max: {point3(a[1])}}};")
                source.append(f"    KPoint3 p{index} = {point3(point)};")
                call = f"keel_bounds3_contains(box{index}, p{index})"
            else:
                source.append(f"    KBounds3 a{index} = new KBounds3{{min: {point3(a[0])}, max: {point3(a[1])}}};")
                source.append(f"    KBounds3 b{index} = new KBounds3{{min: {point3(b[0])}, max: {point3(b[1])}}};")
                call = f"keel_bounds3_{operation}(a{index}, b{index})"
            if operation in ("make", "union"):
                source.append(f"    show_bounds({call});")
                if want is None:
                    expected.append("none")
                else:
                    expected.append(",".join(str(x) for x in (*want[0], *want[1])))
            else:
                source.append(f"    show_bool({call});")
                expected.append("none" if want is None else ("true" if want else "false"))
        source.append("}")

# Polygon calls are emitted in small functions to bound generated source size.
for batch_start in range(0, len(polygon_cases), 8):
    batch = polygon_cases[batch_start:batch_start + 8]
    function_name = f"run_polygon_{batch_start // 8}"
    source.append(f"void {function_name}() {{")
    for offset, (vertices, point, want) in enumerate(batch):
        index = batch_start + offset
        source.append(f"    List<KPoint2> poly{index} = new List<KPoint2>();")
        for vertex in vertices:
            source.append(f"    poly{index}.push({point2(vertex)});")
        source.append(f"    show_bool(keel_polygon2_valid(poly{index}));")
        source.append(f"    show_sign(keel_point_in_polygon2d(poly{index}, {point2(point)}));")
        valid_want = polygon_valid(vertices)
        expected.append("none" if valid_want is None else ("true" if valid_want else "false"))
        expected.append("none" if want is None else str(want))
    source.append("}")
source.append("int main() {")
for dimension, cases in (("2d", cases2), ("3d", cases3), ("seg", cases_seg), ("tet", cases_tet)):
    for batch_start in range(0, len(cases), 32):
        source.append(f"    run_{dimension}_{batch_start // 32}();")
for operation, cases in vec_cases.items():
    for batch_start in range(0, len(cases), 32):
        source.append(f"    run_vec_{operation}_{batch_start // 32}();")
source.append("    run_vec_fit_guards();")
for operation, cases in box_cases.items():
    for batch_start in range(0, len(cases), 32):
        source.append(f"    run_bounds_{operation}_{batch_start // 32}();")
for batch_start in range(0, len(polygon_cases), 8):
    source.append(f"    run_polygon_{batch_start // 8}();")
source.append("    return 0;")
source.append("}")
source_text = "\n".join(source) + "\n"

with tempfile.TemporaryDirectory(prefix="capstan-keel-predicates-") as tmp:
    main = os.path.join(tmp, "generated.cap")
    cfile = os.path.join(tmp, "predicates.c")
    exe = os.path.join(tmp, "predicates")
    with open(main, "w", encoding="utf-8") as f:
        f.write(source_text)
    build = subprocess.run(
        [CAPSTANC, "build", "--strict", "-o", cfile,
         os.path.join(ROOT, "lib/keel/predicates.cap"),
         os.path.join(ROOT, "lib/keel/spatial.cap"),
         os.path.join(ROOT, "lib/keel/polygon.cap"), main],
        cwd=ROOT, capture_output=True, text=True)
    if build.returncode:
        sys.exit("Keel predicate program did not compile:\n" + build.stdout + build.stderr)
    compile_result = subprocess.run(
        [CC, *CFLAGS, cfile, "-o", exe],
        cwd=ROOT, capture_output=True, text=True)
    if compile_result.returncode:
        sys.exit("Keel predicate C did not compile:\n" + compile_result.stdout + compile_result.stderr)
    run = subprocess.run([exe], cwd=ROOT, capture_output=True, text=True)
    if run.returncode:
        sys.exit(f"Keel predicate executable exited {run.returncode}:\n{run.stdout}{run.stderr}")
    actual = run.stdout.splitlines()
    if actual != expected:
        for i, (got, want) in enumerate(zip(actual, expected)):
            if got != want:
                sys.exit(f"predicate case {i}: expected {want}, got {got}")
        sys.exit(f"predicate output length: expected {len(expected)}, got {len(actual)}")

print(f"{len(polygon_cases)} polygon, {len(cases2)} 2D, {len(cases3)} 3D, {len(cases_seg)} segment, {len(cases_tet)} tetrahedron, {sum(map(len, vec_cases.values()))} vector and {sum(map(len, box_cases.values()))} bounds cases match independent oracles")
