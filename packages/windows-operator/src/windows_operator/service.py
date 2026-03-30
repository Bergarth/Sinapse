"""Windows operator placeholder service.

No real desktop automation is performed yet. This module only exposes the
contract surface that the daemon can wire into capability/status APIs.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OperatorAvailability:
    """Availability snapshot for the windows operator capability."""

    is_available: bool
    detail: str


@dataclass(frozen=True)
class OperatorActionResult:
    """Placeholder result for future operator actions."""

    is_success: bool
    detail: str


class WindowsOperatorService:
    """Placeholder windows operator service.

    This service is intentionally thin: it defines the stable method contracts
    the daemon can call while implementation remains TODO.
    """

    name = "windows-operator"

    def availability(self) -> OperatorAvailability:
        return OperatorAvailability(
            is_available=True,
            detail="Windows operator contract is wired (placeholder implementation).",
        )

    def observe_window(self, *, window_ref: str) -> OperatorActionResult:
        _ = window_ref
        return OperatorActionResult(False, "Not implemented yet: observe_window")

    def focus_window(self, *, window_ref: str) -> OperatorActionResult:
        _ = window_ref
        return OperatorActionResult(False, "Not implemented yet: focus_window")

    def invoke_control(self, *, window_ref: str, control_ref: str, action: str) -> OperatorActionResult:
        _ = (window_ref, control_ref, action)
        return OperatorActionResult(False, "Not implemented yet: invoke_control")

    def set_text(self, *, window_ref: str, control_ref: str, text: str) -> OperatorActionResult:
        _ = (window_ref, control_ref, text)
        return OperatorActionResult(False, "Not implemented yet: set_text")

    def send_keys(self, *, window_ref: str, keys: str) -> OperatorActionResult:
        _ = (window_ref, keys)
        return OperatorActionResult(False, "Not implemented yet: send_keys")

    def capture_region(self, *, window_ref: str, region: str) -> OperatorActionResult:
        _ = (window_ref, region)
        return OperatorActionResult(False, "Not implemented yet: capture_region")
