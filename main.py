import os
import time
import signal
import logging

os.environ["GDK_BACKEND"] = "wayland"

from gi.repository import GLib

from layeroverlay import LayerOverlay
from sprite import SpriteSet
from rat import Rat, Surface
from window_detector import get_walkable_surfaces

log = logging.getLogger(__name__)

FPS = 30
FRAME_DT = 1.0 / FPS
SPRITE_SCALE = 3
WINDOW_SCAN_INTERVAL = 3.0
DOCK_HEIGHT = 0


class RatniqApp:
    def __init__(self):
        logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")

        self.sprites = SpriteSet(scale=SPRITE_SCALE)
        sprite_w, sprite_h = self.sprites.frame_size()

        self.overlay = LayerOverlay(sprite_w, sprite_h)
        sw, sh = self.overlay.screen_size
        sh -= DOCK_HEIGHT

        self.rat = Rat(0, 0, sw, sh, sprite_w, sprite_h)
        self._last_time = time.time()
        self._window_scan_timer = 0.0
        self._screen_w = sw
        self._screen_h = sh
        self._running = True
        self._loop = GLib.MainLoop()

        self._scan_windows()

        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, self._quit)
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, self._quit)
        GLib.timeout_add(int(FRAME_DT * 1000), self._tick)

    def _quit(self, *args):
        self._running = False
        log.info("Shutting down")
        self.overlay.close()
        self._loop.quit()
        return False

    def _scan_windows(self):
        surfaces_raw = get_walkable_surfaces(self._screen_w, self._screen_h)
        surfaces = []
        for s in surfaces_raw:
            if s["type"] == "window_top":
                surfaces.append(
                    Surface(s["y"], s["x_start"], s["x_end"], "window_top")
                )
        self.rat.update_surfaces(surfaces)

    def _tick(self):
        if not self._running:
            return False

        now = time.time()
        dt = min(now - self._last_time, 0.1)
        self._last_time = now

        self._window_scan_timer += dt
        if self._window_scan_timer >= WINDOW_SCAN_INTERVAL:
            self._window_scan_timer = 0.0
            self._scan_windows()

        self.rat.update(dt)

        state_name, dir_name = self.rat.get_frame_key()
        frame = self.sprites.get_frame(state_name, dir_name, self.rat.frame_index)

        try:
            self.overlay.draw_frame(frame, self.rat.x, self.rat.y)
        except Exception as e:
            log.error("Draw error: %s", e)
            self._running = False
            return False

        return True

    def run(self):
        try:
            self._loop.run()
        except KeyboardInterrupt:
            pass
        finally:
            self.overlay.close()


def main():
    app = RatniqApp()
    app.run()


if __name__ == "__main__":
    main()
