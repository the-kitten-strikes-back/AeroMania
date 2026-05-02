import json
import os
import subprocess
import sys
from dataclasses import dataclass
import time
import textwrap
import math

try:
    import pygame
    from pygame import mixer
except ImportError as exc:
    raise SystemExit(
        "pygame is required for menu.py. Install it with: pip install pygame"
    ) from exc


QUESTS_FILE = "quests.json"
SAVE_DIR = "save"
PROGRESSION_FILE = os.path.join(SAVE_DIR, "progression.json")
SESSION_FILE = os.path.join(SAVE_DIR, "session_config.json")

AIRCRAFTS = [
    {"id": "f16", "name": "F-16 Falcon", "model": "models/f16"},
    {"id": "f167", "name": "F-16 Variant", "model": "models/f167"},
    {"id": "tinker", "name": "Tinker", "model": "models/tinker"},
    {"id": "ac130", "name": "AC-130", "model": "models/ac130"},
    {"id": "xwing", "name": "X-Wing", "model": "models/xwing"},
]

CONTROL_LINES = [
    ("W / S", "Pitch"),
    ("A / D", "Yaw"),
    ("Q / E", "Throttle ±"),
    ("M", "Fire missile"),
    ("G", "Guns"),
    ("F", "Flare"),
    ("T / R", "Cycle target"),
    ("B", "Break lock"),
    ("C", "Toggle cockpit"),
    ("H", "Radar"),
    ("Z / X / V", "Zoom"),
    ("ESC", "Quit"),
]

SHOP_ITEMS = {
    "armor": [
        {"id": "light_armor", "name": "Light Armor", "price": 1000, "health_bonus": 50, "speed_penalty": 0.05, "description": "Basic protection with minimal speed loss"},
        {"id": "medium_armor", "name": "Medium Armor", "price": 2000, "health_bonus": 100, "speed_penalty": 0.1, "description": "Balanced protection and mobility"},
        {"id": "heavy_armor", "name": "Heavy Armor", "price": 3000, "health_bonus": 200, "speed_penalty": 0.15, "description": "Maximum protection at cost of speed"}
    ],
    "planes": [
        {"id": "tinker", "name": "Tinker", "price": 4000, "speed": 80, "turn_rate": 2.0, "held_keys": 1, "size": 1.0, "description": "Agile fighter with good maneuverability"},
        {"id": "ac130", "name": "AC-130", "price": 6000, "speed": 60, "turn_rate": 0.8, "held_keys": 3, "size": 2.0, "description": "Heavy gunship with devastating firepower"},
        {"id": "xwing", "name": "X-Wing", "price": 5000, "speed": 90, "turn_rate": 1.5, "held_keys": 2, "size": 1.2, "description": "Starfighter with balanced stats"}
    ],
    "missiles": [
        {"id": "mega", "name": "Mega Missile", "price": 600, "speed": 1.2, "turn_rate": 1.1, "count": 2, "damage": 150, "color": (255, 255, 0), "description": "Enhanced missile with better tracking"},
        {"id": "military_grade", "name": "Military-Grade", "price": 1000, "speed": 1.5, "turn_rate": 1.3, "count": 3, "damage": 200, "color": (255, 0, 0), "description": "Professional military missile"},
        {"id": "supersonic", "name": "Supersonic", "price": 1600, "speed": 2.0, "turn_rate": 1.5, "count": 4, "damage": 250, "color": (0, 255, 255), "description": "High-speed missile with excellent range"},
        {"id": "hypersonic", "name": "Hypersonic", "price": 2400, "speed": 3.0, "turn_rate": 1.8, "count": 5, "damage": 300, "color": (255, 0, 255), "description": "Ultra-fast missile with perfect tracking"},
        {"id": "nuclear", "name": "Nuclear", "price": 4000, "speed": 2.5, "turn_rate": 2.0, "count": 6, "damage": 500, "color": (255, 255, 255), "description": "Devastating nuclear missile"}
    ],
    "radars": [
        {"id": "mega", "name": "Mega Radar", "price": 800, "range": 800, "description": "Extended detection range"},
        {"id": "military_grade", "name": "Military-Grade", "price": 1400, "range": 1200, "description": "Advanced military radar system"}
    ],
    "flares": [
        {"id": "flare_pack", "name": "Flares (10)", "price": 200, "count": 10, "description": "Additional flare countermeasures"}
    ]
}

BADGE_DEFINITIONS = [
    {"id": "first_kill", "name": "First Blood", "description": "Get your first kill", "requirement": {"kills": 1}},
    {"id": "ace", "name": "Ace Pilot", "description": "Destroy 5 enemies", "requirement": {"kills": 5}},
    {"id": "veteran", "name": "Veteran", "description": "Destroy 25 enemies", "requirement": {"kills": 25}},
    {"id": "survivor", "name": "Survivor", "description": "Survive for 5 minutes", "requirement": {"survival_time": 300}},
    {"id": "mission_master", "name": "Mission Master", "description": "Complete 10 missions", "requirement": {"missions": 10}},
    {"id": "speed_demon", "name": "Speed Demon", "description": "Reach max speed in any aircraft", "requirement": {"max_speed": True}},
    {"id": "untouchable", "name": "Untouchable", "description": "Complete a mission without taking damage", "requirement": {"no_damage": True}}
]

# ─── REDESIGNED THEME ────────────────────────────────────────────────────────
THEME = {
    "bg":           (4, 6, 12),
    "bg2":          (8, 11, 22),
    "panel":        (10, 16, 30),
    "panel_hi":     (16, 26, 48),
    "panel_edge":   (0, 180, 220),
    "panel_edge2":  (22, 38, 68),
    "accent":       (0, 210, 255),
    "accent2":      (0, 140, 200),
    "accent_hot":   (255, 60, 200),
    "accent_warn":  (255, 200, 60),
    "accent_green": (0, 220, 130),
    "text":         (210, 235, 255),
    "text_dim":     (140, 175, 210),
    "text_muted":   (80, 105, 140),
    "success":      (0, 220, 130),
    "danger":       (255, 80, 90),
    "locked":       (20, 28, 44),
    "locked_fg":    (60, 80, 110),
    "done":         (10, 50, 38),
    "done_fg":      (0, 200, 120),
    "row_a":        (12, 20, 38),
    "row_b":        (16, 24, 44),
    "row_hover":    (0, 60, 90),
    "row_active":   (0, 50, 80),
}

W, H = 1200, 750


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def ensure_save_dir():
    os.makedirs(SAVE_DIR, exist_ok=True)


def load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def save_json(path, data):
    ensure_save_dir()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def default_progression():
    return {
        "completed_nodes": [],
        "node_stars": {},
        "challenge_stars": {},
        "unlocked_aircraft": ["f16", "f167"],
        "selected_aircraft": "f167",
        "upgrades": {},
        "cosmetics": [],
        "currency": 1000,
        "inventory": {
            "armor": [],
            "planes": ["f16", "f167"],
            "missiles": ["basic"],
            "radars": ["basic"],
            "flares": 10
        },
        "equipped": {
            "armor": None,
            "plane": "f167",
            "missile": "basic",
            "radar": "basic"
        },
        "badges": [],
        "stats": {
            "total_kills": 0,
            "total_deaths": 0,
            "missions_completed": 0,
            "time_flown": 0,
            "best_survival_time": 0
        }
    }


def normalize_progression(progression):
    progression.setdefault("completed_nodes", [])
    progression.setdefault("node_stars", {})
    progression.setdefault("challenge_stars", {})
    progression.setdefault("unlocked_aircraft", ["f16", "f167"])
    progression.setdefault("selected_aircraft", "f167")
    progression.setdefault("upgrades", {})
    progression.setdefault("cosmetics", [])
    progression.setdefault("currency", 1000)
    progression.setdefault("inventory", {
        "armor": [],
        "planes": ["f16", "f167"],
        "missiles": ["basic"],
        "radars": ["basic"],
        "flares": 10
    })
    progression.setdefault("equipped", {
        "armor": None,
        "plane": "f167",
        "missile": "basic",
        "radar": "basic"
    })
    progression.setdefault("badges", [])
    progression.setdefault("stats", {
        "total_kills": 0,
        "total_deaths": 0,
        "missions_completed": 0,
        "time_flown": 0,
        "best_survival_time": 0
    })
    return progression


def load_quests():
    data = load_json(QUESTS_FILE, {})
    if "tiers" not in data or "challenges" not in data:
        raise ValueError("quests.json must include 'tiers' and 'challenges'.")
    return data


def total_stars(progression):
    return (
        sum(progression.get("node_stars", {}).values())
        + sum(progression.get("challenge_stars", {}).values())
    )


def can_afford(progression, item_price):
    return progression["currency"] >= item_price


def purchase_item(progression, category, item_id):
    if category not in SHOP_ITEMS:
        return False, "Invalid category"
    item = next((i for i in SHOP_ITEMS[category] if i["id"] == item_id), None)
    if not item:
        return False, "Item not found"
    if not can_afford(progression, item["price"]):
        return False, "Insufficient funds"
    progression["currency"] -= item["price"]
    if category == "flares":
        progression["inventory"]["flares"] += item["count"]
    else:
        if item_id not in progression["inventory"][category]:
            progression["inventory"][category].append(item_id)
    save_json(PROGRESSION_FILE, progression)
    return True, f"Purchased {item['name']}"


def check_badges(progression):
    new_badges = []
    for badge in BADGE_DEFINITIONS:
        if badge["id"] in progression["badges"]:
            continue
        req = badge["requirement"]
        earned = True
        if "kills" in req and progression["stats"]["total_kills"] < req["kills"]:
            earned = False
        if "survival_time" in req and progression["stats"]["best_survival_time"] < req["survival_time"]:
            earned = False
        if "missions" in req and progression["stats"]["missions_completed"] < req["missions"]:
            earned = False
        if "max_speed" in req and not progression["stats"].get("max_speed_achieved", False):
            earned = False
        if "no_damage" in req and not progression["stats"].get("no_damage_mission", False):
            earned = False
        if earned:
            progression["badges"].append(badge["id"])
            new_badges.append(badge)
    if new_badges:
        save_json(PROGRESSION_FILE, progression)
    return new_badges


def node_index(quests):
    nodes = {}
    for tier in quests.get("tiers", []):
        for node in tier.get("nodes", []):
            nodes[node["id"]] = node
    return nodes


def node_unlocked(node, progression, nodes):
    if node.get("id") in progression.get("completed_nodes", []):
        return True
    req = node.get("unlock_requirements", {})
    req_nodes = req.get("completed_nodes", [])
    req_stars = req.get("min_stars", 0)
    completed = set(progression.get("completed_nodes", []))
    if any(n not in completed for n in req_nodes if n in nodes):
        return False
    return total_stars(progression) >= req_stars


def aircraft_unlocked(aircraft_id, progression):
    return aircraft_id in progression.get("unlocked_aircraft", [])


# ─── DRAWING UTILITIES ───────────────────────────────────────────────────────

def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def draw_rect_alpha(surface, color, rect, alpha=180, radius=10):
    s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(s, (*color, alpha), (0, 0, rect.width, rect.height), border_radius=radius)
    surface.blit(s, (rect.x, rect.y))


def draw_glow_rect(surface, color, rect, radius=10, glow_size=8, alpha=60):
    for i in range(glow_size, 0, -1):
        a = int(alpha * (i / glow_size) ** 2)
        expanded = pygame.Rect(rect.x - i, rect.y - i, rect.width + 2 * i, rect.height + 2 * i)
        draw_rect_alpha(surface, color, expanded, a, radius + i)


def draw_panel(surface, rect, title=None, title_font=None, accent=None):
    """Draw a styled panel with gradient header and glowing border."""
    accent = accent or THEME["panel_edge"]
    # Background
    draw_rect_alpha(surface, THEME["panel"], rect, 240, 12)
    # Top gradient strip
    top = pygame.Rect(rect.x, rect.y, rect.width, 48)
    draw_rect_alpha(surface, THEME["panel_hi"], top, 200, 12)
    # Glowing border
    draw_glow_rect(surface, accent, rect, 12, 5, 40)
    pygame.draw.rect(surface, accent, rect, width=1, border_radius=12)
    # Top accent line
    pygame.draw.line(surface, accent,
                     (rect.x + 14, rect.y + 1),
                     (rect.x + rect.width - 14, rect.y + 1), 2)
    # Corner marks
    cl = 14
    for cx, cy, dx, dy in [
        (rect.x, rect.y, 1, 1),
        (rect.right, rect.y, -1, 1),
        (rect.x, rect.bottom, 1, -1),
        (rect.right, rect.bottom, -1, -1),
    ]:
        pygame.draw.line(surface, accent, (cx + dx * 8, cy), (cx + dx * (8 + cl), cy), 2)
        pygame.draw.line(surface, accent, (cx, cy + dy * 8), (cx, cy + dy * (8 + cl)), 2)
    if title and title_font:
        txt = title_font.render(title, True, THEME["text"])
        surface.blit(txt, (rect.x + 18, rect.y + 12))


def draw_separator(surface, x, y, width, color=None):
    color = color or THEME["panel_edge2"]
    pygame.draw.line(surface, color, (x, y), (x + width, y), 1)
    draw_rect_alpha(surface, THEME["accent"], pygame.Rect(x, y, width, 1), 30, 0)


def draw_tag(surface, text, x, y, font, bg, fg, radius=5, pad_x=8, pad_y=3):
    tw = font.size(text)[0]
    rect = pygame.Rect(x, y, tw + pad_x * 2, font.get_height() + pad_y * 2)
    draw_rect_alpha(surface, bg, rect, 200, radius)
    surface.blit(font.render(text, True, fg), (x + pad_x, y + pad_y))
    return rect


def draw_stat_row(surface, label, value, x, y, lw, label_font, value_font, divider=True):
    surface.blit(label_font.render(label, True, THEME["text_dim"]), (x, y))
    val_surf = value_font.render(str(value), True, THEME["accent"])
    surface.blit(val_surf, (x + lw, y))
    if divider:
        draw_separator(surface, x, y + label_font.get_height() + 4, 380)


def draw_pill_row(surface, items, selected, x, y, w, h, font, mouse_pos, accent=None):
    """Draw a row of pill-style toggle buttons; returns which index was at mouse_pos."""
    accent = accent or THEME["accent"]
    total = len(items)
    gap = 8
    pill_w = (w - gap * (total - 1)) // total
    hovered = None
    for i, label in enumerate(items):
        px = x + i * (pill_w + gap)
        rect = pygame.Rect(px, y, pill_w, h)
        active = selected == i
        if active:
            draw_glow_rect(surface, accent, rect, h // 2, 6, 50)
            draw_rect_alpha(surface, accent, rect, 220, h // 2)
            surface.blit(font.render(label, True, (5, 10, 18)), font.render(label, True, (5, 10, 18)).get_rect(center=rect.center).topleft)
        else:
            is_hov = rect.collidepoint(mouse_pos)
            if is_hov:
                hovered = i
                draw_rect_alpha(surface, THEME["accent2"], rect, 120, h // 2)
            else:
                draw_rect_alpha(surface, THEME["panel_hi"], rect, 180, h // 2)
            pygame.draw.rect(surface, THEME["panel_edge2"], rect, width=1, border_radius=h // 2)
            surface.blit(font.render(label, True, THEME["text_dim"] if not is_hov else THEME["text"]),
                         font.render(label, True, THEME["text"]).get_rect(center=rect.center).topleft)
    return hovered


# ─── STAR DRAWING ─────────────────────────────────────────────────────────────

def draw_stars(surface, count, max_stars, x, y, size=10, gap=3, color_on=None, color_off=None):
    color_on = color_on or THEME["accent_warn"]
    color_off = color_off or THEME["panel_edge2"]
    for i in range(max_stars):
        c = color_on if i < count else color_off
        cx = x + i * (size + gap) + size // 2
        cy = y + size // 2
        points = []
        for k in range(5):
            angle = math.pi / 2 + k * 2 * math.pi / 5
            outer = (cx + size // 2 * math.cos(angle), cy - size // 2 * math.sin(angle))
            inner_angle = angle + math.pi / 5
            inner = (cx + size // 4 * math.cos(inner_angle), cy - size // 4 * math.sin(inner_angle))
            points.extend([outer, inner])
        pygame.draw.polygon(surface, c, points)


# ─── BACKGROUND EFFECTS ──────────────────────────────────────────────────────

class GridBackground:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.surface = pygame.Surface((w, h))
        self._bake()

    def _bake(self):
        self.surface.fill(THEME["bg"])
        # Subtle grid
        for x in range(0, self.w, 60):
            pygame.draw.line(self.surface, (10, 18, 35), (x, 0), (x, self.h))
        for y in range(0, self.h, 60):
            pygame.draw.line(self.surface, (10, 18, 35), (0, y), (self.w, y))
        # Diagonal streaks
        for i in range(0, self.w + self.h, 180):
            s = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            pygame.draw.line(s, (0, 60, 100, 12), (i, 0), (i - self.h, self.h), 1)
            self.surface.blit(s, (0, 0))

    def draw(self, surface, t):
        surface.blit(self.surface, (0, 0))
        # Animated scan line
        scan_y = int((t * 60) % self.h)
        s = pygame.Surface((self.w, 3), pygame.SRCALPHA)
        s.fill((0, 200, 255, 18))
        surface.blit(s, (0, scan_y))
        # Vignette
        v = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        for edge, alpha in [(80, 60), (40, 100)]:
            pygame.draw.rect(v, (0, 0, 0, alpha), (0, 0, self.w, edge))
            pygame.draw.rect(v, (0, 0, 0, alpha), (0, self.h - edge, self.w, edge))
            pygame.draw.rect(v, (0, 0, 0, alpha), (0, 0, edge, self.h))
            pygame.draw.rect(v, (0, 0, 0, alpha), (self.w - edge, 0, edge, self.h))
        surface.blit(v, (0, 0))


# ─── SCROLLABLE LIST ─────────────────────────────────────────────────────────

class ScrollList:
    def __init__(self, rect):
        self.rect = rect
        self.scroll = 0
        self.content_height = 0

    def handle_scroll(self, delta, mouse_pos, speed=28):
        if self.rect.collidepoint(mouse_pos) and delta:
            max_s = max(0, self.content_height - self.rect.height)
            self.scroll = max(-max_s, min(0, self.scroll + delta))

    def begin(self, surface):
        self._prev_clip = surface.get_clip()
        surface.set_clip(self.rect)
        return self.rect.y + self.scroll

    def end(self, surface, content_height):
        surface.set_clip(self._prev_clip)
        self.content_height = content_height
        max_s = max(0, content_height - self.rect.height)
        self.scroll = max(-max_s, min(0, self.scroll))
        if max_s > 0:
            track = pygame.Rect(self.rect.right - 8, self.rect.y + 6, 4, self.rect.height - 12)
            draw_rect_alpha(surface, (20, 35, 60), track, 180, 2)
            thumb_h = max(20, int(self.rect.height * self.rect.height / content_height))
            thumb_y = int(self.rect.y + 6 + (-self.scroll / max_s) * (track.height - thumb_h))
            thumb = pygame.Rect(track.x, thumb_y, track.width, thumb_h)
            draw_rect_alpha(surface, THEME["accent"], thumb, 200, 2)


# ─── MAIN MENU ───────────────────────────────────────────────────────────────

def run_menu():
    pygame.init()
    audio_ready = False
    music_loaded = False
    try:
        mixer.init()
        audio_ready = True
        if os.path.exists("models/menu_music.mp3"):
            mixer.music.load("models/menu_music.mp3")
            mixer.music.set_volume(0.8)
            time.sleep(0.15)
            mixer.music.play(-1)
            music_loaded = True
    except pygame.error:
        audio_ready = False
        music_loaded = False

    pygame.display.set_caption("AeroMania — Mission Menu")
    screen = pygame.display.set_mode((W, H))
    clock = pygame.time.Clock()

    # Fonts — monospaced for HUD feel
    try:
        title_font   = pygame.font.SysFont("consolas", 52, bold=True)
        sub_font     = pygame.font.SysFont("consolas", 14)
        heading_font = pygame.font.SysFont("consolas", 20, bold=True)
        body_font    = pygame.font.SysFont("consolas", 17)
        small_font   = pygame.font.SysFont("consolas", 15)
        tiny_font    = pygame.font.SysFont("consolas", 12)
        key_font     = pygame.font.SysFont("consolas", 13, bold=True)
    except Exception:
        title_font = heading_font = body_font = small_font = tiny_font = key_font = sub_font = pygame.font.SysFont(None, 20)

    try:
        quests = load_quests()
        quests_error = ""
    except ValueError as exc:
        quests = {"tiers": [], "challenges": []}
        quests_error = str(exc)

    progression = normalize_progression(load_json(PROGRESSION_FILE, default_progression()))
    nodes = node_index(quests)

    current_tab = "campaign"
    selected_mode = "quests"
    selected_node_id = None
    selected_challenge_id = None

    selected_aircraft = progression.get("selected_aircraft", "f167")
    if not aircraft_unlocked(selected_aircraft, progression):
        selected_aircraft = progression.get("unlocked_aircraft", ["f16"])[0]

    selected_info = ""
    selected_name = ""
    shop_category = "armor"
    shop_message = ""
    shop_message_ok = True

    bg = GridBackground(W, H)
    mission_list = ScrollList(pygame.Rect(46, 238, 494, 400))

    running = True

    while running:
        mouse_pos = pygame.mouse.get_pos()
        clicked = False
        scroll_delta = 0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                clicked = True
            elif event.type == pygame.MOUSEWHEEL:
                scroll_delta = event.y * 28
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
                scroll_delta = (1 if event.button == 4 else -1) * 28

        t = pygame.time.get_ticks() / 1000.0
        pulse = 0.55 + 0.45 * (0.5 + 0.5 * math.sin(t * 2.0))
        pulse2 = 0.5 + 0.5 * (0.5 + 0.5 * math.sin(t * 3.1 + 1.2))

        # ── BACKGROUND ──────────────────────────────────────────────────────
        bg.draw(screen, t)

        # ── HEADER ──────────────────────────────────────────────────────────
        header = pygame.Rect(20, 12, W - 40, 78)
        draw_rect_alpha(screen, THEME["panel"], header, 230, 10)
        pygame.draw.rect(screen, THEME["panel_edge"], header, width=1, border_radius=10)
        # Top line glow
        draw_rect_alpha(screen, THEME["accent"], pygame.Rect(header.x + 10, header.y, header.width - 20, 2), int(120 * pulse), 1)

        # Title
        title_s = title_font.render("AeroMania", True, THEME["text"])
        screen.blit(title_s, (42, 22))
        # Glow pass
        glow_c = (int(THEME["accent"][0] * pulse * 0.6),
                  int(THEME["accent"][1] * pulse * 0.6),
                  int(THEME["accent"][2] * pulse * 0.6))
        glow_s = title_font.render("AeroMania", True, glow_c)
        s_tmp = pygame.Surface(glow_s.get_size(), pygame.SRCALPHA)
        s_tmp.blit(glow_s, (0, 0))
        screen.blit(s_tmp, (44, 24))


        # Currency badge
        cur_str = f"◈  {progression.get('currency', 0):,}  AIRBUCKS"
        cw = body_font.size(cur_str)[0] + 28
        cur_rect = pygame.Rect(W - 40 - cw, 30, cw, 36)
        draw_glow_rect(screen, THEME["accent_warn"], cur_rect, 8, 5, 40)
        draw_rect_alpha(screen, (40, 30, 8), cur_rect, 200, 8)
        pygame.draw.rect(screen, THEME["accent_warn"], cur_rect, width=1, border_radius=8)
        screen.blit(body_font.render(cur_str, True, THEME["accent_warn"]), (cur_rect.x + 14, cur_rect.y + 8))

        # Stars badge
        stars_total = total_stars(progression)
        star_str = f"★  {stars_total}"
        sw = body_font.size(star_str)[0] + 28
        star_rect = pygame.Rect(W - 50 - cw - sw, 30, sw, 36)
        draw_rect_alpha(screen, (8, 32, 55), star_rect, 200, 8)
        pygame.draw.rect(screen, THEME["accent"], star_rect, width=1, border_radius=8)
        screen.blit(body_font.render(star_str, True, THEME["accent"]), (star_rect.x + 14, star_rect.y + 8))

        # ── TAB BAR ─────────────────────────────────────────────────────────
        tabs = ["campaign", "loadout", "shop", "badges"]
        tab_names = ["⬟  CAMPAIGN", "⬙  LOADOUT", "◈  SHOP", "★  BADGES"]
        tab_total_w = 680
        tab_x0 = (W - tab_total_w) // 2
        tab_w = (tab_total_w - 12) // len(tabs)
        tab_bar = pygame.Rect(tab_x0 - 6, 96, tab_total_w + 12, 44)
        draw_rect_alpha(screen, THEME["panel"], tab_bar, 210, 8)
        pygame.draw.rect(screen, THEME["panel_edge2"], tab_bar, width=1, border_radius=8)

        for i, (tab, name) in enumerate(zip(tabs, tab_names)):
            tx = tab_x0 + i * (tab_w + 4)
            rect = pygame.Rect(tx, 99, tab_w, 38)
            active = current_tab == tab
            hovered = rect.collidepoint(mouse_pos) and not active
            if active:
                draw_glow_rect(screen, THEME["accent"], rect, 8, 6, 50)
                draw_rect_alpha(screen, THEME["accent"], rect, 220, 8)
                screen.blit(key_font.render(name, True, (4, 8, 16)),
                            key_font.render(name, True, (4, 8, 16)).get_rect(center=rect.center).topleft)
            else:
                draw_rect_alpha(screen, THEME["panel_hi"], rect, 160, 8)
                if hovered:
                    draw_rect_alpha(screen, THEME["accent2"], rect, 60, 8)
                screen.blit(key_font.render(name, True, THEME["text_dim"] if not hovered else THEME["text"]),
                            key_font.render(name, True, THEME["text"]).get_rect(center=rect.center).topleft)
            if clicked and rect.collidepoint(mouse_pos):
                current_tab = tab
                shop_message = ""
                mission_list.scroll = 0

        # ══════════════════════════════════════════════════════════════════════
        # CAMPAIGN TAB
        # ══════════════════════════════════════════════════════════════════════
        if current_tab == "campaign":
            # LEFT PANEL — Mission list
            lp = pygame.Rect(22, 152, 540, 578)
            draw_panel(screen, lp, title=None, accent=THEME["panel_edge"])

            # Mode toggle
            mode_labels = ["QUESTS", "CHALLENGES"]
            mode_x = lp.x + 16
            mode_y = lp.y + 14
            for i, lbl in enumerate(mode_labels):
                rect = pygame.Rect(mode_x + i * 136, mode_y, 128, 32)
                active = (selected_mode == "quests" and i == 0) or (selected_mode == "challenges" and i == 1)
                hov = rect.collidepoint(mouse_pos) and not active
                if active:
                    draw_glow_rect(screen, THEME["accent"], rect, 6, 5, 40)
                    draw_rect_alpha(screen, THEME["accent"], rect, 210, 6)
                    screen.blit(small_font.render(lbl, True, (4, 8, 16)),
                                small_font.render(lbl, True, (4, 8, 16)).get_rect(center=rect.center).topleft)
                else:
                    draw_rect_alpha(screen, THEME["panel_hi"], rect, 180, 6)
                    if hov:
                        draw_rect_alpha(screen, THEME["accent2"], rect, 60, 6)
                    pygame.draw.rect(screen, THEME["panel_edge2"], rect, width=1, border_radius=6)
                    screen.blit(small_font.render(lbl, True, THEME["text_dim"] if not hov else THEME["text"]),
                                small_font.render(lbl, True, THEME["text"]).get_rect(center=rect.center).topleft)
                if clicked and rect.collidepoint(mouse_pos):
                    selected_mode = "quests" if i == 0 else "challenges"
                    mission_list.scroll = 0

            draw_separator(screen, lp.x + 12, lp.y + 50, lp.width - 24)

            # Mission list
            mission_list.rect = pygame.Rect(lp.x + 8, lp.y + 56, lp.width - 16, lp.height - 60)
            mission_list.handle_scroll(scroll_delta, mouse_pos)
            list_y = mission_list.begin(screen)

            content_h = 0
            if quests_error:
                screen.blit(small_font.render(quests_error, True, THEME["danger"]),
                            (mission_list.rect.x + 10, list_y + 8))
                content_h = 30
            elif selected_mode == "quests":
                row = 0
                for tier in quests.get("tiers", []):
                    tier_label = f"── {tier.get('id', '').upper()}: {tier.get('name', '').upper()} ──"
                    screen.blit(tiny_font.render(tier_label, True, THEME["text_muted"]),
                                (mission_list.rect.x + 12, list_y + 6))
                    list_y += 24
                    content_h += 24
                    for node in tier.get("nodes", []):
                        unlocked = node_unlocked(node, progression, nodes)
                        done = node.get("id") in progression.get("completed_nodes", [])
                        stars = progression.get("node_stars", {}).get(node.get("id"), 0)
                        rect = pygame.Rect(mission_list.rect.x + 4, list_y, mission_list.rect.width - 20, 36)
                        bg_col = THEME["done"] if done else (THEME["row_a"] if row % 2 == 0 else THEME["row_b"])
                        if not unlocked:
                            bg_col = THEME["locked"]
                        selected = selected_node_id == node.get("id")
                        hov = rect.collidepoint(mouse_pos) and unlocked
                        if selected:
                            draw_glow_rect(screen, THEME["accent"], rect, 6, 4, 30)
                            draw_rect_alpha(screen, THEME["row_active"], rect, 200, 6)
                            pygame.draw.rect(screen, THEME["accent"], rect, width=1, border_radius=6)
                        elif hov:
                            draw_rect_alpha(screen, THEME["row_hover"], rect, 200, 6)
                        else:
                            draw_rect_alpha(screen, bg_col, rect, 180, 6)

                        # Status tag
                        if done:
                            tag_bg, tag_fg, tag_txt = THEME["done"], THEME["done_fg"], "DONE"
                        elif unlocked:
                            tag_bg, tag_fg, tag_txt = (0, 40, 80), THEME["accent"], "OPEN"
                        else:
                            tag_bg, tag_fg, tag_txt = (18, 22, 35), THEME["locked_fg"], "LOCK"
                        draw_tag(screen, tag_txt, rect.x + 8, rect.y + 8, tiny_font, tag_bg, tag_fg, 4, 6, 2)

                        # Node name
                        name_col = THEME["text"] if unlocked else THEME["locked_fg"]
                        screen.blit(small_font.render(node.get("name", ""), True, name_col), (rect.x + 62, rect.y + 10))

                        # Stars
                        if stars > 0:
                            draw_stars(screen, stars, 3, rect.right - 70, rect.y + 12, 9, 3)

                        if clicked and rect.collidepoint(mouse_pos) and unlocked:
                            selected_node_id = node.get("id")
                            selected_challenge_id = None
                            selected_name = node.get("name", "")
                            selected_info = node.get("description", "")
                        list_y += 38
                        content_h += 38
                        row += 1
                    list_y += 8
                    content_h += 8
            else:
                for row, ch in enumerate(quests.get("challenges", [])):
                    unlocked = total_stars(progression) >= ch.get("unlock_requirements", {}).get("min_stars", 0)
                    stars = progression.get("challenge_stars", {}).get(ch.get("id"), 0)
                    rect = pygame.Rect(mission_list.rect.x + 4, list_y, mission_list.rect.width - 20, 36)
                    bg_col = THEME["row_a"] if row % 2 == 0 else THEME["row_b"]
                    if not unlocked:
                        bg_col = THEME["locked"]
                    selected = selected_challenge_id == ch.get("id")
                    hov = rect.collidepoint(mouse_pos) and unlocked
                    if selected:
                        draw_glow_rect(screen, THEME["accent_hot"], rect, 6, 4, 30)
                        draw_rect_alpha(screen, (50, 10, 50), rect, 200, 6)
                        pygame.draw.rect(screen, THEME["accent_hot"], rect, width=1, border_radius=6)
                    elif hov:
                        draw_rect_alpha(screen, THEME["row_hover"], rect, 200, 6)
                    else:
                        draw_rect_alpha(screen, bg_col, rect, 180, 6)

                    tag_bg, tag_fg, tag_txt = ((0, 40, 80), THEME["accent_hot"], "OPEN") if unlocked else ((18, 22, 35), THEME["locked_fg"], "LOCK")
                    draw_tag(screen, tag_txt, rect.x + 8, rect.y + 8, tiny_font, tag_bg, tag_fg, 4, 6, 2)
                    screen.blit(small_font.render(ch.get("name", ""), True, THEME["text"] if unlocked else THEME["locked_fg"]),
                                (rect.x + 62, rect.y + 10))
                    if stars > 0:
                        draw_stars(screen, stars, 3, rect.right - 70, rect.y + 12, 9, 3, color_on=THEME["accent_hot"])
                    if clicked and rect.collidepoint(mouse_pos) and unlocked:
                        selected_challenge_id = ch.get("id")
                        selected_node_id = None
                        selected_name = ch.get("name", "")
                        objective_text = "\n".join(
                            obj.get("description", "") for obj in ch.get("mission", {}).get("objectives", [])
                            if obj.get("description")
                        )
                        selected_info = objective_text

                    list_y += 38
                    content_h += 38

            mission_list.end(screen, content_h)

            # RIGHT PANEL — Aircraft + Controls + Briefing
            rp = pygame.Rect(574, 152, 604, 578)
            draw_panel(screen, rp, accent=THEME["panel_edge"])

            ry = rp.y + 16

            # Aircraft section
            screen.blit(heading_font.render("AIRCRAFT SELECT", True, THEME["accent"]), (rp.x + 16, ry))
            ry += 30
            draw_separator(screen, rp.x + 12, ry, rp.width - 24)
            ry += 10

            cols = 3
            ac_w = (rp.width - 32 - (cols - 1) * 8) // cols
            for idx, aircraft in enumerate(AIRCRAFTS):
                col = idx % cols
                acx = rp.x + 16 + col * (ac_w + 8)
                acy = ry + (idx // cols) * 44
                rect = pygame.Rect(acx, acy, ac_w, 36)
                unlocked_ac = aircraft_unlocked(aircraft["id"], progression)
                active_ac = selected_aircraft == aircraft["id"]
                hov_ac = rect.collidepoint(mouse_pos) and unlocked_ac

                if active_ac:
                    draw_glow_rect(screen, THEME["accent"], rect, 6, 5, 45)
                    draw_rect_alpha(screen, (0, 40, 70), rect, 220, 6)
                    pygame.draw.rect(screen, THEME["accent"], rect, width=1, border_radius=6)
                elif hov_ac:
                    draw_rect_alpha(screen, THEME["row_hover"], rect, 200, 6)
                elif not unlocked_ac:
                    draw_rect_alpha(screen, THEME["locked"], rect, 200, 6)
                    pygame.draw.rect(screen, THEME["panel_edge2"], rect, width=1, border_radius=6)
                else:
                    draw_rect_alpha(screen, THEME["panel_hi"], rect, 180, 6)
                    pygame.draw.rect(screen, THEME["panel_edge2"], rect, width=1, border_radius=6)

                name_c = THEME["accent"] if active_ac else (THEME["locked_fg"] if not unlocked_ac else (THEME["text"] if not hov_ac else THEME["accent"]))
                label_txt = aircraft["name"] if unlocked_ac else f"🔒 {aircraft['name']}"
                s = small_font.render(label_txt, True, name_c)
                screen.blit(s, s.get_rect(center=rect.center).topleft)

                if clicked and rect.collidepoint(mouse_pos) and unlocked_ac:
                    selected_aircraft = aircraft["id"]
                    progression["selected_aircraft"] = selected_aircraft
                    save_json(PROGRESSION_FILE, progression)

            ry += (math.ceil(len(AIRCRAFTS) / cols)) * 44 + 8
            draw_separator(screen, rp.x + 12, ry, rp.width - 24)
            ry += 12

            # Controls section — two column layout
            screen.blit(heading_font.render("CONTROLS", True, THEME["accent"]), (rp.x + 16, ry))
            ry += 28
            col_w = (rp.width - 32) // 2
            for i, (key, desc) in enumerate(CONTROL_LINES):
                cx = rp.x + 16 + (i % 2) * col_w
                cy = ry + (i // 2) * 22
                # Key badge
                kw = key_font.size(key)[0] + 10
                k_rect = pygame.Rect(cx, cy + 1, kw, 18)
                draw_rect_alpha(screen, (0, 35, 65), k_rect, 200, 3)
                pygame.draw.rect(screen, THEME["accent2"], k_rect, width=1, border_radius=3)
                screen.blit(key_font.render(key, True, THEME["accent"]), (cx + 5, cy + 2))
                screen.blit(tiny_font.render(desc, True, THEME["text_dim"]), (cx + kw + 6, cy + 3))

            ry += (math.ceil(len(CONTROL_LINES) / 2)) * 22 + 10
            draw_separator(screen, rp.x + 12, ry, rp.width - 24)
            ry += 12

            # Briefing section
            screen.blit(heading_font.render("MISSION BRIEFING", True, THEME["accent"]), (rp.x + 16, ry))
            ry += 28
            selected_ok = (
                (selected_mode == "quests" and selected_node_id is not None)
                or (selected_mode == "challenges" and selected_challenge_id is not None)
            )
            if selected_ok and selected_name:
                screen.blit(body_font.render(selected_name, True, THEME["text"]), (rp.x + 16, ry))
                ry += 26
                info_lines = textwrap.wrap(selected_info, width=60) if selected_info else []
                for line in info_lines[:4]:
                    screen.blit(small_font.render(line, True, THEME["text_dim"]), (rp.x + 16, ry))
                    ry += 20
            else:
                screen.blit(small_font.render("[ No mission selected ]", True, THEME["text_muted"]), (rp.x + 16, ry))

            # LAUNCH button
            launch_rect = pygame.Rect(rp.right - 210, rp.bottom - 56, 196, 44)
            launch_hov = launch_rect.collidepoint(mouse_pos)
            if selected_ok:
                if launch_hov:
                    draw_glow_rect(screen, THEME["accent_green"], launch_rect, 8, 8, 60)
                    draw_rect_alpha(screen, (0, 80, 50), launch_rect, 220, 8)
                    pygame.draw.rect(screen, THEME["accent_green"], launch_rect, width=2, border_radius=8)
                    lbl_c = THEME["accent_green"]
                else:
                    draw_rect_alpha(screen, (0, 50, 35), launch_rect, 200, 8)
                    pygame.draw.rect(screen, THEME["accent_green"], launch_rect, width=1, border_radius=8)
                    lbl_c = THEME["accent_green"]
            else:
                draw_rect_alpha(screen, THEME["locked"], launch_rect, 180, 8)
                pygame.draw.rect(screen, THEME["panel_edge2"], launch_rect, width=1, border_radius=8)
                lbl_c = THEME["text_muted"]

            lbl_surf = heading_font.render("▶  LAUNCH MISSION", True, lbl_c)
            screen.blit(lbl_surf, lbl_surf.get_rect(center=launch_rect.center).topleft)

            if clicked and selected_ok and launch_rect.collidepoint(mouse_pos):
                selected_aircraft_model = next(
                    (a["model"] for a in AIRCRAFTS if a["id"] == selected_aircraft),
                    "models/f167",
                )
                session = {
                    "mode": selected_mode,
                    "selected_node_id": selected_node_id,
                    "selected_challenge_id": selected_challenge_id,
                    "selected_aircraft_id": selected_aircraft,
                    "selected_aircraft_model": selected_aircraft_model,
                }
                progression["selected_aircraft"] = selected_aircraft
                save_json(PROGRESSION_FILE, progression)
                save_json(SESSION_FILE, session)
                subprocess.Popen([sys.executable, "master_of_puppets.py"])
                running = False

        # ══════════════════════════════════════════════════════════════════════
        # LOADOUT TAB
        # ══════════════════════════════════════════════════════════════════════
        elif current_tab == "loadout":
            lp = pygame.Rect(22, 152, 1156, 578)
            draw_panel(screen, lp, accent=THEME["panel_edge"])

            equipped = progression.get("equipped", {})
            inventory = progression.get("inventory", {})

            categories = ["plane", "armor", "missile", "radar"]
            cat_names  = ["AIRCRAFT", "ARMOR", "MISSILE", "RADAR"]
            cat_icons  = ["✈", "🛡", "🚀", "📡"]
            inventory_keys = {
                "plane": "planes",
                "armor": "armor",
                "missile": "missiles",
                "radar": "radars",
            }

            col_w = (lp.width - 40) // len(categories)
            for ci, (cat, name, icon) in enumerate(zip(categories, cat_names, cat_icons)):
                cx = lp.x + 16 + ci * col_w
                cy = lp.y + 16

                # Column header
                head_rect = pygame.Rect(cx, cy, col_w - 8, 40)
                draw_rect_alpha(screen, THEME["panel_hi"], head_rect, 200, 8)
                pygame.draw.rect(screen, THEME["panel_edge"], head_rect, width=1, border_radius=8)
                screen.blit(heading_font.render(f"{icon} {name}", True, THEME["accent"]),
                            (cx + 12, cy + 10))
                cy += 48

                equip_val = equipped.get(cat)
                inv_key = inventory_keys.get(cat, cat)
                available = inventory.get(inv_key, [])
                if not isinstance(available, list):
                    available = []

                for item_id in available[:8]:
                    rect = pygame.Rect(cx, cy, col_w - 8, 38)
                    active = equip_val == item_id
                    hov = rect.collidepoint(mouse_pos)
                    if active:
                        draw_glow_rect(screen, THEME["accent"], rect, 6, 5, 40)
                        draw_rect_alpha(screen, (0, 40, 70), rect, 220, 6)
                        pygame.draw.rect(screen, THEME["accent"], rect, width=1, border_radius=6)
                    elif hov:
                        draw_rect_alpha(screen, THEME["row_hover"], rect, 180, 6)
                    else:
                        draw_rect_alpha(screen, THEME["row_a"], rect, 160, 6)
                        pygame.draw.rect(screen, THEME["panel_edge2"], rect, width=1, border_radius=6)

                    if active:
                        draw_tag(screen, "EQUIPPED", rect.x + 8, rect.y + 10, tiny_font,
                                 THEME["accent"], (4, 8, 16), 3, 5, 2)
                        screen.blit(small_font.render(item_id, True, THEME["accent"]),
                                    (rect.x + 90, rect.y + 10))
                    else:
                        screen.blit(small_font.render(item_id, True, THEME["text_dim"] if not hov else THEME["text"]),
                                    (rect.x + 12, rect.y + 10))

                    if clicked and rect.collidepoint(mouse_pos):
                        progression["equipped"][cat] = item_id
                        save_json(PROGRESSION_FILE, progression)
                    cy += 44

                if not available:
                    screen.blit(small_font.render("None owned", True, THEME["text_muted"]), (cx + 12, cy + 10))

            # Flares
            fl_y = lp.bottom - 50
            draw_separator(screen, lp.x + 12, fl_y - 10, lp.width - 24)
            fl_str = f"✦  FLARES AVAILABLE:  {inventory.get('flares', 0)}"
            screen.blit(body_font.render(fl_str, True, THEME["accent_warn"]), (lp.x + 20, fl_y))

        # ══════════════════════════════════════════════════════════════════════
        # SHOP TAB
        # ══════════════════════════════════════════════════════════════════════
        elif current_tab == "shop":
            lp = pygame.Rect(22, 152, 540, 578)
            draw_panel(screen, lp, accent=THEME["panel_edge"])

            rp = pygame.Rect(574, 152, 604, 578)
            draw_panel(screen, rp, accent=THEME["panel_edge"])

            # Category pills
            cat_ids = ["armor", "planes", "missiles", "radars", "flares"]
            cat_labels = ["ARMOR", "PLANES", "MISSILES", "RADARS", "FLARES"]
            pill_y = lp.y + 14
            total_pill_w = lp.width - 28
            pill_h = 32
            single_w = (total_pill_w - 4 * 6) // 5
            for i, (cid, clbl) in enumerate(zip(cat_ids, cat_labels)):
                px = lp.x + 14 + i * (single_w + 6)
                rect = pygame.Rect(px, pill_y, single_w, pill_h)
                active = shop_category == cid
                hov = rect.collidepoint(mouse_pos) and not active
                if active:
                    draw_glow_rect(screen, THEME["accent"], rect, 6, 4, 40)
                    draw_rect_alpha(screen, THEME["accent"], rect, 210, 6)
                    screen.blit(tiny_font.render(clbl, True, (4, 8, 16)),
                                tiny_font.render(clbl, True, (4, 8, 16)).get_rect(center=rect.center).topleft)
                else:
                    draw_rect_alpha(screen, THEME["panel_hi"], rect, 180, 6)
                    if hov:
                        draw_rect_alpha(screen, THEME["accent2"], rect, 60, 6)
                    pygame.draw.rect(screen, THEME["panel_edge2"], rect, width=1, border_radius=6)
                    screen.blit(tiny_font.render(clbl, True, THEME["text_dim"] if not hov else THEME["text"]),
                                tiny_font.render(clbl, True, THEME["text"]).get_rect(center=rect.center).topleft)
                if clicked and rect.collidepoint(mouse_pos):
                    shop_category = cid
                    shop_message = ""

            draw_separator(screen, lp.x + 12, lp.y + 52, lp.width - 24)

            # Shop items list
            iy = lp.y + 64
            hovered_item = None
            for item in SHOP_ITEMS.get(shop_category, []):
                owned = False
                if shop_category == "flares":
                    owned = False
                else:
                    owned = item["id"] in progression["inventory"].get(shop_category, [])

                rect = pygame.Rect(lp.x + 14, iy, lp.width - 28, 64)
                hov = rect.collidepoint(mouse_pos)
                if hov:
                    hovered_item = item

                if owned:
                    draw_rect_alpha(screen, THEME["done"], rect, 180, 8)
                    pygame.draw.rect(screen, THEME["done_fg"], rect, width=1, border_radius=8)
                elif hov:
                    draw_glow_rect(screen, THEME["accent"], rect, 8, 4, 25)
                    draw_rect_alpha(screen, THEME["row_hover"], rect, 200, 8)
                    pygame.draw.rect(screen, THEME["accent"], rect, width=1, border_radius=8)
                else:
                    draw_rect_alpha(screen, THEME["panel_hi"], rect, 180, 8)
                    pygame.draw.rect(screen, THEME["panel_edge2"], rect, width=1, border_radius=8)

                # Owned badge
                if owned:
                    draw_tag(screen, "OWNED", rect.x + 8, rect.y + 8, tiny_font, THEME["done"], THEME["done_fg"], 3, 5, 2)
                    nx = rect.x + 70
                else:
                    nx = rect.x + 10

                screen.blit(small_font.render(item["name"], True, THEME["done_fg"] if owned else (THEME["accent"] if hov else THEME["text"])),
                            (nx, rect.y + 8))
                desc_lines = textwrap.wrap(item["description"], 44)
                if desc_lines:
                    screen.blit(tiny_font.render(desc_lines[0], True, THEME["text_dim"]), (nx, rect.y + 28))
                # Price
                price_s = body_font.render(f"◈ {item['price']:,}", True, THEME["accent_warn"] if not owned else THEME["text_muted"])
                screen.blit(price_s, (rect.right - price_s.get_width() - 12, rect.y + 22))

                if not owned and clicked and rect.collidepoint(mouse_pos):
                    success, message = purchase_item(progression, shop_category, item["id"])
                    shop_message = message
                    shop_message_ok = success
                    if success:
                        progression = normalize_progression(load_json(PROGRESSION_FILE, default_progression()))
                iy += 72

            # Message
            if shop_message:
                msg_c = THEME["accent_green"] if shop_message_ok else THEME["danger"]
                screen.blit(body_font.render(shop_message, True, msg_c), (lp.x + 14, iy + 8))

            # Right panel: item detail
            screen.blit(heading_font.render("ITEM DETAILS", True, THEME["accent"]), (rp.x + 16, rp.y + 14))
            draw_separator(screen, rp.x + 12, rp.y + 44, rp.width - 24)
            if hovered_item:
                dy = rp.y + 58
                screen.blit(heading_font.render(hovered_item["name"], True, THEME["text"]), (rp.x + 16, dy))
                dy += 32
                # Description
                for line in textwrap.wrap(hovered_item.get("description", ""), 52):
                    screen.blit(small_font.render(line, True, THEME["text_dim"]), (rp.x + 16, dy))
                    dy += 22
                dy += 12
                draw_separator(screen, rp.x + 12, dy, rp.width - 24)
                dy += 16
                # Stats
                stat_map = [
                    ("Price", f"{hovered_item.get('price', 0):,} AirBucks"),
                    ("Health Bonus", f"+{hovered_item['health_bonus']} HP" if "health_bonus" in hovered_item else None),
                    ("Speed Penalty", f"-{int(hovered_item['speed_penalty']*100)}%" if "speed_penalty" in hovered_item else None),
                    ("Damage", str(hovered_item["damage"]) if "damage" in hovered_item else None),
                    ("Speed Mult", f"×{hovered_item['speed']:.1f}" if "speed" in hovered_item and isinstance(hovered_item["speed"], float) else None),
                    ("Turn Rate", f"×{hovered_item.get('turn_rate', '')}" if "turn_rate" in hovered_item else None),
                    ("Count", str(hovered_item["count"]) if "count" in hovered_item else None),
                    ("Radar Range", f"{hovered_item['range']} m" if "range" in hovered_item else None),
                ]
                for label, val in stat_map:
                    if val:
                        draw_stat_row(screen, f"{label:<18}", val, rp.x + 16, dy, 200, small_font, body_font, True)
                        dy += 30
                # Affordability
                can = can_afford(progression, hovered_item.get("price", 0))
                aff_str = "✔ You can afford this" if can else "✘ Insufficient AirBucks"
                aff_c = THEME["accent_green"] if can else THEME["danger"]
                screen.blit(small_font.render(aff_str, True, aff_c), (rp.x + 16, dy + 10))
            else:
                screen.blit(small_font.render("Hover an item to see details", True, THEME["text_muted"]),
                            (rp.x + 16, rp.y + 64))

        # ══════════════════════════════════════════════════════════════════════
        # BADGES TAB
        # ══════════════════════════════════════════════════════════════════════
        elif current_tab == "badges":
            # Stats panel (left)
            sp = pygame.Rect(22, 152, 380, 578)
            draw_panel(screen, sp, accent=THEME["accent"])
            screen.blit(heading_font.render("PILOT STATISTICS", True, THEME["accent"]), (sp.x + 16, sp.y + 14))
            draw_separator(screen, sp.x + 12, sp.y + 44, sp.width - 24)

            stats = progression.get("stats", {})
            stat_rows = [
                ("Total Kills",    stats.get("total_kills", 0)),
                ("Total Deaths",   stats.get("total_deaths", 0)),
                ("Missions Done",  stats.get("missions_completed", 0)),
                ("Best Survival",  f"{stats.get('best_survival_time', 0):.1f} s"),
                ("Time Flown",     f"{stats.get('time_flown', 0):.1f} s"),
            ]
            sy = sp.y + 60
            for label, val in stat_rows:
                # Bar background
                bar_rect = pygame.Rect(sp.x + 16, sy, sp.width - 32, 48)
                draw_rect_alpha(screen, THEME["panel_hi"], bar_rect, 180, 6)
                pygame.draw.rect(screen, THEME["panel_edge2"], bar_rect, width=1, border_radius=6)
                screen.blit(small_font.render(label, True, THEME["text_dim"]), (sp.x + 26, sy + 8))
                val_s = heading_font.render(str(val), True, THEME["accent"])
                screen.blit(val_s, (sp.right - val_s.get_width() - 24, sy + 10))
                sy += 56

            # K/D ratio
            kills = stats.get("total_kills", 0)
            deaths = max(1, stats.get("total_deaths", 1))
            kd = kills / deaths
            kd_rect = pygame.Rect(sp.x + 16, sy + 8, sp.width - 32, 56)
            draw_glow_rect(screen, THEME["accent_warn"], kd_rect, 8, 5, 35)
            draw_rect_alpha(screen, (40, 28, 0), kd_rect, 200, 8)
            pygame.draw.rect(screen, THEME["accent_warn"], kd_rect, width=1, border_radius=8)
            screen.blit(small_font.render("K/D RATIO", True, THEME["text_dim"]), (kd_rect.x + 14, kd_rect.y + 10))
            kd_s = title_font.render(f"{kd:.2f}", True, THEME["accent_warn"])
            screen.blit(kd_s, (kd_rect.right - kd_s.get_width() - 14, kd_rect.y + 8))

            # Badges panel (right)
            bp = pygame.Rect(414, 152, 764, 578)
            draw_panel(screen, bp, accent=THEME["accent_warn"])
            screen.blit(heading_font.render("BADGES & ACHIEVEMENTS", True, THEME["accent_warn"]), (bp.x + 16, bp.y + 14))
            draw_separator(screen, bp.x + 12, bp.y + 44, bp.width - 24)

            by = bp.y + 58
            badge_cols = 2
            badge_col_w = (bp.width - 32 - 12) // badge_cols
            for bi, badge_def in enumerate(BADGE_DEFINITIONS):
                earned = badge_def["id"] in progression.get("badges", [])
                bx = bp.x + 16 + (bi % badge_cols) * (badge_col_w + 12)
                bcy = by + (bi // badge_cols) * 76
                b_rect = pygame.Rect(bx, bcy, badge_col_w, 68)

                if earned:
                    draw_glow_rect(screen, THEME["accent_warn"], b_rect, 8, 5, 35)
                    draw_rect_alpha(screen, (40, 30, 0), b_rect, 210, 8)
                    pygame.draw.rect(screen, THEME["accent_warn"], b_rect, width=1, border_radius=8)
                else:
                    draw_rect_alpha(screen, THEME["locked"], b_rect, 180, 8)
                    pygame.draw.rect(screen, THEME["panel_edge2"], b_rect, width=1, border_radius=8)

                icon = "★" if earned else "○"
                ic = THEME["accent_warn"] if earned else THEME["text_muted"]
                screen.blit(heading_font.render(icon, True, ic), (b_rect.x + 10, b_rect.y + 10))
                nc = THEME["text"] if earned else THEME["locked_fg"]
                screen.blit(small_font.render(badge_def["name"], True, nc), (b_rect.x + 36, b_rect.y + 10))
                dc = THEME["text_dim"] if earned else THEME["text_muted"]
                for li, dl in enumerate(textwrap.wrap(badge_def["description"], 34)[:2]):
                    screen.blit(tiny_font.render(dl, True, dc), (b_rect.x + 36, b_rect.y + 32 + li * 16))

        # ── FOOTER ──────────────────────────────────────────────────────────
        footer_y = H - 22
        if not audio_ready:
            screen.blit(tiny_font.render("⚠ Audio device unavailable", True, THEME["danger"]), (28, footer_y))
        elif audio_ready and not music_loaded:
            screen.blit(tiny_font.render("♪ Menu music missing (models/menu_music.mp3)", True, THEME["text_muted"]), (28, footer_y))

        version_s = tiny_font.render("AeroMania  v1.0  //  MISSION COMMAND", True, THEME["text_muted"])
        screen.blit(version_s, (W - version_s.get_width() - 28, footer_y))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    run_menu()
