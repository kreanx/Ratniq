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
    RatState.IDLE: 10,
    RatState.SIT: 10,
    RatState.WALK: 10,
    RatState.RUN: 12,
    RatState.JUMP: 10,
    RatState.FALL: 10,
    RatState.CLIMB: 10,
}

GRAVITY = 1400.0
WALK_ACCEL = 500.0
RUN_ACCEL = 1200.0
DECEL = 600.0
MAX_WALK_SPEED = 120.0
MAX_RUN_SPEED = 320.0
JUMP_VEL_Y = -550.0
CLIMB_SPEED = 250.0
MOUSE_FEAR_RADIUS = 250.0
MOUSE_PANIC_RADIUS = 100.0


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

        self.vel_x = 0.0
        self.vel_y = 0.0

        self.state_timer = 0.0
        self.state_duration = random.uniform(1.0, 3.0)
        self.paused = False

        self._target_x = None
        self._surfaces = []
        self._current_surface = None

        self._transition_target = None
        self._fall_vel = 0.0
        self._pending_climb = False
        self._jump_landing_surface = None
        self._fleeing = False

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
                if self.state in (RatState.WALK, RatState.RUN, RatState.IDLE, RatState.SIT):
                    self.x += dx_start
                    self.y = matched.y
                elif self.state == RatState.JUMP:
                    self.x += dx_start
                self._current_surface = matched
                if self._target_x is not None and self.state in (RatState.WALK, RatState.RUN):
                    self._target_x += dx_start
            elif self._current_surface.surface_type == "window_top":
                if self.state in (RatState.WALK, RatState.RUN, RatState.IDLE, RatState.SIT):
                    self.vel_y = 0.0
                    self._transition_target = None
                    self._change_state(RatState.FALL)

        if self._transition_target is not None:
            matched = self._find_closest(self._transition_target)
            if matched is not None:
                self._transition_target = matched
            else:
                self._transition_target = None
                if self.state == RatState.CLIMB:
                    if self._current_surface:
                        self.y = self._current_surface.y
                    self._change_state(RatState.WALK)

        if self._jump_landing_surface is not None:
            matched = self._find_closest(self._jump_landing_surface)
            if matched is not None:
                self._jump_landing_surface = matched

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
        self._fleeing = False

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
        elif new_state == RatState.JUMP:
            self.frame_interval = 0.08
            self.state_duration = 5.0
        elif new_state == RatState.CLIMB:
            self.frame_interval = 0.08
            self.state_duration = 15.0
        elif new_state == RatState.FALL:
            self.frame_interval = 0.08
            self.state_duration = 10.0

    def _find_landing_surface(self, x, y_bottom, prev_y_bottom):
        best = None
        best_y = float("inf")
        for s in self._surfaces:
            if not s.contains_x(x + self.sprite_w / 2):
                continue
            if s.y >= prev_y_bottom and s.y <= y_bottom:
                if s.y < best_y:
                    best_y = s.y
                    best = s
        return best

    def update(self, dt, mouse_x=None, mouse_y=None):
        if self.paused:
            return

        self._check_mouse(mouse_x, mouse_y)

        self.state_timer += dt
        self.frame_timer += dt

        if self.frame_timer >= self.frame_interval:
            self.frame_timer -= self.frame_interval
            count = FRAME_COUNTS.get(self.state, 10)
            self.frame_index = (self.frame_index + 1) % count

        if self.state == RatState.WALK:
            self._do_walk(dt)
        elif self.state == RatState.RUN:
            self._do_run(dt)
        elif self.state == RatState.JUMP:
            self._do_jump(dt)
        elif self.state == RatState.FALL:
            self._do_fall(dt)
        elif self.state == RatState.CLIMB:
            self._do_climb(dt)
        elif self.state in (RatState.IDLE, RatState.SIT):
            self._do_still(dt)

        if (self.state not in (RatState.CLIMB, RatState.FALL, RatState.JUMP)
                and self.state_timer >= self.state_duration
                and not self._pending_climb
                and self._transition_target is None
                and not self._fleeing):
            self._decide_next_state()

    def _check_mouse(self, mx, my):
        if mx is None or my is None:
            return
        if self.state in (RatState.CLIMB, RatState.FALL, RatState.JUMP):
            return

        cx = self.x + self.sprite_w / 2
        cy = self.y + self.sprite_h / 2
        dist = math.hypot(mx - cx, my - cy)

        if dist < MOUSE_PANIC_RADIUS:
            self._start_flee(mx, 400.0)
        elif dist < MOUSE_FEAR_RADIUS and not self._fleeing:
            if random.random() < 0.3:
                self._start_flee(mx, 280.0)

    def _start_flee(self, mouse_x, speed):
        self._fleeing = True
        if mouse_x > self.x:
            self._target_x = self.x - random.uniform(200, 500)
        else:
            self._target_x = self.x + random.uniform(200, 500)

        if self._current_surface:
            self._target_x = max(
                self._current_surface.x_start + self.sprite_w,
                min(self._target_x, self._current_surface.x_end - self.sprite_w),
            )

        if self.state in (RatState.IDLE, RatState.SIT, RatState.WALK):
            self.state = RatState.RUN
            self.state_timer = 0.0
            self.state_duration = random.uniform(1.5, 3.0)
            self.frame_interval = 0.06

        if self._target_x > self.x:
            self.direction = RatDirection.RIGHT
        else:
            self.direction = RatDirection.LEFT

    def _do_walk(self, dt):
        if self._target_x is None:
            self._apply_friction(dt)
            return

        if self._current_surface:
            self.y = self._current_surface.y

        dx = self._target_x - self.x
        old_x = self.x

        desired = max(-MAX_WALK_SPEED, min(dx * 3.0, MAX_WALK_SPEED))
        steer = desired - self.vel_x
        steer = max(-WALK_ACCEL * dt, min(steer, WALK_ACCEL * dt))
        self.vel_x += steer
        self.x += self.vel_x * dt

        if self.vel_x > 5:
            self.direction = RatDirection.RIGHT
        elif self.vel_x < -5:
            self.direction = RatDirection.LEFT

        crossed = (old_x <= self._target_x <= self.x) or (self.x <= self._target_x <= old_x)
        arrived = abs(self._target_x - self.x) < 2 and abs(self.vel_x) < 10
        if crossed or arrived:
            self.x = self._target_x
            self.vel_x = 0.0

            if getattr(self, "_pending_climb", False):
                self._pending_climb = False
                if self._transition_target is not None:
                    self._begin_surface_transition()
                return

            if self._transition_target is not None:
                self._begin_surface_transition()
                return

            if self._fleeing:
                self._fleeing = False
            self._decide_next_state()
            return

        if self._current_surface:
            self.x = max(
                self._current_surface.x_start,
                min(self.x, self._current_surface.x_end - self.sprite_w),
            )

    def _do_run(self, dt):
        if self._target_x is None:
            self._apply_friction(dt)
            return

        if self._current_surface:
            self.y = self._current_surface.y

        dx = self._target_x - self.x
        old_x = self.x

        max_spd = MAX_RUN_SPEED if self._fleeing else MAX_RUN_SPEED * 0.8
        desired = max(-max_spd, min(dx * 5.0, max_spd))
        steer = desired - self.vel_x
        steer = max(-RUN_ACCEL * dt, min(steer, RUN_ACCEL * dt))
        self.vel_x += steer
        self.x += self.vel_x * dt

        if self.vel_x > 5:
            self.direction = RatDirection.RIGHT
        elif self.vel_x < -5:
            self.direction = RatDirection.LEFT

        crossed = (old_x <= self._target_x <= self.x) or (self.x <= self._target_x <= old_x)
        arrived = abs(self._target_x - self.x) < 2 and abs(self.vel_x) < 15
        if crossed or arrived:
            self.x = self._target_x
            self.vel_x = 0.0

            if getattr(self, "_pending_climb", False):
                self._pending_climb = False
                if self._transition_target is not None:
                    self._begin_surface_transition()
                return

            if self._transition_target is not None:
                self._begin_surface_transition()
                return

            if self._fleeing:
                self._fleeing = False
            self._decide_next_state()
            return

        if self._current_surface:
            self.x = max(
                self._current_surface.x_start,
                min(self.x, self._current_surface.x_end - self.sprite_w),
            )

    def _do_still(self, dt):
        self._apply_friction(dt)
        if self._current_surface:
            self.y = self._current_surface.y

    def _apply_friction(self, dt):
        if abs(self.vel_x) < DECEL * dt:
            self.vel_x = 0.0
        elif self.vel_x > 0:
            self.vel_x -= DECEL * dt
        else:
            self.vel_x += DECEL * dt

    def _do_jump(self, dt):
        self.vel_y += GRAVITY * dt
        prev_bottom = self.y + self.sprite_h
        self.x += self.vel_x * dt
        self.y += self.vel_y * dt
        new_bottom = self.y + self.sprite_h

        if self.vel_x > 5:
            self.direction = RatDirection.RIGHT
        elif self.vel_x < -5:
            self.direction = RatDirection.LEFT

        if self.vel_y > 0:
            landing = self._find_landing_surface(self.x, new_bottom, prev_bottom)
            if landing is not None:
                self.y = landing.y
                self._current_surface = landing
                self.vel_y = 0.0
                self._jump_landing_surface = None
                self._change_state(RatState.WALK)
                return

        if self.y > self.screen_h + self.sprite_h:
            self._respawn()

    def _do_fall(self, dt):
        self.vel_y += GRAVITY * dt
        self._apply_friction(dt)
        prev_bottom = self.y + self.sprite_h
        self.x += self.vel_x * dt
        self.y += self.vel_y * dt
        new_bottom = self.y + self.sprite_h

        landing = self._find_landing_surface(self.x, new_bottom, prev_bottom)
        if landing is not None:
            self.y = landing.y
            self._current_surface = landing
            self.vel_y = 0.0
            self.vel_x *= 0.3
            self._change_state(RatState.WALK)
            return

        if self.y > self.screen_h + self.sprite_h:
            self._respawn()

    def _do_climb(self, dt):
        target = self._transition_target
        if target is None:
            self._change_state(RatState.WALK)
            return

        dy = target.y - self.y
        if abs(dy) < CLIMB_SPEED * dt:
            self.y = target.y
            self._current_surface = target
            self._transition_target = None
            self.vel_y = 0.0
            self._change_state(RatState.WALK)
            return

        climb_dir = -1.0 if dy < 0 else 1.0
        self.vel_y = CLIMB_SPEED * climb_dir
        self.y += self.vel_y * dt

    def _begin_surface_transition(self):
        target = self._transition_target
        self._transition_target = None

        dy = target.y - self.y
        if abs(dy) < 2:
            self._current_surface = target
            self.y = target.y
            self._change_state(RatState.WALK)
            return

        cx = self.x + self.sprite_w / 2
        if target.x_start <= cx <= target.x_end:
            self._start_jump_to(target)
            return

        edge_x = self._nearest_edge_x(target)
        if abs(edge_x - self.x) > self.sprite_w * 0.5:
            self._transition_target = target
            self._target_x = edge_x
            self._pending_climb = True
            self._change_state(RatState.WALK, keep_target=True)
            return

        self._start_jump_to(target)

    def _start_jump_to(self, target):
        dx = 0.0
        dy = target.y - self.y

        if dy < 0:
            self._transition_target = target
            self._jump_landing_surface = target
            self.vel_x = 0.0
            self.vel_y = JUMP_VEL_Y
            self._current_surface = None
            self._change_state(RatState.CLIMB)
            return

        self._jump_landing_surface = target
        t = 0.5
        self.vel_x = dx / t if t > 0 else 0.0
        self.vel_y = (dy - 0.5 * GRAVITY * t * t) / t if t > 0 else 0.0
        self._current_surface = None
        self._change_state(RatState.FALL)

    def _nearest_edge_x(self, target):
        cx = self.x + self.sprite_w / 2
        if self._current_surface:
            left_edge = self._current_surface.x_start
            right_edge = self._current_surface.x_end - self.sprite_w
        else:
            left_edge = target.x_start
            right_edge = target.x_end - self.sprite_w
        if right_edge < left_edge:
            return left_edge
        return left_edge if abs(cx - left_edge) <= abs(cx - right_edge) else right_edge

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
                and self.state not in (RatState.CLIMB, RatState.FALL, RatState.JUMP)):
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
        self._target_x = x
        self._change_state(RatState.WALK, keep_target=True)

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
        self._jump_landing_surface = None
        self.vel_x = 0.0
        self.vel_y = 0.0
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
