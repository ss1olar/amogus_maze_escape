import pygame
import random
import time
import sys
import os
import json
from collections import deque

# --- CONFIG ---
pygame.init()
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
SAVE_FILE = "data.json"

BG_COLOR = (5, 5, 12)
WALL_COLOR = (20, 20, 25)
PATH_COLOR = (240, 240, 240)
IMPOSTOR_PURPLE = (140, 0, 180)
VISOR_COLOR = (150, 200, 255)

GOLD_BASE, GOLD_HIGH = (218, 165, 32), (255, 215, 0)
PLAT_BASE, PLAT_HIGH = (160, 160, 170), (220, 220, 230)
RUBY_BASE, RUBY_HIGH = (180, 0, 30), (255, 50, 80)
RHOD_BASE, RHOD_HIGH = (180, 100, 255), (230, 180, 255)

f_l = pygame.font.Font(None, 80)
f_m = pygame.font.Font(None, 45)
f_s = pygame.font.Font(None, 28)

def load_data():
    default = {
        'credits': 1000, 'keys': 1, 'cases': 5,
        'owned_colors': [[0, 0, 255]], 'owned_hats': ['none'],
        'curr_col': [0, 0, 255], 'curr_hat': 'none',
        'extreme_beaten': False
    }
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r") as f: 
                d = json.load(f)
                for k, v in default.items():
                    if k not in d: d[k] = v
                return d
        except: return default
    return default

def save_data(data):
    with open(SAVE_FILE, "w") as f: json.dump(data, f, indent=4)

def draw_medal(surf, cx, cy, size, m_type):
    if m_type == 'none': return
    s, h = size, size // 2
    if m_type == 'gold':
        r = (cx-h, cy-s//4, s, s//2)
        pygame.draw.rect(surf, GOLD_BASE, r, border_radius=2)
        pygame.draw.rect(surf, GOLD_HIGH, (cx-h, cy-s//4, s, s//6), border_radius=2)
    elif m_type == 'plat':
        pts = [(cx + h * pygame.math.Vector2(1, 0).rotate(i*60).x, cy + h * pygame.math.Vector2(1, 0).rotate(i*60).y) for i in range(6)]
        pygame.draw.polygon(surf, PLAT_BASE, pts)
    elif m_type == 'rhodium':
        pts = [(cx - h, cy - h), (cx + h, cy - h), (cx, cy + h)] 
        pygame.draw.polygon(surf, RHOD_BASE, pts)
    elif m_type == 'ruby':
        pts = [(cx, cy-h), (cx+h//1.5, cy), (cx, cy+h), (cx-h//1.5, cy)]
        pygame.draw.polygon(surf, RUBY_BASE, pts)
    pygame.draw.polygon(surf, (0,0,0), pts if 'pts' in locals() else [(cx-h, cy-s//4), (cx+h, cy-s//4), (cx+h, cy+s//4), (cx-h, cy+s//4)], 1)

def draw_amogus(screen, x, y, size, col, hat, alpha=255):
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    c = list(col) if isinstance(col, (list, tuple)) else [0,0,255]
    pygame.draw.rect(surf, (*c, alpha), (size//6, size//4, size-size//3, size-size//2), border_radius=size//4)
    pygame.draw.rect(surf, (*VISOR_COLOR, alpha), (size//2, size//3, size//3, size//5), border_radius=size//10)
    draw_medal(surf, size//2, size//8, size//2.2, hat)
    screen.blit(surf, (x, y))

class Maze:
    def __init__(self, w, h):
        self.width, self.height = w, h
        self.grid = [[1 for _ in range(w)] for _ in range(h)]
        self.generate(); self.end = (w-2, h-2); self.grid[self.end[1]][self.end[0]] = 0
    def generate(self):
        stack = [(1, 1)]; self.grid[1][1] = 0; visited = {(1, 1)}
        while stack:
            cx, cy = stack[-1]; neighbors = []
            for dx, dy in [(0,-2),(2,0),(0,2),(-2,0)]:
                nx, ny = cx+dx, cy+dy
                if 0<nx<self.width-1 and 0<ny<self.height-1 and (nx, ny) not in visited: neighbors.append((nx, ny))
            if neighbors:
                nx, ny = random.choice(neighbors)
                self.grid[(cy+ny)//2][(cx+nx)//2] = 0; self.grid[ny][nx] = 0
                visited.add((nx, ny)); stack.append((nx, ny))
            else: stack.pop()
    def get_path(self, start, end):
        q = deque([(start, [])]); v = {start}
        while q:
            (cx, cy), path = q.popleft()
            if (cx, cy) == end: return path + [(cx, cy)]
            for dx, dy in [(0,1),(0,-1),(1,0),(-1,0)]:
                nx, ny = cx+dx, cy+dy
                if 0<=nx<self.width and 0<=ny<self.height and self.grid[ny][nx]==0 and (nx, ny) not in v:
                    v.add((nx, ny)); q.append(((nx, ny), path + [(cx, cy)]))
        return []

class Chaser:
    def __init__(self, x, y, speed):
        self.x, self.y, self.speed, self.last_move = x, y, speed, 0
    def update(self, p, maze, ct):
        if ct - self.last_move >= self.speed:
            q = deque([((self.x, self.y), [])]); v = {(self.x, self.y)}
            while q:
                (cx, cy), path = q.popleft()
                if (cx, cy) == (p.x, p.y):
                    if path: self.x += path[0][0]; self.y += path[0][1]
                    break
                for dx, dy in [(0,1),(0,-1),(1,0),(-1,0)]:
                    nx, ny = cx+dx, cy+dy
                    if 0<=nx<maze.width and 0<=ny<maze.height and maze.grid[ny][nx]==0 and (nx, ny) not in v:
                        v.add((nx, ny)); q.append(((nx, ny), path + [(dx, dy)]))
            self.last_move = ct

def main():
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    data = load_data(); state = "MENU"; clock = pygame.time.Clock()
    maze = p = None; chasers = []; diff = ""; case_items = []; case_offset = 0; case_speed = 0; won_item = None
    light_broken = False; target_key = None; reaction_start = 0; immortal_until = 0; start_time = 0

    while True:
        ct = time.time(); screen.fill(BG_COLOR); mx, my = pygame.mouse.get_pos()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: save_data(data); pygame.quit(); sys.exit()
            if ev.type == pygame.MOUSEBUTTONDOWN:
                if state == "MENU":
                    if 300<mx<500:
                        if 200<my<250: state = "SELECT"
                        elif 270<my<320: state = "SHOP"
                        elif 340<my<390: state = "CASES"
                        elif 410<my<460: state = "INV"
                elif state == "SELECT":
                    for i, d_opt in enumerate(['easy', 'medium', 'hard', 'extreme']):
                        if 30+i*185 < mx < 30+i*185+170 and 180 < my < 240: diff = d_opt; state = "GEN"
                    if 325<mx<475 and 510<my<560: state = "MENU"
                elif state == "SHOP":
                    if 250<mx<550 and 250<my<310 and data['credits'] >= 500: data['credits'] -= 500; data['keys'] += 1
                    if 325<mx<475 and 500<my<550: state = "MENU"
                elif state == "INV":
                    if 325<mx<475 and 510<my<560: state = "MENU"
                    for i in range(len(data['owned_colors'])):
                        rx, ry = 50+(i%8)*80, 140+(i//8)*80
                        if rx<mx<rx+70 and ry<my<ry+70: data['curr_col'] = data['owned_colors'][i]
                    for i in range(len(data['owned_hats'])):
                        rx, ry = 50+(i%8)*80, 320+(i//8)*80
                        if rx<mx<rx+70 and ry<my<ry+70: data['curr_hat'] = data['owned_hats'][i]
                elif state == "CASES":
                    if 300<mx<500 and 200<my<350 and data['keys']>0 and data['cases']>0:
                        state="OPENING"; data['keys']-=1; data['cases']-=1; case_items=[{'type':random.choice(['col','hat']), 'val':[random.randint(50,255),random.randint(50,255),random.randint(50,255)] if random.randint(0,1)==0 else random.choice(['gold','plat','ruby'])} for _ in range(60)]; case_speed,case_offset=40,0
                    if 325<mx<475 and 500<my<550: state = "MENU"
                elif state == "OPENING" and won_item and 300<mx<500 and 480<my<530:
                    if won_item['type']=='col': data['owned_colors'].append(won_item['val'])
                    else: data['owned_hats'].append(won_item['val'])
                    state="CASES"; won_item=None
                elif state in ["DEAD", "WIN"] and 325<mx<475 and 510<my<560: state = "MENU"
                save_data(data)

            if ev.type == pygame.KEYDOWN and state == "PLAY":
                if not light_broken:
                    if ev.key in [pygame.K_w, pygame.K_UP] and maze.grid[p.y-1][p.x]==0: p.y-=1
                    elif ev.key in [pygame.K_s, pygame.K_DOWN] and maze.grid[p.y+1][p.x]==0: p.y+=1
                    elif ev.key in [pygame.K_a, pygame.K_LEFT] and maze.grid[p.y][p.x-1]==0: p.x-=1
                    elif ev.key in [pygame.K_d, pygame.K_RIGHT] and maze.grid[p.y][p.x+1]==0: p.x+=1
                elif pygame.key.name(ev.key).upper() == target_key: light_broken = False

        if state == "GEN":
            light_broken = False; mw, mh, nc, sp = {'easy':(15,15,0,0), 'medium':(25,21,1,0.3), 'hard':(41,33,1,0.2), 'extreme':(65,49,3,0.18)}[diff]
            maze = Maze(mw, mh); p = type('P',(),{'x':1,'y':1})()
            m_path = maze.get_path((1, 1), maze.end)
            chasers = []
            while len(chasers) < nc:
                tx, ty = random.randint(1, mw-2), random.randint(1, mh-2)
                if maze.grid[ty][tx] == 0 and abs(tx-p.x)+abs(ty-p.y) > 15 and (tx, ty) not in m_path: chasers.append(Chaser(tx, ty, sp))
            cs = min(740//mw, 480//mh); ox, oy = (800-mw*cs)//2, (600-mh*cs)//2+30
            state = "PLAY"; start_time = time.time(); immortal_until = ct + 5

        elif state == "PLAY":
            elapsed = ct - start_time
            if ct > immortal_until and diff in ['hard','extreme'] and not light_broken and random.random()<0.007: light_broken, reaction_start, target_key = True, ct, random.choice(['W','A','S','D'])
            if light_broken and ct-reaction_start>0.8: state = "DEAD"
            for y in range(maze.height):
                for x in range(maze.width):
                    c = WALL_COLOR if maze.grid[y][x] else PATH_COLOR
                    if (x,y)==maze.end: c=(0,255,0)
                    pygame.draw.rect(screen, c, (ox+x*cs, oy+y*cs, cs, cs))
            a = 100 if ct < immortal_until and int(ct*10)%2==0 else 255
            draw_amogus(screen, ox+p.x*cs, oy+p.y*cs, cs, data['curr_col'], data['curr_hat'], a)
            for ch in chasers:
                if elapsed > 2.5: ch.update(p, maze, ct)
                draw_amogus(screen, ox+ch.x*cs, oy+ch.y*cs, cs, IMPOSTOR_PURPLE, 'none')
                if ch.x==p.x and ch.y==p.y and ct > immortal_until: state="DEAD"
            if light_broken:
                s=pygame.Surface((800,600)); s.set_alpha(200); screen.blit(s,(0,0))
                screen.blit(f_m.render(f"FIX IT! PRESS: {target_key}", True, (255,0,0)), (300, 280))
            if (p.x, p.y)==maze.end:
                data['credits'] += 1500 if diff=='extreme' else 500; data['extreme_beaten'] = True
                state = "WIN"

        elif state == "MENU":
            screen.blit(f_l.render("AMOGUS MAZE", True, (255,255,255)), (220, 80))
            if data.get('extreme_beaten'):
                screen.blit(f_s.render("★ EXTREME CONQUEROR ★", True, RHOD_HIGH), (285, 140))
            for i, txt in enumerate(["START", "SHOP", "CASES", "INV"]):
                pygame.draw.rect(screen, (40,40,60), (300, 200+i*70, 200, 50), border_radius=10)
                screen.blit(f_m.render(txt, True, (255,255,255)), (345, 210+i*70))

        elif state == "INV":
            # ИСПРАВЛЕННЫЙ ИНВЕНТАРЬ
            screen.blit(f_m.render("INVENTORY", True, (255,255,255)), (320, 50))
            # Цвета
            for i, c in enumerate(data['owned_colors'][:16]):
                rx, ry = 50+(i%8)*80, 140+(i//8)*80
                pygame.draw.rect(screen, (30,30,40), (rx, ry, 70, 70), border_radius=5)
                if c == data['curr_col']: 
                    pygame.draw.rect(screen, GOLD_HIGH, (rx, ry, 70, 70), 3, border_radius=5)
                draw_amogus(screen, rx+10, ry+10, 50, c, 'none')
            # Шапки
            for i, h in enumerate(data['owned_hats'][:16]):
                rx, ry = 50+(i%8)*80, 320+(i//8)*80
                pygame.draw.rect(screen, (30,30,40), (rx, ry, 70, 70), border_radius=5)
                if h == data['curr_hat']: 
                    pygame.draw.rect(screen, GOLD_HIGH, (rx, ry, 70, 70), 3, border_radius=5)
                draw_amogus(screen, rx+10, ry+10, 50, (80,80,80), h)
            
            pygame.draw.rect(screen, (70,70,70), (325, 510, 150, 50), border_radius=10)
            screen.blit(f_m.render("BACK", True, (255,255,255)), (360, 520))

        # Экраны SELECT/SHOP/CASES/WIN/DEAD остаются без изменений
        elif state == "SELECT":
            screen.blit(f_m.render("SELECT LEVEL", True, (255,255,255)), (280, 100))
            for i, (t, c) in enumerate([("EASY",(50,150,50)),("MEDIUM",(50,100,150)),("HARD",(150,100,50)),("EXTREME",(150,50,50))]):
                pygame.draw.rect(screen, c, (30+i*185, 180, 170, 60), border_radius=10)
                screen.blit(f_s.render(t, True, (255,255,255)), (30+i*185+45, 200))
            pygame.draw.rect(screen, (70,70,70), (325, 510, 150, 50), border_radius=10); screen.blit(f_m.render("BACK", True, (255,255,255)), (360, 520))
        elif state == "WIN":
            screen.fill((0,40,0)); screen.blit(f_l.render("MISSION CLEAR", True, (0,255,0)), (180, 250))
            pygame.draw.rect(screen, (70,70,70), (325, 510, 150, 50), border_radius=10); screen.blit(f_m.render("BACK", True, (255,255,255)), (360, 520))
        elif state == "DEAD":
            screen.fill((40,0,0)); screen.blit(f_l.render("WASTED", True, (255,0,0)), (280, 250))
            pygame.draw.rect(screen, (70,70,70), (325, 510, 150, 50), border_radius=10); screen.blit(f_m.render("BACK", True, (255,255,255)), (360, 520))
        elif state == "SHOP":
            screen.blit(f_m.render(f"CREDITS: {data['credits']}", True, GOLD_HIGH), (300, 150))
            pygame.draw.rect(screen, (30,80,30), (250, 250, 300, 60), border_radius=10); screen.blit(f_s.render("BUY KEY (500 CR)", True, (255,255,255)), (320, 275))
            pygame.draw.rect(screen, (70,70,70), (325, 500, 150, 50), border_radius=10); screen.blit(f_m.render("BACK", True, (255,255,255)), (360, 510))
        elif state == "CASES":
            screen.blit(f_m.render(f"KEYS: {data['keys']}  CASES: {data['cases']}", True, (255,255,255)), (250, 150))
            pygame.draw.rect(screen, (100,60,20), (300, 250, 200, 100), border_radius=10); screen.blit(f_m.render("OPEN", True, (255,255,255)), (365, 285))
            pygame.draw.rect(screen, (70,70,70), (325, 500, 150, 50), border_radius=10); screen.blit(f_m.render("BACK", True, (255,255,255)), (360, 510))
        elif state == "OPENING":
            if case_speed > 0.1: case_offset += case_speed; case_speed *= 0.98
            else:
                case_speed = 0
                if not won_item: won_item = case_items[int((case_offset+400)//130)%60]
            for i, it in enumerate(case_items):
                x = (i*130)-case_offset+50
                if -150<x<850:
                    pygame.draw.rect(screen, (40,40,60), (x, 265, 110, 130), border_radius=5)
                    draw_amogus(screen, x+25, 290, 60, it['val'] if it['type']=='col' else (100,100,100), it['val'] if it['type']=='hat' else 'none')
            pygame.draw.polygon(screen, (255,255,255), [(400, 410), (385, 430), (415, 430)])
            if case_speed == 0 and won_item:
                pygame.draw.rect(screen, (50,150,50), (300, 480, 200, 50), border_radius=10); screen.blit(f_s.render("COLLECT", True, (255,255,255)), (355, 495))

        pygame.display.flip(); clock.tick(60)

if __name__ == "__main__": main()