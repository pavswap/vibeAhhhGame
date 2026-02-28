"""
renderer.py  –  All pygame.draw / blit calls. Zero game state owned here.
"""

import math
import pygame
from settings import (
    SW, SH, BG_COLORS, PALETTE, NUM_LEVELS,
    TIER_BASIC_END, TIER_SPINNER_END, TIER_VOID_END, TIER_SHOOTER_START,
    GUN_AMMO_PER_LEVEL,
)
from utils import draw_spike, draw_heart


class Renderer:
    def __init__(self, screen):
        self.screen     = screen
        self.font_big   = pygame.font.SysFont("consolas", 72, bold=True)
        self.font_med   = pygame.font.SysFont("consolas", 36, bold=True)
        self.font_small = pygame.font.SysFont("consolas", 24)
        self.font_tiny  = pygame.font.SysFont("consolas", 18)

    # ─────────────────────────────────────────────────────────── master ──

    def draw(self, game):
        self._draw_background(game)
        self._draw_border(game)
        self._draw_void_walls(game)
        self._draw_platforms(game)
        self._draw_spikes(game)
        self._draw_rotators(game)
        self._draw_enemies(game)
        self._draw_shooters(game)
        self._draw_enemy_projectiles(game)
        self._draw_player_projectiles(game)
        self._draw_goal(game)
        self._draw_ball(game)
        self._draw_particles(game)
        self._draw_flashes(game)
        self._draw_hud(game)
        self._draw_overlay(game)
        pygame.display.flip()

    # ────────────────────────────────────────────────────── background ──

    def _draw_background(self, game):
        bg = BG_COLORS[game.bg_color_idx % len(BG_COLORS)]
        self.screen.fill(bg)
        gc = tuple(min(255, c+15) for c in bg)
        for x in range(0, SW, 80):
            pygame.draw.line(self.screen, gc, (x,0), (x,SH), 1)
        for y in range(0, SH, 80):
            pygame.draw.line(self.screen, gc, (0,y), (SW,y), 1)

    def _draw_border(self, game):
        col = PALETTE["deadly_wall"] if game.walls_deadly else PALETTE["safe_wall"]
        pygame.draw.rect(self.screen, col, (0,0,SW,SH), 6)

    # ───────────────────────────────────────────────────── void walls ──

    def _draw_void_walls(self, game):
        for vw in game.void_walls:
            vw.draw(self.screen)

    # ──────────────────────────────────────────────────── world items ──

    def _draw_platforms(self, game):
        for p in game.platforms:
            pygame.draw.rect(self.screen, PALETTE["platform"], p)
            pygame.draw.rect(self.screen, (100,220,255), p, 2)

    def _draw_spikes(self, game):
        for sr, d in game.spikes:
            draw_spike(self.screen, sr, d, PALETTE["spike"])

    def _draw_rotators(self, game):
        for rot in game.rotators:
            rot.draw(self.screen)

    def _draw_enemies(self, game):
        for e in game.enemies:
            e.draw(self.screen)

    def _draw_shooters(self, game):
        for s in game.shooters:
            s.draw(self.screen)

    def _draw_enemy_projectiles(self, game):
        for ep in game.enemy_projectiles:
            ep.draw(self.screen)

    def _draw_player_projectiles(self, game):
        for pp in game.player_projectiles:
            pp.draw(self.screen)

    # ──────────────────────────────────────────────────────────── goal ──

    def _draw_goal(self, game):
        gr = game.goal_rect
        for ring in range(4, 0, -1):
            gs = pygame.Surface((gr.w+ring*16, gr.h+ring*16), pygame.SRCALPHA)
            pygame.draw.rect(gs, (50,255,150,max(0,40-ring*8)),
                             (0,0,gr.w+ring*16,gr.h+ring*16), border_radius=12)
            self.screen.blit(gs, (gr.x-ring*8, gr.y-ring*8))
        pygame.draw.rect(self.screen, PALETTE["goal"], gr, border_radius=6)
        pygame.draw.rect(self.screen, (200,255,220), gr, 3, border_radius=6)
        t = pygame.time.get_ticks() / 500
        for i in range(8):
            a = i*math.pi/4 + t
            pygame.draw.circle(self.screen, (200,255,200),
                               (int(gr.centerx+math.cos(a)*22),
                                int(gr.centery+math.sin(a)*22)), 4)
        lbl = self.font_small.render("EXIT", True, (20,80,40))
        self.screen.blit(lbl, (gr.centerx-lbl.get_width()//2,
                               gr.centery-lbl.get_height()//2))

    # ──────────────────────────────────────────────────────────── ball ──

    def _draw_ball(self, game):
        bxi, byi = int(game.bx), int(game.by)
        r = game.ball_r

        # Glow rings
        for gr2 in range(r+12, r-1, -4):
            av = max(0, 120-(gr2-r)*20)
            gs = pygame.Surface((gr2*2, gr2*2), pygame.SRCALPHA)
            pygame.draw.circle(gs, (*PALETTE["ball"],av), (gr2,gr2), gr2)
            self.screen.blit(gs, (bxi-gr2, byi-gr2))

        pygame.draw.circle(self.screen, PALETTE["ball"], (bxi,byi), r)
        pygame.draw.circle(self.screen, (255,200,190), (bxi-5,byi-5), 6)

        # Gold ring when gun is equipped and loaded
        if game.has_gun and game.ammo > 0:
            pygame.draw.circle(self.screen, (255,240,80), (bxi,byi), r+5, 2)

        # Double-jump indicator dots
        gx, gy = game.gravity_dir
        doff   = r + 10
        for i in range(2):
            active = i < game.jumps_left
            dc = (150,200,255) if active else (50,60,80)
            dx2 = bxi + int(gx*doff) + (i*14-7)*int(abs(gy))
            dy2 = byi + int(gy*doff) + (i*14-7)*int(abs(gx))
            pygame.draw.circle(self.screen, dc, (dx2,dy2), 5)
            if active:
                pygame.draw.circle(self.screen, (200,230,255), (dx2,dy2), 3)

    # ───────────────────────────────────────────────────────── effects ──

    def _draw_particles(self, game):
        for p in game.particles: p.draw(self.screen)

    def _draw_flashes(self, game):
        for f in game.flashes: f.draw(self.screen)

    # ──────────────────────────────────────────────────────────── HUD ──

    def _draw_hud(self, game):
        idx = game.level_idx

        # Tier badge
        if   idx < TIER_BASIC_END:    tier_lbl,tier_col = "BASIC",    (70,180,255)
        elif idx < TIER_SPINNER_END:  tier_lbl,tier_col = "SPINNERS", (255,160, 40)
        elif idx < TIER_SHOOTER_START: tier_lbl,tier_col = "VOID",    ( 80,  0,180)
        else:                          tier_lbl,tier_col = "HAUNTED",  (200, 80,255)

        lv = self.font_med.render(f"LEVEL {idx+1}/{NUM_LEVELS}", True, PALETTE["text"])
        self.screen.blit(lv, (20, 20))
        badge = self.font_small.render(f"[ {tier_lbl} ]", True, tier_col)
        self.screen.blit(badge, (20+lv.get_width()+14, 30))

        # Gravity label
        gx,gy = game.gravity_dir
        dmap  = {(0,1):"↓ Gravity",(0,-1):"↑ Gravity",
                 (1,0):"→ Gravity",(-1,0):"← Gravity"}
        self.screen.blit(
            self.font_small.render(dmap.get((gx,gy),""),True,(180,180,255)),
            (20, 65))

        # Wall state
        wtxt = "⚠ DEADLY WALLS" if game.walls_deadly else "Safe Walls"
        wcol = PALETTE["deadly_wall"] if game.walls_deadly else (120,120,160)
        self.screen.blit(self.font_small.render(wtxt,True,wcol),(20,92))

        # Enemy / hazard counts
        row = 120
        if game.enemies:
            alive_e = sum(1 for e in game.enemies if e.alive)
            self.screen.blit(
                self.font_small.render(f"👻  x{alive_e}",True,(200,80,255)),(20,row))
            row += 26
        if game.shooters:
            alive_s = sum(1 for s in game.shooters if s.alive)
            self.screen.blit(
                self.font_small.render(f"🔴  x{alive_s}",True,(255,80,80)),(20,row))
            row += 26
        if game.void_walls:
            self.screen.blit(
                self.font_small.render(
                    f"🌀  x{len(game.void_walls)}",True,(120,60,220)),(20,row))
            row += 26

        # Ammo strip
        if game.has_gun:
            self._draw_ammo(game, row)
            row += 30

        # Compass
        self._draw_compass(game)

        # Hearts (top-right)
        hs,hsp = 28,44
        sx2    = SW - hsp*5 - 20
        for i in range(5):
            col2 = PALETTE["heart_full"] if i < game.hearts else PALETTE["heart_empty"]
            draw_heart(self.screen, sx2+i*hsp+hs, 36, hs, col2)

        # One-time hints
        self._draw_hints(game)

    def _draw_ammo(self, game, y):
        lbl = self.font_small.render("AMMO:", True, (255,255,100))
        self.screen.blit(lbl, (20, y))
        for i in range(GUN_AMMO_PER_LEVEL):
            cx = 20 + lbl.get_width() + 12 + i*22
            cy = y + 11
            col = (255,255,80) if i < game.ammo else (55,55,30)
            pygame.draw.circle(self.screen, col, (cx,cy), 7)
            if i < game.ammo:
                pygame.draw.circle(self.screen,(255,255,200),(cx,cy),7,2)

    def _draw_compass(self, game):
        cx,cy = 60, SH-80
        pygame.draw.circle(self.screen,(30,30,50),(cx,cy),28)
        pygame.draw.circle(self.screen,(60,60,90),(cx,cy),28,2)
        dx = SW//2 - int(game.bx); dy = SH//2 - int(game.by)
        dist = math.hypot(dx,dy)
        if dist > 1:
            ndx,ndy = dx/dist, dy/dist
            tip=(cx+int(ndx*18),cy+int(ndy*18))
            px_,py_ = -ndy, ndx
            b1=(cx+int((-ndx+px_*0.5)*10),cy+int((-ndy+py_*0.5)*10))
            b2=(cx+int((-ndx-px_*0.5)*10),cy+int((-ndy-py_*0.5)*10))
            pygame.draw.polygon(self.screen,PALETTE["goal"],[tip,b1,b2])
        lbl=self.font_small.render("EXIT",True,PALETTE["goal"])
        self.screen.blit(lbl,(cx-lbl.get_width()//2,cy+32))
        dt2=self.font_small.render(f"Deaths:{game.total_deaths}",True,(160,160,180))
        self.screen.blit(dt2,(cx+36,cy+32))

    def _draw_hints(self, game):
        idx = game.level_idx
        if game.state != "play": return
        lines = []
        # Level 1 controls
        if idx == 0 and game.total_deaths == 0:
            lines.append(("WASD: Move  |  SPACE: Jump (×2)  |  ESC: Quit",
                          (140,140,160)))
        # First gun level
        if game.has_gun and idx == TIER_SPINNER_END and game.total_deaths == 0:
            lines.append(("🔫 ARROW KEYS: Shoot  |  WASD: Move  |  3 shots per level",
                          (255,255,100)))
        # First void level
        if game.void_walls and idx == TIER_SPINNER_END and game.total_deaths == 0:
            lines.append(("🌀 Faint purple walls are secret portals – "
                          "cross one to warp to the other side!",
                          (160,100,255)))
        y = SH - 38
        for txt, col in reversed(lines):
            s = self.font_tiny.render(txt, True, col)
            self.screen.blit(s, (SW//2-s.get_width()//2, y))
            y -= 24

    # ─────────────────────────────────────────────────────── overlays ──

    def _draw_overlay(self, game):
        if game.state == "level_clear":
            self._overlay("LEVEL CLEAR!", (50,255,150), "Press ENTER to continue")
        elif game.state == "game_over":
            self._overlay("GAME OVER", (255,60,60),
                          f"Deaths: {game.total_deaths}  |  R: restart  |  M: menu")
        elif game.state == "win":
            self._overlay("YOU WIN!", (255,220,50),
                          f"Deaths: {game.total_deaths}  |  R: play again  |  M: menu")

    def _overlay(self, title, color, sub=""):
        panel = pygame.Surface((SW,SH), pygame.SRCALPHA)
        panel.fill((0,0,0,160))
        self.screen.blit(panel,(0,0))
        ts = self.font_big.render(title, True, color)
        self.screen.blit(ts,(SW//2-ts.get_width()//2, SH//2-80))
        if sub:
            ss = self.font_med.render(sub, True, PALETTE["text"])
            self.screen.blit(ss,(SW//2-ss.get_width()//2, SH//2+20))
