"""Windows operator service.

Current scope intentionally stays safety-scoped:
- enumerate visible top-level windows (read-only)
- launch applications by app name or executable path
- focus an existing window
- open a local file with its default app
- type text into the focused target (or a matched window)

Destructive and arbitrary command execution capabilities are intentionally out of scope.
"""

from __future__ import annotations

import ctypes
import os
import subprocess
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
    payload: Any | None = None


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
            detail=(
                "Windows operator is available for safe actions: enumerate windows, launch app, "
                "focus window, open file, and type text."
            ),
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

    def launch_application(self, *, app_name: str | None = None, executable_path: str | None = None) -> OperatorActionResult:
        if os.name != "nt":
            return OperatorActionResult(False, "This action requires Windows.", payload=None)

        requested = (executable_path or app_name or "").strip()
        if not requested:
            return OperatorActionResult(False, "Please provide an app name or executable path.", payload=None)

        try:
            if executable_path and executable_path.strip():
                os.startfile(executable_path.strip())  # type: ignore[attr-defined]
                launched_target = executable_path.strip()
            else:
                subprocess.Popen(requested, shell=False)  # noqa: S603
                launched_target = requested
        except Exception as exc:  # noqa: BLE001
            return OperatorActionResult(False, f"Could not launch application: {exc}", payload=None)

        return OperatorActionResult(
            True,
            f"Launched application: {launched_target}",
            payload={"launched": launched_target},
        )

    def focus_window(self, *, window_ref: str) -> OperatorActionResult:
        if os.name != "nt":
            return OperatorActionResult(False, "This action requires Windows.", payload=None)
        requested = window_ref.strip()
        if not requested:
            return OperatorActionResult(False, "Please provide a window title or process hint.", payload=None)

        matched = self._find_window_handle(requested)
        if matched is None:
            return OperatorActionResult(False, f"No visible window matched '{requested}'.", payload=None)

        hwnd, title = matched
        user32 = ctypes.windll.user32
        user32.ShowWindow(hwnd, 5)  # SW_SHOW
        if not user32.SetForegroundWindow(hwnd):
            return OperatorActionResult(False, f"Found '{title}', but could not focus it.", payload=None)

        return OperatorActionResult(
            True,
            f"Focused window: {title}",
            payload={"window_id": int(hwnd), "title": title},
        )

    def open_file(self, *, file_path: str) -> OperatorActionResult:
        if os.name != "nt":
            return OperatorActionResult(False, "This action requires Windows.", payload=None)
        requested = file_path.strip().strip('"')
        if not requested:
            return OperatorActionResult(False, "Please provide a file path.", payload=None)
        if not os.path.isfile(requested):
            return OperatorActionResult(False, f"File not found: {requested}", payload=None)

        try:
            os.startfile(requested)  # type: ignore[attr-defined]
        except Exception as exc:  # noqa: BLE001
            return OperatorActionResult(False, f"Could not open file: {exc}", payload=None)

        return OperatorActionResult(True, f"Opened file: {requested}", payload={"file_path": requested})

    def type_text(self, *, target: str, text: str) -> OperatorActionResult:
        if os.name != "nt":
            return OperatorActionResult(False, "This action requires Windows.", payload=None)
        normalized_target = target.strip().lower()
        content = text
        if not content:
            return OperatorActionResult(False, "Please provide text to type.", payload=None)

        if normalized_target not in {"focused", "focused field", "active", "current"}:
            focused = self.focus_window(window_ref=target)
            if not focused.is_success:
                return OperatorActionResult(False, focused.detail, payload=None)

        try:
            self._send_unicode_text(content)
        except Exception as exc:  # noqa: BLE001
            return OperatorActionResult(False, f"Could not type text: {exc}", payload=None)

        return OperatorActionResult(
            True,
            "Typed text into the active target.",
            payload={"target": target, "typed_length": len(content)},
        )

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

    def _find_window_handle(self, requested: str) -> tuple[int, str] | None:
        requested_lower = requested.lower()
        windows = self.enumerate_open_windows().payload or []
        for window in windows:
            title = str(window.get("title", ""))
            class_name = str(window.get("class_name", ""))
            if requested_lower in title.lower() or requested_lower in class_name.lower():
                return int(window["window_id"]), title
        return None

    @staticmethod
    def _send_unicode_text(text: str) -> None:
        KEYEVENTF_UNICODE = 0x0004
        KEYEVENTF_KEYUP = 0x0002
        INPUT_KEYBOARD = 1

        class KEYBDINPUT(ctypes.Structure):
            _fields_ = [
                ("wVk", ctypes.c_ushort),
                ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_uint),
                ("time", ctypes.c_uint),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
            ]

        class INPUT(ctypes.Structure):
            class _INPUT(ctypes.Union):
                _fields_ = [("ki", KEYBDINPUT)]

            _anonymous_ = ("i",)
            _fields_ = [("type", ctypes.c_uint), ("i", _INPUT)]

        user32 = ctypes.windll.user32
        for char in text:
            scan_code = ord(char)
            key_down = INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(0, scan_code, KEYEVENTF_UNICODE, 0, None))
            key_up = INPUT(
                type=INPUT_KEYBOARD,
                ki=KEYBDINPUT(0, scan_code, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0, None),
            )
            user32.SendInput(1, ctypes.byref(key_down), ctypes.sizeof(INPUT))
            user32.SendInput(1, ctypes.byref(key_up), ctypes.sizeof(INPUT))
