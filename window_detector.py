import subprocess
import re
import logging

log = logging.getLogger(__name__)

_WMCTRL_RE = re.compile(
    r"^(\S+)\s+(\S+)\s+(\S+)\s+(.+)$"
)


def _detect_via_wmctrl():
    try:
        output = subprocess.check_output(
            ["wmctrl", "-l", "-G"], timeout=2, stderr=subprocess.DEVNULL
        ).decode("utf-8", errors="replace")
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None

    windows = []
    for line in output.strip().splitlines():
        parts = line.split(None, 6)
        if len(parts) < 7:
            continue
        try:
            win_id = parts[0]
            desktop = int(parts[1])
            x = int(parts[2])
            y = int(parts[3])
            w = int(parts[4])
            h = int(parts[5])
            name = parts[6]
        except (ValueError, IndexError):
            continue

        if w < 50 or h < 50:
            continue
        if desktop == -1:
            continue
        if name.lower().startswith("ratniq"):
            continue

        windows.append({
            "x": x,
            "y": y,
            "width": w,
            "height": h,
            "top_edge_y": y,
            "name": name,
        })
    return windows


def _detect_via_xwininfo():
    try:
        output = subprocess.check_output(
            ["xwininfo", "-tree", "-root"], timeout=2, stderr=subprocess.DEVNULL
        ).decode("utf-8", errors="replace")
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None

    windows = []
    for line in output.splitlines():
        match = re.search(
            r"^\s+(0x[\da-f]+)\s+.*?(\d+)x(\d+)\+(-?\d+)\+(-?\d+)\s+", line
        )
        if not match:
            continue
        w = int(match.group(2))
        h = int(match.group(3))
        x = int(match.group(4))
        y = int(match.group(5))

        if w < 50 or h < 50:
            continue
        name_part = line.strip()
        if "ratniq" in name_part.lower():
            continue
        if "root window" in name_part.lower():
            continue
        if "has no name" in name_part.lower():
            continue

        windows.append({
            "x": x,
            "y": y,
            "width": w,
            "height": h,
            "top_edge_y": y,
        })
    return windows


def _detect_via_xlib():
    try:
        from Xlib.display import Display
        from Xlib.X import AnyPropertyType
    except ImportError:
        return None

    def _get_prop(win, name):
        try:
            prop = win.get_property(name, AnyPropertyType, 0, 1024)
            if prop and prop.value:
                return prop.value
        except Exception:
            pass
        return None

    def _walk(win, results, depth=0):
        if depth > 8:
            return
        try:
            attrs = win.get_attributes()
            if attrs and attrs.map_state == 0:
                return
        except Exception:
            return

        try:
            geom = win.get_geometry()
            translated = win.translate_coords(
                win.display.screen().root, 0, 0
            )
            if geom and translated and geom.width > 50 and geom.height > 50:
                wm_class = _get_prop(win, "WM_CLASS")
                if wm_class:
                    if isinstance(wm_class, bytes):
                        cls_str = wm_class.decode("utf-8", errors="replace").lower()
                    else:
                        cls_str = str(wm_class).lower()
                    if "ratniq" in cls_str:
                        return

                results.append({
                    "x": translated.x,
                    "y": translated.y,
                    "width": geom.width,
                    "height": geom.height,
                    "top_edge_y": translated.y,
                })
        except Exception:
            pass

        try:
            tree = win.query_tree()
            if tree and tree.children:
                for child in tree.children:
                    _walk(child, results, depth + 1)
        except Exception:
            pass

    try:
        display = Display()
        root = display.screen().root
        windows = []
        _walk(root, windows)
        display.close()
        return windows
    except Exception as e:
        log.debug("Xlib detection failed: %s", e)
        return None


def get_open_windows():
    for detector in (_detect_via_wmctrl, _detect_via_xwininfo, _detect_via_xlib):
        result = detector()
        if result is not None:
            return result
    return []


def get_walkable_surfaces(screen_w, screen_h):
    windows = get_open_windows()
    surfaces = []

    for win in windows:
        surfaces.append({
            "type": "window_top",
            "y": win["top_edge_y"],
            "x_start": win["x"],
            "x_end": win["x"] + win["width"],
            "window": win,
        })

    surfaces.append({
        "type": "screen_bottom",
        "y": screen_h,
        "x_start": 0,
        "x_end": screen_w,
    })

    return surfaces
