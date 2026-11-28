"""Read back actual group artifacts and submit independently checked fields to Capstan."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from systematic_runner import ROOT, MANIFEST, validate_manifest, capstan_summary_valid

MAX_JSON = 4 * 1024 * 1024
MAX_LOG = 64 * 1024 * 1024


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field: " + key)
        result[key] = value
    return result


def bounded_bytes(path, limit):
    if not path.is_file() or path.is_symlink():
        raise ValueError("missing or nonregular artifact: " + str(path))
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError("artifact exceeds size limit: " + str(path))
    return data


def digest(data):
    return hashlib.sha256(data).hexdigest()


def command_hash(argv):
    return digest(json.dumps(argv, ensure_ascii=True, separators=(",", ":")).encode("ascii"))


def readback(directory, group, commands, revision, tree, manifest_hash):
    data = json.loads(bounded_bytes(directory / "evidence.json", MAX_JSON),
                      object_pairs_hook=unique_object)
    if not isinstance(data, dict) or set(data) != {
        "schema", "revision", "tree", "group", "manifest_sha256",
        "expected_count", "results", "passed"
    }:
        raise ValueError("invalid evidence schema")
    if type(data["schema"]) is not int or data["schema"] != 1:
        raise ValueError("unsupported schema")
    if (data["revision"], data["tree"], data["group"], data["manifest_sha256"]) != (
            revision, tree, group, manifest_hash):
        raise ValueError("stale or mismatched evidence identity")
    if (not 1 <= len(commands) <= 64 or type(data["expected_count"]) is not int
            or data["expected_count"] != len(commands)
            or not isinstance(data["results"], list)
            or len(data["results"]) != len(commands) or data["passed"] is not True):
        raise ValueError("incomplete or unsuccessful group")
    args = [revision, tree, manifest_hash, group, str(len(commands)),
            str(data["schema"]), data["revision"], data["tree"],
            data["manifest_sha256"], data["group"]]
    args += [command_hash(cmd) for cmd in commands]
    expected_files = {"evidence.json"}
    for i, (row, cmd) in enumerate(zip(data["results"], commands)):
        name = f"{i:03d}.log"
        expected_files.add(name)
        if not isinstance(row, dict) or set(row) != {
            "argv", "returncode", "error", "elapsed_seconds", "log", "log_sha256"
        }:
            raise ValueError("invalid result schema")
        if row["argv"] != cmd or row["log"] != name:
            raise ValueError("command order or log path mismatch")
        log = bounded_bytes(directory / name, MAX_LOG)
        if digest(log) != row["log_sha256"]:
            raise ValueError("log digest mismatch")
        if type(row["returncode"]) is not int or row["returncode"] != 0 or row["error"] != "":
            raise ValueError("unsuccessful result")
        if cmd[0] == "bin/capstan" and not capstan_summary_valid(log):
            raise ValueError("incomplete Capstan test summary")
        args += [str(i), command_hash(row["argv"]), row["log_sha256"], "1", "1",
                 str(row["returncode"]), row["error"]]
    if {p.name for p in directory.iterdir()} != expected_files:
        raise ValueError("unexpected evidence files")
    return args


def main():
    if len(sys.argv) != 2:
        raise SystemExit("select one group")
    group = sys.argv[1]
    raw = bounded_bytes(MANIFEST, MAX_JSON)
    manifest = validate_manifest(json.loads(raw, object_pairs_hook=unique_object))
    def git(ref):
        return subprocess.check_output(["git", "rev-parse", ref], cwd=ROOT, text=True).strip()
    directory = ROOT / "build/systematic-evidence" / group
    args = readback(directory, group, manifest[group], git("HEAD"), git("HEAD^{tree}"), digest(raw))
    executable = ROOT / "build/assurance-evidence-admission"
    subprocess.run([ROOT / "bin/capstan", "build",
                    ROOT / "verification/assurance_evidence_policy_tests.cap",
                    ROOT / "tools/assurance/evidence_admission.cap", "-o", executable],
                   cwd=ROOT, check=True, timeout=180)
    result = subprocess.run([executable, *args], cwd=ROOT, check=True,
                            capture_output=True, text=True, timeout=60)
    if result.stdout.strip() != "assurance evidence admitted":
        raise ValueError("unexpected Capstan policy response")
    print(result.stdout.strip())


if __name__ == "__main__":
    main()
