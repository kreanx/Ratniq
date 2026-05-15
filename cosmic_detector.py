import logging
import os
import json
import subprocess

log = logging.getLogger(__name__)


def get_cosmic_window_rects():
    try:
        rects = _query_cosmic_toplevels()
        if rects:
            return rects
    except Exception as e:
        log.debug("COSMIC query failed: %s", e)

    return _get_x11_rects()


def _get_x11_rects():
    rects = []
    try:
        from Xlib.display import Display as XDisplay
        d = XDisplay()
        root = d.screen().root
        net_type = d.intern_atom("_NET_WM_WINDOW_TYPE")
        children = root.query_tree().children
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
                })
            except Exception:
                pass
        d.close()
    except Exception:
        pass
    return rects


def _query_cosmic_toplevels():
    result = subprocess.run(
        ["/usr/bin/env", "python3", "-c", _QUERY_SCRIPT],
        capture_output=True, text=True, timeout=3,
        env={**os.environ},
    )
    if result.returncode == 0 and result.stdout.strip():
        return json.loads(result.stdout)
    if result.stderr:
        log.debug("cosmic query stderr: %s", result.stderr[:200])
    return []


_QUERY_SCRIPT = r"""
import os, struct, ctypes, ctypes.util, json

lib = ctypes.CDLL(ctypes.util.find_library("wayland-client") or "libwayland-client.so.0")

wl_display_connect = lib.wl_display_connect
wl_display_connect.restype = ctypes.c_void_p
wl_display_connect.argtypes = [ctypes.c_char_p]

wl_display_roundtrip = lib.wl_display_roundtrip
wl_display_roundtrip.restype = ctypes.c_int
wl_display_roundtrip.argtypes = [ctypes.c_void_p]

wl_display_dispatch = lib.wl_display_dispatch
wl_display_dispatch.restype = ctypes.c_int
wl_display_dispatch.argtypes = [ctypes.c_void_p]

wl_display_flush = lib.wl_display_flush
wl_display_flush.restype = ctypes.c_int
wl_display_flush.argtypes = [ctypes.c_void_p]

wl_display_disconnect = lib.wl_display_disconnect
wl_display_disconnect.argtypes = [ctypes.c_void_p]

wl_display_get_fd = lib.wl_display_get_fd
wl_display_get_fd.restype = ctypes.c_int
wl_display_get_fd.argtypes = [ctypes.c_void_p]

wl_proxy_add_listener = lib.wl_proxy_add_listener
wl_proxy_add_listener.restype = ctypes.c_int
wl_proxy_add_listener.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p]

wl_proxy_destroy = lib.wl_proxy_destroy
wl_proxy_destroy.argtypes = [ctypes.c_void_p]

wl_proxy_get_user_data = lib.wl_proxy_get_user_data
wl_proxy_get_user_data.restype = ctypes.c_void_p
wl_proxy_get_user_data.argtypes = [ctypes.c_void_p]

wl_proxy_set_user_data = lib.wl_proxy_set_user_data
wl_proxy_set_user_data.argtypes = [ctypes.c_void_p, ctypes.c_void_p]

class wl_message(ctypes.Structure):
    pass

wl_message._fields_ = [
    ("name", ctypes.c_char_p),
    ("signature", ctypes.c_char_p),
    ("types", ctypes.POINTER(ctypes.c_void_p)),
]

class wl_interface(ctypes.Structure):
    pass

wl_interface._fields_ = [
    ("name", ctypes.c_char_p),
    ("version", ctypes.c_int),
    ("method_count", ctypes.c_int),
    ("methods", ctypes.POINTER(wl_message)),
    ("event_count", ctypes.c_int),
    ("events", ctypes.POINTER(wl_message)),
]

try:
    _wl_registry_interface = ctypes.POINTER(wl_interface).in_dll(lib, b"wl_registry_interface")
    _wl_output_interface = ctypes.POINTER(wl_interface).in_dll(lib, b"wl_output_interface")
except Exception:
    print("[]")
    exit(0)

wl_proxy_marshal_constructor = lib.wl_proxy_marshal_constructor
wl_proxy_marshal_constructor.restype = ctypes.c_void_p
wl_proxy_marshal_constructor.argtypes = [ctypes.c_void_p, ctypes.c_uint]

wl_proxy_marshal = lib.wl_proxy_marshal
wl_proxy_marshal.restype = None
wl_proxy_marshal.argtypes = [ctypes.c_void_p, ctypes.c_uint]

try:
    wl_proxy_marshal_constructor_versioned = lib.wl_proxy_marshal_constructor_versioned
    wl_proxy_marshal_constructor_versioned.restype = ctypes.c_void_p
    wl_proxy_marshal_constructor_versioned.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_uint]
except Exception:
    wl_proxy_marshal_constructor_versioned = None

try:
    wl_proxy_create_wrapper = lib.wl_proxy_create_wrapper
    wl_proxy_create_wrapper.restype = ctypes.c_void_p
    wl_proxy_create_wrapper.argtypes = [ctypes.c_void_p]
except Exception:
    wl_proxy_create_wrapper = None

import select, time

cosmic_info_name = [None]
cosmic_info_version = [0]
outputs = {}
toplevels = {}
finished = [False]

@ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_uint, ctypes.c_char_p, ctypes.c_uint)
def on_global(data, registry, name, interface, version):
    iface = interface.decode() if interface else ""
    if iface == "zcosmic_toplevel_info_v1":
        cosmic_info_name[0] = name
        cosmic_info_version[0] = version

@ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_uint)
def on_global_remove(data, registry, name):
    pass

reg_listeners = (ctypes.c_void_p * 2)(
    ctypes.cast(on_global, ctypes.c_void_p),
    ctypes.cast(on_global_remove, ctypes.c_void_p),
)

@ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p)
def on_toplevel(data, info_proxy, new_id):
    pass

@ctypes.CFUNCTYPE(None, ctypes.c_void_p)
def on_finished(data, info_proxy):
    finished[0] = True

info_listeners = (ctypes.c_void_p * 2)(
    ctypes.cast(on_toplevel, ctypes.c_void_p),
    ctypes.cast(on_finished, ctypes.c_void_p),
)

@ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int)
def on_handle_geometry(data, handle, output, x, y, w, h):
    pid = ctypes.addressof(handle) if handle else 0
    if pid not in toplevels:
        toplevels[pid] = {}
    toplevels[pid].update({"x": x, "y": y, "w": w, "h": h})

@ctypes.CFUNCTYPE(None, ctypes.c_void_p)
def on_handle_done(data, handle):
    pid = ctypes.addressof(handle) if handle else 0
    if pid not in toplevels:
        toplevels[pid] = {}
    toplevels[pid]["done"] = True

@ctypes.CFUNCTYPE(None, ctypes.c_void_p)
def on_handle_closed(data, handle):
    pass

@ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_char_p)
def on_handle_title(data, handle, title):
    pass

@ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_char_p)
def on_handle_app_id(data, handle, app_id):
    pass

handle_listeners = (ctypes.c_void_p * 6)(
    ctypes.cast(on_handle_closed, ctypes.c_void_p),
    ctypes.cast(on_handle_done, ctypes.c_void_p),
    ctypes.cast(on_handle_title, ctypes.c_void_p),
    ctypes.cast(on_handle_app_id, ctypes.c_void_p),
    ctypes.cast(ctypes.py_object(lambda d, h, o, x, y, w, h: None), ctypes.c_void_p),
    ctypes.cast(ctypes.py_object(lambda d, h: None), ctypes.c_void_p),
)

disp = wl_display_connect(os.environ.get("WAYLAND_DISPLAY", "wayland-1").encode())
if not disp:
    print("[]")
    exit(0)

reg = lib.wl_display_get_registry(disp)
wl_proxy_add_listener(reg, reg_listeners, None)
wl_display_roundtrip(disp)

if cosmic_info_name[0] is None:
    wl_display_disconnect(disp)
    print("[]")
    exit(0)

wl_display_disconnect(disp)
print("[]")
"""
