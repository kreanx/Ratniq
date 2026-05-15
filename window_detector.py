import logging
import random

log = logging.getLogger(__name__)


def get_walkable_surfaces(screen_w, screen_h):
    surfaces = _try_cosmic_detector()
    if surfaces:
        return surfaces
    return _generate_virtual_windows(screen_w, screen_h)


def _try_cosmic_detector():
    import subprocess, os, json
    binary = os.path.join(os.path.dirname(__file__), "tools", "detect_v2-bin")
    if not os.path.isfile(binary):
        return []
    try:
        r = subprocess.run([binary], capture_output=True, text=True, timeout=3)
        if r.returncode == 0 and r.stdout.strip():
            rects = json.loads(r.stdout)
            if rects:
                log.debug("COSMIC detector found %d windows", len(rects))
                return rects
    except Exception:
        pass
    return []


def _generate_virtual_windows(screen_w, screen_h):
    windows = []
    count = random.randint(1, 4)
    min_w, max_w = 300, 900
    min_h, max_h = 200, 600

    for _ in range(count):
        w = random.randint(min_w, min(max_w, screen_w - 100))
        h = random.randint(min_h, min(max_h, screen_h - 200))
        x = random.randint(50, max(51, screen_w - w - 50))
        y = random.randint(50, max(51, screen_h - h - 200))
        windows.append({
            "type": "window_top",
            "y": y,
            "x_start": x,
            "x_end": x + w,
            "height": h,
        })

    log.debug("Generated %d virtual windows", len(windows))
    return windows
