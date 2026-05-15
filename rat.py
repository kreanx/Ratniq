import enum
import random
import math
import time


class RatState(enum.Enum):
    IDLE = "idle"
    SIT = "sit"
    WALK = "walk"
    RUN = "run"
    CLIMB = "climb"
    FALL = "fall"


class RatDirection(enum.Enum):
    LEFT = "left"
    RIGHT = "right"


FRAME_COUNTS = {
    RatState.IDLE: 10,
    RatState.SIT: 10,
    RatState.WALK: 10,
    RatState.RUN: 12,
    RatState.CLIMB: 10,
    RatState.FALL: 10,
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

    def overlap_range(self, other):
        lo = max(self.x_start, other.x_start)
        hi = min(self.x_end, other.x_end)
        return lo, hi

    @property
    def width(self):
        return self.x_end - self.x_start

    def _distance_to(self, other):
        return (
            abs(self.y - other.y)
            + abs(self.x_start - other.x_start)
            + abs(self.x_end - other.x_end)
        )


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

        self.walk_speed = 100.0
        self.run_speed = 250.0
        self.climb_speed = 2000.0
        self.fall_speed = 400.0

        self.state_timer = 0.0
        self.state_duration = random.uniform(1.0, 3.0)
        self.paused = False

        self._target_x = None
        self._surfaces = []
        self._current_surface = None

        self._transition_target = None
        self._transition_x = None
        self._fall_vel = 0.0
        self._pending_climb = False

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

        if self._current_surface is not None:
            matched = self._find_closest(self._current_surface)
            if matched is not None:
                old = self._current_surface
                dy = matched.y - old.y
                dx_start = matched.x_start - old.x_start
                if self.state not in (RatState.CLIMB, RatState.FALL):
                    self.y += dy
                self.x += dx_start
                self._current_surface = matched
                if self._target_x is not None and self.state in (RatState.WALK, RatState.RUN):
                    self._target_x += dx_start
                if self.state not in (RatState.CLIMB, RatState.FALL):
                    self.y = matched.y
            elif self._current_surface.surface_type == "window_top":
                if self.state not in (RatState.CLIMB, RatState.FALL):
                    self._transition_target = ground
                    self._target_y = ground.y
                    self._fall_vel = 0.0
                    self._change_state(RatState.FALL)

        if self._transition_target is not None:
            matched = self._find_closest(self._transition_target)
            if matched is not None:
                self._transition_target = matched
                if hasattr(self, "_target_y"):
                    self._target_y = matched.y
            else:
                self._transition_target = None
                if self.state in (RatState.CLIMB, RatState.FALL):
                    if self._current_surface:
                        self.y = self._current_surface.y
                    self._change_state(RatState.WALK)

        if self._current_surface is None:
            self._current_surface = ground
            self.y = ground.y

        self._clamp_to_surface()

    def _find_closest(self, old_surface):
        if old_surface.surface_type == "screen_bottom":
            for s in self._surfaces:
                if s.surface_type == "screen_bottom":
                    return s
            return None

        best = None
        best_score = float("inf")
        for s in self._surfaces:
            if s.surface_type != old_surface.surface_type:
                continue
            width_diff = abs(s.width - old_surface.width)
            pos_dist = abs(s.x_start - old_surface.x_start) + abs(s.y - old_surface.y)
            if width_diff < 20:
                score = pos_dist
            elif width_diff < 100:
                score = pos_dist + width_diff * 5
            else:
                score = pos_dist + width_diff * 20
            if score < best_score:
                best_score = score
                best = s
        if best is not None and best_score < 10000:
            return best
        return None

    def _clamp_to_surface(self):
        if self._current_surface is None:
            return
        s = self._current_surface
        self.x = max(s.x_start, min(self.x, s.x_end - self.sprite_w))

    def _pick_walk_target(self):
        if self._current_surface:
            margin = self.sprite_w
            self._target_x = self._current_surface.random_x(margin)
        else:
            self._target_x = random.uniform(self.sprite_w, self.screen_w - self.sprite_w)

    def _change_state(self, new_state, keep_target=False):
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
            self.state_duration = random.uniform(3.0, 10.0)
            if not keep_target:
                self._pick_walk_target()
            self.frame_interval = 0.1
        elif new_state == RatState.RUN:
            self.state_duration = random.uniform(1.0, 3.0)
            if not keep_target:
                self._pick_walk_target()
            self.frame_interval = 0.06
        elif new_state == RatState.CLIMB:
            self.frame_interval = 0.08
            self.state_duration = 15.0
        elif new_state == RatState.FALL:
            self.frame_interval = 0.08
            self._fall_vel = 0.0
            self.state_duration = 10.0

    def _find_transition_target(self):
        if not self._current_surface or len(self._surfaces) < 2:
            return None, None

        candidates = []
        for s in self._surfaces:
            if s is self._current_surface:
                continue

            if s.overlaps_x(self._current_surface):
                overlap_lo, overlap_hi = s.overlap_range(self._current_surface)
                overlap_lo += self.sprite_w
                overlap_hi -= self.sprite_w
                if overlap_lo < overlap_hi:
                    x = random.uniform(overlap_lo, overlap_hi)
                    candidates.append((s, x))

        if not candidates:
            return None, None

        random.shuffle(candidates)
        return candidates[0]

    def _decide_next_state(self):
        hour = time.localtime().tm_hour
        if 1 <= hour <= 4 and random.random() < 0.3:
            self._change_state(RatState.RUN)
            return

        roll = random.random()
        window_surfs = [
            s for s in self._surfaces if s.surface_type == "window_top"
        ]

        if (window_surfs and roll < 0.30
                and self.state not in (RatState.CLIMB, RatState.FALL)):
            self._try_transition()
        elif roll < 0.50:
            self._change_state(RatState.WALK)
        elif roll < 0.65:
            self._change_state(RatState.SIT)
        elif roll < 0.80:
            self._change_state(RatState.IDLE)
        else:
            self._change_state(RatState.WALK)

    def _try_transition(self):
        target, x = self._find_transition_target()
        if target is None:
            self._change_state(RatState.WALK)
            return

        self._transition_target = target
        self._transition_x = x
        self._target_x = x
        self._change_state(RatState.WALK, keep_target=True)

    def update(self, dt):
        if self.paused:
            return

        self.state_timer += dt
        self.frame_timer += dt

        if self.frame_timer >= self.frame_interval:
            self.frame_timer -= self.frame_interval
            count = FRAME_COUNTS.get(self.state, 10)
            self.frame_index = (self.frame_index + 1) % count

        if self.state == RatState.WALK:
            self._do_walk(dt, self.walk_speed)
        elif self.state == RatState.RUN:
            self._do_walk(dt, self.run_speed)
        elif self.state == RatState.CLIMB:
            self._do_climb(dt)
        elif self.state == RatState.FALL:
            self._do_fall(dt)

        if (self.state not in (RatState.CLIMB, RatState.FALL)
                and self.state_timer >= self.state_duration
                and not self._pending_climb
                and self._transition_target is None):
            self._decide_next_state()

    def _do_walk(self, dt, speed):
        if self._target_x is None:
            return

        if self._current_surface:
            self.y = self._current_surface.y

        dx = self._target_x - self.x
        if abs(dx) < speed * dt:
            self.x = self._target_x

            if getattr(self, "_pending_climb", False):
                self._pending_climb = False
                if self._transition_target is not None:
                    dy = self._transition_target.y - self.y
                    self._start_vertical(self._transition_target, dy)
                return

            if self._transition_target is not None:
                self._begin_surface_transition()
                return

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

    def _begin_surface_transition(self):
        target = self._transition_target
        self._transition_target = None

        dy = target.y - self.y
        if abs(dy) < 2:
            self._current_surface = target
            self.y = target.y
            self._change_state(RatState.WALK)
            return

        edge_x = self._nearest_edge_x(target)
        if abs(edge_x - self.x) > self.sprite_w * 0.5:
            self._transition_target = target
            self._target_x = edge_x
            self._pending_climb = True
            self._change_state(RatState.WALK, keep_target=True)
            return

        self._start_vertical(target, dy)

    def _nearest_edge_x(self, target):
        cx = self.x + self.sprite_w / 2
        left_edge = target.x_start
        right_edge = target.x_end - self.sprite_w
        if right_edge < left_edge:
            return left_edge
        return left_edge if abs(cx - left_edge) <= abs(cx - right_edge) else right_edge

    def _start_vertical(self, target, dy):
        self._transition_target = target
        self._target_x = self.x
        self._target_y = target.y
        if dy < 0:
            self._change_state(RatState.CLIMB)
        else:
            self._change_state(RatState.FALL)

    def _do_climb(self, dt):
        target = self._transition_target
        if target is None:
            self._change_state(RatState.WALK)
            return

        dy = target.y - self.y
        if abs(dy) < self.climb_speed * dt:
            self.y = target.y
            self._current_surface = target
            self._transition_target = None
            self._change_state(RatState.WALK)
            return

        self.y += math.copysign(self.climb_speed * dt, dy)

    def _do_fall(self, dt):
        target = self._transition_target
        if target is None:
            self._change_state(RatState.WALK)
            return

        self._fall_vel += 3000.0 * dt
        self.y += self._fall_vel * dt

        if self.y >= target.y:
            self.y = target.y
            self._current_surface = target
            self._transition_target = None
            self._fall_vel = 0.0
            self._change_state(RatState.WALK)

        if self.y > self.screen_h + self.sprite_h:
            self._respawn()

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

        self._transition_target = None
        self._fall_vel = 0.0
        self._change_state(RatState.WALK)

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
