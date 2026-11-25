#!/usr/bin/env python3
"""Deterministic, test-only contract model for Anchor A1 process supervision.

This is not a process launcher and never creates an OS child. It exercises the
adapter contract against a fake backend so that a future Capstan-native backend
can be checked against the same cases.
"""
from __future__ import annotations

import json
import re
import unittest
from dataclasses import dataclass, field
from enum import Enum, auto


MAX_FRAME_BYTES = 16 * 1024 * 1024
MAX_HEADER_BYTES = 4096
MAX_HEADER_FIELDS = 16
MAX_READ_CHUNK = 64 * 1024
MAX_RETAINED_OUTPUT = 64 * 1024
MAX_JSON_DEPTH = 64
MAX_PENDING_REQUESTS = 256
MAX_OPEN_DOCUMENTS = 1000
MAX_ACTIVE_PROCESSES = 4
MAX_ARG_COUNT = 128
MAX_ARG_BYTES = 64 * 1024
ALLOWED_ENV = frozenset({"LANG", "LC_ALL", "TZ"})
FORBIDDEN_ENV = frozenset({"PATH", "LD_PRELOAD", "LD_LIBRARY_PATH", "DYLD_INSERT_LIBRARIES"})


class ContractError(Exception):
    pass


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ContractError("duplicate JSON object key")
        result[key] = value
    return result


def _check_json_depth(raw):
    depth = 0
    in_string = False
    escaped = False
    for byte in raw:
        if in_string:
            if escaped:
                escaped = False
            elif byte == 92:
                escaped = True
            elif byte == 34:
                in_string = False
        elif byte == 34:
            in_string = True
        elif byte in (123, 91):
            depth += 1
            if depth > MAX_JSON_DEPTH:
                raise ContractError("JSON nesting exceeds configured limit")
        elif byte in (125, 93):
            depth -= 1


def _valid_rpc_message(message):
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
        raise ContractError("JSON-RPC message must be an object with jsonrpc 2.0")
    has_method = "method" in message
    has_result = "result" in message
    has_error = "error" in message
    if has_method:
        if not isinstance(message["method"], str) or not message["method"]:
            raise ContractError("request method must be a non-empty string")
        if has_result or has_error:
            raise ContractError("request cannot also contain a response")
        if "id" in message and (isinstance(message["id"], bool) or
                                not isinstance(message["id"], (str, int))):
            raise ContractError("request id must be a string or integer")
    else:
        if "id" not in message or has_result == has_error:
            raise ContractError("response must contain id and exactly one result/error")
        if isinstance(message["id"], bool) or not isinstance(message["id"], (str, int)):
            raise ContractError("response id must be a string or integer")
        if has_error and (not isinstance(message["error"], dict) or
                          not isinstance(message["error"].get("code"), int) or
                          not isinstance(message["error"].get("message"), str)):
            raise ContractError("malformed JSON-RPC error")
    return message


class BoundedFrameDecoder:
    """Incremental strict Content-Length decoder with a fixed per-frame ceiling."""

    def __init__(self, max_body=MAX_FRAME_BYTES):
        if not 0 < max_body <= MAX_FRAME_BYTES:
            raise ValueError("invalid frame limit")
        self.max_body = max_body
        self.buffer = bytearray()

    def feed(self, chunk):
        if not isinstance(chunk, (bytes, bytearray)):
            raise TypeError("wire input must be bytes")
        if len(chunk) > MAX_READ_CHUNK:
            raise ContractError("transport read exceeds configured chunk limit")
        if len(self.buffer) + len(chunk) > self.max_body + MAX_HEADER_BYTES + MAX_READ_CHUNK:
            raise ContractError("buffer exceeds the maximum incomplete frame plus one read")
        self.buffer.extend(chunk)
        messages = []
        while True:
            marker = self.buffer.find(b"\r\n\r\n")
            if marker < 0:
                if len(self.buffer) > MAX_HEADER_BYTES:
                    raise ContractError("header exceeds configured limit")
                break
            if marker > MAX_HEADER_BYTES:
                raise ContractError("header exceeds configured limit")
            raw_headers = bytes(self.buffer[:marker])
            try:
                lines = raw_headers.decode("ascii").split("\r\n") if raw_headers else []
            except UnicodeDecodeError as exc:
                raise ContractError("header is not ASCII") from exc
            if not 1 <= len(lines) <= MAX_HEADER_FIELDS:
                raise ContractError("invalid header field count")
            lengths = []
            for line in lines:
                if ":" not in line:
                    raise ContractError("malformed header field")
                name, value = line.split(":", 1)
                if name.lower() == "content-length":
                    lengths.append(value.strip())
                elif name.lower() == "content-type":
                    if value.strip().lower() not in ("application/vscode-jsonrpc; charset=utf-8",
                                                      "application/json; charset=utf-8",
                                                      "application/vscode-jsonrpc"):
                        raise ContractError("unsupported content type")
                else:
                    raise ContractError("unsupported header")
            if len(lengths) != 1 or not re.fullmatch(r"[0-9]{1,10}", lengths[0]):
                raise ContractError("missing, duplicate or malformed Content-Length")
            size = int(lengths[0])
            if size > self.max_body:
                raise ContractError("frame body exceeds configured limit")
            body_start = marker + 4
            frame_end = body_start + size
            if len(self.buffer) < frame_end:
                break
            raw_body = bytes(self.buffer[body_start:frame_end])
            del self.buffer[:frame_end]
            try:
                _check_json_depth(raw_body)
                body = raw_body.decode("utf-8")
                message = json.loads(body, object_pairs_hook=_unique_object)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ContractError("invalid UTF-8 or JSON body") from exc
            messages.append(_valid_rpc_message(message))
        return messages

    def finish(self):
        if self.buffer:
            raise ContractError("truncated frame at end of stream")


def encode_frame(message):
    body = json.dumps(message, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if len(body) > MAX_FRAME_BYTES:
        raise ContractError("frame body exceeds configured limit")
    return b"Content-Length: " + str(len(body)).encode("ascii") + b"\r\n\r\n" + body


class RequestTracker:
    """Correlation and cancellation rules, independent of process transport."""

    def __init__(self, max_pending=MAX_PENDING_REQUESTS):
        if max_pending < 1:
            raise ValueError("invalid pending request limit")
        self.max_pending = max_pending
        self.pending = set()
        self.cancelled = set()

    def begin(self, request_id):
        if isinstance(request_id, bool) or not isinstance(request_id, (int, str)):
            raise ContractError("invalid request id")
        if request_id in self.pending:
            raise ContractError("duplicate in-flight request id")
        if len(self.pending) >= self.max_pending:
            raise ContractError("pending request queue is full")
        self.cancelled.discard(request_id)
        self.pending.add(request_id)

    def cancel(self, request_id):
        if request_id not in self.pending:
            return False
        self.pending.remove(request_id)
        self.cancelled.add(request_id)
        return True

    def resolve(self, request_id):
        if request_id not in self.pending:
            return False
        self.pending.remove(request_id)
        return True


class DiagnosticVersions:
    """Prevents older compiler publications replacing newer open-buffer state."""

    def __init__(self, max_documents=MAX_OPEN_DOCUMENTS):
        self.max_documents = max_documents
        self.latest = {}

    def accept(self, uri, version):
        if not isinstance(uri, str) or not uri:
            raise ContractError("diagnostic URI must be non-empty")
        if isinstance(version, bool) or not isinstance(version, int) or version < 0:
            raise ContractError("diagnostic version must be a non-negative integer")
        if uri not in self.latest and len(self.latest) >= self.max_documents:
            raise ContractError("open-document diagnostic table is full")
        previous = self.latest.get(uri, -1)
        if version < previous:
            return False
        self.latest[uri] = version
        return True

    def close(self, uri):
        self.latest.pop(uri, None)


@dataclass(frozen=True)
class StartRequest:
    executable_identity: str
    argv: tuple[str, ...]
    working_directory_grant: str
    environment: tuple[tuple[str, str], ...] = ()
    profile: str = "lsp"
    deadline_ms: int = 30_000
    output_limit: int = MAX_RETAINED_OUTPUT

    def validate(self):
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", self.executable_identity):
            raise ContractError("executable must have a valid pinned SHA-256 identity")
        if (not isinstance(self.argv, tuple) or not self.argv or
                any(not isinstance(x, str) or "\x00" in x for x in self.argv) or not self.argv[0]):
            raise ContractError("argv must be a non-empty immutable vector without NUL bytes")
        if len(self.argv) > MAX_ARG_COUNT:
            raise ContractError("argument count exceeds configured limit")
        try:
            if sum(len(arg.encode("utf-8")) + 1 for arg in self.argv) > MAX_ARG_BYTES:
                raise ContractError("aggregate argument bytes exceed configured limit")
        except UnicodeEncodeError as exc:
            raise ContractError("argv must contain valid Unicode") from exc
        if not self.working_directory_grant:
            raise ContractError("working directory grant is required")
        if self.profile not in {"lsp", "check", "build", "test", "fmt"}:
            raise ContractError("unsupported command profile")
        if not 1 <= self.deadline_ms <= 3_600_000:
            raise ContractError("deadline outside profile limits")
        if not 1 <= self.output_limit <= MAX_RETAINED_OUTPUT:
            raise ContractError("output limit outside profile limits")
        if any(not isinstance(k, str) or not isinstance(v, str) or
               not k or "\x00" in k or "\x00" in v for k, v in self.environment):
            raise ContractError("environment entries must be valid NUL-free strings")
        names = [key for key, _ in self.environment]
        if len(names) != len(set(names)):
            raise ContractError("duplicate environment variable")
        if any(key in FORBIDDEN_ENV or key not in ALLOWED_ENV for key in names):
            raise ContractError("environment variable is not permitted")
        try:
            if sum(len(k.encode("utf-8")) + len(v.encode("utf-8")) + 2
                   for k, v in self.environment) > 8192:
                raise ContractError("environment profile exceeds configured limit")
        except UnicodeEncodeError as exc:
            raise ContractError("environment must contain valid Unicode") from exc


class FakeClock:
    def __init__(self):
        self.now_ms = 0

    def advance(self, delta_ms):
        if delta_ms < 0:
            raise ContractError("monotonic clock cannot move backwards")
        self.now_ms += delta_ms


class ProcessState(Enum):
    RUNNING = auto()
    TERMINATION_REQUESTED = auto()
    KILL_REQUESTED = auto()
    EXITED = auto()
    REAPED = auto()


@dataclass
class FakeChild:
    pid: int
    request: StartRequest
    exit_code: int | None = None
    state: ProcessState = ProcessState.RUNNING
    events: list[str] = field(default_factory=list)


class FakeBackend:
    """A deterministic OS boundary double. It never launches a real process."""

    def __init__(self, clock):
        self.clock = clock
        self.children = {}
        self.next_pid = 100
        self.events = []

    def spawn(self, request):
        request.validate()
        child = FakeChild(self.next_pid, request)
        self.next_pid += 1
        self.children[child.pid] = child
        self.events.append(("spawn", child.pid, request.executable_identity, request.argv))
        return child

    def terminate(self, child, force=False):
        if child.state in (ProcessState.EXITED, ProcessState.REAPED):
            return
        child.state = ProcessState.KILL_REQUESTED if force else ProcessState.TERMINATION_REQUESTED
        event = "kill" if force else "terminate"
        child.events.append(event)
        self.events.append((event, child.pid))
        if force:
            child.exit_code = -9

    def observe_exit(self, child, exit_code):
        if child.state is ProcessState.REAPED:
            raise ContractError("cannot change a reaped process")
        child.exit_code = exit_code
        child.state = ProcessState.EXITED

    def reap(self, child):
        if child.exit_code is None:
            raise ContractError("cannot reap before exit is observed")
        if child.state is ProcessState.REAPED:
            raise ContractError("process reaped more than once")
        child.state = ProcessState.REAPED
        self.events.append(("reap", child.pid, child.exit_code))
        return child.exit_code


@dataclass
class SupervisedProcess:
    child: FakeChild
    deadline_ms: int
    output_limit: int
    grace_ms: int
    retained_output: bytearray = field(default_factory=bytearray)
    terminal_reason: str | None = None
    kill_deadline_ms: int | None = None
    exit_code: int | None = None


class ProcessSupervisorModel:
    """Reference state-machine model; the production adapter is not implemented here."""

    def __init__(self, backend, clock, grace_ms=250):
        self.backend = backend
        self.clock = clock
        self.grace_ms = grace_ms
        self.active = {}

    def start(self, request):
        request.validate()
        if len(self.active) >= MAX_ACTIVE_PROCESSES:
            raise ContractError("active process budget exhausted")
        child = self.backend.spawn(request)
        process = SupervisedProcess(child, self.clock.now_ms + request.deadline_ms,
                                    request.output_limit, self.grace_ms)
        self.active[child.pid] = process
        return process

    def output(self, process, data):
        if process.child.state is not ProcessState.RUNNING:
            return
        room = process.output_limit - len(process.retained_output)
        if len(data) > room:
            process.retained_output.extend(data[:max(0, room)])
            self._request_termination(process, "output_limit")
        else:
            process.retained_output.extend(data)

    def cancel(self, process):
        if process.terminal_reason is None and process.child.state is ProcessState.RUNNING:
            self._request_termination(process, "cancelled")

    def _request_termination(self, process, reason):
        if process.terminal_reason is not None:
            return
        process.terminal_reason = reason
        process.kill_deadline_ms = self.clock.now_ms + process.grace_ms
        self.backend.terminate(process.child)

    def tick(self, process):
        if process.child.state is ProcessState.REAPED:
            return
        # Observe an already-exited child before applying timeout/cancellation.
        # This makes exit-vs-deadline races deterministic and avoids relabelling
        # an exit that happened first as a timeout.
        if process.child.exit_code is not None:
            self._reap(process)
            return
        if process.terminal_reason is None and self.clock.now_ms >= process.deadline_ms:
            self._request_termination(process, "timeout")
        if (process.child.state is ProcessState.TERMINATION_REQUESTED and
                process.kill_deadline_ms is not None and
                self.clock.now_ms >= process.kill_deadline_ms):
            self.backend.terminate(process.child, force=True)
        if process.child.exit_code is not None:
            self._reap(process)

    def _reap(self, process):
        process.exit_code = self.backend.reap(process.child)
        process.child.state = ProcessState.REAPED
        if process.terminal_reason is None:
            process.terminal_reason = "exited"
        self.active.pop(process.child.pid, None)


def restart_delay_ms(failures, base_ms=100, cap_ms=5000):
    if failures < 0:
        raise ContractError("failure count cannot be negative")
    return min(cap_ms, base_ms * (2 ** min(failures, 30)))


class RestartPolicy:
    """Bounded restart budget with reset only after a stable healthy interval."""

    def __init__(self, max_restarts=3, base_ms=100, cap_ms=5000):
        if max_restarts < 0 or base_ms < 1 or cap_ms < base_ms:
            raise ContractError("invalid restart policy limits")
        self.max_restarts = max_restarts
        self.base_ms = base_ms
        self.cap_ms = cap_ms
        self.failures = 0

    def record_failure(self):
        if self.failures >= self.max_restarts:
            return None
        delay = restart_delay_ms(self.failures, self.base_ms, self.cap_ms)
        self.failures += 1
        return delay

    def record_healthy(self):
        self.failures = 0


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.backend = FakeBackend(self.clock)
        self.supervisor = ProcessSupervisorModel(self.backend, self.clock)

    def request(self, **overrides):
        fields = dict(executable_identity="sha256:" + "a" * 64,
                      argv=("lsp", "--stdio"), working_directory_grant="workspace-root",
                      environment=(("LANG", "C.UTF-8"),), profile="lsp",
                      deadline_ms=1000, output_limit=16)
        fields.update(overrides)
        return StartRequest(**fields)

    def test_argv_is_vector_and_shell_is_not_an_execution_mode(self):
        request = self.request(argv=("check", "a file.cap", "$(touch pwned)"))
        request.validate()
        self.assertEqual(request.argv[1], "a file.cap")
        self.assertEqual(len(self.backend.events), 0)
        with self.assertRaises(ContractError):
            self.request(argv="capstan check file.cap").validate()

    def test_unpinned_executable_and_ambient_environment_rejected(self):
        with self.assertRaises(ContractError):
            self.request(executable_identity="/usr/bin/capstan").validate()
        with self.assertRaises(ContractError):
            self.request(executable_identity="sha256:not-a-digest").validate()
        with self.assertRaises(ContractError):
            self.request(argv=("capstan\x00",)).validate()
        for name in ("PATH", "LD_PRELOAD", "DYLD_INSERT_LIBRARIES"):
            with self.subTest(name=name), self.assertRaises(ContractError):
                self.request(environment=((name, "attacker-value"),)).validate()
        with self.assertRaises(ContractError):
            self.request(environment=(("LANG", "C\x00.UTF-8"),)).validate()

    def test_output_is_bounded_and_triggers_termination(self):
        process = self.supervisor.start(self.request(output_limit=8))
        self.supervisor.output(process, b"123456")
        self.supervisor.output(process, b"7890")
        self.assertEqual(bytes(process.retained_output), b"12345678")
        self.assertEqual(process.terminal_reason, "output_limit")
        self.assertEqual(process.child.events, ["terminate"])

    def test_cancel_is_not_reported_as_stopped_until_reaped(self):
        process = self.supervisor.start(self.request())
        self.supervisor.cancel(process)
        self.assertEqual(process.child.state, ProcessState.TERMINATION_REQUESTED)
        self.assertIsNone(process.exit_code)
        self.clock.advance(250)
        self.supervisor.tick(process)
        self.assertEqual(process.child.state, ProcessState.KILL_REQUESTED)
        self.assertIsNone(process.exit_code)
        self.supervisor.tick(process)
        self.assertEqual(process.child.state, ProcessState.REAPED)
        self.assertEqual(process.exit_code, -9)
        self.assertEqual([e[0] for e in self.backend.events if e[0] in ("terminate", "kill", "reap")],
                         ["terminate", "kill", "reap"])

    def test_deadline_uses_monotonic_clock_and_reaps(self):
        process = self.supervisor.start(self.request(deadline_ms=20))
        self.clock.advance(19)
        self.supervisor.tick(process)
        self.assertIsNone(process.terminal_reason)
        self.clock.advance(1)
        self.supervisor.tick(process)
        self.assertEqual(process.terminal_reason, "timeout")
        self.clock.advance(250)
        self.supervisor.tick(process)
        self.assertEqual(process.child.state, ProcessState.REAPED)

    def test_natural_exit_is_observed_and_reaped_once(self):
        process = self.supervisor.start(self.request())
        self.backend.observe_exit(process.child, 7)
        self.supervisor.tick(process)
        self.assertEqual(process.exit_code, 7)
        self.assertEqual(process.terminal_reason, "exited")
        self.assertEqual(process.child.state, ProcessState.REAPED)
        with self.assertRaises(ContractError):
            self.backend.reap(process.child)

    def test_exit_wins_race_with_deadline_and_late_cancel(self):
        process = self.supervisor.start(self.request(deadline_ms=1))
        self.clock.advance(1)
        self.backend.observe_exit(process.child, 0)
        self.supervisor.cancel(process)
        self.supervisor.tick(process)
        self.assertEqual(process.terminal_reason, "exited")
        self.assertEqual(process.exit_code, 0)
        self.assertEqual(process.child.state, ProcessState.REAPED)
        self.assertFalse(any(event[0] in ("terminate", "kill") for event in self.backend.events))

    def test_restart_backoff_is_bounded(self):
        delays = [restart_delay_ms(n) for n in range(8)]
        self.assertEqual(delays[:4], [100, 200, 400, 800])
        self.assertTrue(all(value <= 5000 for value in delays))
        self.assertEqual(restart_delay_ms(100), 5000)

    def test_crash_is_reaped_and_restart_budget_opens_circuit(self):
        policy = RestartPolicy(max_restarts=3)
        first = self.supervisor.start(self.request())
        self.backend.observe_exit(first.child, 1)
        self.supervisor.tick(first)
        self.assertEqual(first.child.state, ProcessState.REAPED)
        self.assertEqual(first.exit_code, 1)
        self.assertEqual(policy.record_failure(), 100)
        self.assertEqual(policy.record_failure(), 200)
        self.assertEqual(policy.record_failure(), 400)
        self.assertIsNone(policy.record_failure())
        policy.record_healthy()
        self.assertEqual(policy.record_failure(), 100)

    def test_fragmented_and_coalesced_json_rpc_frames(self):
        first = encode_frame({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        second = encode_frame({"jsonrpc": "2.0", "method": "initialized"})
        decoder = BoundedFrameDecoder()
        self.assertEqual(decoder.feed(first[:7]), [])
        self.assertEqual(decoder.feed(first[7:] + second), [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize"},
            {"jsonrpc": "2.0", "method": "initialized"}])
        decoder.finish()

    def test_duplicate_length_malformed_length_and_oversize_rejected(self):
        cases = [
            b"Content-Length: 2\r\nContent-Length: 2\r\n\r\n{}",
            b"Content-Length: -1\r\n\r\n",
            b"Content-Length: 99999999999\r\n\r\n",
            b"Content-Length: 33\r\n\r\n{}",
        ]
        for raw in cases:
            with self.subTest(raw=raw), self.assertRaises(ContractError):
                BoundedFrameDecoder(max_body=32).feed(raw)

    def test_bad_json_duplicate_keys_and_truncated_frames_rejected(self):
        for raw in (b"Content-Length: 1\r\n\r\n{",
                    b'Content-Length: 25\r\n\r\n{"jsonrpc":"2.0","id":1',
                    b'Content-Length: 33\r\n\r\n{"jsonrpc":"2.0","jsonrpc":"2.0"}'):
            decoder = BoundedFrameDecoder()
            with self.subTest(raw=raw), self.assertRaises(ContractError):
                decoder.feed(raw)
                decoder.finish()

    def test_request_correlation_duplicate_ids_late_reply_and_queue_limit(self):
        tracker = RequestTracker(max_pending=1)
        tracker.begin(41)
        with self.assertRaises(ContractError):
            tracker.begin(42)
        with self.assertRaises(ContractError):
            tracker.begin(41)
        self.assertTrue(tracker.cancel(41))
        self.assertFalse(tracker.resolve(41))
        tracker.begin(41)
        self.assertTrue(tracker.resolve(41))
        self.assertFalse(tracker.resolve(41))

    def test_stale_diagnostics_do_not_replace_newer_buffer_version(self):
        versions = DiagnosticVersions()
        self.assertTrue(versions.accept("file:///workspace/main.cap", 8))
        self.assertFalse(versions.accept("file:///workspace/main.cap", 7))
        self.assertEqual(versions.latest["file:///workspace/main.cap"], 8)
        self.assertTrue(versions.accept("file:///workspace/main.cap", 9))
        versions.close("file:///workspace/main.cap")
        self.assertNotIn("file:///workspace/main.cap", versions.latest)

    def test_document_table_and_process_count_are_bounded(self):
        versions = DiagnosticVersions(max_documents=1)
        self.assertTrue(versions.accept("file:///one.cap", 1))
        with self.assertRaises(ContractError):
            versions.accept("file:///two.cap", 1)
        processes = [self.supervisor.start(self.request()) for _ in range(MAX_ACTIVE_PROCESSES)]
        with self.assertRaises(ContractError):
            self.supervisor.start(self.request())
        for process in processes:
            self.backend.observe_exit(process.child, 0)
            self.supervisor.tick(process)

    def test_json_nesting_is_bounded(self):
        body = b'{"jsonrpc":"2.0","method":"x","params":' + b'[' * (MAX_JSON_DEPTH + 1) + b'0' + b']' * (MAX_JSON_DEPTH + 1) + b'}'
        raw = b"Content-Length: " + str(len(body)).encode("ascii") + b"\r\n\r\n" + body
        with self.assertRaises(ContractError):
            BoundedFrameDecoder().feed(raw)

    def test_monotonic_clock_cannot_move_backwards(self):
        with self.assertRaises(ContractError):
            self.clock.advance(-1)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ContractTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
