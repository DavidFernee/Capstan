#!/usr/bin/env python3
"""Deterministic reference model for Shroud's optional GPU backend contract.

This is deliberately not a GPU driver or a rendering implementation. It pins
selection, capability validation, resource accounting and device-loss fallback
semantics until Shroud has an immutable display list and a reviewed host API.
"""
from dataclasses import dataclass
from enum import Enum, auto
import unittest


class Backend(Enum):
    SOFTWARE = auto()
    GPU = auto()


class Policy(Enum):
    SOFTWARE_ONLY = auto()
    PREFER_GPU = auto()
    REQUIRE_GPU = auto()


class DeviceState(Enum):
    READY = auto()
    LOST = auto()
    CLOSED = auto()


@dataclass(frozen=True)
class Capabilities:
    api_version: int
    integer_targets: bool
    premultiplied_alpha: bool
    max_width: int
    max_height: int
    max_pixels: int
    device_budget_bytes: int


@dataclass(frozen=True)
class Request:
    width: int
    height: int
    estimated_resource_bytes: int
    policy: Policy = Policy.PREFER_GPU


@dataclass(frozen=True)
class Selection:
    backend: Backend
    reason: str


def _valid_dimensions(width: int, height: int, max_width: int,
                      max_height: int, max_pixels: int) -> bool:
    if min(width, height, max_width, max_height, max_pixels) < 1:
        return False
    if width > max_width or height > max_height:
        return False
    # Division-based check mirrors the overflow-safe Capstan contract.
    return width <= max_pixels // height


def select_backend(request: Request, caps: Capabilities | None,
                   state: DeviceState) -> Selection:
    if request.width < 1 or request.height < 1:
        raise ValueError("invalid surface dimensions")
    if request.estimated_resource_bytes < 0:
        raise ValueError("negative resource estimate")
    if request.policy is Policy.SOFTWARE_ONLY:
        return Selection(Backend.SOFTWARE, "software explicitly requested")
    reason = None
    if caps is None:
        reason = "no GPU capability record"
    elif state is not DeviceState.READY:
        reason = "GPU device is not ready"
    elif caps.api_version < 1:
        reason = "unsupported GPU API version"
    elif not caps.integer_targets or not caps.premultiplied_alpha:
        reason = "required pixel semantics are unavailable"
    elif not _valid_dimensions(request.width, request.height,
                               caps.max_width, caps.max_height,
                               caps.max_pixels):
        reason = "surface exceeds GPU dimensions or pixel budget"
    elif request.estimated_resource_bytes > caps.device_budget_bytes:
        reason = "GPU resource budget exceeded"
    if reason is None:
        return Selection(Backend.GPU, "GPU capabilities satisfy request")
    if request.policy is Policy.REQUIRE_GPU:
        raise RuntimeError(reason)
    return Selection(Backend.SOFTWARE, reason)


class Device:
    """Small lifecycle model; resource charges are explicit and failure-atomic."""
    def __init__(self, budget: int):
        if budget < 0:
            raise ValueError("negative device budget")
        self.budget = budget
        self.used = 0
        self.state = DeviceState.READY

    def reserve(self, amount: int) -> bool:
        if amount < 0:
            raise ValueError("negative resource charge")
        if self.state is not DeviceState.READY:
            return False
        if amount > self.budget - self.used:
            return False
        self.used += amount
        return True

    def release(self, amount: int) -> None:
        if amount < 0 or amount > self.used:
            raise ValueError("invalid resource release")
        self.used -= amount

    def lose(self) -> None:
        if self.state is DeviceState.READY:
            self.state = DeviceState.LOST
            self.used = 0  # device-owned resources cease to be addressable

    def close(self) -> None:
        self.state = DeviceState.CLOSED
        self.used = 0


class GpuContractTests(unittest.TestCase):
    def setUp(self):
        self.caps = Capabilities(1, True, True, 8192, 8192,
                                 16_777_216, 64 * 1024 * 1024)
        self.request = Request(1280, 720, 8 * 1024 * 1024)

    def test_compatible_device_is_selected(self):
        self.assertEqual(select_backend(self.request, self.caps,
                                        DeviceState.READY).backend, Backend.GPU)

    def test_software_only_never_probes_gpu(self):
        req = Request(1280, 720, 0, Policy.SOFTWARE_ONLY)
        self.assertEqual(select_backend(req, None, DeviceState.CLOSED).backend,
                         Backend.SOFTWARE)

    def test_absent_or_lost_device_falls_back(self):
        self.assertEqual(select_backend(self.request, None, DeviceState.READY).backend,
                         Backend.SOFTWARE)
        self.assertEqual(select_backend(self.request, self.caps, DeviceState.LOST).backend,
                         Backend.SOFTWARE)

    def test_required_gpu_fails_closed(self):
        req = Request(1280, 720, 1, Policy.REQUIRE_GPU)
        with self.assertRaises(RuntimeError):
            select_backend(req, None, DeviceState.READY)

    def test_semantic_capabilities_are_mandatory(self):
        caps = Capabilities(1, False, True, 8192, 8192, 16_777_216, 1_000_000)
        self.assertEqual(select_backend(self.request, caps, DeviceState.READY).backend,
                         Backend.SOFTWARE)

    def test_pixel_budget_uses_division_check(self):
        self.assertFalse(_valid_dimensions(8192, 8192, 8192, 8192, 16_777_216 - 1))
        self.assertTrue(_valid_dimensions(4096, 4096, 8192, 8192, 16_777_216))

    def test_resource_budget_falls_back_or_rejects(self):
        caps = Capabilities(1, True, True, 8192, 8192, 16_777_216, 1024)
        self.assertEqual(select_backend(self.request, caps, DeviceState.READY).backend,
                         Backend.SOFTWARE)
        req = Request(1280, 720, 2048, Policy.REQUIRE_GPU)
        with self.assertRaises(RuntimeError):
            select_backend(req, caps, DeviceState.READY)

    def test_invalid_dimensions_and_charges_are_rejected(self):
        with self.assertRaises(ValueError):
            select_backend(Request(0, 10, 0), self.caps, DeviceState.READY)
        with self.assertRaises(ValueError):
            select_backend(Request(10, 10, -1), self.caps, DeviceState.READY)

    def test_reservation_is_failure_atomic(self):
        device = Device(100)
        self.assertTrue(device.reserve(60))
        self.assertFalse(device.reserve(41))
        self.assertEqual(device.used, 60)
        device.release(60)
        self.assertEqual(device.used, 0)

    def test_release_cannot_underflow(self):
        device = Device(100)
        with self.assertRaises(ValueError):
            device.release(1)

    def test_device_loss_invalidates_resources_and_stops_admission(self):
        device = Device(100)
        self.assertTrue(device.reserve(80))
        device.lose()
        self.assertEqual(device.used, 0)
        self.assertFalse(device.reserve(1))
        self.assertEqual(device.state, DeviceState.LOST)

    def test_close_is_idempotent(self):
        device = Device(100)
        device.reserve(20)
        device.close()
        device.close()
        self.assertEqual(device.used, 0)
        self.assertFalse(device.reserve(1))


if __name__ == "__main__":
    unittest.main(verbosity=2)
