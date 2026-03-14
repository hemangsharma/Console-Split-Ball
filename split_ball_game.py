import math
import random
import sys
import pygame

pygame.init()

WIDTH, HEIGHT = 1280, 760
HUD_H = max(60, int(HEIGHT * 0.05))
GAME_H = HEIGHT - HUD_H

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Console Split Ball")
clock = pygame.time.Clock()

BG = (6, 10, 8)
GRID = (12, 24, 16)
PANEL = (8, 16, 10)
BORDER = (38, 255, 122)
TEXT = (170, 255, 190)
TEXT_DIM = (105, 170, 120)
TEXT_SOFT = (70, 120, 82)
BALL_COLORS = [
    (255, 190, 110),
    (255, 120, 120),
    (120, 210, 255),
    (180, 255, 150),
    (220, 170, 255),
    (255, 235, 120),
]

font = pygame.font.SysFont("consolas", 22)
small = pygame.font.SysFont("consolas", 18)

GRAVITY = 920
AIR_FRICTION = 0.999
WALL_RESTITUTION = 0.84
WALL_FRICTION = 0.986
COLLISION_RESTITUTION = 0.94
MAX_BALLS = 16000

class Ball:
    def __init__(self, x, y, vx, vy, radius, color, depth, seed_speed):
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.radius = float(radius)
        self.color = color
        self.depth = depth
        self.seed_speed = seed_speed
        self.mass = max(1.0, radius * radius)

    def update(self, dt):
        self.vy += GRAVITY * dt
        self.vx *= AIR_FRICTION
        self.vy *= AIR_FRICTION
        self.x += self.vx * dt
        self.y += self.vy * dt

    def draw(self, surf):
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), int(self.radius))
        pygame.draw.circle(surf, (245, 255, 245), (int(self.x), int(self.y)), int(self.radius), 1)

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def random_ball_color():
    return random.choice(BALL_COLORS)

def launch_ball(v):
    speed = 280 + (v - 1) * 10
    #speed = 220 + (v ** 1.35) * 4
    radius = 24 + v * 0.55
    x = WIDTH - radius - 4
    y = GAME_H * 0.24 + random.uniform(-18, 18)
    vx = -speed
    vy = -random.uniform(35, 140)
    return Ball(x, y, vx, vy, radius, (255, 180, 95), 0, v)

def split_ball(ball, hit_axis):
    if len(balls) >= MAX_BALLS:
        return [ball]
    min_radius = 8
    max_depth = 3
    seed = clamp(ball.seed_speed, 1, 100)
    count = clamp(2 + int(seed / 8) + ball.depth // 2, 2, 6)
    new_radius = max(min_radius, ball.radius * (0.48 - 0.04 * min(ball.depth, 2)))
    if ball.radius <= min_radius + 1 or ball.depth >= max_depth:
        return [ball]
    fragments = []
    base_speed = max(180, abs(ball.vx) + abs(ball.vy) * 0.35 + seed * 10)
    angle_start = random.uniform(0, math.tau)
    for i in range(count):
        angle = angle_start + i * (math.tau / count) + random.uniform(-0.22, 0.22)
        burst = base_speed * random.uniform(0.6, 1.02)
        vx = math.cos(angle) * burst
        vy = math.sin(angle) * burst - random.uniform(40, 150)
        if hit_axis == "x":
            vx *= 1.25
        else:
            vy *= 1.25
        offset = ball.radius * 0.16
        bx = ball.x + math.cos(angle) * offset
        by = ball.y + math.sin(angle) * offset
        fragments.append(Ball(bx, by, vx, vy, new_radius, random_ball_color(), ball.depth + 1, ball.seed_speed))
    return fragments

def handle_wall(ball):
    hit = None
    if ball.x - ball.radius <= 0:
        ball.x = ball.radius
        ball.vx = abs(ball.vx) * WALL_RESTITUTION
        ball.vy *= WALL_FRICTION
        hit = "x"
    elif ball.x + ball.radius >= WIDTH:
        ball.x = WIDTH - ball.radius
        ball.vx = -abs(ball.vx) * WALL_RESTITUTION
        ball.vy *= WALL_FRICTION
        hit = "x"
    if ball.y - ball.radius <= 0:
        ball.y = ball.radius
        ball.vy = abs(ball.vy) * WALL_RESTITUTION
        ball.vx *= WALL_FRICTION
        hit = "y"
    elif ball.y + ball.radius >= GAME_H:
        ball.y = GAME_H - ball.radius
        ball.vy = -abs(ball.vy) * WALL_RESTITUTION
        ball.vx *= 0.992
        hit = "y"
    if hit is None:
        return [ball]
    impact = math.hypot(ball.vx, ball.vy)
    threshold = 280 + ball.depth * 110
    if impact > threshold:
        return split_ball(ball, hit)
    return [ball]

def resolve_collisions(items):
    n = len(items)
    for i in range(n):
        a = items[i]
        for j in range(i + 1, n):
            b = items[j]
            dx = b.x - a.x
            dy = b.y - a.y
            dist_sq = dx * dx + dy * dy
            min_dist = a.radius + b.radius
            if dist_sq == 0:
                dx = random.uniform(-1, 1)
                dy = random.uniform(-1, 1)
                dist_sq = dx * dx + dy * dy
            if dist_sq < min_dist * min_dist:
                dist = math.sqrt(dist_sq)
                nx = dx / dist
                ny = dy / dist
                overlap = min_dist - dist
                total_mass = a.mass + b.mass
                a_shift = overlap * (b.mass / total_mass)
                b_shift = overlap * (a.mass / total_mass)
                a.x -= nx * a_shift
                a.y -= ny * a_shift
                b.x += nx * b_shift
                b.y += ny * b_shift
                rvx = b.vx - a.vx
                rvy = b.vy - a.vy
                vel_normal = rvx * nx + rvy * ny
                if vel_normal < 0:
                    impulse = -(1 + COLLISION_RESTITUTION) * vel_normal
                    impulse /= (1 / a.mass) + (1 / b.mass)
                    ix = impulse * nx
                    iy = impulse * ny
                    a.vx -= ix / a.mass
                    a.vy -= iy / a.mass
                    b.vx += ix / b.mass
                    b.vy += iy / b.mass

def draw_grid():
    for x in range(0, WIDTH, 32):
        pygame.draw.line(screen, GRID, (x, 0), (x, GAME_H), 1)
    for y in range(0, GAME_H, 32):
        pygame.draw.line(screen, GRID, (0, y), (WIDTH, y), 1)

def draw_frame():
    pygame.draw.rect(screen, BORDER, (0, 0, WIDTH, GAME_H), 2)
    pygame.draw.rect(screen, PANEL, (0, GAME_H, WIDTH, HUD_H))
    pygame.draw.line(screen, BORDER, (0, GAME_H), (WIDTH, GAME_H), 2)

def draw_hud(entry_text, last_velocity, status, ball_count):
    prompt = "velocity[1-100]>"
    shown = entry_text if entry_text else ""
    left = f"{prompt} {shown}"
    right = f"last={last_velocity if last_velocity is not None else '-'}  balls={ball_count}  {status}"
    controls = "[enter] launch  [r] reset  [esc] quit"

    left_surf = font.render(left, True, TEXT)
    right_surf = small.render(right, True, TEXT_DIM)
    ctrl_surf = small.render(controls, True, TEXT_SOFT)

    pad_x = 14
    center_y = GAME_H + 8

    screen.blit(left_surf, (pad_x, center_y))
    screen.blit(ctrl_surf, (pad_x, center_y + 26))
    screen.blit(right_surf, (WIDTH - right_surf.get_width() - pad_x, center_y + 3))

    cursor_x = pad_x + font.size(left)[0] + 2
    t = pygame.time.get_ticks() % 1000
    if t < 550:
        pygame.draw.line(screen, TEXT, (cursor_x, center_y + 3), (cursor_x, center_y + 22), 2)

def draw_scene(items, entry_text, last_velocity, status):
    screen.fill(BG)
    draw_grid()
    for ball in items:
        ball.draw(screen)
    draw_frame()
    draw_hud(entry_text, last_velocity, status, len(items))

balls = []
entry = ""
last_valid = None
status = "ready"
running = True

while running:
    dt = min(clock.tick(120) / 1000.0, 0.016)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_r:
                balls.clear()
                status = "reset"
            elif event.key == pygame.K_BACKSPACE:
                entry = entry[:-1]
            elif event.key == pygame.K_RETURN:
                if entry.strip().isdigit():
                    v = int(entry.strip())
                    if 1 <= v <= 100:
                        last_valid = v
                        balls.append(launch_ball(v))
                        status = f"launched v={v}"
                        entry = ""
                    else:
                        status = "invalid velocity"
                else:
                    status = "enter digits only"
            else:
                if event.unicode.isdigit() and len(entry) < 3:
                    candidate = entry + event.unicode
                    if int(candidate) <= 100:
                        entry = candidate

    for ball in balls:
        ball.update(dt)

    resolve_collisions(balls)

    new_balls = []
    for ball in balls:
        new_balls.extend(handle_wall(ball))
    balls = new_balls[:MAX_BALLS]

    balls = [b for b in balls if -200 <= b.x <= WIDTH + 200 and -200 <= b.y <= GAME_H + 200]

    draw_scene(balls, entry, last_valid, status)
    pygame.display.flip()

pygame.quit()
sys.exit()