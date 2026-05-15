import os
import time
import signal
import logging
import random

os.environ["GDK_BACKEND"] = "wayland"

from gi.repository import GLib

from layeroverlay import LayerOverlay
from sprite import SpriteSet, VARIANTS
from rat import Rat, Surface
from window_detector import get_walkable_surfaces, start_background_scan

log = logging.getLogger(__name__)

FPS = 30
FRAME_DT = 1.0 / FPS
SPRITE_SCALE = 3
WINDOW_SCAN_INTERVAL = 0.1
DOCK_HEIGHT = 0
RAT_COUNT = 3


class RatniqApp:
    def __init__(self):
        logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")

        variant_names = list(VARIANTS.keys())
        random.shuffle(variant_names)

        self.rats = []
        self.sprites_list = []
        for i in range(RAT_COUNT):
            variant = variant_names[i % len(variant_names)]
            sprites = SpriteSet(scale=SPRITE_SCALE, variant=variant)
            if i == 0:
                sprite_w, sprite_h = sprites.frame_size()
            self.sprites_list.append(sprites)

        self.overlay = LayerOverlay(sprite_w, sprite_h)
        sw, sh = self.overlay.screen_size
        sh -= DOCK_HEIGHT

        for i in range(RAT_COUNT):
            rat = Rat(0, 0, sw, sh, sprite_w, sprite_h)
            self._randomize_start(rat, sw, sh, sprite_w, sprite_h)
            self.rats.append(rat)

        self._last_time = time.time()
        self._screen_w = sw
        self._screen_h = sh
        self._sprite_h = sprite_h
        self._running = True
        self._loop = GLib.MainLoop()

        start_background_scan(sw, sh, WINDOW_SCAN_INTERVAL)
        self._scan_windows()

        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, self._quit)
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, self._quit)
        GLib.timeout_add(int(FRAME_DT * 1000), self._tick)

    def _randomize_start(self, rat, sw, sh, sprite_w, sprite_h):
        ground_y = sh - sprite_h
        side = random.choice(["left", "right", "screen"])
        if side == "left":
            rat.x = -sprite_w
            rat._target_x = random.uniform(sw * 0.2, sw * 0.6)
            rat.direction = rat.direction.RIGHT
        elif side == "right":
            rat.x = sw + sprite_w
            rat._target_x = random.uniform(sw * 0.3, sw * 0.8)
            rat.direction = rat.direction.LEFT
        else:
            rat.x = random.uniform(sprite_w, sw - sprite_w)
            rat._target_x = random.uniform(sprite_w, sw - sprite_w)
            if rat._target_x > rat.x:
                rat.direction = rat.direction.RIGHT
            else:
                rat.direction = rat.direction.LEFT
        rat.y = ground_y

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
            if s["type"] != "window_top":
                continue
            if s["y"] < 50:
                continue
            if s["x_start"] < -10:
                continue
            x_start = max(0, s["x_start"])
            x_end = min(self._screen_w, s["x_end"])
            if x_end - x_start < 100:
                continue
            y = s["y"] - self._sprite_h
            if y < 10:
                continue
            surfaces.append(Surface(y, x_start, x_end, "window_top"))
        for rat in self.rats:
            rat.update_surfaces(surfaces)

    def _tick(self):
        if not self._running:
            return False

        now = time.time()
        dt = min(now - self._last_time, 0.1)
        self._last_time = now

        self._scan_windows()

        rat_data = []
        for i, rat in enumerate(self.rats):
            rat.update(dt)
            state_name, dir_name = rat.get_frame_key()
            frame = self.sprites_list[i].get_frame(state_name, dir_name, rat.frame_index)
            rat_data.append((frame, rat.x, rat.y))

        try:
            self.overlay.draw_rats(rat_data)
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
