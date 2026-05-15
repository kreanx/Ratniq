import enum
import random
import math
import time


class RatState(enum.Enum):
    IDLE = "idle"
    SIT = "sit"
    WALK = "walk"
    RUN = "run"
    JUMP = "jump"
    FALL = "fall"
    CLIMB = "climb"


class RatDirection(enum.Enum):
    LEFT = "left"
    RIGHT = "right"


FRAME_COUNTS = {
    RatState.IDLE: 4,
    RatState.SIT: 3,
    RatState.WALK: 6,
    RatState.RUN: 6,
    RatState.JUMP: 4,
    RatState.FALL: 4,
    RatState.CLIMB: 4,
}


class Surface:
    def __init__(self, y, x_start, x_end, surface_type="ground"):
        self.y = y
        self.x_start = x_start
        self.x_end = x_end
        self.surface_type = surface_type

    def contains_x(self, x):
        return self.x_start <= x <= self.x_end

    def random_x(self, margin=0):
        lo = self.x_start + margin
        hi = self.x_end - margin
        if lo >= hi:
            return lo
        return random.uniform(lo, hi)

    def overlaps_x(self, other):
        return self.x_start < other.x_end and other.x_start < self.x_end

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
        self.run_speed = 280.0
        self.jump_speed_x = 200.0
        self.jump_speed_y = 350.0
        self.climb_speed = 150.0
        self.gravity = 600.0

        self.state_timer = 0.0
        self.state_duration = random.uniform(1.0, 3.0)
        self.paused = False

        self._target_x = None
        self._target_y = None
        self._surfaces = []
        self._current_surface = None

        self._vel_x = 0.0
        self._vel_y = 0.0

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

    def _find_jump_target(self):
        if not self._surfaces or len(self._surfaces) < 2:
            return None

        window_surfs = [
            s for s in self._surfaces
            if s.surface_type == "window_top" and s is not self._current_surface
        ]
        if not window_surfs:
            return None

        reachable = []
        for s in window_surfs:
            dy = s.y - self.y
            if dy > 0:
                continue
            cx = (s.x_start + s.x_end) / 2
            dx = abs(cx - self.x)
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < 800:
                reachable.append((s, dist))

        if not reachable:
            return None

        reachable.sort(key=lambda t: t[1])
        return reachable[0][0]

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
        self.state_timer = 0.0

        if new_state == RatState.IDLE:
            self.state_duration = random.uniform(1.0, 3.0)
            self.frame_interval = 0.15
        elif new_state == RatState.SIT:
            self.state_duration = random.uniform(2.0, 5.0)
            self.frame_interval = 0.2
        elif new_state == RatState.WALK:
            self.state_duration = random.uniform(4.0, 12.0)
            self._pick_new_target()
            self.frame_interval = 0.1
        elif new_state == RatState.RUN:
            self.state_duration = random.uniform(1.0, 3.0)
            self._pick_new_target()
            self.frame_interval = 0.06
        elif new_state == RatState.JUMP:
            self.frame_interval = 0.08
            self._start_jump()
        elif new_state == RatState.FALL:
            self.frame_interval = 0.08
        elif new_state == RatState.CLIMB:
            self.frame_interval = 0.08
            self.state_duration = 10.0

    def _start_jump(self):
        target = self._find_jump_target()
        if target is None:
            self._change_state(RatState.WALK)
            return

        self._target_x = random.uniform(
            target.x_start + self.sprite_w, target.x_end - self.sprite_w
        )
        self._target_y = target.y - self.sprite_h

        dx = self._target_x - self.x
        dy = self._target_y - self.y

        t = math.sqrt(abs(dy) * 2 / self.gravity) if dy < 0 else 0.3
        t = max(t, 0.3)
        t = min(t, 1.0)

        self._vel_x = dx / t
        self._vel_y = dy / t - 0.5 * self.gravity * t

        if dx > 0:
            self.direction = RatDirection.RIGHT
        elif dx < 0:
            self.direction = RatDirection.LEFT

        self.state_duration = t + 0.5
        self._current_surface = None

    def _decide_next_state(self):
        hour = time.localtime().tm_hour
        if 1 <= hour <= 4 and random.random() < 0.4:
            self._change_state(RatState.RUN)
            return

        roll = random.random()
        window_surfs = [
            s for s in self._surfaces if s.surface_type == "window_top"
        ]

        if (window_surfs and roll < 0.20
                and self.state not in (RatState.JUMP, RatState.FALL)):
            self._change_state(RatState.JUMP)
        elif roll < 0.45:
            self._change_state(RatState.WALK)
        elif roll < 0.60:
            self._change_state(RatState.SIT)
        elif roll < 0.75:
            self._change_state(RatState.IDLE)
        else:
            self._change_state(RatState.WALK)

    def update(self, dt):
        if self.paused:
            return

        self.state_timer += dt
        self.frame_timer += dt

        if self.frame_timer >= self.frame_interval:
            self.frame_timer -= self.frame_interval
            count = FRAME_COUNTS.get(self.state, 6)
            self.frame_index = (self.frame_index + 1) % count

        if self.state == RatState.WALK:
            self._move_toward_target(dt, self.walk_speed)
        elif self.state == RatState.RUN:
            self._move_toward_target(dt, self.run_speed)
        elif self.state == RatState.JUMP:
            self._move_jump(dt)
        elif self.state == RatState.FALL:
            self._move_fall(dt)
        elif self.state == RatState.CLIMB:
            self._move_climb(dt)

        if (self.state not in (RatState.JUMP, RatState.FALL)
                and self.state_timer >= self.state_duration):
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
            self.x = max(
                self._current_surface.x_start,
                min(self.x, self._current_surface.x_end - self.sprite_w),
            )

    def _move_jump(self, dt):
        self._vel_y += self.gravity * dt
        self.x += self._vel_x * dt
        self.y += self._vel_y * dt

        landed = self._check_landing()
        if landed:
            return

        if self.state_timer >= self.state_duration:
            self._change_state(RatState.FALL)

    def _move_fall(self, dt):
        self._vel_y += self.gravity * dt
        self.x += self._vel_x * dt
        self.y += self._vel_y * dt
        self._check_landing()

    def _check_landing(self):
        for surf in self._surfaces:
            if not surf.overlaps_x(Surface(0, self.x, self.x + self.sprite_w)):
                continue

            if (self._vel_y >= 0
                    and self.y + self.sprite_h >= surf.y
                    and self.y + self.sprite_h <= surf.y + self.sprite_h * 0.5):
                self.y = surf.y
                self._current_surface = surf
                self._vel_x = 0.0
                self._vel_y = 0.0
                self._change_state(RatState.WALK)
                return True

        if self.y > self.screen_h + self.sprite_h:
            self._respawn()
            return True

        return False

    def _respawn(self):
        ground = None
        for s in self._surfaces:
            if s.surface_type == "screen_bottom":
                ground = s
                break
        if ground is None and self._surfaces:
            ground = self._surfaces[0]

        if ground:
            self._current_surface = ground
            self.y = ground.y
        else:
            self.y = self.screen_h - self.sprite_h

        side = random.choice(["left", "right"])
        if side == "left":
            self.x = -self.sprite_w
            self.direction = RatDirection.RIGHT
        else:
            self.x = self.screen_w + self.sprite_w
            self.direction = RatDirection.LEFT

        self._vel_x = 0.0
        self._vel_y = 0.0
        self._change_state(RatState.WALK)

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
