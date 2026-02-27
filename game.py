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

# --- Level definitions ---
# Each level: list of platforms [(x,y,w,h)], spikes [(x,y,w,h,dir)], goal rect
# Coordinates are in a 1920x1080 normalized space, scaled at runtime.
# We'll just tile levels for multiple "worlds".

def make_levels():
    levels = []

    # Level 1 – simple intro
    levels.append({
        "platforms": [
            (0,   900, 400, 30),
            (450, 750, 300, 30),
            (800, 600, 200, 30),
            (1050,450, 300, 30),
            (1400,300, 300, 30),
            (0,   900, 1920, 30),   # floor
        ],
        "spikes": [
            (500, 720, 40, 30, "up"),
            (600, 720, 40, 30, "up"),
            (860, 570, 40, 30, "up"),
        ],
        "goal": (1600, 220, 60, 80),
        "spawn": (80, 840),
    })

    # Level 2 – more complex
    levels.append({
        "platforms": [
            (0,   950, 1920, 30),   # floor
            (200, 750, 200, 20),
            (500, 600, 150, 20),
            (750, 700, 200, 20),
            (1000,500, 180, 20),
            (1250,350, 200, 20),
            (1500,500, 200, 20),
            (1700,650, 220, 20),
        ],
        "spikes": [
            (250, 720, 40, 30, "up"),
            (350, 720, 40, 30, "up"),
            (800, 670, 40, 30, "up"),
            (1050,470, 40, 30, "up"),
            (1300,320, 40, 30, "up"),
            (1560,470, 40, 30, "up"),
        ],
        "goal": (1820, 580, 60, 80),
        "spawn": (50, 880),
    })

    # Level 3 – vertical challenge
    levels.append({
        "platforms": [
            (0,   1000, 1920, 30),
            (100, 800,  150, 20),
            (350, 650,  150, 20),
            (600, 500,  150, 20),
            (850, 650,  150, 20),
            (1100,500, 150, 20),
            (1350,350, 150, 20),
            (1600,200, 200, 20),
        ],
        "spikes": [
            (120, 770,  40, 30, "up"),
            (370, 620,  40, 30, "up"),
            (620, 470,  40, 30, "up"),
            (870, 620,  40, 30, "up"),
            (1120,470, 40, 30, "up"),
            (1370,320, 40, 30, "up"),
        ],
        "goal": (1750, 120, 60, 80),
        "spawn": (50, 930),
    })

    # Level 4 – maze-like
    levels.append({
        "platforms": [
            (0,   1000, 1920, 30),
            (0,   700,  300, 20),
            (400, 850,  300, 20),
            (800, 700,  300, 20),
            (1200,850, 300, 20),
            (1600,700, 320, 20),
            (300, 550,  200, 20),
            (700, 400,  200, 20),
            (1100,550, 200, 20),
            (1500,400, 200, 20),
        ],
        "spikes": [
            (50,  670,  40, 30, "up"),
            (450, 820,  40, 30, "up"),
            (850, 670,  40, 30, "up"),
            (1250,820, 40, 30, "up"),
            (360, 520,  40, 30, "up"),
            (760, 370,  40, 30, "up"),
            (1160,520, 40, 30, "up"),
        ],
        "goal": (1620, 320, 60, 80),
        "spawn": (50, 930),
    })

    # Level 5 – boss chaos
    levels.append({
        "platforms": [
            (0,   1000, 1920, 30),
            (0,   0,    1920, 30),  # ceiling
            (0,   0,    30,   1080),# left wall platform
            (1890,0,    30,   1080),# right wall platform
            (200, 800,  100, 20),
            (400, 650,  100, 20),
            (600, 500,  100, 20),
            (800, 350,  100, 20),
            (1000,500, 100, 20),
            (1200,650, 100, 20),
            (1400,500, 100, 20),
            (1600,350, 100, 20),
        ],
        "spikes": [
            (230, 770,  40, 30, "up"),
            (430, 620,  40, 30, "up"),
            (630, 470,  40, 30, "up"),
            (830, 320,  40, 30, "up"),
            (230, 770,  30, 40, "right"),
            (1030,470, 40, 30, "up"),
            (1230,620, 40, 30, "up"),
            (1430,470, 40, 30, "up"),
            (1630,320, 40, 30, "up"),
        ],
        "goal": (900, 150, 60, 80),
        "spawn": (50, 930),
    })

    return levels

LEVELS_DATA = make_levels()


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
                    if self.level_idx >= len(LEVELS_DATA):
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

        # Draw goal
        gr = self.goal_rect
        pygame.draw.rect(screen, PALETTE["goal"], gr)
        pygame.draw.rect(screen, (200, 255, 220), gr, 3)
        # Pulsing star
        t = pygame.time.get_ticks() / 500
        for i in range(8):
            angle = i * math.pi / 4 + t
            ex = gr.centerx + math.cos(angle) * 20
            ey = gr.centery + math.sin(angle) * 20
            pygame.draw.circle(screen, (200, 255, 200), (int(ex), int(ey)), 4)

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
            f"LEVEL {self.level_idx + 1}/{len(LEVELS_DATA)}", True, PALETTE["text"])
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

        # Deaths
        dt_text = self.font_small.render(f"Deaths: {self.total_deaths}", True, (160, 160, 180))
        screen.blit(dt_text, (20, SH - 40))

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

