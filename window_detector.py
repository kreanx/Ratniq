import logging
import random
import subprocess
import json
import os

log = logging.getLogger(__name__)

DETECTOR_BIN = os.path.join(os.path.dirname(__file__), "tools", "detect_v2-bin")


def get_walkable_surfaces(screen_w, screen_h):
    rects = _try_cosmic_detector()
    if rects:
        return rects

    rects = _try_x11()
    if rects:
        return rects

    return _generate_virtual_windows(screen_w, screen_h)


def _try_cosmic_detector():
    if not os.path.isfile(DETECTOR_BIN):
        return []
    try:
        r = subprocess.run(
            [DETECTOR_BIN], capture_output=True, text=True, timeout=3,
        )
        if r.returncode == 0 and r.stdout.strip():
            rects = json.loads(r.stdout)
            if rects:
                log.debug("COSMIC detector: %d windows", len(rects))
                return rects
    except Exception:
        pass
    return []


def _try_x11():
    rects = []
    try:
        from Xlib.display import Display as XDisplay

        d = XDisplay()
        root = d.screen().root
        children = root.query_tree().children
        net_type = d.intern_atom("_NET_WM_WINDOW_TYPE")
        for w in children:
            try:
                attrs = w.get_attributes()
                if attrs.map_state != 2:
                    continue
                geom = w.get_geometry()
                if geom.width < 50 or geom.height < 50:
                    continue
                wa = w.get_full_property(net_type, 0)
                if wa and wa.value:
                    continue
                rects.append({
                    "type": "window_top",
                    "y": geom.y,
                    "x_start": geom.x,
                    "x_end": geom.x + geom.width,
                    "height": geom.height,
                })
            except Exception:
                pass
        d.close()
    except Exception:
        pass
    return rects


def _generate_virtual_windows(screen_w, screen_h):
    windows = []
    count = random.randint(2, 5)
    for _ in range(count):
        w = random.randint(350, min(900, screen_w - 100))
        h = random.randint(250, min(600, screen_h - 250))
        x = random.randint(50, max(51, screen_w - w - 50))
        y = random.randint(80, max(81, screen_h - h - 200))
        windows.append({
            "type": "window_top",
            "y": y,
            "x_start": x,
            "x_end": x + w,
            "height": h,
        })
    log.debug("Virtual windows: %d", len(windows))
    return windows
