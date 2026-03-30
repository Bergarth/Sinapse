"""Windows operator service.

Current scope intentionally stays read-only and safe:
- enumerate visible top-level windows

Mutating actions are still placeholders.
"""

from __future__ import annotations

import ctypes
import os
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class OperatorAvailability:
    """Availability snapshot for the windows operator capability."""

    is_available: bool
    detail: str


@dataclass(frozen=True)
class OperatorActionResult:
    """Result object for operator actions."""

    is_success: bool
    detail: str
    payload: list[dict[str, Any]] | None = None


@dataclass(frozen=True)
class TopLevelWindow:
    """Read-only summary for one visible top-level window."""

    window_id: int
    title: str
    class_name: str


class WindowsOperatorService:
    """Windows operator service.

    Read-only actions are implemented first. Mutating actions remain blocked.
    """

    name = "windows-operator"

    def availability(self) -> OperatorAvailability:
        if os.name != "nt":
            return OperatorAvailability(
                is_available=False,
                detail="Windows operator is only available when the daemon runs on Windows.",
            )

        return OperatorAvailability(
            is_available=True,
            detail="Windows operator is available for read-only window enumeration.",
        )

    def enumerate_open_windows(self) -> OperatorActionResult:
        if os.name != "nt":
            return OperatorActionResult(
                is_success=False,
                detail="This read-only action requires Windows.",
                payload=[],
            )

        user32 = ctypes.windll.user32
        windows: list[TopLevelWindow] = []

        enum_windows_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

        def _enum_callback(hwnd, _lparam):
            if not user32.IsWindowVisible(hwnd):
                return True
            title_length = user32.GetWindowTextLengthW(hwnd)
            if title_length <= 0:
                return True

            title_buffer = ctypes.create_unicode_buffer(title_length + 1)
            user32.GetWindowTextW(hwnd, title_buffer, title_length + 1)
            title = title_buffer.value.strip()
            if not title:
                return True

            class_buffer = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, class_buffer, len(class_buffer))
            windows.append(
                TopLevelWindow(
                    window_id=int(hwnd),
                    title=title,
                    class_name=class_buffer.value.strip(),
                )
            )
            return True

        if not user32.EnumWindows(enum_windows_proc(_enum_callback), 0):
            return OperatorActionResult(
                is_success=False,
                detail="Windows API call failed while enumerating top-level windows.",
                payload=[],
            )

        windows.sort(key=lambda item: item.title.lower())
        return OperatorActionResult(
            is_success=True,
            detail=f"Found {len(windows)} visible top-level window(s).",
            payload=[
                {
                    "window_id": window.window_id,
                    "title": window.title,
                    "class_name": window.class_name,
                }
                for window in windows
            ],
        )

    def observe_window(self, *, window_ref: str) -> OperatorActionResult:
        _ = window_ref
        return OperatorActionResult(False, "Not implemented yet: observe_window", payload=None)

    def focus_window(self, *, window_ref: str) -> OperatorActionResult:
        _ = window_ref
        return OperatorActionResult(False, "Read-only mode: focus_window is disabled.", payload=None)

    def invoke_control(self, *, window_ref: str, control_ref: str, action: str) -> OperatorActionResult:
        _ = (window_ref, control_ref, action)
        return OperatorActionResult(False, "Read-only mode: invoke_control is disabled.", payload=None)

    def set_text(self, *, window_ref: str, control_ref: str, text: str) -> OperatorActionResult:
        _ = (window_ref, control_ref, text)
        return OperatorActionResult(False, "Read-only mode: set_text is disabled.", payload=None)

    def send_keys(self, *, window_ref: str, keys: str) -> OperatorActionResult:
        _ = (window_ref, keys)
        return OperatorActionResult(False, "Read-only mode: send_keys is disabled.", payload=None)

    def capture_region(self, *, window_ref: str, region: str) -> OperatorActionResult:
        _ = (window_ref, region)
        return OperatorActionResult(False, "Not implemented yet: capture_region", payload=None)
