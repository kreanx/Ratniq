import logging
import random
import subprocess
import json
import os
import threading

log = logging.getLogger(__name__)

DETECTOR_BIN = os.path.join(os.path.dirname(__file__), "tools", "detect_daemon-bin")
DETECTOR_V2_BIN = os.path.join(os.path.dirname(__file__), "tools", "detect_v2-bin")

_latest_surfaces = []
_lock = threading.Lock()
_scanner_thread = None


def get_walkable_surfaces(screen_w, screen_h):
    with _lock:
        if _latest_surfaces:
            return list(_latest_surfaces)
    return []


def start_background_scan(screen_w, screen_h, interval=3.0):
    global _scanner_thread
    _scanner_thread = threading.Thread(target=_event_loop, daemon=True)
    _scanner_thread.start()
    log.info("Event-driven window scanner started")


def _event_loop():
    while True:
        try:
            _run_daemon()
        except Exception as e:
            log.debug("Daemon error: %s, retrying in 2s", e)
        import time
        time.sleep(2)


def _run_daemon():
    if not os.path.isfile(DETECTOR_BIN):
        _fallback_poll()
        return

    proc = subprocess.Popen(
        [DETECTOR_BIN],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        bufsize=1,
    )

    log.info("Daemon started pid=%d", proc.pid)

    for line in iter(proc.stdout.readline, b""):
        if not line:
            break
        try:
            rects = json.loads(line)
            if isinstance(rects, list):
                with _lock:
                    _latest_surfaces.clear()
                    _latest_surfaces.extend(rects)
        except json.JSONDecodeError:
            pass

    proc.wait()
    log.info("Daemon exited code=%d", proc.returncode)


def _fallback_poll():
    bin_path = DETECTOR_V2_BIN
    if not os.path.isfile(bin_path):
        return
    while True:
        try:
            r = subprocess.run(
                [bin_path], capture_output=True, text=True, timeout=3,
            )
            if r.returncode == 0 and r.stdout.strip():
                rects = json.loads(r.stdout)
                if rects:
                    with _lock:
                        _latest_surfaces.clear()
                        _latest_surfaces.extend(rects)
        except Exception:
            pass
        import time
        time.sleep(2)
