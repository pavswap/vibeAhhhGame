"""
CHAOS BALL - A 2D platformer where dying changes the rules of physics.
Requirements: pip install pygame
Run: python chaos_ball.py
"""

import pygame
import sys
import random
import math

pygame.init()

# --- Screen Setup (fullscreen desktop size) ---
info = pygame.display.Info()
SW, SH = info.current_w, info.current_h
screen = pygame.display.set_mode((SW, SH))
pygame.display.set_caption("CHAOS BALL")
clock = pygame.time.Clock()
FPS = 60

# --- Colors ---
BG_COLORS = [
    (15, 10, 30),   # deep purple night
    (10, 30, 15),   # deep green
    (30, 10, 10),   # deep red
    (10, 20, 35),   # deep blue
    (30, 25, 5),    # deep amber
]

PALETTE = {
    "ball":        (255, 80,  50),
    "platform":    (70,  180, 255),
    "spike":       (255, 220, 50),
    "deadly_wall": (255, 50,  100),
    "safe_wall":   (60,  60,  80),
    "goal":        (50,  255, 150),
    "heart_full":  (255, 60,  80),
    "heart_empty": (80,  40,  50),
    "text":        (240, 240, 255),
    "shadow":      (0,   0,   0),
}

# --- Gravity directions ---
# (gx, gy) normalized; then scaled
GRAVITY_DIRS = [
    (0,  1),   # normal: down
    (0, -1),   # up
    (1,  0),   # right
    (-1, 0),   # left
]

GRAVITY_STRENGTH = 1400  # px/s^2  (feels weighty, never goes below this)

# ---------------------------------------------------------------------------
# PROCEDURAL LEVEL GENERATOR
# ---------------------------------------------------------------------------
# All coordinates are in 1920×1080 normalised space, scaled at runtime.
# The goal is ALWAYS placed at the exact centre (960, 540).
# Spawn is always in a safe corner far from the goal.
# Platforms come in several "shapes": horizontal slabs, vertical pillars,
# diagonal staircases, L-shapes, T-shapes, U-channels, and floating rings.
# Spikes are seeded on platform edges (top/bottom/left/right) after placement.
# ---------------------------------------------------------------------------

GOAL_W, GOAL_H = 70, 90          # normalised goal size
GOAL_CX, GOAL_CY = 960, 540      # always centre of 1920×1080

# Safe-zone radius around goal – no platforms/spikes inside here
GOAL_SAFE_R = 140

# Safe-zone radius around spawn – no spikes inside here
SPAWN_SAFE_R = 180

rng = random.Random()   # seeded per level so same level_idx gives same layout


def _overlap(ax, ay, aw, ah, bx, by, bw, bh, margin=20):
    """True if two rects (with margin) overlap."""
    return (ax - margin < bx + bw and ax + aw + margin > bx and
            ay - margin < by + bh and ay + ah + margin > by)


def _near_centre(x, y, w, h, safe_r=GOAL_SAFE_R):
    """True if rect is too close to the goal centre."""
    cx = x + w / 2
    cy = y + h / 2
    return math.hypot(cx - GOAL_CX, cy - GOAL_CY) < safe_r


def _near_spawn(x, y, w, h, sx, sy, safe_r=SPAWN_SAFE_R):
    cx = x + w / 2
    cy = y + h / 2
    return math.hypot(cx - sx, cy - sy) < safe_r


def _place_platform(existing, x, y, w, h, sx, sy):
    """Try to place a rect; reject if it overlaps existing or goal/spawn zones."""
    if _near_centre(x, y, w, h):
        return False
    if _near_spawn(x, y, w, h, sx, sy):
        return False
    # Clamp inside arena with margin
    margin = 40
    if x < margin or y < margin or x + w > 1920 - margin or y + h > 1080 - margin:
        return False
    for (ex, ey, ew, eh) in existing:
        if _overlap(x, y, w, h, ex, ey, ew, eh):
            return False
    existing.append((x, y, w, h))
    return True


def _add_shape(platforms, shape, sx, sy):
    """Add a platform shape (list of rects) if all pieces fit."""
    tmp = list(platforms)
    ok = True
    for (x, y, w, h) in shape:
        if not _place_platform(tmp, x, y, w, h, sx, sy):
            ok = False
            break
    if ok:
        platforms.clear()
        platforms.extend(tmp)
        return True
    return False


def _rand_slab(r):
    """Random horizontal slab."""
    w = r.randint(120, 340)
    h = r.randint(18, 28)
    x = r.randint(60, 1920 - 60 - w)
    y = r.randint(80, 1080 - 80 - h)
    return [(x, y, w, h)]


def _rand_pillar(r):
    """Random vertical pillar."""
    w = r.randint(18, 30)
    h = r.randint(100, 260)
    x = r.randint(60, 1920 - 60 - w)
    y = r.randint(80, 1080 - 80 - h)
    return [(x, y, w, h)]


def _rand_L(r):
    """L-shape: horizontal arm + vertical leg."""
    w1 = r.randint(160, 280)
    h1 = 22
    w2 = 22
    h2 = r.randint(80, 180)
    x = r.randint(60, 1920 - 60 - w1)
    y = r.randint(80, 1080 - 80 - h1 - h2)
    flip = r.choice([True, False])
    if flip:
        return [(x, y, w1, h1), (x + w1 - w2, y + h1, w2, h2)]
    else:
        return [(x, y, w1, h1), (x, y + h1, w2, h2)]


def _rand_T(r):
    """T-shape: wide horizontal + thin vertical stem."""
    w1 = r.randint(180, 300)
    h1 = 22
    w2 = 22
    h2 = r.randint(60, 140)
    x = r.randint(60, 1920 - 60 - w1)
    y = r.randint(80, 1080 - 80 - h1 - h2)
    return [(x, y, w1, h1), (x + w1 // 2 - w2 // 2, y + h1, w2, h2)]


def _rand_staircase(r):
    """3-step diagonal staircase."""
    step_w = r.randint(90, 150)
    step_h = 20
    dx = r.choice([-1, 1]) * r.randint(60, 100)
    dy = r.randint(60, 120)
    x0 = r.randint(200, 1920 - 200 - step_w)
    y0 = r.randint(200, 1080 - 200 - step_h)
    steps = []
    for i in range(3):
        steps.append((x0 + dx * i, y0 + dy * i, step_w, step_h))
    return steps


def _rand_U(r):
    """U-channel: two vertical walls + bottom slab."""
    bw = r.randint(160, 260)
    bh = 20
    wall_h = r.randint(80, 160)
    wall_w = 20
    x = r.randint(80, 1920 - 80 - bw)
    y = r.randint(80, 1080 - 80 - bh - wall_h)
    return [
        (x, y + wall_h, bw, bh),          # bottom
        (x, y, wall_w, wall_h),            # left wall
        (x + bw - wall_w, y, wall_w, wall_h),  # right wall
    ]


def _rand_ring(r):
    """Floating ring/square frame (4 thin slabs)."""
    size = r.randint(160, 260)
    t = 18
    x = r.randint(80, 1920 - 80 - size)
    y = r.randint(80, 1080 - 80 - size)
    return [
        (x,            y,            size, t),    # top
        (x,            y + size - t, size, t),    # bottom
        (x,            y + t,        t,    size - 2*t),  # left
        (x + size - t, y + t,        t,    size - 2*t),  # right
    ]


def _rand_cross(r):
    """Plus/cross shape."""
    arm = r.randint(100, 180)
    t   = 22
    x   = r.randint(100, 1920 - 100 - arm)
    y   = r.randint(100, 1080 - 100 - arm)
    cx2 = x + arm // 2 - t // 2
    cy2 = y + arm // 2 - t // 2
    return [
        (x,   cy2, arm, t),   # horizontal arm
        (cx2, y,   t,  arm),  # vertical arm
    ]


SHAPE_FUNCS = [
    _rand_slab, _rand_slab, _rand_slab,   # slabs most common
    _rand_pillar,
    _rand_L,
    _rand_T,
    _rand_staircase,
    _rand_U,
    _rand_ring,
    _rand_cross,
]


def _spike_for_platform(px, py, pw, ph, level_difficulty, r):
    """
    Return 0-3 spike tuples for a platform.
    Difficulty 0-4 controls density and multi-face spikes.
    Spike tuple: (x, y, w, h, direction)
    """
    spikes = []
    spike_h = 24
    spike_w = 24

    # Possible faces and their spike geometry
    faces = []
    faces.append(("up",    px, py - spike_h, pw, spike_h))        # top face
    faces.append(("down",  px, py + ph,      pw, spike_h))        # bottom face
    faces.append(("right", px + pw, py,      spike_h, ph))        # right face
    faces.append(("left",  px - spike_h, py, spike_h, ph))        # left face

    # How many faces to consider spiking (scale with difficulty)
    max_faces = 1 + level_difficulty // 2
    r.shuffle(faces)

    for i, (direction, sx, sy, sw, sh) in enumerate(faces[:max_faces]):
        # Probability of actually placing spikes on this face
        prob = 0.35 + level_difficulty * 0.10
        if r.random() > prob:
            continue
        # Clamp spike rect inside arena
        sx = max(10, min(1920 - 10 - sw, sx))
        sy = max(10, min(1080 - 10 - sh, sy))
        spikes.append((sx, sy, sw, sh, direction))

    return spikes


def generate_level(level_idx, seed=None):
    """
    Generate one level dict with:
      - goal at exact screen centre
      - spawn in a safe corner
      - 10-18 platform shapes (varied)
      - spikes seeded on platform edges
    """
    r = random.Random(seed if seed is not None else level_idx * 7919 + 42)

    difficulty = min(level_idx, 4)   # 0-4

    # Goal always at centre
    goal = (GOAL_CX - GOAL_W // 2, GOAL_CY - GOAL_H // 2, GOAL_W, GOAL_H)

    # Spawn: pick from 4 safe corner areas, pick one far from goal
    corners = [
        (80,  80),
        (1840, 80),
        (80,  1000),
        (1840, 1000),
    ]
    spawn = r.choice(corners)

    # --- Generate platforms ---
    platforms = []

    # Always add a solid floor/ceiling/wall on at least one edge so there's
    # always somewhere to land regardless of gravity direction.
    border_choice = r.choice(["floor", "ceiling", "left", "right"])
    if border_choice == "floor":
        platforms.append((0, 1050, 1920, 30))
    elif border_choice == "ceiling":
        platforms.append((0, 0, 1920, 30))
    elif border_choice == "left":
        platforms.append((0, 0, 30, 1080))
    else:
        platforms.append((1890, 0, 30, 1080))

    # Place a safe landing pad at spawn
    pad_w, pad_h = 200, 22
    pad_x = max(10, min(1920 - 10 - pad_w, spawn[0] - pad_w // 2))
    pad_y = max(10, min(1080 - 10 - pad_h, spawn[1] + 30))
    # Don't check near_centre for the spawn pad (it's already far)
    platforms.append((pad_x, pad_y, pad_w, pad_h))

    # Place random shapes
    target_shapes = 10 + difficulty * 2
    attempts = 0
    while len(platforms) < target_shapes + 2 and attempts < 400:
        attempts += 1
        shape_fn = r.choice(SHAPE_FUNCS)
        shape = shape_fn(r)
        _add_shape(platforms, shape, spawn[0], spawn[1])

    # --- Generate spikes ---
    spikes = []
    spike_blacklist_rects = [
        # no spikes near goal
        (GOAL_CX - GOAL_SAFE_R, GOAL_CY - GOAL_SAFE_R,
         GOAL_SAFE_R * 2, GOAL_SAFE_R * 2),
        # no spikes near spawn
        (spawn[0] - SPAWN_SAFE_R, spawn[1] - SPAWN_SAFE_R,
         SPAWN_SAFE_R * 2, SPAWN_SAFE_R * 2),
    ]

    for (px, py, pw, ph) in platforms[2:]:   # skip border + spawn pad
        for (sx, sy, sw, sh, direction) in _spike_for_platform(
                px, py, pw, ph, difficulty, r):
            # Check not in blacklist zones
            blocked = False
            for (bx, by, bw, bh) in spike_blacklist_rects:
                if _overlap(sx, sy, sw, sh, bx, by, bw, bh, margin=0):
                    blocked = True
                    break
            if not blocked:
                spikes.append((sx, sy, sw, sh, direction))

    return {
        "platforms": platforms,
        "spikes":    spikes,
        "goal":      goal,
        "spawn":     spawn,
    }


NUM_LEVELS = 8

LEVELS_DATA = [generate_level(i) for i in range(NUM_LEVELS)]


# --- Helper: scale rect from 1920x1080 to actual screen ---
def scale_rect(r):
    x, y, w, h = r
    return (
        int(x * SW / 1920),
        int(y * SH / 1080),
        int(w * SW / 1920),
        int(h * SH / 1080),
    )

def scale_pt(pt):
    x, y = pt
    return (int(x * SW / 1920), int(y * SH / 1080))


# --- Spike drawing ---
def draw_spike(surf, rect, direction, color):
    x, y, w, h = rect
    # direction: "up", "down", "left", "right"
    num = max(1, w // 20)
    tw = w // num
    for i in range(num):
        if direction == "up":
            pts = [
                (x + i*tw, y + h),
                (x + i*tw + tw//2, y),
                (x + i*tw + tw, y + h),
            ]
        elif direction == "down":
            pts = [
                (x + i*tw, y),
                (x + i*tw + tw//2, y + h),
                (x + i*tw + tw, y),
            ]
        elif direction == "right":
            pts = [
                (x, y + i*tw),
                (x + h, y + i*tw + tw//2),
                (x, y + i*tw + tw),
            ]
        elif direction == "left":
            pts = [
                (x + w, y + i*tw),
                (x, y + i*tw + tw//2),
                (x + w, y + i*tw + tw),
            ]
        pygame.draw.polygon(surf, color, pts)


# --- Heart drawing ---
def draw_heart(surf, cx, cy, size, color):
    # Simple heart using circles + triangle
    r = size // 2
    pygame.draw.circle(surf, color, (cx - r//2, cy - r//4), r//2)
    pygame.draw.circle(surf, color, (cx + r//2, cy - r//4), r//2)
    pts = [
        (cx - r, cy - r//4),
        (cx + r, cy - r//4),
        (cx, cy + r),
    ]
    pygame.draw.polygon(surf, color, pts)


# --- Particle System ---
class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        angle = random.uniform(0, 2*math.pi)
        speed = random.uniform(100, 400)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = random.uniform(0.4, 1.0)
        self.max_life = self.life
        self.color = color
        self.r = random.randint(3, 8)

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 200 * dt
        self.life -= dt

    def draw(self, surf):
        alpha = max(0, self.life / self.max_life)
        r = int(self.r * alpha)
        if r > 0:
            c = tuple(int(v * alpha) for v in self.color)
            pygame.draw.circle(surf, c, (int(self.x), int(self.y)), r)


# --- Screen Flash ---
class Flash:
    def __init__(self, color, duration=0.3):
        self.color = color
        self.duration = duration
        self.timer = duration

    def update(self, dt):
        self.timer -= dt

    def draw(self, surf):
        alpha = max(0, self.timer / self.duration)
        overlay = pygame.Surface((SW, SH), pygame.SRCALPHA)
        overlay.fill((*self.color, int(120 * alpha)))
        surf.blit(overlay, (0, 0))

    @property
    def done(self):
        return self.timer <= 0


# --- Game State ---
class Game:
    def __init__(self):
        self.font_big   = pygame.font.SysFont("consolas", 72, bold=True)
        self.font_med   = pygame.font.SysFont("consolas", 36, bold=True)
        self.font_small = pygame.font.SysFont("consolas", 24)

        self.reset_all()

    def reset_all(self):
        self.level_idx   = 0
        self.hearts      = 5
        self.total_deaths = 0
        self.state       = "play"   # "play", "dead_screen", "level_clear", "game_over", "win"
        self.gravity_dir = (0, 1)   # starts normal
        self.walls_deadly = False
        self.bg_color_idx = 0
        self.particles   = []
        self.flashes     = []
        self.death_timer = 0.0
        self.load_level()

    def load_level(self):
        data = LEVELS_DATA[self.level_idx % len(LEVELS_DATA)]
        self.platforms = [pygame.Rect(*scale_rect(p)) for p in data["platforms"]]
        self.spikes    = [(pygame.Rect(*scale_rect(s[:4])), s[4]) for s in data["spikes"]]
        self.goal_rect = pygame.Rect(*scale_rect(data["goal"]))
        sx, sy         = scale_pt(data["spawn"])
        ball_r         = int(22 * SW / 1920)
        self.ball_r    = ball_r
        self.bx        = float(sx)
        self.by        = float(sy)
        self.bvx       = 0.0
        self.bvy       = 0.0
        self.on_ground  = False
        self.jumps_left = 2   # double jump
        self.particles  = []
        self.flashes    = []

    def respawn_with_chaos(self):
        self.total_deaths += 1
        self.hearts -= 1

        # Emit death particles
        for _ in range(40):
            self.particles.append(Particle(self.bx, self.by, PALETTE["ball"]))

        self.flashes.append(Flash((255, 60, 60), 0.4))

        if self.hearts <= 0:
            self.state = "game_over"
            return

        # Change physics randomly
        self.gravity_dir = random.choice(GRAVITY_DIRS)

        # 40% chance walls become deadly (toggle)
        if random.random() < 0.4:
            self.walls_deadly = not self.walls_deadly

        self.bg_color_idx = (self.bg_color_idx + 1) % len(BG_COLORS)
        self.load_level()

    def get_gravity(self):
        gx, gy = self.gravity_dir
        return gx * GRAVITY_STRENGTH, gy * GRAVITY_STRENGTH

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()
                if event.key == pygame.K_r and self.state in ("game_over", "win"):
                    self.reset_all()
                    return
                if event.key == pygame.K_RETURN and self.state == "level_clear":
                    self.level_idx += 1
                    if self.level_idx >= NUM_LEVELS:
                        self.state = "win"
                    else:
                        self.state = "play"
                        self.load_level()
                # Jump: direction depends on gravity
                if event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w) and self.state == "play":
                    if self.jumps_left > 0:
                        gx, gy = self.gravity_dir
                        jump_speed = 700
                        self.bvx -= gx * jump_speed
                        self.bvy -= gy * jump_speed
                        self.jumps_left -= 1
                        self.on_ground = False
                        # Puff particles on double jump (second jump)
                        if self.jumps_left == 0:
                            for _ in range(18):
                                p = Particle(self.bx, self.by, (150, 200, 255))
                                p.vx *= 0.6
                                p.vy *= 0.6
                                self.particles.append(p)

    def update(self, dt):
        if self.state != "play":
            # Update particles and flashes even on other screens
            self.particles = [p for p in self.particles if p.life > 0]
            for p in self.particles: p.update(dt)
            self.flashes   = [f for f in self.flashes if not f.done]
            for f in self.flashes: f.update(dt)
            return

        keys = pygame.key.get_pressed()
        gx, gy = self.gravity_dir
        move_speed = 500

        # Determine "horizontal" movement axes based on gravity
        # If gravity is vertical (up/down), player moves left/right
        # If gravity is horizontal (left/right), player moves up/down
        if gy != 0:
            # Normal or flipped gravity – left/right movement
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.bvx -= move_speed * dt * 8
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.bvx += move_speed * dt * 8
            self.bvx *= 0.80  # friction
        else:
            # Sideways gravity – up/down movement
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                self.bvy -= move_speed * dt * 8
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                self.bvy += move_speed * dt * 8
            self.bvy *= 0.80

        # Apply gravity
        agx, agy = self.get_gravity()
        self.bvx += agx * dt
        self.bvy += agy * dt

        # Cap velocity
        max_vel = 1200
        self.bvx = max(-max_vel, min(max_vel, self.bvx))
        self.bvy = max(-max_vel, min(max_vel, self.bvy))

        # Move X
        self.bx += self.bvx * dt
        self.on_ground = False
        ball_rect = pygame.Rect(self.bx - self.ball_r, self.by - self.ball_r,
                                self.ball_r*2, self.ball_r*2)

        for plat in self.platforms:
            if ball_rect.colliderect(plat):
                # Resolve X
                if self.bvx > 0:
                    self.bx = plat.left - self.ball_r
                elif self.bvx < 0:
                    self.bx = plat.right + self.ball_r
                self.bvx = 0

        # Move Y
        self.by += self.bvy * dt
        ball_rect = pygame.Rect(self.bx - self.ball_r, self.by - self.ball_r,
                                self.ball_r*2, self.ball_r*2)

        for plat in self.platforms:
            if ball_rect.colliderect(plat):
                if self.bvy > 0:
                    self.by = plat.top - self.ball_r
                    if gy > 0:
                        self.on_ground = True
                        self.jumps_left = 2
                elif self.bvy < 0:
                    self.by = plat.bottom + self.ball_r
                    if gy < 0:
                        self.on_ground = True
                        self.jumps_left = 2
                # sideways gravity landing
                if gx > 0 and self.bvx > 0:
                    self.bx = plat.left - self.ball_r
                    self.on_ground = True
                    self.jumps_left = 2
                elif gx < 0 and self.bvx < 0:
                    self.bx = plat.right + self.ball_r
                    self.on_ground = True
                    self.jumps_left = 2
                self.bvy = 0

        ball_rect = pygame.Rect(self.bx - self.ball_r, self.by - self.ball_r,
                                self.ball_r*2, self.ball_r*2)

        # --- Wall collision ---
        hit_wall = False
        if self.bx - self.ball_r < 0:
            self.bx = self.ball_r
            self.bvx = abs(self.bvx) * 0.5
            hit_wall = True
            if gx < 0:
                self.on_ground = True
                self.jumps_left = 2
        if self.bx + self.ball_r > SW:
            self.bx = SW - self.ball_r
            self.bvx = -abs(self.bvx) * 0.5
            hit_wall = True
            if gx > 0:
                self.on_ground = True
                self.jumps_left = 2
        if self.by - self.ball_r < 0:
            self.by = self.ball_r
            self.bvy = abs(self.bvy) * 0.5
            hit_wall = True
            if gy < 0:
                self.on_ground = True
                self.jumps_left = 2
        if self.by + self.ball_r > SH:
            self.by = SH - self.ball_r
            self.bvy = -abs(self.bvy) * 0.5
            hit_wall = True
            if gy > 0:
                self.on_ground = True
                self.jumps_left = 2

        if hit_wall and self.walls_deadly:
            self.respawn_with_chaos()
            return

        # --- Spike collision ---
        ball_rect = pygame.Rect(self.bx - self.ball_r + 4, self.by - self.ball_r + 4,
                                self.ball_r*2 - 8, self.ball_r*2 - 8)
        for spike_rect, _ in self.spikes:
            if ball_rect.colliderect(spike_rect):
                self.respawn_with_chaos()
                return

        # --- Goal collision ---
        if ball_rect.colliderect(self.goal_rect):
            self.state = "level_clear"
            self.flashes.append(Flash((50, 255, 150), 0.5))
            for _ in range(60):
                self.particles.append(Particle(self.goal_rect.centerx,
                                               self.goal_rect.centery,
                                               PALETTE["goal"]))
            return

        # Update particles / flashes
        self.particles = [p for p in self.particles if p.life > 0]
        for p in self.particles: p.update(dt)
        self.flashes   = [f for f in self.flashes if not f.done]
        for f in self.flashes: f.update(dt)

    def draw(self):
        bg = BG_COLORS[self.bg_color_idx]
        screen.fill(bg)

        # Draw grid lines for atmosphere
        grid_col = tuple(min(255, c + 15) for c in bg)
        for x in range(0, SW, 80):
            pygame.draw.line(screen, grid_col, (x, 0), (x, SH), 1)
        for y in range(0, SH, 80):
            pygame.draw.line(screen, grid_col, (0, y), (SW, y), 1)

        # Walls deadly indicator
        wall_col = PALETTE["deadly_wall"] if self.walls_deadly else PALETTE["safe_wall"]
        border = 6
        pygame.draw.rect(screen, wall_col, (0, 0, SW, SH), border)

        # Draw platforms
        for plat in self.platforms:
            pygame.draw.rect(screen, PALETTE["platform"], plat)
            pygame.draw.rect(screen, (100, 220, 255), plat, 2)

        # Draw spikes
        for spike_rect, direction in self.spikes:
            draw_spike(screen, spike_rect, direction, PALETTE["spike"])

        # Draw goal (with radial glow)
        gr = self.goal_rect
        # Soft glow rings
        for ring in range(4, 0, -1):
            gs = pygame.Surface((gr.w + ring*16, gr.h + ring*16), pygame.SRCALPHA)
            alpha = int(40 - ring * 8)
            pygame.draw.rect(gs, (50, 255, 150, alpha),
                             (0, 0, gr.w + ring*16, gr.h + ring*16), border_radius=12)
            screen.blit(gs, (gr.x - ring*8, gr.y - ring*8))
        pygame.draw.rect(screen, PALETTE["goal"], gr, border_radius=6)
        pygame.draw.rect(screen, (200, 255, 220), gr, 3, border_radius=6)
        # Pulsing orbiting dots
        t = pygame.time.get_ticks() / 500
        for i in range(8):
            angle = i * math.pi / 4 + t
            ex = gr.centerx + math.cos(angle) * 22
            ey = gr.centery + math.sin(angle) * 22
            pygame.draw.circle(screen, (200, 255, 200), (int(ex), int(ey)), 4)
        # "EXIT" label
        exit_surf = self.font_small.render("EXIT", True, (20, 80, 40))
        screen.blit(exit_surf, (gr.centerx - exit_surf.get_width()//2,
                                gr.centery - exit_surf.get_height()//2))

        # Draw ball (with glow)
        bxi, byi = int(self.bx), int(self.by)
        for glow_r in range(self.ball_r + 12, self.ball_r - 1, -4):
            alpha_val = max(0, 120 - (glow_r - self.ball_r) * 20)
            glow_surf = pygame.Surface((glow_r*2, glow_r*2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (*PALETTE["ball"], alpha_val),
                               (glow_r, glow_r), glow_r)
            screen.blit(glow_surf, (bxi - glow_r, byi - glow_r))
        pygame.draw.circle(screen, PALETTE["ball"], (bxi, byi), self.ball_r)
        pygame.draw.circle(screen, (255, 200, 190), (bxi - 5, byi - 5), 6)

        # Double-jump indicator: dots below ball (relative to gravity)
        gx, gy = self.gravity_dir
        dot_offset = self.ball_r + 10
        for i in range(2):
            active = i < self.jumps_left
            dot_col = (150, 200, 255) if active else (50, 60, 80)
            dot_x = bxi + int(gx * dot_offset) + (i - 0) * int(gy * 0 + (1 - abs(gy)) * 14) + (i * 14 - 7) * int(abs(gy))
            dot_y = byi + int(gy * dot_offset) + (i * 14 - 7) * int(abs(gx))
            pygame.draw.circle(screen, dot_col, (dot_x, dot_y), 5)
            if active:
                pygame.draw.circle(screen, (200, 230, 255), (dot_x, dot_y), 3)

        # Draw particles
        for p in self.particles:
            p.draw(screen)

        # Draw flashes
        for f in self.flashes:
            f.draw(screen)

        # --- HUD ---
        self.draw_hud()

        # --- Overlays ---
        if self.state == "level_clear":
            self.draw_overlay("LEVEL CLEAR!", (50, 255, 150),
                              "Press ENTER to continue")
        elif self.state == "game_over":
            self.draw_overlay("GAME OVER", (255, 60, 60),
                              f"Deaths: {self.total_deaths}  |  Press R to restart")
        elif self.state == "win":
            self.draw_overlay("YOU WIN!", (255, 220, 50),
                              f"Deaths: {self.total_deaths}  |  Press R to play again")

        pygame.display.flip()

    def draw_hud(self):
        # Level
        lv_text = self.font_med.render(
            f"LEVEL {self.level_idx + 1}/{NUM_LEVELS}", True, PALETTE["text"])
        screen.blit(lv_text, (20, 20))

        # Gravity indicator
        gx, gy = self.gravity_dir
        dir_map = {(0,1): "↓ Gravity", (0,-1): "↑ Gravity",
                   (1,0): "→ Gravity", (-1,0): "← Gravity"}
        grav_text = self.font_small.render(dir_map.get((gx, gy), ""), True, (180, 180, 255))
        screen.blit(grav_text, (20, 65))

        # Walls indicator
        wall_txt = "⚠ DEADLY WALLS" if self.walls_deadly else "Safe Walls"
        wall_col = PALETTE["deadly_wall"] if self.walls_deadly else (120, 120, 160)
        wt = self.font_small.render(wall_txt, True, wall_col)
        screen.blit(wt, (20, 92))

        # Compass arrow pointing to exit (bottom-left area)
        compass_cx, compass_cy = 60, SH - 80
        pygame.draw.circle(screen, (30, 30, 50), (compass_cx, compass_cy), 28)
        pygame.draw.circle(screen, (60, 60, 90), (compass_cx, compass_cy), 28, 2)
        # Arrow direction toward goal centre
        goal_sx = SW // 2
        goal_sy = SH // 2
        dx = goal_sx - int(self.bx)
        dy = goal_sy - int(self.by)
        dist = math.hypot(dx, dy)
        if dist > 1:
            ndx, ndy = dx / dist, dy / dist
            ax = compass_cx + int(ndx * 18)
            ay = compass_cy + int(ndy * 18)
            # Arrowhead
            perp_x, perp_y = -ndy, ndx
            tip  = (ax, ay)
            base1 = (compass_cx + int((-ndx + perp_x * 0.5) * 10),
                     compass_cy + int((-ndy + perp_y * 0.5) * 10))
            base2 = (compass_cx + int((-ndx - perp_x * 0.5) * 10),
                     compass_cy + int((-ndy - perp_y * 0.5) * 10))
            pygame.draw.polygon(screen, PALETTE["goal"], [tip, base1, base2])
        # Label + deaths
        comp_lbl = self.font_small.render("EXIT", True, PALETTE["goal"])
        screen.blit(comp_lbl, (compass_cx - comp_lbl.get_width()//2, compass_cy + 32))
        dt_text = self.font_small.render(f"Deaths: {self.total_deaths}", True, (160, 160, 180))
        screen.blit(dt_text, (compass_cx + 36, compass_cy + 32))

        # Hearts – top right
        heart_size = 28
        heart_spacing = 44
        start_x = SW - (heart_spacing * 5) - 20
        for i in range(5):
            cx = start_x + i * heart_spacing + heart_size
            cy = 36
            color = PALETTE["heart_full"] if i < self.hearts else PALETTE["heart_empty"]
            draw_heart(screen, cx, cy, heart_size, color)

        # Controls hint (first level)
        if self.level_idx == 0 and self.total_deaths == 0:
            hint = self.font_small.render(
                "WASD / Arrows: Move   |   SPACE: Jump (x2 Double Jump)   |   ESC: Quit",
                True, (140, 140, 160))
            screen.blit(hint, (SW//2 - hint.get_width()//2, SH - 40))

    def draw_overlay(self, title, color, sub=""):
        overlay = pygame.Surface((SW, SH), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        screen.blit(overlay, (0, 0))

        t_surf = self.font_big.render(title, True, color)
        screen.blit(t_surf, (SW//2 - t_surf.get_width()//2, SH//2 - 80))

        if sub:
            s_surf = self.font_med.render(sub, True, PALETTE["text"])
            screen.blit(s_surf, (SW//2 - s_surf.get_width()//2, SH//2 + 20))


def main():
    game = Game()
    while True:
        dt = clock.tick(FPS) / 1000.0
        dt = min(dt, 0.05)  # cap delta time

        game.handle_events()
        game.update(dt)
        game.draw()


if __name__ == "__main__":
    main()
