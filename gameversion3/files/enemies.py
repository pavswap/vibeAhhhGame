"""
enemies.py
──────────
All hostile / moving objects:

  RotatingObstacle   – spinning arm (instant kill on touch)
  FlyingEnemy        – homing ghost; behaviour randomised fresh every respawn
  ShootingEnemy      – stationary turret with aim wobble + random fire cadence
  EnemyProjectile    – bullet fired by ShootingEnemy
  PlayerProjectile   – bullet fired by the player
  VoidWall           – secret portal; crossing it wraps the player to the
                       opposite side of the screen
"""

import math, random
import pygame
from settings import SW, SH, PALETTE, GUN_PROJ_RADIUS


# ─────────────────────────────────────────────────────────────────────────────
# Geometry helper
# ─────────────────────────────────────────────────────────────────────────────

def _circle_vs_poly(cx, cy, r, poly):
    """True if the circle (cx,cy,r) intersects a convex polygon."""
    n = len(poly)
    for i in range(n):
        ax,ay = poly[i]; bx_,by_ = poly[(i+1)%n]
        ex,ey = bx_-ax, by_-ay
        t = max(0.0, min(1.0, ((cx-ax)*ex+(cy-ay)*ey)/(ex*ex+ey*ey+1e-9)))
        nx_,ny_ = ax+t*ex-cx, ay+t*ey-cy
        if nx_*nx_+ny_*ny_ <= r*r: return True
    # Centre-inside check (ray-casting)
    inside=False; j=n-1
    for i in range(n):
        xi,yi=poly[i]; xj,yj=poly[j]
        if ((yi>cy)!=(yj>cy)) and (cx<(xj-xi)*(cy-yi)/(yj-yi+1e-9)+xi):
            inside=not inside
        j=i
    return inside


# ─────────────────────────────────────────────────────────────────────────────
# RotatingObstacle
# ─────────────────────────────────────────────────────────────────────────────

class RotatingObstacle:
    """Orange spinning bar around a fixed pivot. Instant kill on contact."""

    def __init__(self, canvas_pivot, arm_len, arm_thick, speed_deg,
                 color=(255,140,0)):
        from utils import scale_pt
        px,py = scale_pt(canvas_pivot)
        self.pivot     = (px, py)
        self.arm_len   = int(arm_len   * SW / 1920)
        self.arm_thick = int(arm_thick * SW / 1920)
        self.speed     = math.radians(speed_deg)   # rad/s
        self.angle     = 0.0
        self.color     = color
        self._poly     = []

    def update(self, dt):
        self.angle += self.speed * dt
        cx,cy = self.pivot
        ca,sa = math.cos(self.angle), math.sin(self.angle)
        hl,ht = self.arm_len, self.arm_thick//2
        self._poly = [(cx+lx*ca-ly*sa, cy+lx*sa+ly*ca)
                      for lx,ly in [(-hl,-ht),(hl,-ht),(hl,ht),(-hl,ht)]]

    def draw(self, surf):
        if len(self._poly)==4:
            pygame.draw.polygon(surf, self.color, self._poly)
            pygame.draw.polygon(surf, (255,200,100), self._poly, 2)
        pygame.draw.circle(surf, (255,220,150), self.pivot, 6)
        pygame.draw.circle(surf, (200,160, 80), self.pivot, 6, 2)

    def collides_with_ball(self, bx, by, ball_r):
        if not self._poly: return False
        xs=[p[0] for p in self._poly]; ys=[p[1] for p in self._poly]
        if (bx+ball_r<min(xs) or bx-ball_r>max(xs) or
                by+ball_r<min(ys) or by-ball_r>max(ys)): return False
        return _circle_vs_poly(bx, by, ball_r, self._poly)


# ─────────────────────────────────────────────────────────────────────────────
# FlyingEnemy  – behaviour re-rolled on every instantiation
# ─────────────────────────────────────────────────────────────────────────────

_BEHAVIOURS = ["home","circle","zigzag","strafe","erratic"]

class FlyingEnemy:
    """
    Purple ghost that homes toward the player.
    Movement pattern is randomised each time the object is created (i.e. each
    respawn), making every encounter feel different.

    Contact costs 1 heart; 1.5 s invincibility window prevents spam damage.
    """
    INVINCIBILITY_TIME = 1.5
    RADIUS             = 22

    def __init__(self, canvas_pos, speed=80.0):
        from utils import scale_pt
        sx,sy = scale_pt(canvas_pos)
        self.x     = float(sx)
        self.y     = float(sy)
        self.speed = speed * SW / 1920
        self.angle = 0.0          # animation bobbing phase
        self.alive = True
        self._hit_cooldown = 0.0

        # ── randomised behaviour ──────────────────────────────────────────
        self._behaviour  = random.choice(_BEHAVIOURS)
        self._phase      = random.uniform(0, math.tau)
        self._orb_r      = random.uniform(120, 260)
        self._orb_spd    = random.choice([-1,1]) * random.uniform(0.6, 1.4)
        self._orb_cx     = self.x
        self._orb_cy     = self.y
        self._zig_dir    = random.choice([-1,1])
        self._zig_timer  = 0.0
        self._zig_period = random.uniform(0.5, 1.4)
        self._vx         = 0.0
        self._vy         = 0.0
        self._erratic_t  = 0.0

    # ── movement ──────────────────────────────────────────────────────────

    def update(self, dt, player_x, player_y):
        if not self.alive: return
        self.angle        += dt * 2.0
        self._hit_cooldown = max(0.0, self._hit_cooldown - dt)

        b = self._behaviour
        if b == "home":
            self._toward(player_x, player_y, self.speed, dt)

        elif b == "circle":
            # Orbit a lazy centre that slowly tracks the player
            self._orb_cx += (player_x - self._orb_cx) * 0.25 * dt
            self._orb_cy += (player_y - self._orb_cy) * 0.25 * dt
            self._phase  += self._orb_spd * dt
            tx = self._orb_cx + math.cos(self._phase) * self._orb_r
            ty = self._orb_cy + math.sin(self._phase) * self._orb_r
            self._toward(tx, ty, self.speed * 1.4, dt)

        elif b == "zigzag":
            dx=player_x-self.x; dy=player_y-self.y
            dist=math.hypot(dx,dy)
            if dist > 1:
                nx,ny = dx/dist, dy/dist
                px_,py_ = -ny, nx
                self._zig_timer += dt
                if self._zig_timer > self._zig_period:
                    self._zig_dir = -self._zig_dir
                    self._zig_timer = 0.0
                side = self._zig_dir * self.speed * 0.7
                self.x += (nx*self.speed + px_*side) * dt
                self.y += (ny*self.speed + py_*side) * dt

        elif b == "strafe":
            dx=player_x-self.x; dy=player_y-self.y
            dist=math.hypot(dx,dy)
            if dist > 200:
                self._toward(player_x, player_y, self.speed*0.6, dt)
            else:
                nx,ny = (dx/dist, dy/dist) if dist>1 else (1.0,0.0)
                px_,py_ = -ny, nx
                self._phase += dt * 1.2
                s = math.sin(self._phase * 2) * self.speed
                self.x += px_ * s * dt
                self.y += py_ * s * dt

        elif b == "erratic":
            self._erratic_t -= dt
            if self._erratic_t <= 0:
                ang = random.uniform(0, math.tau)
                spd = self.speed * random.uniform(0.5, 2.0)
                self._vx = math.cos(ang)*spd
                self._vy = math.sin(ang)*spd
                self._erratic_t = random.uniform(0.3, 0.9)
            # weak homing pull
            dx=player_x-self.x; dy=player_y-self.y; dist=math.hypot(dx,dy)
            if dist > 1:
                self._vx += dx/dist * self.speed*0.4 * dt
                self._vy += dy/dist * self.speed*0.4 * dt
            spd2 = math.hypot(self._vx, self._vy)
            cap  = self.speed * 2
            if spd2 > cap: self._vx*=cap/spd2; self._vy*=cap/spd2
            self.x += self._vx * dt; self.y += self._vy * dt

        # Keep inside screen
        r = self.RADIUS
        self.x = max(r, min(SW-r, self.x))
        self.y = max(r, min(SH-r, self.y))

    def _toward(self, tx, ty, spd, dt):
        dx=tx-self.x; dy=ty-self.y; dist=math.hypot(dx,dy)
        if dist > 1: self.x+=dx/dist*spd*dt; self.y+=dy/dist*spd*dt

    # ── drawing ───────────────────────────────────────────────────────────

    def draw(self, surf):
        if not self.alive: return
        ix,iy = int(self.x), int(self.y)
        bob   = int(math.sin(self.angle) * 4)
        # Glow
        for gr in range(self.RADIUS+14, self.RADIUS, -5):
            alpha = max(0, 100-(gr-self.RADIUS)*14)
            gs = pygame.Surface((gr*2,gr*2), pygame.SRCALPHA)
            pygame.draw.circle(gs,(180,60,255,alpha),(gr,gr),gr)
            surf.blit(gs,(ix-gr, iy+bob-gr))
        # Body
        pygame.draw.circle(surf,(200,80,255),(ix,iy+bob),self.RADIUS)
        pygame.draw.circle(surf,(230,160,255),(ix,iy+bob),self.RADIUS,2)
        # Eyes
        pygame.draw.circle(surf,(255,255,255),(ix-7,iy+bob-4),4)
        pygame.draw.circle(surf,(255,255,255),(ix+7,iy+bob-4),4)
        pygame.draw.circle(surf,(80,0,160),(ix-6,iy+bob-3),2)
        pygame.draw.circle(surf,(80,0,160),(ix+8,iy+bob-3),2)
        # Tentacles
        for i in range(5):
            tx2=ix-18+i*9; ty0=iy+bob+self.RADIUS-2
            ty1=ty0+10+int(math.sin(self.angle+i)*5)
            pygame.draw.line(surf,(180,60,220),(tx2,ty0),(tx2,ty1),2)

    # ── collision ─────────────────────────────────────────────────────────

    def try_hit(self, bx, by, ball_r):
        """Return True and start cooldown if ball overlaps enemy."""
        if not self.alive or self._hit_cooldown > 0: return False
        if math.hypot(bx-self.x, by-self.y) < ball_r+self.RADIUS-4:
            self._hit_cooldown = self.INVINCIBILITY_TIME
            return True
        return False


# ─────────────────────────────────────────────────────────────────────────────
# EnemyProjectile
# ─────────────────────────────────────────────────────────────────────────────

class EnemyProjectile:
    """Slow red ball fired by a ShootingEnemy."""
    RADIUS   = 8
    SPEED    = 220   # px/s screen space – intentionally slow

    def __init__(self, x, y, target_x, target_y):
        self.x=float(x); self.y=float(y)
        dx=target_x-x; dy=target_y-y; dist=math.hypot(dx,dy)
        if dist<1: dx,dy=1.0,0.0; dist=1.0
        self.vx = dx/dist*self.SPEED
        self.vy = dy/dist*self.SPEED
        self.alive = True
        self._age  = 0.0

    def update(self, dt):
        if not self.alive: return
        self.x+=self.vx*dt; self.y+=self.vy*dt
        self._age+=dt
        if self._age>6.0 or not(0<self.x<SW) or not(0<self.y<SH):
            self.alive=False

    def draw(self, surf):
        if not self.alive: return
        ix,iy=int(self.x),int(self.y)
        gs=pygame.Surface((self.RADIUS*4,self.RADIUS*4),pygame.SRCALPHA)
        pygame.draw.circle(gs,(255,60,60,55),(self.RADIUS*2,self.RADIUS*2),self.RADIUS*2)
        surf.blit(gs,(ix-self.RADIUS*2,iy-self.RADIUS*2))
        pygame.draw.circle(surf,PALETTE["enemy_proj"],(ix,iy),self.RADIUS)
        pygame.draw.circle(surf,(255,180,180),(ix,iy),self.RADIUS,2)

    def hits_ball(self, bx, by, ball_r):
        return self.alive and math.hypot(bx-self.x,by-self.y)<ball_r+self.RADIUS-2


# ─────────────────────────────────────────────────────────────────────────────
# ShootingEnemy
# ─────────────────────────────────────────────────────────────────────────────

class ShootingEnemy:
    """
    Stationary red turret.
    Aim wobble amplitude, frequency, and fire cadence are all randomised at
    construction so every turret feels distinct even within the same level.
    """
    RADIUS = 26

    def __init__(self, canvas_pos, fire_interval=2.5):
        from utils import scale_pt
        sx,sy = scale_pt(canvas_pos)
        self.x = float(sx); self.y = float(sy)
        self.alive = True
        self._aim_angle = 0.0
        self._time      = 0.0
        # Randomise fire timing so multiple turrets don't synch-fire
        self.fire_interval = fire_interval * random.uniform(0.6,1.4)
        self._fire_timer   = random.uniform(0, self.fire_interval)
        # Random aim wobble
        self._wob_amp   = random.uniform(0.0, 0.45)
        self._wob_freq  = random.uniform(0.4, 2.2)
        self._wob_phase = random.uniform(0, math.tau)

    def update(self, dt, player_x, player_y):
        if not self.alive: return
        self._time      += dt
        self._fire_timer -= dt
        dx=player_x-self.x; dy=player_y-self.y
        base = math.atan2(dy, dx)
        wob  = self._wob_amp * math.sin(self._wob_freq*self._time+self._wob_phase)
        self._aim_angle = base + wob

    def try_fire(self):
        """Returns a new EnemyProjectile, or None if not ready."""
        if not self.alive or self._fire_timer > 0: return None
        self._fire_timer = self.fire_interval
        tx = self.x + math.cos(self._aim_angle)*200
        ty = self.y + math.sin(self._aim_angle)*200
        return EnemyProjectile(self.x, self.y, tx, ty)

    def draw(self, surf):
        if not self.alive: return
        ix,iy=int(self.x),int(self.y)
        # Body
        pygame.draw.circle(surf,(140,25,25),(ix,iy),self.RADIUS)
        pygame.draw.circle(surf,(220,70,70),(ix,iy),self.RADIUS,3)
        # Barrel
        blen=self.RADIUS+14
        ex=ix+int(math.cos(self._aim_angle)*blen)
        ey=iy+int(math.sin(self._aim_angle)*blen)
        pygame.draw.line(surf,(200,55,55),(ix,iy),(ex,ey),7)
        pygame.draw.circle(surf,(255,90,90),(ex,ey),5)
        # Eye
        pygame.draw.circle(surf,(255,220,50),(ix,iy),6)
        pygame.draw.circle(surf,(200,150, 0),(ix,iy),3)


# ─────────────────────────────────────────────────────────────────────────────
# PlayerProjectile
# ─────────────────────────────────────────────────────────────────────────────

class PlayerProjectile:
    """Yellow bullet fired by the player. Destroys ghosts and turrets."""
    RADIUS = GUN_PROJ_RADIUS

    def __init__(self, x, y, vx, vy):
        self.x=float(x); self.y=float(y)
        self.vx=vx; self.vy=vy
        self.alive=True
        self._age=0.0

    def update(self, dt):
        if not self.alive: return
        self.x+=self.vx*dt; self.y+=self.vy*dt
        self._age+=dt
        if self._age>3.0 or not(0<self.x<SW) or not(0<self.y<SH):
            self.alive=False

    def draw(self, surf):
        if not self.alive: return
        ix,iy=int(self.x),int(self.y)
        gs=pygame.Surface((self.RADIUS*4,self.RADIUS*4),pygame.SRCALPHA)
        pygame.draw.circle(gs,(255,255,80,80),(self.RADIUS*2,self.RADIUS*2),self.RADIUS*2)
        surf.blit(gs,(ix-self.RADIUS*2,iy-self.RADIUS*2))
        pygame.draw.circle(surf,PALETTE["projectile"],(ix,iy),self.RADIUS)
        pygame.draw.circle(surf,(255,255,200),(ix,iy),self.RADIUS,2)

    def hits_enemy(self, ex, ey, radius):
        return self.alive and math.hypot(self.x-ex,self.y-ey)<self.RADIUS+radius-2


# ─────────────────────────────────────────────────────────────────────────────
# VoidWall
# ─────────────────────────────────────────────────────────────────────────────

class VoidWall:
    """
    A semi-transparent portal strip.  When the ball crosses it the player
    is wrapped to the opposite side of the screen (momentum is preserved).

    The visual is deliberately subtle – a faint shimmer – so the player has
    to explore to find it, matching the "secret" nature.
    """
    THICKNESS = 18   # screen pixels

    def __init__(self, orientation, position_frac):
        """
        orientation   : "vertical"   → left/right wrap
                        "horizontal" → top/bottom wrap
        position_frac : 0.0–1.0 fraction across screen width / height
        """
        self.orientation = orientation
        self._shimmer    = 0.0
        self._cooldown   = 0.0
        col = (80, 0, 180)

        if orientation == "vertical":
            px = int(position_frac * SW)
            self.rect = pygame.Rect(px - self.THICKNESS//2, 0, self.THICKNESS, SH)
        else:
            py = int(position_frac * SH)
            self.rect = pygame.Rect(0, py - self.THICKNESS//2, SW, self.THICKNESS)

        self._col = col

    def update(self, dt):
        self._shimmer  += dt * 3.0
        self._cooldown  = max(0.0, self._cooldown - dt)

    def draw(self, surf):
        alpha = int(28 + 22 * math.sin(self._shimmer))
        s = pygame.Surface((self.rect.w, self.rect.h), pygame.SRCALPHA)
        s.fill((*self._col, alpha))
        surf.blit(s, (self.rect.x, self.rect.y))
        # Single-pixel centre line
        col3 = self._col
        if self.orientation == "vertical":
            pygame.draw.line(surf, col3, (self.rect.centerx, 0),
                             (self.rect.centerx, SH), 1)
        else:
            pygame.draw.line(surf, col3, (0, self.rect.centery),
                             (SW, self.rect.centery), 1)

    def check_teleport(self, bx, by, ball_r):
        """Return (new_x, new_y) if a teleport should occur, else None."""
        if self._cooldown > 0: return None
        br = pygame.Rect(int(bx)-ball_r, int(by)-ball_r, ball_r*2, ball_r*2)
        if not br.colliderect(self.rect): return None
        self._cooldown = 0.6
        if self.orientation == "vertical":
            return (ball_r+10, by) if bx > SW/2 else (SW-ball_r-10, by)
        else:
            return (bx, ball_r+10) if by > SH/2 else (bx, SH-ball_r-10)
