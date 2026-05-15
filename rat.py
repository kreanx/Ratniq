import enum
import random
import math
import time


class RatState(enum.Enum):
    IDLE = "idle"
    WALK = "walk"
    RUNNING = "running"
    GESTURE = "gesture"
    CLIMBING = "climbing"


class RatDirection(enum.Enum):
    LEFT = "left"
    RIGHT = "right"


class Surface:
    def __init__(self, y, x_start, x_end, surface_type="ground"):
        self.y = y
        self.x_start = x_start
        self.x_end = x_end
        self.surface_type = surface_type

    def contains_x(self, x):
        return self.x_start <= x <= self.x_end

    def random_x(self, margin=0):
        lo = max(self.x_start + margin, self.x_start)
        hi = min(self.x_end - margin, self.x_end)
        if lo >= hi:
            return lo
        return random.uniform(lo, hi)

    @property
    def width(self):
        return self.x_end - self.x_start


class Rat:
    def __init__(self, x, y, screen_w, screen_h, sprite_w, sprite_h):
        self.x = float(x)
        self.y = float(y)
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.sprite_w = sprite_w
        self.sprite_h = sprite_h

        self.state = RatState.WALK
        self.direction = RatDirection.LEFT
        self.frame_index = 0
        self.frame_timer = 0.0
        self.frame_interval = 0.1

        self.walk_speed = 120.0
        self.run_speed = 300.0
        self.climb_speed = 150.0

        self.state_timer = 0.0
        self.state_duration = random.uniform(1.0, 3.0)
        self.paused = False

        self._target_x = None
        self._target_y = None
        self._surfaces = []
        self._current_surface = None

        ground = Surface(screen_h - sprite_h, 0, screen_w, "screen_bottom")
        self._surfaces = [ground]
        self._current_surface = ground
        self.x = float(screen_w + sprite_w)
        self.y = ground.y
        self._target_x = random.uniform(screen_w * 0.2, screen_w * 0.8)

    def update_surfaces(self, window_surfaces):
        ground = Surface(
            self.screen_h - self.sprite_h, 0, self.screen_w, "screen_bottom"
        )
        self._surfaces = [ground] + window_surfaces
        if self._current_surface not in self._surfaces:
            self._current_surface = ground
            self.y = ground.y

    def _find_nearby_surface(self, prefer_window=True):
        if not self._surfaces:
            return None

        candidates = list(self._surfaces)

        if prefer_window:
            window_surfs = [s for s in candidates if s.surface_type == "window_top"]
            if window_surfs:
                weights = []
                for s in window_surfs:
                    x_dist = abs((s.x_start + s.x_end) / 2 - self.x)
                    y_dist = abs(s.y - self.y)
                    dist = math.sqrt(x_dist ** 2 + y_dist)
                    weights.append(1.0 / (1.0 + dist))
                total = sum(weights)
                weights = [w / total for w in weights]
                return random.choices(window_surfs, weights=weights, k=1)[0]

        return random.choice(candidates)

    def _pick_new_target(self):
        if self._current_surface:
            margin = self.sprite_w
            self._target_x = self._current_surface.random_x(margin)
        else:
            margin = self.sprite_w
            self._target_x = random.uniform(margin, self.screen_w - margin)
        self._target_y = None

    def _change_state(self, new_state):
        self.state = new_state
        self.frame_index = 0
        self.frame_timer = 0.0

        if new_state == RatState.IDLE:
            self.state_duration = random.uniform(1.0, 3.0)
        elif new_state == RatState.WALK:
            self.state_duration = random.uniform(4.0, 12.0)
            self._pick_new_target()
            self.frame_interval = 0.1
        elif new_state == RatState.RUNNING:
            self.state_duration = random.uniform(1.0, 3.0)
            self._pick_new_target()
            self.frame_interval = 0.06
        elif new_state == RatState.GESTURE:
            self.state_duration = random.uniform(1.0, 2.5)
        elif new_state == RatState.CLIMBING:
            target_surface = self._find_nearby_surface(prefer_window=True)
            if target_surface and target_surface is not self._current_surface:
                self._target_y = target_surface.y - self.sprite_h
                self._target_x = random.uniform(
                    target_surface.x_start, target_surface.x_end - self.sprite_w
                )
                self.state_duration = 10.0
                self.frame_interval = 0.08
            else:
                self._change_state(RatState.WALK)
                return

        self.state_timer = 0.0

    def _decide_next_state(self):
        hour = time.localtime().tm_hour
        if 1 <= hour <= 4 and random.random() < 0.4:
            self._change_state(RatState.RUNNING)
            return

        roll = random.random()
        window_surfs = [s for s in self._surfaces if s.surface_type == "window_top"]

        if window_surfs and roll < 0.15 and self.state != RatState.CLIMBING:
            self._change_state(RatState.CLIMBING)
        elif roll < 0.40:
            self._change_state(RatState.WALK)
        elif roll < 0.55:
            self._change_state(RatState.GESTURE)
        else:
            self._change_state(RatState.IDLE)

    def update(self, dt):
        if self.paused:
            return

        self.state_timer += dt
        self.frame_timer += dt

        if self.frame_timer >= self.frame_interval:
            self.frame_timer -= self.frame_interval
            frames_map = {
                RatState.IDLE: 10,
                RatState.WALK: 10,
                RatState.RUNNING: 4,
                RatState.GESTURE: 10,
                RatState.CLIMBING: 10,
            }
            count = frames_map.get(self.state, 10)
            self.frame_index = (self.frame_index + 1) % count

        if self.state == RatState.WALK:
            self._move_toward_target(dt, self.walk_speed)
        elif self.state == RatState.RUNNING:
            self._move_toward_target(dt, self.run_speed)
        elif self.state == RatState.CLIMBING:
            self._move_climb(dt)

        if self.state_timer >= self.state_duration:
            self._decide_next_state()

    def _move_toward_target(self, dt, speed):
        if self._target_x is None:
            return

        if self._current_surface:
            self.y = self._current_surface.y

        dx = self._target_x - self.x
        if abs(dx) < speed * dt:
            self.x = self._target_x
            self._decide_next_state()
            return

        if dx > 0:
            self.direction = RatDirection.RIGHT
        else:
            self.direction = RatDirection.LEFT

        self.x += math.copysign(speed * dt, dx)

        if self._current_surface:
            self.x = max(self._current_surface.x_start,
                         min(self.x, self._current_surface.x_end - self.sprite_w))

    def _move_climb(self, dt):
        if self._target_x is None or self._target_y is None:
            self._change_state(RatState.WALK)
            return

        dx = self._target_x - self.x
        dy = self._target_y - self.y
        dist = math.sqrt(dx * dx + dy * dy)

        if dist < self.climb_speed * dt:
            self.x = self._target_x
            self.y = self._target_y

            for surf in self._surfaces:
                if (surf.surface_type == "window_top"
                        and abs(surf.y - self.sprite_h - self.y) < 5):
                    self._current_surface = surf
                    break
            else:
                if self._surfaces:
                    self._current_surface = self._surfaces[0]
                    self.y = self._current_surface.y
                else:
                    self._current_surface = None

            self._change_state(RatState.WALK)
            return

        if dx > 0:
            self.direction = RatDirection.RIGHT
        elif dx < 0:
            self.direction = RatDirection.LEFT

        ratio_x = dx / dist if dist > 0 else 0
        ratio_y = dy / dist if dist > 0 else 0
        self.x += ratio_x * self.climb_speed * dt
        self.y += ratio_y * self.climb_speed * dt

    def toggle_pause(self):
        self.paused = not self.paused
        if self.paused:
            self._change_state(RatState.IDLE)

    def get_frame_key(self):
        return self.state.value, self.direction.value

    @property
    def bounds(self):
        return (int(self.x), int(self.y), self.sprite_w, self.sprite_h)

    def reposition(self, screen_w, screen_h):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.x = min(self.x, screen_w - self.sprite_w)
        self.y = min(self.y, screen_h - self.sprite_h)
