"""Embedded AirPlay Audio Receiver for Windows."""

from __future__ import annotations

import atexit
import logging
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_PROCESS: subprocess.Popen | None = None


def _find_shairport_bin() -> Path | None:
    candidates = []
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        candidates.append(Path(sys._MEIPASS) / "handset" / "bin" / "shairport.exe")
    candidates.extend(
        [
            Path(__file__).resolve().parent / "bin" / "shairport.exe",
            Path(sys.executable).resolve().parent / "handset" / "bin" / "shairport.exe",
            Path.cwd() / "handset" / "bin" / "shairport.exe",
        ]
    )
    for p in candidates:
        if p.is_file():
            return p
    return None


def configure_registry() -> None:
    """Pre-configure Shairport4w registry for silent background execution as 'Pane Audio'."""
    try:
        import winreg

        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Shairport4w")
        winreg.SetValueEx(key, "ApName", 0, winreg.REG_SZ, "Pane Audio")
        winreg.SetValueEx(key, "StartMinimized", 0, winreg.REG_SZ, "yes")
        winreg.SetValueEx(key, "Tray", 0, winreg.REG_SZ, "yes")
        winreg.SetValueEx(key, "TrayTrackInfo", 0, winreg.REG_SZ, "no")
        winreg.SetValueEx(key, "InfoPanel", 0, winreg.REG_SZ, "no")
        winreg.CloseKey(key)
        logger.info("Configured Shairport4w registry as 'Pane Audio'")
    except Exception as e:
        logger.warning("Could not set Shairport4w registry: %s", e)


def start_airplay_receiver() -> bool:
    """Start embedded AirPlay Audio receiver in the background."""
    global _PROCESS
    if _PROCESS and _PROCESS.poll() is None:
        return True

    exe = _find_shairport_bin()
    if not exe:
        logger.warning("AirPlay receiver binary not found")
        return False

    configure_registry()

    try:
        _PROCESS = subprocess.Popen(
            [str(exe)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info("AirPlay Audio receiver started (PID %d) as 'Pane Audio'", _PROCESS.pid)
        atexit.register(stop_airplay_receiver)
        return True
    except Exception as e:
        logger.error("Failed to start AirPlay receiver: %s", e)
        return False


def is_airplay_connected() -> bool:
    """Return True if an iPhone is currently connected and streaming audio to Shairport."""
    global _PROCESS
    if not _PROCESS or _PROCESS.poll() is not None:
        return False
    try:
        import psutil

        p = psutil.Process(_PROCESS.pid)
        for conn in p.connections():
            if conn.status == "ESTABLISHED" and getattr(conn.laddr, "port", None) == 5000:
                return True
            if getattr(conn, "raddr", None) and getattr(conn, "type", None) == psutil.SOCK_DGRAM:
                return True
    except Exception:
        pass
    return False


def stop_airplay_receiver() -> None:
    """Stop the AirPlay Audio receiver."""
    global _PROCESS
    if _PROCESS and _PROCESS.poll() is None:
        try:
            _PROCESS.terminate()
            _PROCESS.wait(timeout=2)
            logger.info("AirPlay Audio receiver stopped")
        except Exception:
            try:
                _PROCESS.kill()
            except Exception:
                pass
        _PROCESS = None

