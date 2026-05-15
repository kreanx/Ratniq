import logging
import array
import io

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
from gi.repository import Gtk, Gdk, GLib, GdkPixbuf, GtkLayerShell
import cairo
from PIL import Image

log = logging.getLogger(__name__)


class LayerOverlay:
    def __init__(self, sprite_w, sprite_h):
        self._sprite_w = sprite_w
        self._sprite_h = sprite_h

        self._pixmap_cache = {}

        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor() or display.get_monitor(0)
        geom = monitor.get_geometry()
        self._screen_w = geom.width
        self._screen_h = geom.height

        self._window = Gtk.Window()
        self._window.set_decorated(False)
        self._window.set_app_paintable(True)
        self._window.set_skip_taskbar_hint(True)
        self._window.set_skip_pager_hint(True)

        visual = self._window.get_screen().get_rgba_visual()
        if visual:
            self._window.set_visual(visual)

        GtkLayerShell.init_for_window(self._window)
        GtkLayerShell.set_layer(self._window, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_anchor(self._window, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_anchor(self._window, GtkLayerShell.Edge.BOTTOM, True)
        GtkLayerShell.set_anchor(self._window, GtkLayerShell.Edge.LEFT, True)
        GtkLayerShell.set_anchor(self._window, GtkLayerShell.Edge.RIGHT, True)
        GtkLayerShell.set_exclusive_zone(self._window, -1)
        GtkLayerShell.set_keyboard_mode(self._window, GtkLayerShell.KeyboardMode.NONE)

        self._window.connect("draw", self._on_draw)

        self._rat_entries = []
        self._prev_entries = []

        self._window.show_all()

        w = self._window.get_window()
        if w:
            w.input_shape_combine_region(cairo.Region(), 0, 0)

        log.info(
            "Layer overlay: screen %dx%d",
            self._screen_w, self._screen_h,
        )

    @property
    def screen_size(self):
        return self._screen_w, self._screen_h

    def _pil_to_cairo_surface(self, pil_rgba):
        w, h = pil_rgba.size

        rgba = pil_rgba.convert("RGBA")
        px = rgba.load()
        raw = array.array('B')
        for y in range(h):
            for x in range(w):
                r, g, b, a = px[x, y]
                raw.append(r)
                raw.append(g)
                raw.append(b)
                raw.append(a)

        pixbuf = GdkPixbuf.Pixbuf.new_from_data(
            bytes(raw), GdkPixbuf.Colorspace.RGB,
            True, 8, w, h, w * 4,
            None, None,
        )

        surface = cairo.ImageSurface(cairo.Format.ARGB32, w, h)
        ctx = cairo.Context(surface)
        Gdk.cairo_set_source_pixbuf(ctx, pixbuf, 0, 0)
        ctx.paint()
        del ctx

        return (surface, raw, pixbuf)

    def _get_surface(self, pil_image):
        if pil_image.mode != "RGBA":
            pil_image = pil_image.convert("RGBA")
        key = id(pil_image)
        if key not in self._pixmap_cache:
            self._pixmap_cache[key] = self._pil_to_cairo_surface(pil_image)
        return self._pixmap_cache[key][0]

    def _on_draw(self, widget, cr):
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()

        cr.set_operator(cairo.OPERATOR_OVER)
        for entry in self._rat_entries:
            surface, x, y = entry
            cr.set_source_surface(surface, x, y)
            cr.paint()

        return True

    def draw_rats(self, rat_data):
        new_entries = []
        for pil_image, x, y in rat_data:
            ix, iy = int(x), int(y)
            surface = self._get_surface(pil_image)
            new_entries.append((surface, ix, iy))

        old_entries = self._prev_entries
        self._rat_entries = new_entries

        regions = []
        for entries in (old_entries, new_entries):
            for e in entries:
                _, ex, ey = e
                regions.append((ex, ey))

        if regions:
            min_x = min(r[0] for r in regions)
            min_y = min(r[1] for r in regions)
            max_x = max(r[0] for r in regions)
            max_y = max(r[1] for r in regions)
            self._window.queue_draw_area(
                min_x, min_y,
                self._sprite_w + (max_x - min_x),
                self._sprite_h + (max_y - min_y),
            )

        self._prev_entries = list(new_entries)

    def poll_events(self):
        pass

    def close(self):
        try:
            self._window.destroy()
        except Exception:
            pass
