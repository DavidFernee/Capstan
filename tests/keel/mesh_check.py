#!/usr/bin/env python3
"""Focused conformance tests for Keel's bounded triangle-mesh contract."""
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CAPSTANC, CC, *CFLAGS = sys.argv[1:]

program = r'''
void show_bool(bool? value) {
    if (let v = value) {
        if (v) { println("true"); } else { println("false"); }
    } else { println("none"); }
}
void show_topology(KMesh3Topology? value) {
    if (let t = value) {
        println(int_to_str(t.unique_edges) + "," +
                int_to_str(t.boundary_edges) + "," +
                int_to_str(t.two_face_edges) + "," +
                int_to_str(t.nonmanifold_edges) + "," +
                int_to_str(t.inconsistent_winding_edges) + "," +
                int_to_str(t.duplicate_faces) + "," +
                int_to_str(t.connected_components) + "," +
                int_to_str(t.referenced_vertices) + "," +
                int_to_str(t.isolated_vertices));
    } else { println("none"); }
}

void show_bounds(KBounds3? value) {
    if (let b = value) {
        println(int_to_str(b.min.x) + "," + int_to_str(b.min.y) + "," +
                int_to_str(b.min.z) + "," + int_to_str(b.max.x) + "," +
                int_to_str(b.max.y) + "," + int_to_str(b.max.z));
    } else { println("none"); }
}
int main() {
    List<KPoint3> v = new List<KPoint3>();
    v.push(keel_point3(0, 0, 0));
    v.push(keel_point3(10, 0, 0));
    v.push(keel_point3(0, 10, 0));
    v.push(keel_point3(0, 0, 10));
    List<int> ix = new List<int>();
    ix.push(0); ix.push(1); ix.push(2);
    ix.push(0); ix.push(3); ix.push(1);
    ix.push(0); ix.push(2); ix.push(3);
    ix.push(1); ix.push(3); ix.push(2);
    show_bool(keel_mesh3_valid(v, ix));
    show_bounds(keel_mesh3_bounds(v));

    List<int> bad_index = new List<int>();
    bad_index.push(0); bad_index.push(1); bad_index.push(99);
    show_bool(keel_mesh3_valid(v, bad_index));

    List<int> negative_index = new List<int>();
    negative_index.push(-1); negative_index.push(1); negative_index.push(2);
    show_bool(keel_mesh3_valid(v, negative_index));

    List<int> repeated_index = new List<int>();
    repeated_index.push(0); repeated_index.push(0); repeated_index.push(1);
    show_bool(keel_mesh3_valid(v, repeated_index));

    List<KPoint3> collinear = new List<KPoint3>();
    collinear.push(keel_point3(0, 0, 0));
    collinear.push(keel_point3(1, 1, 1));
    collinear.push(keel_point3(2, 2, 2));
    List<int> one_triangle = new List<int>();
    one_triangle.push(0); one_triangle.push(1); one_triangle.push(2);
    show_bool(keel_mesh3_valid(collinear, one_triangle));

    List<KPoint3> invalid_vertex = new List<KPoint3>();
    invalid_vertex.push(keel_point3(0, 0, 0));
    invalid_vertex.push(keel_point3(1, 0, 0));
    invalid_vertex.push(keel_point3(0, 1, 0));
    invalid_vertex.push(keel_point3(0x40000, 0, 0));
    show_bool(keel_mesh3_valid(invalid_vertex, one_triangle));
    show_bounds(keel_mesh3_bounds(invalid_vertex));

    List<int> incomplete = new List<int>();
    incomplete.push(0); incomplete.push(1);
    show_bool(keel_mesh3_valid(v, incomplete));

    List<KPoint3> empty = new List<KPoint3>();
    show_bool(keel_mesh3_valid(empty, ix));
    show_bounds(keel_mesh3_bounds(empty));

    show_bool(keel_triangle3_non_degenerate(
        keel_point3(0, 0, 0), keel_point3(10, 0, 0),
        keel_point3(0, 10, 0)));
    show_bool(keel_triangle3_non_degenerate(
        keel_point3(0, 0, 0), keel_point3(1, 1, 1),
        keel_point3(2, 2, 2)));
    show_bool(keel_triangle3_non_degenerate(
        keel_point3(0x40000, 0, 0), keel_point3(1, 0, 0),
        keel_point3(0, 1, 0)));
    // Closed tetrahedron: every edge has two oppositely directed incident faces.
    show_topology(keel_mesh3_topology(v, ix));

    List<KPoint3> tv = new List<KPoint3>();
    tv.push(keel_point3(0, 0, 0));
    tv.push(keel_point3(1, 0, 0));
    tv.push(keel_point3(0, 1, 0));
    tv.push(keel_point3(0, 0, 1));
    tv.push(keel_point3(0, -1, 0));
    tv.push(keel_point3(0, 0, -1));
    tv.push(keel_point3(1, 1, 1));

    // One open triangle has three boundary edges.
    List<int> single = new List<int>();
    single.push(0); single.push(1); single.push(2);
    show_topology(keel_mesh3_topology(tv, single));

    // Two faces traverse their shared edge in the same direction.
    List<int> same_winding = new List<int>();
    same_winding.push(0); same_winding.push(1); same_winding.push(2);
    same_winding.push(0); same_winding.push(1); same_winding.push(3);
    show_topology(keel_mesh3_topology(tv, same_winding));

    // Three incident faces make the shared edge non-manifold.
    List<int> nonmanifold = new List<int>();
    nonmanifold.push(0); nonmanifold.push(1); nonmanifold.push(2);
    nonmanifold.push(0); nonmanifold.push(1); nonmanifold.push(3);
    nonmanifold.push(0); nonmanifold.push(1); nonmanifold.push(4);
    show_topology(keel_mesh3_topology(tv, nonmanifold));

    // A duplicate face is counted independent of its winding.
    List<int> duplicate = new List<int>();
    duplicate.push(0); duplicate.push(1); duplicate.push(2);
    duplicate.push(0); duplicate.push(1); duplicate.push(2);
    show_topology(keel_mesh3_topology(tv, duplicate));
    show_topology(keel_mesh3_topology(tv, incomplete));

    // Disconnected triangle components remain representable; vertex 6 is isolated.
    List<int> disconnected = new List<int>();
    disconnected.push(0); disconnected.push(1); disconnected.push(2);
    disconnected.push(3); disconnected.push(4); disconnected.push(5);
    show_topology(keel_mesh3_topology(tv, disconnected));
    return 0;
}
'''
expected = [
    "true",
    "0,0,0,10,10,10",
    "false",
    "false",
    "false",
    "false",
    "none",
    "none",
    "false",
    "false",
    "none",
    "true",
    "false",
    "none",
    "6,0,6,0,0,0,1,4,0",
    "3,3,0,0,0,0,1,3,4",
    "5,4,1,0,1,0,1,4,3",
    "7,6,0,1,0,0,1,5,2",
    "3,0,3,0,3,1,1,3,4",
    "none",
    "6,6,0,0,0,0,2,6,1",
]
with tempfile.TemporaryDirectory(prefix="capstan-keel-mesh-") as tmp:
    main = os.path.join(tmp, "mesh_check.cap")
    cfile = os.path.join(tmp, "mesh_check.c")
    exe = os.path.join(tmp, "mesh_check")
    with open(main, "w", encoding="utf-8") as f:
        f.write(program)
    build = subprocess.run(
        [CAPSTANC, "build", "--strict", "-o", cfile,
         os.path.join(ROOT, "lib/keel/mesh.cap"), main],
        cwd=ROOT, capture_output=True, text=True)
    if build.returncode:
        sys.exit("Keel mesh program did not compile:\n" + build.stdout + build.stderr)
    compiled = subprocess.run(
        [CC, *CFLAGS, cfile, "-o", exe],
        cwd=ROOT, capture_output=True, text=True)
    if compiled.returncode:
        sys.exit("Keel mesh C did not compile:\n" + compiled.stdout + compiled.stderr)
    run = subprocess.run([exe], cwd=ROOT, capture_output=True, text=True)
    if run.returncode:
        sys.exit(f"Keel mesh executable exited {run.returncode}:\n{run.stdout}{run.stderr}")
    actual = run.stdout.splitlines()
    if actual != expected:
        for i, (got, want) in enumerate(zip(actual, expected)):
            if got != want:
                sys.exit(f"mesh case {i}: expected {want}, got {got}")
        sys.exit(f"mesh output length: expected {len(expected)}, got {len(actual)}")
print("Keel mesh validation: valid tetrahedral surface, bounds, invalid indices, repeated indices, degenerate geometry, out-of-domain vertices, incomplete triangles and empty input")


# Differential topology checks against a separate Python integer oracle. The
# generator deliberately includes repeated faces, reversed winding, shared
# edges, disconnected components and unused vertices.
import random


def non_degenerate(vertices, face):
    a, b, c = (vertices[i] for i in face)
    ab = tuple(b[j] - a[j] for j in range(3))
    ac = tuple(c[j] - a[j] for j in range(3))
    cross = (
        ab[1] * ac[2] - ab[2] * ac[1],
        ab[2] * ac[0] - ab[0] * ac[2],
        ab[0] * ac[1] - ab[1] * ac[0],
    )
    return cross != (0, 0, 0)


def topology_oracle(vertex_count, triangles):
    edge_incidence = {}
    face_counts = {}
    parent = list(range(vertex_count))
    rank = [0] * vertex_count
    referenced = set()

    def root(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        a, b = root(a), root(b)
        if a == b:
            return
        if rank[a] < rank[b]:
            parent[a] = b
        elif rank[a] > rank[b]:
            parent[b] = a
        else:
            parent[b] = a
            rank[a] += 1

    for a, b, c in triangles:
        for x, y in ((a, b), (b, c), (c, a)):
            key = tuple(sorted((x, y)))
            count, direction = edge_incidence.get(key, (0, 0))
            edge_incidence[key] = (count + 1, direction + (1 if x < y else -1))
        face = tuple(sorted((a, b, c)))
        face_counts[face] = face_counts.get(face, 0) + 1
        referenced.update((a, b, c))
        union(a, b)
        union(b, c)

    boundary = sum(count == 1 for count, _ in edge_incidence.values())
    two_face = sum(count == 2 for count, _ in edge_incidence.values())
    nonmanifold = sum(count > 2 for count, _ in edge_incidence.values())
    winding = sum(count == 2 and abs(direction) == 2
                  for count, direction in edge_incidence.values())
    duplicates = sum(count - 1 for count in face_counts.values() if count > 1)
    components = len({root(vertex) for vertex in referenced})
    return (
        len(edge_incidence), boundary, two_face, nonmanifold, winding,
        duplicates, components, len(referenced), vertex_count - len(referenced),
    )


rng = random.Random(20261125)
cases = []
for _ in range(64):
    count = rng.randint(4, 12)
    points = []
    while len(points) < count:
        point = tuple(rng.randint(-20, 20) for _ in range(3))
        if point not in points:
            points.append(point)
    faces = []
    for _face in range(rng.randint(1, 18)):
        if faces and rng.randrange(7) == 0:
            old = rng.choice(faces)
            faces.append(old if rng.randrange(2) else (old[0], old[2], old[1]))
            continue
        for _attempt in range(100):
            candidate = tuple(rng.sample(range(count), 3))
            if non_degenerate(points, candidate):
                faces.append(candidate)
                break
        else:
            break
    if faces:
        cases.append((points, faces))

oracle_program = [r'''
void show_topology(KMesh3Topology? value) {
    if (let t = value) {
        println(int_to_str(t.unique_edges) + "," +
                int_to_str(t.boundary_edges) + "," +
                int_to_str(t.two_face_edges) + "," +
                int_to_str(t.nonmanifold_edges) + "," +
                int_to_str(t.inconsistent_winding_edges) + "," +
                int_to_str(t.duplicate_faces) + "," +
                int_to_str(t.connected_components) + "," +
                int_to_str(t.referenced_vertices) + "," +
                int_to_str(t.isolated_vertices));
    } else { println("none"); }
}
int main() {
''']
oracle_expected = []
for case_no, (points, faces) in enumerate(cases):
    oracle_program.append(f"    List<KPoint3> vertices{case_no} = new List<KPoint3>();")
    for x, y, z in points:
        oracle_program.append(
            f"    vertices{case_no}.push(keel_point3({x}, {y}, {z}));")
    oracle_program.append(f"    List<int> indices{case_no} = new List<int>();")
    for face in faces:
        for index in face:
            oracle_program.append(f"    indices{case_no}.push({index});")
    oracle_program.append(
        f"    show_topology(keel_mesh3_topology(vertices{case_no}, indices{case_no}));")
    oracle_expected.append(",".join(map(str, topology_oracle(len(points), faces))))
oracle_program.append("    return 0;\n}\n")
oracle_program = "\n".join(oracle_program)

with tempfile.TemporaryDirectory(prefix="capstan-keel-topology-oracle-") as tmp:
    main = os.path.join(tmp, "topology_oracle.cap")
    cfile = os.path.join(tmp, "topology_oracle.c")
    exe = os.path.join(tmp, "topology_oracle")
    with open(main, "w", encoding="utf-8") as f:
        f.write(oracle_program)
    build = subprocess.run(
        [CAPSTANC, "build", "--strict", "-o", cfile,
         os.path.join(ROOT, "lib/keel/mesh.cap"), main],
        cwd=ROOT, capture_output=True, text=True)
    if build.returncode:
        sys.exit("Keel topology oracle program did not compile:\n" +
                 build.stdout + build.stderr)
    compiled = subprocess.run(
        [CC, *CFLAGS, cfile, "-o", exe],
        cwd=ROOT, capture_output=True, text=True)
    if compiled.returncode:
        sys.exit("Keel topology oracle C did not compile:\n" +
                 compiled.stdout + compiled.stderr)
    run = subprocess.run([exe], cwd=ROOT, capture_output=True, text=True)
    if run.returncode:
        sys.exit(f"Keel topology oracle executable exited {run.returncode}:\n" +
                 run.stdout + run.stderr)
    actual = run.stdout.splitlines()
    if actual != oracle_expected:
        for i, (got, want) in enumerate(zip(actual, oracle_expected)):
            if got != want:
                sys.exit(f"topology oracle case {i}: expected {want}, got {got}")
        sys.exit(f"topology oracle output length: expected {len(oracle_expected)}, got {len(actual)}")
print(f"Keel topology differential oracle: {len(cases)} deterministic random meshes agree")
