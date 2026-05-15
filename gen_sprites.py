"""
Generate pixel art rat sprites programmatically.
States: idle, walk, jump, fall, climb, sit
Each frame is 32x32 RGBA.
"""
from PIL import Image, ImageDraw
import os

OUT_DIR = os.path.join(os.path.dirname(__file__), "assets", "sprites", "generated")
SIZE = 32

RAT_BODY = (139, 90, 43, 255)
RAT_BELLY = (180, 140, 90, 255)
RAT_EYE = (20, 20, 20, 255)
RAT_EYE_WHITE = (240, 240, 240, 255)
RAT_NOSE = (200, 120, 120, 255)
RAT_EAR_INNER = (200, 140, 140, 255)
RAT_TAIL = (160, 110, 60, 255)
RAT_PAW = (120, 80, 40, 255)


def _new():
    return Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))


def _draw_rat_profile(draw, body_pts, head_offset=(0, 0), ear_up=True,
                      eye_open=True, tail_pts=None, legs=None,
                      facing="left"):
    """Draw a side-view rat from point lists."""
    if legs is None:
        legs = []
    if tail_pts is None:
        tail_pts = []

    if tail_pts:
        draw.line(tail_pts, fill=RAT_TAIL, width=2)

    draw.polygon(body_pts, fill=RAT_BODY)

    belly_pts = []
    for px, py in body_pts:
        belly_pts.append((px, py + 2))
    if len(belly_pts) >= 3:
        draw.polygon(belly_pts, fill=RAT_BELLY)

    hx, hy = head_offset
    head_cx, head_cy = body_pts[0][0] + hx, body_pts[0][1] + hy

    draw.ellipse(
        [head_cx - 5, head_cy - 4, head_cx + 5, head_cy + 4],
        fill=RAT_BODY,
    )

    if ear_up:
        ear_x = head_cx + (-1 if facing == "left" else 1)
        draw.polygon(
            [(ear_x - 3, head_cy - 3), (ear_x, head_cy - 9), (ear_x + 3, head_cy - 3)],
            fill=RAT_BODY,
        )
        draw.polygon(
            [(ear_x - 2, head_cy - 4), (ear_x, head_cy - 8), (ear_x + 2, head_cy - 4)],
            fill=RAT_EAR_INNER,
        )

    if eye_open:
        ex = head_cx + (-2 if facing == "left" else 2)
        draw.rectangle([ex - 1, head_cy - 1, ex + 1, head_cy + 1], fill=RAT_EYE_WHITE)
        draw.rectangle([ex, head_cy - 1, ex + 1, head_cy], fill=RAT_EYE)
    else:
        ex = head_cx + (-2 if facing == "left" else 2)
        draw.line([(ex - 1, head_cy), (ex + 1, head_cy)], fill=RAT_EYE, width=1)

    nose_x = head_cx + (-5 if facing == "left" else 5)
    draw.rectangle([nose_x, head_cy, nose_x + 1, head_cy + 1], fill=RAT_NOSE)

    for lx1, ly1, lx2, ly2 in legs:
        draw.line([(lx1, ly1), (lx2, ly2)], fill=RAT_PAW, width=2)


def gen_idle(n_frames=4):
    frames = []
    for i in range(n_frames):
        img = _new()
        d = ImageDraw.Draw(img)
        bob = (i % 2) - 0.5
        _draw_rat_profile(
            d,
            body_pts=[(8, 18 + bob), (22, 18 + bob), (22, 24 + bob), (8, 24 + bob)],
            head_offset=(-3, -6),
            tail_pts=[(22, 22 + bob), (28, 18 + bob), (30, 14 + bob)],
            legs=[
                (10, 24 + bob, 10, 28),
                (14, 24 + bob, 14, 28),
                (18, 24 + bob, 18, 28),
            ],
        )
        frames.append(img)
    return frames


def gen_walk(n_frames=6):
    frames = []
    for i in range(n_frames):
        img = _new()
        d = ImageDraw.Draw(img)
        phase = i / n_frames * 3.14159 * 2
        leg_offsets = [
            int(2 * (1 if (i + j * 3) % 4 < 2 else -1))
            for j in range(3)
        ]
        _draw_rat_profile(
            d,
            body_pts=[(6, 17), (23, 17), (23, 23), (6, 23)],
            head_offset=(-2, -5),
            tail_pts=[(23, 20), (28, 15), (30, 11)],
            legs=[
                (8, 23, 8 + leg_offsets[0], 28),
                (13, 23, 13 + leg_offsets[1], 28),
                (19, 23, 19 + leg_offsets[2], 28),
            ],
        )
        frames.append(img)
    return frames


def gen_jump(n_frames=4):
    frames = []
    for i in range(n_frames):
        img = _new()
        d = ImageDraw.Draw(img)
        stretch = i * 2
        body_y = 20 - stretch
        _draw_rat_profile(
            d,
            body_pts=[
                (6, body_y), (24, body_y),
                (24, body_y + 6), (6, body_y + 6),
            ],
            head_offset=(-2, -5),
            ear_up=(i < 3),
            tail_pts=[(24, body_y + 3), (29, body_y - 2 + i), (31, body_y - 6 + i * 2)],
            legs=[
                (8, body_y + 6, 6, body_y + 10),
                (12, body_y + 6, 10, body_y + 10),
                (18, body_y + 6, 20, body_y + 10),
            ],
        )
        frames.append(img)
    return frames


def gen_fall(n_frames=4):
    frames = []
    for i in range(n_frames):
        img = _new()
        d = ImageDraw.Draw(img)
        spread = i
        _draw_rat_profile(
            d,
            body_pts=[
                (7, 14), (24, 14),
                (24, 20), (7, 20),
            ],
            head_offset=(-2, -5),
            tail_pts=[(24, 17), (29, 20 + spread), (30, 25 + spread)],
            legs=[
                (8, 20, 5, 24 + spread),
                (13, 20, 11, 24 + spread),
                (19, 20, 22, 24 + spread),
            ],
        )
        frames.append(img)
    return frames


def gen_climb(n_frames=4):
    frames = []
    for i in range(n_frames):
        img = _new()
        d = ImageDraw.Draw(img)
        leg_lift = [(-2 if (i + j) % 2 == 0 else 2) for j in range(4)]
        _draw_rat_profile(
            d,
            body_pts=[(10, 12), (24, 12), (24, 20), (10, 20)],
            head_offset=(0, -6),
            ear_up=True,
            tail_pts=[(24, 16), (28, 10 - i), (30, 6 - i)],
            legs=[
                (12, 20, 12 + leg_lift[0], 26),
                (16, 20, 16 + leg_lift[1], 26),
                (20, 20, 20 + leg_lift[2], 26),
            ],
        )
        frames.append(img)
    return frames


def gen_sit(n_frames=3):
    frames = []
    for i in range(n_frames):
        img = _new()
        d = ImageDraw.Draw(img)
        blink = (i == 1)
        _draw_rat_profile(
            d,
            body_pts=[(8, 18), (22, 16), (24, 24), (8, 26)],
            head_offset=(-2, -6),
            eye_open=(not blink),
            tail_pts=[(22, 22), (27, 18), (29, 22)],
            legs=[
                (10, 26, 10, 28),
                (14, 26, 14, 28),
            ],
        )
        frames.append(img)
    return frames


def generate_all():
    os.makedirs(OUT_DIR, exist_ok=True)

    sheets = {
        "idle": gen_idle,
        "walk": gen_walk,
        "jump": gen_jump,
        "fall": gen_fall,
        "climb": gen_climb,
        "sit": gen_sit,
    }

    for name, gen_fn in sheets.items():
        frames = gen_fn()
        total_w = SIZE * len(frames)
        sheet = Image.new("RGBA", (total_w, SIZE), (0, 0, 0, 0))
        for i, frame in enumerate(frames):
            sheet.paste(frame, (i * SIZE, 0))
        path = os.path.join(OUT_DIR, f"rat_{name}.png")
        sheet.save(path)
        print(f"  {path}: {len(frames)} frames")

    print("Done.")


if __name__ == "__main__":
    generate_all()
