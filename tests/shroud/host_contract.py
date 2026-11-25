#!/usr/bin/env python3
"""Deterministic Shroud S1 host-contract reference model; not a native backend."""
import struct
import unittest
from dataclasses import dataclass
from enum import Enum, auto

MAX_MESSAGE = 65532  # Wayland's 16-bit size field, rounded down to 4-byte alignment
MAX_BUFFERED = 4 << 20
MAX_POOL_BYTES = 128 << 20
MAX_DIMENSION = 8192
MAX_BUFFER_BYTES = 64 << 20
UINT32_MAX = (1 << 32) - 1


class ProtocolError(ValueError):
    pass


@dataclass(frozen=True)
class Message:
    object_id: int
    opcode: int
    payload: bytes = b""

    def encode(self):
        size = 8 + len(self.payload)
        if not 1 <= self.object_id <= UINT32_MAX or not 0 <= self.opcode <= 65535:
            raise ProtocolError("invalid header field")
        if size > MAX_MESSAGE or size & 3:
            raise ProtocolError("invalid message size")
        return struct.pack("<II", self.object_id, (size << 16) | self.opcode) + self.payload


class StreamDecoder:
    def __init__(self, max_message=MAX_MESSAGE, max_buffered=MAX_BUFFERED):
        if max_message < 8 or max_message > MAX_MESSAGE or max_message & 3:
            raise ValueError("invalid message budget")
        if max_buffered < max_message or max_buffered > MAX_BUFFERED:
            raise ValueError("invalid stream budget")
        self.limit, self.budget = max_message, max_buffered
        self.buffer, self.failed = bytearray(), False

    def feed(self, data):
        if self.failed:
            raise ProtocolError("decoder failed")
        if not isinstance(data, bytes):
            raise TypeError("input must be bytes")
        if len(data) > self.budget - len(self.buffer):
            self.failed = True
            raise ProtocolError("buffer budget exceeded")
        self.buffer.extend(data)
        result = []
        try:
            while len(self.buffer) >= 8:
                obj, word = struct.unpack_from("<II", self.buffer)
                size, opcode = word >> 16, word & 65535
                if obj == 0:
                    raise ProtocolError("zero object id")
                if size < 8 or size & 3 or size > self.limit:
                    raise ProtocolError("invalid declared size")
                if size > self.budget:
                    raise ProtocolError("declared size exceeds stream budget")
                if len(self.buffer) < size:
                    break
                result.append(Message(obj, opcode, bytes(self.buffer[8:size])))
                del self.buffer[:size]
        except ProtocolError:
            self.failed = True
            self.buffer.clear()
            raise
        return result

    def eof(self):
        if self.buffer:
            self.failed = True
            self.buffer.clear()
            raise ProtocolError("truncated stream")


class ObjectTable:
    def __init__(self):
        self.objects = {}

    def add(self, object_id, interface, version):
        if not 1 <= object_id <= UINT32_MAX or object_id in self.objects:
            raise ProtocolError("invalid or duplicate object id")
        if not interface or not 1 <= version <= 64:
            raise ProtocolError("invalid interface version")
        self.objects[object_id] = (interface, version)

    def require(self, object_id, interface=None):
        item = self.objects.get(object_id)
        if item is None or (interface is not None and item[0] != interface):
            raise ProtocolError("unknown object or interface mismatch")
        return item

    def remove(self, object_id):
        if object_id not in self.objects:
            raise ProtocolError("destroy of unknown object")
        del self.objects[object_id]


MAX_FDS_PER_MESSAGE = 16


class OwnedHandle:
    _next_id = 1

    def __init__(self, owner):
        self.owner = owner
        self.id = OwnedHandle._next_id
        OwnedHandle._next_id += 1
        self.closed = False

    def duplicate_for(self, owner):
        if self.closed:
            raise ProtocolError("transfer of closed handle")
        return OwnedHandle(owner)

    def close(self):
        self.closed = True


def receive_rights(sender_handles, receiver, max_fds=MAX_FDS_PER_MESSAGE,
                   payload_truncated=False, control_truncated=False):
    """Model SCM_RIGHTS: receiver gets owned duplicates; sender keeps its handles."""
    received = []
    try:
        if len(sender_handles) > max_fds or len(sender_handles) > MAX_FDS_PER_MESSAGE:
            raise ProtocolError("descriptor count exceeds limit")
        for handle in sender_handles:
            received.append(handle.duplicate_for(receiver))
        if payload_truncated or control_truncated:
            raise ProtocolError("truncated ancillary message")
        return received
    except ProtocolError:
        for handle in received:
            handle.close()
        raise


def wait_until_ready(start_ms, deadline_ms, outcomes):
    """Deterministic poll model; EINTR retries against one absolute deadline."""
    now = start_ms
    for outcome, elapsed_ms in outcomes:
        remaining = deadline_ms - now
        if remaining <= 0:
            return False, now
        if elapsed_ms < 0:
            raise ProtocolError("negative wait duration")
        if elapsed_ms >= remaining:
            return False, deadline_ms
        now += elapsed_ms
        if outcome == "EINTR":
            continue
        if outcome == "READY":
            return True, now
        if outcome == "ERROR":
            raise ProtocolError("readiness wait failed")
        raise ProtocolError("unknown readiness result")
    return False, min(now, deadline_ms)


class State(Enum):
    DISCONNECTED = auto()
    CONNECTED = auto()
    CONFIGURED = auto()
    CLOSED = auto()
    FAILED = auto()


class BufferState(Enum):
    FREE = auto()
    OWNED = auto()


@dataclass
class Buffer:
    generation: int
    index: int
    byte_length: int
    state: BufferState = BufferState.FREE


@dataclass(frozen=True)
class FrameLease:
    generation: int
    index: int


class HostModel:
    """Single-threaded configure, resize, frame and compositor-lease model."""
    def __init__(self):
        self.state = State.DISCONNECTED
        self.configure_serial = None
        self.acked_serial = None
        self.generation = 0
        self.buffers = {}
        self.rendered_generation = None

    def connect(self):
        if self.state is not State.DISCONNECTED:
            raise ProtocolError("invalid connect state")
        self.state = State.CONNECTED

    def configure(self, serial):
        if self.state not in (State.CONNECTED, State.CONFIGURED) or not 1 <= serial <= UINT32_MAX:
            raise ProtocolError("invalid configure")
        # Wayland serials are opaque uint32 values and may wrap.
        self.configure_serial, self.acked_serial = serial, None
        self.state = State.CONFIGURED

    def ack_configure(self, serial):
        if self.state is not State.CONFIGURED or serial != self.configure_serial:
            raise ProtocolError("ack does not match latest configure")
        self.acked_serial = serial

    @staticmethod
    def buffer_size(width, height):
        if not 1 <= width <= MAX_DIMENSION or not 1 <= height <= MAX_DIMENSION:
            raise ProtocolError("invalid dimensions")
        if width > MAX_BUFFER_BYTES // 4 // height:
            raise ProtocolError("surface byte budget exceeded")
        return width * height * 4

    def resize(self, width, height):
        if self.state is not State.CONFIGURED or self.acked_serial != self.configure_serial:
            raise ProtocolError("resize before configure acknowledgement")
        size = self.buffer_size(width, height)
        # Keep old buffers only while the compositor owns them. Account for
        # retained generations before changing state; a rejected resize is atomic.
        retained = {k: b for k, b in self.buffers.items() if b.state is BufferState.OWNED}
        retained_bytes = sum(b.byte_length for b in retained.values())
        if retained_bytes > MAX_POOL_BYTES - 2 * size:
            raise ProtocolError("aggregate buffer-pool budget exceeded")
        next_generation = self.generation + 1
        for index in range(2):
            retained[(next_generation, index)] = Buffer(next_generation, index, size)
        self.buffers = retained
        self.generation = next_generation
        self.rendered_generation = None

    def render(self):
        if self.state is not State.CONFIGURED or not self.generation:
            raise ProtocolError("render without configured surface")
        self.rendered_generation = self.generation

    def acquire(self):
        if self.rendered_generation != self.generation or self.state is not State.CONFIGURED:
            raise ProtocolError("no current frame")
        for index in range(2):
            b = self.buffers[(self.generation, index)]
            if b.state is BufferState.FREE:
                b.state = BufferState.OWNED
                return FrameLease(self.generation, index)
        raise ProtocolError("all buffers compositor-owned")

    def release(self, lease):
        key = (lease.generation, lease.index)
        b = self.buffers.get(key)
        if b is None or b.state is not BufferState.OWNED:
            raise ProtocolError("unknown, stale or released lease")
        if lease.generation != self.generation:
            del self.buffers[key]
        else:
            b.state = BufferState.FREE

    def dispatch_input(self, generation):
        if (self.state is not State.CONFIGURED or generation != self.generation
                or self.rendered_generation != self.generation):
            raise ProtocolError("input against stale or unrendered surface")

    def disconnect(self):
        if self.state not in (State.CLOSED, State.FAILED):
            self.state = State.FAILED
            self.buffers.clear()
            self.rendered_generation = None

    def close(self):
        if self.state is not State.CLOSED:
            self.state = State.CLOSED
            self.buffers.clear()
            self.rendered_generation = None


class ContractTests(unittest.TestCase):
    def ready(self, width=64, height=64):
        h = HostModel()
        h.connect()
        h.configure(1)
        h.ack_configure(1)
        h.resize(width, height)
        h.render()
        return h

    def test_fragmented_header_and_payload(self):
        wire = Message(7, 3, b"abcd").encode()
        d = StreamDecoder()
        self.assertEqual(d.feed(wire[:3]), [])
        self.assertEqual(d.feed(wire[3:9]), [])
        self.assertEqual(d.feed(wire[9:]), [Message(7, 3, b"abcd")])
        d.eof()

    def test_multiple_messages_per_read(self):
        wire = Message(1, 0).encode() + Message(2, 4, b"1234").encode()
        self.assertEqual(StreamDecoder().feed(wire), [Message(1, 0), Message(2, 4, b"1234")])

    def test_truncated_eof(self):
        d = StreamDecoder()
        d.feed(Message(1, 0, b"abcd").encode()[:10])
        with self.assertRaisesRegex(ProtocolError, "truncated"):
            d.eof()

    def test_bad_headers(self):
        for obj, word in ((0, 8 << 16), (1, 4 << 16), (1, (9 << 16) | 1), (1, 68 << 16)):
            with self.subTest(obj=obj, word=word), self.assertRaises(ProtocolError):
                StreamDecoder(max_message=64).feed(struct.pack("<II", obj, word))

    def test_stream_budget_and_failed_state(self):
        d = StreamDecoder(max_message=64, max_buffered=64)
        with self.assertRaisesRegex(ProtocolError, "budget"):
            d.feed(b"x" * 65)
        with self.assertRaisesRegex(ProtocolError, "failed"):
            d.feed(b"")

    def test_encoder_rejects_unaligned_payload(self):
        with self.assertRaisesRegex(ProtocolError, "size"):
            Message(1, 0, b"x").encode()

    def test_object_ids_and_interfaces(self):
        t = ObjectTable()
        t.add(1, "wl_display", 1)
        self.assertEqual(t.require(1, "wl_display"), ("wl_display", 1))
        with self.assertRaisesRegex(ProtocolError, "duplicate"):
            t.add(1, "wl_surface", 1)
        with self.assertRaisesRegex(ProtocolError, "unknown"):
            t.require(2)
        with self.assertRaisesRegex(ProtocolError, "mismatch"):
            t.require(1, "wl_surface")
        t.remove(1)
        with self.assertRaisesRegex(ProtocolError, "unknown"):
            t.remove(1)

    def test_descriptor_transfer_duplicates_ownership(self):
        sender = [OwnedHandle("sender"), OwnedHandle("sender")]
        received = receive_rights(sender, "receiver")
        self.assertEqual([h.owner for h in sender], ["sender", "sender"])
        self.assertEqual([h.owner for h in received], ["receiver", "receiver"])
        self.assertTrue(all(not h.closed for h in sender + received))
        received[0].close()
        self.assertFalse(sender[0].closed)

    def test_descriptor_transfer_rejects_excess_and_closes_received(self):
        sender = [OwnedHandle("sender") for _ in range(MAX_FDS_PER_MESSAGE + 1)]
        with self.assertRaisesRegex(ProtocolError, "count exceeds"):
            receive_rights(sender, "receiver")
        with self.assertRaisesRegex(ProtocolError, "closed handle"):
            receive_rights([OwnedHandle("sender")], "receiver",
                           payload_truncated=True)

    def test_descriptor_transfer_closes_partial_rights_on_control_truncation(self):
        sender = [OwnedHandle("sender") for _ in range(3)]
        # The helper closes every receiver-side duplicate before surfacing truncation.
        with self.assertRaisesRegex(ProtocolError, "truncated ancillary"):
            receive_rights(sender, "receiver", control_truncated=True)
        self.assertTrue(all(not h.closed for h in sender))

    def test_readiness_wait_retries_eintr_with_absolute_deadline(self):
        ready, now = wait_until_ready(100, 110, [
            ("EINTR", 3), ("EINTR", 3), ("READY", 2)])
        self.assertTrue(ready)
        self.assertEqual(now, 108)

    def test_readiness_wait_does_not_extend_deadline_after_eintr(self):
        ready, now = wait_until_ready(100, 110, [
            ("EINTR", 6), ("EINTR", 6), ("READY", 1)])
        self.assertFalse(ready)
        self.assertEqual(now, 110)

    def test_readiness_wait_rejects_errors_and_negative_durations(self):
        with self.assertRaisesRegex(ProtocolError, "wait failed"):
            wait_until_ready(0, 10, [("ERROR", 1)])
        with self.assertRaisesRegex(ProtocolError, "negative"):
            wait_until_ready(0, 10, [("EINTR", -1)])

    def test_configure_ack_gate_and_serial_wrap(self):
        h = HostModel()
        h.connect()
        with self.assertRaisesRegex(ProtocolError, "acknowledgement"):
            h.resize(10, 10)
        h.configure(UINT32_MAX)
        h.configure(1)
        with self.assertRaisesRegex(ProtocolError, "latest configure"):
            h.ack_configure(UINT32_MAX)
        h.ack_configure(1)
        h.resize(10, 10)

    def test_dimensions_and_overflow_budget(self):
        for dims in ((0, 1), (1, 0), (8193, 1), (8192, 8192)):
            with self.subTest(dims=dims), self.assertRaises(ProtocolError):
                HostModel.buffer_size(*dims)
        self.assertEqual(HostModel.buffer_size(640, 480), 640 * 480 * 4)

    def test_input_requires_render_after_resize(self):
        h = self.ready()
        old = h.generation
        h.resize(80, 80)
        with self.assertRaisesRegex(ProtocolError, "stale or unrendered"):
            h.dispatch_input(old)
        h.render()
        h.dispatch_input(h.generation)

    def test_pool_never_overwrites_owned_buffers(self):
        h = self.ready()
        a, b = h.acquire(), h.acquire()
        with self.assertRaisesRegex(ProtocolError, "compositor-owned"):
            h.acquire()
        h.release(a)
        c = h.acquire()
        self.assertEqual(c.index, a.index)
        h.release(b)
        h.release(c)

    def test_resize_retains_old_buffer_only_until_release(self):
        h = self.ready()
        old = h.acquire()
        h.resize(128, 128)
        h.render()
        new = h.acquire()
        self.assertNotEqual(old.generation, new.generation)
        h.release(old)
        self.assertNotIn((old.generation, old.index), h.buffers)
        h.release(new)

    def test_double_release_and_unknown_lease(self):
        h = self.ready()
        lease = h.acquire()
        h.release(lease)
        with self.assertRaisesRegex(ProtocolError, "released lease"):
            h.release(lease)
        with self.assertRaisesRegex(ProtocolError, "released lease"):
            h.release(FrameLease(999, 0))

    def test_pool_budget_rejects_resize_atomically(self):
        h = self.ready(4096, 4096)
        h.acquire()
        h.acquire()
        generation = h.generation
        keys = set(h.buffers)
        with self.assertRaisesRegex(ProtocolError, "aggregate buffer-pool"):
            h.resize(1, 1)
        self.assertEqual(h.generation, generation)
        self.assertEqual(set(h.buffers), keys)
        self.assertIsNone(h.rendered_generation)

    def test_disconnect_invalidates_leases(self):
        h = self.ready()
        lease = h.acquire()
        h.disconnect()
        with self.assertRaisesRegex(ProtocolError, "released lease"):
            h.release(lease)
        h.disconnect()
        self.assertIs(h.state, State.FAILED)

    def test_close_idempotent(self):
        h = self.ready()
        h.acquire()
        h.close()
        h.close()
        self.assertIs(h.state, State.CLOSED)
        with self.assertRaisesRegex(ProtocolError, "invalid connect"):
            h.connect()


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ContractTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)
    print(f"Shroud host contract: {result.testsRun} tests passed (reference model only)")
