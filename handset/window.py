"""Windows API helpers to make Chrome frameless and draggable."""

from __future__ import annotations

import ctypes
import time
from threading import Thread

_user32 = ctypes.windll.user32


def find_pane_hwnd() -> int | None:
    found = None

    def enum_cb(hwnd, _):
        nonlocal found
        if not _user32.IsWindowVisible(hwnd):
            return True
        length = _user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buff = ctypes.create_unicode_buffer(length + 1)
            _user32.GetWindowTextW(hwnd, buff, length + 1)
            if "Pane" in buff.value:
                class_buff = ctypes.create_unicode_buffer(256)
                _user32.GetClassNameW(hwnd, class_buff, 256)
                if "Chrome" in class_buff.value or "Widget" in class_buff.value:
                    found = hwnd
                    return False
        return True

    CMPFUNC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    _user32.EnumWindows(CMPFUNC(enum_cb), 0)
    return found


def strip_window_caption() -> bool:
    hwnd = find_pane_hwnd()
    if not hwnd:
        return False
    GWL_STYLE = -16
    WS_CAPTION = 0x00C00000
    SWP_FRAMECHANGED = 0x0020
    SWP_NOMOVE = 0x0002
    SWP_NOSIZE = 0x0001
    SWP_NOZORDER = 0x0004
    style = _user32.GetWindowLongW(hwnd, GWL_STYLE)
    if style & WS_CAPTION:
        style &= ~WS_CAPTION
        _user32.SetWindowLongW(hwnd, GWL_STYLE, style)
        _user32.SetWindowPos(
            hwnd, 0, 0, 0, 0, 0, SWP_FRAMECHANGED | SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER
        )
    return True


def start_caption_stripper(max_duration: float = 10.0) -> None:
    def _worker():
        start = time.time()
        while time.time() - start < max_duration:
            if strip_window_caption():
                # Apply a couple more times to ensure Chrome finishes drawing
                for _ in range(5):
                    time.sleep(0.3)
                    strip_window_caption()
                break
            time.sleep(0.2)

    Thread(target=_worker, name="caption-stripper", daemon=True).start()


def window_action(action: str, width: int = 0, height: int = 0) -> bool:
    hwnd = find_pane_hwnd()
    if not hwnd:
        return False
    if action == "drag":
        _user32.ReleaseCapture()
        _user32.SendMessageW(hwnd, 0x0112, 0xF012, 0)
        return True
    if action == "minimize":
        _user32.ShowWindow(hwnd, 6)
        return True
    if action == "close":
        _user32.PostMessageW(hwnd, 0x0010, 0, 0)
        return True
    if action == "resize" and width and height:
        SWP_NOMOVE = 0x0002
        SWP_NOZORDER = 0x0004
        _user32.SetWindowPos(hwnd, 0, 0, 0, int(width), int(height), SWP_NOMOVE | SWP_NOZORDER)
        return True
    return False

