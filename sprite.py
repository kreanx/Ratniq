import os
from PIL import Image

SPRITE_SHEET = os.path.join(os.path.dirname(__file__), "assets", "sprites", "rat_bat_spritesheet.png")
RUNNING_SHEET = os.path.join(os.path.dirname(__file__), "assets", "sprites", "running_rat_strip.png")
CELL_SIZE = 32

RAT_IDLE_ROW = 0
RAT_WALK_ROW = 2
RAT_GESTURE_ROW = 1
RAT_FRAMES = 10

RUN_FRAME_COUNT = 4
RUN_FRAME_W = 64
RUN_FRAME_H = 64


def _crop_row(img, row, count):
    frames = []
    for col in range(count):
        x0 = col * CELL_SIZE
        y0 = row * CELL_SIZE
        frame = img.crop((x0, y0, x0 + CELL_SIZE, y0 + CELL_SIZE))
        frames.append(frame)
    return frames


def _mirror_frames(frames):
    return [f.transpose(Image.FLIP_LEFT_RIGHT) for f in frames]


def _scale_frames(frames, scale):
    return [
        f.resize((f.width * scale, f.height * scale), Image.NEAREST)
        for f in frames
    ]


def _recolor(frames, hue_shift=0, sat_mult=1.0, val_mult=1.0):
    import colorsys
    result = []
    for frame in frames:
        img = frame.copy()
        px = img.load()
        w, h = img.size
        for y in range(h):
            for x in range(w):
                r, g, b, a = px[x, y]
                if a == 0:
                    continue
                h_, s_, v_ = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
                h_ = (h_ + hue_shift) % 1.0
                s_ = min(1.0, s_ * sat_mult)
                v_ = min(1.0, v_ * val_mult)
                nr, ng, nb = colorsys.hsv_to_rgb(h_, s_, v_)
                px[x, y] = (int(nr * 255), int(ng * 255), int(nb * 255), a)
        result.append(img)
    return result


VARIANTS = {
    "brown": {"hue_shift": 0.0, "sat_mult": 1.0, "val_mult": 1.0},
    "white": {"hue_shift": 0.0, "sat_mult": 0.05, "val_mult": 1.4},
    "gray": {"hue_shift": 0.0, "sat_mult": 0.1, "val_mult": 0.7},
    "dark": {"hue_shift": 0.0, "sat_mult": 0.2, "val_mult": 0.4},
}


class SpriteSet:
    def __init__(self, scale=2, variant="brown"):
        self.scale = scale
        self.variant = variant
        self._load_sprites()

    def _load_sprites(self):
        try:
            sheet = Image.open(SPRITE_SHEET).convert("RGBA")
        except FileNotFoundError:
            raise SystemExit(f"Sprite sheet not found: {SPRITE_SHEET}")

        idle_raw = _crop_row(sheet, RAT_IDLE_ROW, RAT_FRAMES)
        walk_raw = _crop_row(sheet, RAT_WALK_ROW, RAT_FRAMES)
        gesture_raw = _crop_row(sheet, RAT_GESTURE_ROW, RAT_FRAMES)

        params = VARIANTS.get(self.variant, VARIANTS["brown"])

        idle_recolored = _recolor(idle_raw, **params)
        walk_recolored = _recolor(walk_raw, **params)
        gesture_recolored = _recolor(gesture_raw, **params)

        self._store("idle", idle_recolored)
        self._store("walk", walk_recolored)
        self._store("gesture", gesture_recolored)

        self.climbing_right = self.walk_right
        self.climbing_left = self.walk_left

        try:
            run_sheet = Image.open(RUNNING_SHEET).convert("RGBA")
        except FileNotFoundError:
            raise SystemExit(f"Running sprite sheet not found: {RUNNING_SHEET}")

        run_raw = []
        for i in range(RUN_FRAME_COUNT):
            frame = run_sheet.crop((i * RUN_FRAME_W, 0, (i + 1) * RUN_FRAME_W, RUN_FRAME_H))
            run_raw.append(frame)

        run_recolored = _recolor(run_raw, **params)
        self._store("run", run_recolored)

        if not self.walk_right:
            raise SystemExit("Walk sprites empty — check spritesheet row configuration")

    def _store(self, name, right_frames_raw):
        right_scaled = _scale_frames(right_frames_raw, self.scale)
        left_scaled = _mirror_frames(right_scaled)

        setattr(self, f"{name}_left", right_scaled)
        setattr(self, f"{name}_right", left_scaled)

    def get_frame(self, state, direction, frame_index):
        key = f"{state}_{direction}"
        frames = getattr(self, key, self.idle_right)
        return frames[frame_index % len(frames)]

    def frame_size(self):
        w, h = self.walk_right[0].size
        return w, h
