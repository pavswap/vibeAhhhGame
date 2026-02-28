"""
game.py  –  Core game state and update logic. Zero pygame.draw calls.
"""

import random
import pygame
from settings import (
    SW, SH, BG_COLORS,
    GRAVITY_DIRS, GRAVITY_STRENGTH, NUM_LEVELS,
    GUN_AMMO_PER_LEVEL, GUN_PROJ_SPEED,
)
from utils import scale_rect, scale_pt
from particles import Particle, Flash
from level_generator import LEVELS_DATA
from enemies import (RotatingObstacle, FlyingEnemy,
                     ShootingEnemy, VoidWall, PlayerProjectile)


class Game:
    def __init__(self):
        self.reset_all()

    # ─────────────────────────────────────────────────────────────── init ──

    def reset_all(self):
        self.level_idx    = 0
        self.hearts       = 5
        self.total_deaths = 0
        self.state        = "play"
        self.gravity_dir  = (0, 1)
        self.walls_deadly = False
        self.bg_color_idx = 0
        self.particles    = []
        self.flashes      = []
        self.load_level()

    def start_at(self, level_idx):
        self.reset_all()
        self.level_idx = level_idx
        self.load_level()

    def load_level(self):
        data = LEVELS_DATA[self.level_idx % NUM_LEVELS]

        self.platforms = [pygame.Rect(*scale_rect(p)) for p in data["platforms"]]
        self.spikes    = [(pygame.Rect(*scale_rect(s[:4])), s[4])
                          for s in data["spikes"]]
        self.goal_rect = pygame.Rect(*scale_rect(data["goal"]))

        sx, sy = scale_pt(data["spawn"])
        self.ball_r = int(22 * SW / 1920)
        self.bx = float(sx);  self.by = float(sy)
        self.bvx = 0.0;       self.bvy = 0.0
        self.on_ground  = False
        self.jumps_left = 2

        # Rotating obstacles
        self.rotators = [RotatingObstacle(p, al, at, sp)
                         for p, al, at, sp in data.get("rotators", [])]

        # Flying enemies – fresh random behaviour each load
        self.enemies = [FlyingEnemy(pos, spd)
                        for pos, spd in data.get("enemies", [])]

        # Shooting turrets + their live projectiles
        self.shooters          = [ShootingEnemy(pos, fi)
                                   for pos, fi in data.get("shooters", [])]
        self.enemy_projectiles = []

        # Void walls
        self.void_walls = [VoidWall(ori, frac)
                           for ori, frac in data.get("void_walls", [])]

        # Player gun
        self.has_gun            = data.get("has_gun", False)
        self.ammo               = GUN_AMMO_PER_LEVEL if self.has_gun else 0
        self.player_projectiles = []

        self.particles = []
        self.flashes   = []

    # ──────────────────────────────────────────────────── death / damage ──

    def respawn_with_chaos(self):
        """Full death: lose heart, randomise gravity + wall mode, reload level."""
        self.total_deaths += 1
        self.hearts       -= 1
        for _ in range(40):
            self.particles.append(Particle(self.bx, self.by, (255, 80, 50)))
        self.flashes.append(Flash((255, 60, 60), 0.4))
        if self.hearts <= 0:
            self.state = "game_over"
            return
        
        old_gravity = self.gravity_dir
        self.gravity_dir  = random.choice(GRAVITY_DIRS)
        
        # If gravity direction changed, always disable deadly walls for fairness
        if old_gravity != self.gravity_dir:
            self.walls_deadly = False
        else:
            # Only randomize wall state if gravity stayed the same
            if random.random() < 0.4:
                self.walls_deadly = not self.walls_deadly
        
        self.bg_color_idx = (self.bg_color_idx + 1) % len(BG_COLORS)
        self.load_level()

    def lose_heart(self):
        """Partial damage (enemy contact / projectile hit): lose 1 heart."""
        self.hearts -= 1
        self.flashes.append(Flash((180, 0, 200), 0.35))
        for _ in range(20):
            self.particles.append(Particle(self.bx, self.by, (200, 80, 255)))
        if self.hearts <= 0:
            self.state = "game_over"

    # ───────────────────────────────────────────────────────── events ──

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); raise SystemExit

            if event.type == pygame.KEYDOWN:
                k = event.key
                if k == pygame.K_ESCAPE:
                    pygame.quit(); raise SystemExit

                # Restart / menu
                if k == pygame.K_r and self.state in ("game_over", "win"):
                    self.reset_all(); return

                # Advance level
                if k == pygame.K_RETURN and self.state == "level_clear":
                    self.level_idx += 1
                    if self.level_idx >= NUM_LEVELS:
                        self.state = "win"
                    else:
                        self.state = "play"
                        self.load_level()

                if self.state != "play":
                    continue

                # ── Jump ──────────────────────────────────────────────────
                # SPACE always jumps regardless of gravity or gun status.
                # When gun is NOT equipped, add directional keys for jumping:
                #   - For vertical gravity: W/UP jumps
                #   - For horizontal gravity: A/D or LEFT/RIGHT jumps
                gx, gy = self.gravity_dir
                jump_keys = [pygame.K_SPACE]
                
                if not self.has_gun:
                    # Add direction-specific jump keys when no gun
                    if gy != 0:  # Vertical gravity
                        jump_keys += [pygame.K_w, pygame.K_UP]
                    else:  # Horizontal gravity
                        jump_keys += [pygame.K_a, pygame.K_d, 
                                     pygame.K_LEFT, pygame.K_RIGHT]
                
                if k in jump_keys:
                    self._try_jump()

                # ── Shoot (arrow keys, gun levels only) ───────────────────
                if self.has_gun and self.ammo > 0:
                    shoot_map = {
                        pygame.K_UP:    ( 0, -1),
                        pygame.K_DOWN:  ( 0,  1),
                        pygame.K_LEFT:  (-1,  0),
                        pygame.K_RIGHT: ( 1,  0),
                    }
                    if k in shoot_map:
                        dx, dy = shoot_map[k]
                        self.player_projectiles.append(
                            PlayerProjectile(self.bx, self.by,
                                             dx * GUN_PROJ_SPEED,
                                             dy * GUN_PROJ_SPEED))
                        self.ammo -= 1
                        for _ in range(8):
                            p = Particle(self.bx, self.by, (255, 255, 100))
                            p.vx *= 0.4; p.vy *= 0.4
                            self.particles.append(p)

    def _try_jump(self):
        if self.jumps_left > 0:
            gx, gy = self.gravity_dir
            self.bvx       -= gx * 700
            self.bvy       -= gy * 700
            self.jumps_left -= 1
            self.on_ground   = False
            if self.jumps_left == 0:          # second jump – puff effect
                for _ in range(18):
                    p = Particle(self.bx, self.by, (150, 200, 255))
                    p.vx *= 0.6; p.vy *= 0.6
                    self.particles.append(p)

    # ───────────────────────────────────────────────────────── update ──

    def update(self, dt):
        self._tick_effects(dt)
        if self.state != "play":
            return
        self._apply_movement(dt)
        self._apply_gravity(dt)
        self._cap_velocity()
        self._move_x(dt)
        self._move_y(dt)
        self._check_screen_walls()
        self._check_void_walls()
        self._check_spikes()
        self._check_rotators(dt)
        self._check_enemies(dt)
        self._check_shooters(dt)
        self._tick_player_projectiles(dt)
        self._check_goal()

    # ─────────────────────────────────────────────────────── physics ──

    def _apply_movement(self, dt):
        keys = pygame.key.get_pressed()
        gx, gy = self.gravity_dir
        a = 4000 * dt
        
        # Determine perpendicular movement based on gravity direction
        if self.has_gun:
            # Gun active: arrow keys shoot → movement via WASD only
            if gy != 0:  # Gravity is vertical (up or down)
                # Horizontal movement with A/D
                if keys[pygame.K_a]: self.bvx -= a
                if keys[pygame.K_d]: self.bvx += a
                self.bvx *= 0.80
            else:  # Gravity is horizontal (left or right)
                # Vertical movement with W/S
                if keys[pygame.K_w]: self.bvy -= a
                if keys[pygame.K_s]: self.bvy += a
                self.bvy *= 0.80
        else:
            # No gun: both arrow keys and WASD work for movement
            if gy != 0:  # Gravity is vertical
                # Horizontal movement
                if keys[pygame.K_LEFT]  or keys[pygame.K_a]: self.bvx -= a
                if keys[pygame.K_RIGHT] or keys[pygame.K_d]: self.bvx += a
                self.bvx *= 0.80
            else:  # Gravity is horizontal
                # Vertical movement
                if keys[pygame.K_UP]   or keys[pygame.K_w]: self.bvy -= a
                if keys[pygame.K_DOWN] or keys[pygame.K_s]: self.bvy += a
                self.bvy *= 0.80

    def _apply_gravity(self, dt):
        gx, gy = self.gravity_dir
        self.bvx += gx * GRAVITY_STRENGTH * dt
        self.bvy += gy * GRAVITY_STRENGTH * dt

    def _cap_velocity(self):
        mv = 1200
        self.bvx = max(-mv, min(mv, self.bvx))
        self.bvy = max(-mv, min(mv, self.bvy))

    def _move_x(self, dt):
        self.bx       += self.bvx * dt
        self.on_ground = False
        rect           = self._ball_rect()
        for p in self.platforms:
            if rect.colliderect(p):
                if self.bvx > 0: self.bx = p.left  - self.ball_r
                else:            self.bx = p.right + self.ball_r
                self.bvx = 0

    def _move_y(self, dt):
        gx, gy = self.gravity_dir
        self.by += self.bvy * dt
        rect    = self._ball_rect()
        for p in self.platforms:
            if rect.colliderect(p):
                if self.bvy > 0:
                    self.by = p.top - self.ball_r
                    if gy > 0: self.on_ground = True; self.jumps_left = 2
                elif self.bvy < 0:
                    self.by = p.bottom + self.ball_r
                    if gy < 0: self.on_ground = True; self.jumps_left = 2
                if gx > 0 and self.bvx > 0:
                    self.bx = p.left - self.ball_r
                    self.on_ground = True; self.jumps_left = 2
                elif gx < 0 and self.bvx < 0:
                    self.bx = p.right + self.ball_r
                    self.on_ground = True; self.jumps_left = 2
                self.bvy = 0

    def _check_screen_walls(self):
        gx, gy = self.gravity_dir
        hit    = False
        if self.bx - self.ball_r < 0:
            self.bx = self.ball_r; self.bvx = abs(self.bvx)*0.5; hit=True
            if gx < 0: self.on_ground=True; self.jumps_left=2
        if self.bx + self.ball_r > SW:
            self.bx = SW-self.ball_r; self.bvx = -abs(self.bvx)*0.5; hit=True
            if gx > 0: self.on_ground=True; self.jumps_left=2
        if self.by - self.ball_r < 0:
            self.by = self.ball_r; self.bvy = abs(self.bvy)*0.5; hit=True
            if gy < 0: self.on_ground=True; self.jumps_left=2
        if self.by + self.ball_r > SH:
            self.by = SH-self.ball_r; self.bvy = -abs(self.bvy)*0.5; hit=True
            if gy > 0: self.on_ground=True; self.jumps_left=2
        if hit and self.walls_deadly:
            self.respawn_with_chaos()

    def _check_void_walls(self):
        for vw in self.void_walls:
            result = vw.check_teleport(self.bx, self.by, self.ball_r)
            if result:
                self.bx, self.by = float(result[0]), float(result[1])
                for _ in range(18):
                    self.particles.append(
                        Particle(self.bx, self.by, (100, 50, 255)))
                self.flashes.append(Flash((60, 0, 160), 0.22))
                break   # only one teleport per frame

    def _check_spikes(self):
        rect = self._ball_rect(shrink=4)
        for sr, _ in self.spikes:
            if rect.colliderect(sr):
                self.respawn_with_chaos(); return

    def _check_rotators(self, dt):
        for rot in self.rotators:
            rot.update(dt)
            if rot.collides_with_ball(self.bx, self.by, self.ball_r):
                self.respawn_with_chaos(); return

    def _check_enemies(self, dt):
        for enemy in self.enemies:
            enemy.update(dt, self.bx, self.by)
            if enemy.try_hit(self.bx, self.by, self.ball_r):
                self.lose_heart()
                if self.state == "game_over": return
        # Player bullets vs flying enemies
        for proj in self.player_projectiles:
            if not proj.alive: continue
            for enemy in self.enemies:
                if enemy.alive and proj.hits_enemy(enemy.x, enemy.y, enemy.RADIUS):
                    enemy.alive = False; proj.alive = False
                    for _ in range(25):
                        self.particles.append(
                            Particle(enemy.x, enemy.y, (200, 80, 255)))

    def _check_shooters(self, dt):
        for shooter in self.shooters:
            shooter.update(dt, self.bx, self.by)
            ep = shooter.try_fire()
            if ep: self.enemy_projectiles.append(ep)

        for ep in self.enemy_projectiles:
            ep.update(dt)
            if ep.hits_ball(self.bx, self.by, self.ball_r):
                ep.alive = False
                self.lose_heart()
                if self.state == "game_over": return

        # Player bullets vs turrets
        for proj in self.player_projectiles:
            if not proj.alive: continue
            for shooter in self.shooters:
                if shooter.alive and proj.hits_enemy(shooter.x, shooter.y,
                                                     shooter.RADIUS):
                    shooter.alive = False; proj.alive = False
                    for _ in range(30):
                        self.particles.append(
                            Particle(shooter.x, shooter.y, (255, 60, 60)))

        self.enemy_projectiles = [ep for ep in self.enemy_projectiles if ep.alive]

    def _tick_player_projectiles(self, dt):
        for proj in self.player_projectiles:
            proj.update(dt)
        self.player_projectiles = [p for p in self.player_projectiles if p.alive]

    def _check_goal(self):
        if self._ball_rect(shrink=4).colliderect(self.goal_rect):
            self.state = "level_clear"
            self.flashes.append(Flash((50, 255, 150), 0.5))
            for _ in range(60):
                self.particles.append(
                    Particle(self.goal_rect.centerx,
                             self.goal_rect.centery, (50, 255, 150)))

    # ─────────────────────────────────────────────── effects / utility ──

    def _tick_effects(self, dt):
        self.particles = [p for p in self.particles if p.alive]
        for p in self.particles: p.update(dt)
        self.flashes   = [f for f in self.flashes if not f.done]
        for f in self.flashes: f.update(dt)
        # Void walls need their shimmer + cooldown ticked every frame
        for vw in self.void_walls: vw.update(dt)

    def _ball_rect(self, shrink=0):
        r = self.ball_r - shrink
        return pygame.Rect(int(self.bx)-r, int(self.by)-r, r*2, r*2)
