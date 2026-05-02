from ursina import *
from ursina import Quat
import random, math, time
import os, sys
from copy import deepcopy
from ursina.prefabs.trail_renderer import TrailRenderer
import socket, json, threading, uuid
game_paused = True
def start_game():
    global game_paused
    game_paused = False
y = 4
Text.default_font = "models/orbitron.ttf"

SAVE_DIR = "save"
PROGRESSION_FILE = os.path.join(SAVE_DIR, "progression.json")
SESSION_FILE = os.path.join(SAVE_DIR, "session_config.json")
QUESTS_FILE = "quests.json"


def load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
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
        "currency": 1000,  # AirBucks
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


def load_quests(path=QUESTS_FILE):
    return load_json(path, {"tiers": [], "challenges": []})


def iter_quest_nodes(quests_data):
    for tier in quests_data.get("tiers", []):
        for node in tier.get("nodes", []):
            yield node


def find_quest_node(node_id, quests_data):
    for node in iter_quest_nodes(quests_data):
        if node.get("id") == node_id:
            return node
    return None


def find_challenge(challenge_id, quests_data):
    for challenge in quests_data.get("challenges", []):
        if challenge.get("id") == challenge_id:
            return challenge
    return None


def load_missions(path="missions/missions.json"):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    missions_data = data.get("missions", [])
    if not isinstance(missions_data, list):
        raise ValueError("missions.json format error: 'missions' must be a list")
    return missions_data


def _build_mission_briefing_text(selected_mission):
    objective_lines = []
    for i, objective in enumerate(selected_mission.get("objectives", []), start=1):
        objective_text = objective.get("description", "No objective description")
        objective_lines.append(f"{i}. {objective_text}")
    optional_lines = []
    for i, objective in enumerate(selected_mission.get("optional_objectives", []), start=1):
        optional_lines.append(f"{i}. {objective.get('description', 'Optional objective')}")
    fail_lines = selected_mission.get("fail_conditions", [])

    objectives_block = "\n".join(objective_lines) if objective_lines else "No objectives"
    optional_block = "\n".join(optional_lines) if optional_lines else "None"
    fail_block = "\n".join([f"- {line}" for line in fail_lines]) if fail_lines else "None"
    bonus_time = selected_mission.get("bonus_time")
    bonus_text = f"{bonus_time}s" if bonus_time else "N/A"
    return (
        f"\n=== MISSION BRIEFING ===\n"
        f"Mission: {selected_mission.get('name', 'Unknown Mission')}\n\n"
        f"Briefing: {selected_mission.get('description', 'No briefing available')}\n\n"
        f"Objectives:\n{objectives_block}\n\n"
        f"Optional Objectives:\n{optional_block}\n\n"
        f"Fail Conditions:\n{fail_block}\n\n"
        f"Bonus Time: {bonus_text}"
    )


quests_data = load_quests()
progression = load_json(PROGRESSION_FILE, default_progression())
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
current_session = load_json(SESSION_FILE, {})
session_mode = current_session.get("mode", "random")
selected_node_id = current_session.get("selected_node_id")
selected_challenge_id = current_session.get("selected_challenge_id")
selected_aircraft_model = current_session.get("selected_aircraft_model")
selected_aircraft_id = current_session.get("selected_aircraft_id", progression.get("selected_aircraft", "f167"))
aircraft_models = {
    "f16": "models/f16",
    "f167": "models/f167",
    "tinker": "models/tinker",
    "ac130": "models/ac130",
    "xwing": "models/xwing",
}

SHOP_ITEMS = {
    "armor": [
        {"id": "light_armor", "name": "Light Armor", "price": 1000, "health_bonus": 50, "speed_penalty": 0.05, "description": "Basic protection with minimal speed loss"},
        {"id": "medium_armor", "name": "Medium Armor", "price": 2000, "health_bonus": 100, "speed_penalty": 0.1, "description": "Balanced protection and mobility"},
        {"id": "heavy_armor", "name": "Heavy Armor", "price": 3000, "health_bonus": 200, "speed_penalty": 0.15, "description": "Maximum protection at cost of speed"}
    ],
    "planes": [
        {"id": "tinker", "name": "Tinker", "price": 4000, "speed": 400, "turn_rate": 2.0, "held_keys": 1, "size": 1.0, "description": "Agile fighter with good maneuverability"},
        {"id": "ac130", "name": "AC-130", "price": 6000, "speed": 300, "turn_rate": 0.8, "held_keys": 3, "size": 2.0, "description": "Heavy gunship with devastating firepower"},
        {"id": "xwing", "name": "X-Wing", "price": 5000, "speed": 1000, "turn_rate": 1.5, "held_keys": 2, "size": 1.2, "description": "Starfighter with balanced stats"}
    ],
    "missiles": [
        {"id": "mega", "name": "Mega Missile", "price": 600, "speed": 1.2, "turn_rate": 1.1, "count": 20, "damage": 150, "color": (255, 255, 0), "description": "Enhanced missile with better tracking"},
        {"id": "military_grade", "name": "Military-Grade", "price": 1000, "speed": 1.5, "turn_rate": 1.3, "count": 30, "damage": 200, "color": (255, 0, 0), "description": "Professional military missile"},
        {"id": "supersonic", "name": "Supersonic", "price": 1600, "speed": 2.0, "turn_rate": 1.5, "count": 40, "damage": 250, "color": (0, 255, 255), "description": "High-speed missile with excellent range"},
        {"id": "hypersonic", "name": "Hypersonic", "price": 2400, "speed": 3.0, "turn_rate": 1.8, "count": 50, "damage": 300, "color": (255, 0, 255), "description": "Ultra-fast missile with perfect tracking"},
        {"id": "nuclear", "name": "Nuclear", "price": 4000, "speed": 2.5, "turn_rate": 2.0, "count": 60, "damage": 500, "color": (255, 255, 255), "description": "Devastating nuclear missile"}
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

if not selected_aircraft_model:
    selected_aircraft_model = aircraft_models.get(selected_aircraft_id, "models/f167")

def can_afford(item_price):
    return progression["currency"] >= item_price

def purchase_item(category, item_id):
    if category not in SHOP_ITEMS:
        return False, "Invalid category"
    
    item = next((i for i in SHOP_ITEMS[category] if i["id"] == item_id), None)
    if not item:
        return False, "Item not found"
    
    if not can_afford(item["price"]):
        return False, "Insufficient funds"
    
    progression["currency"] -= item["price"]
    
    if category == "flares":
        progression["inventory"]["flares"] += item["count"]
    else:
        if item_id not in progression["inventory"][category]:
            progression["inventory"][category].append(item_id)
    
    save_json(PROGRESSION_FILE, progression)
    return True, f"Purchased {item['name']}"

def check_badges():
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

def award_currency(amount, reason=""):
    progression["currency"] += amount
    save_json(PROGRESSION_FILE, progression)
    return amount

# Apply equipped items
equipped = progression.get("equipped", {})
base_health = 100
armor_bonus = 0
if equipped.get("armor"):
    armor_item = next((a for a in SHOP_ITEMS["armor"] if a["id"] == equipped["armor"]), None)
    if armor_item:
        armor_bonus = armor_item["health_bonus"]

player_health = base_health + armor_bonus

# Set selected aircraft from equipped
if equipped.get("plane"):
    selected_aircraft_id = equipped["plane"]
    selected_aircraft_model = aircraft_models.get(selected_aircraft_id, "models/f167")

# Missile settings
current_missile_type = equipped.get("missile", "basic")
missile_settings = next((m for m in SHOP_ITEMS["missiles"] if m["id"] == current_missile_type), SHOP_ITEMS["missiles"][0])

# Apply armor speed penalty
speed_penalty = 1.0
if equipped.get("armor"):
    armor_item = next((a for a in SHOP_ITEMS["armor"] if a["id"] == equipped["armor"]), None)
    if armor_item:
        speed_penalty = 1.0 - armor_item.get("speed_penalty", 0.0)

# Apply plane-specific stats
plane_stats = next((p for p in SHOP_ITEMS["planes"] if p["id"] == selected_aircraft_id), None)
if plane_stats:
    # Could modify physics constants here based on plane
    pass

# Set global speed penalty
import physics
physics.speed_penalty = speed_penalty

active_node = find_quest_node(selected_node_id, quests_data) if session_mode == "quests" else None
active_challenge = find_challenge(selected_challenge_id, quests_data) if session_mode == "challenges" else None
difficulty_scale = 1.0
active_mission_id = None
active_mission_type = "random"

if active_node:
    mission = deepcopy(active_node.get("mission", {}))
    difficulty_scale = float(active_node.get("difficulty_scale", 1.0))
    active_mission_id = active_node.get("id")
    active_mission_type = "quest"
elif active_challenge:
    mission = deepcopy(active_challenge.get("mission", {}))
    difficulty_scale = float(active_challenge.get("difficulty_scale", 1.0))
    active_mission_id = active_challenge.get("id")
    active_mission_type = "challenge"
else:
    missions = load_missions()
    if not missions:
        raise ValueError("No missions found in missions/missions.json")
    mission = random.choice(missions).copy()

mission["objectives"] = [obj.copy() for obj in mission.get("objectives", [])]
initial_enemy_count_override = mission.get("enemy_spawn_count")



missiles = []
enemy_planes = []
flares = []
# Offscreen enemy arrows (HUD)
offscreen_arrows = {}
game_over = False

editor_mode = False
editor_cam = None

cockpit_view = False  # Toggle between external & cockpit view

mouse_sensitivity = 28
mouse_pitch = 0
mouse_yaw = 0
max_look_angle = 25

# Initialize Ursina App
app = Ursina()
window.fullscreen = True
window.show_ursina_splash = True
window.borderless = True
window.vsync = True
window.color = color.rgb(0, 0, 0)
window.title = "Flight Simulator - Dogfight Mode"
mouse.locked = False
mouse.visible = True

def restart_game():
    os.execl(sys.executable, sys.executable, *sys.argv)


black_overlay = Entity(
    parent=camera.ui,
    model='quad',
    scale=(2, 2),
    color=color.black,
    z=-1
)

intro_sequence = None
intro_active = False


# HUD text
displayed = Text(
    "",
    parent=camera.ui,
    position=window.center - Vec2(0.5, 0),
    z=-2,
    origin=(-0.5, 0),
    scale=1.3,
    color=color.rgb(0, 255, 100)
)
badge_toast = Text(
    "",
    parent=camera.ui,
    position=window.top + Vec2(0, -0.08),
    origin=(0, 0),
    scale=1.4,
    color=color.rgb(255, 220, 90),
    enabled=False
)
skip_hint = Text(
    "Press Enter to skip",
    parent=camera.ui,
    position=window.bottom_left + Vec2(0.02, 0.04),
    origin=(0, 0),
    scale=0.9,
    color=color.rgb(200, 255, 200),
    enabled=False
)




def typewriter_text(text, base_delay=0.015):
    seq = Sequence()
    displayed.text = ""

    for char in text:
        seq.append(Func(lambda c=char: setattr(displayed, "text", displayed.text + c)))

        if char in ".!?":
            delay = base_delay * 10
        elif char in ",:;":
            delay = base_delay * 5
        elif char == "\n":
            delay = base_delay * 15
        else:
            delay = base_delay

        seq.append(Wait(delay + random.uniform(0, base_delay * 0.5)))

    return seq


def add_text(t):
    displayed.text += t
def clear_displayed():
    displayed.text = ""
def show_badge_unlocked(new_badges):
    if not new_badges:
        return
    badge_names = ", ".join([b["name"] for b in new_badges])
    badge_toast.text = f"Badge Unlocked: {badge_names}"
    badge_toast.color = color.rgba(255, 220, 90, 255)
    badge_toast.enabled = True
    badge_toast.animate_color(color.rgba(255, 220, 90, 0), duration=3)
    invoke(lambda: setattr(badge_toast, "enabled", False), delay=3.1)
def _end_intro():
    global intro_active
    intro_active = False
    skip_hint.enabled = False
def skip_intro():
    global intro_sequence
    if not intro_active:
        return
    if intro_sequence:
        try:
            intro_sequence.finish()
        except Exception:
            try:
                intro_sequence.pause()
            except Exception:
                pass
        intro_sequence = None
    clear_displayed()
    start_game()
    black_overlay.animate_color(color.rgba(0, 0, 0, 0), duration=0.5)
    _end_intro()
def game_intro():
    global game_paused, intro_sequence, intro_active
    game_paused = True

    briefing_text = _build_mission_briefing_text(mission)
    displayed.text = ""

    intro_active = True
    skip_hint.enabled = True

    intro_sequence = Sequence(
        Wait(3),
        typewriter_text(briefing_text, base_delay=0.03),
        Wait(10),
        Func(start_game),  
        Wait(10),
        Func(clear_displayed),
        Func(lambda: black_overlay.animate_color(color.rgba(0,0,0,0), duration=2)),
        Func(_end_intro)

    )
    intro_sequence.start()

start_game()
clear_displayed()
black_overlay.animate_color(color.rgba(0, 0, 0, 0), duration=0.5)
mission_start_time = time.time()
#Physics Constants
g = 9.81  # Gravity (m/s²)
vertical_velocity = 0  # Vertical velocity (m/s)
rho0 = 1.225  # Air density at sea level (kg/m³)
H = 8000  # Scale height for atmosphere (m)
S = 27.87  # Wing area of F-16 (m²)
Sf = 28  # Reference area for drag
mass = 12000  # Max takeoff weight (kg)
T_max = 129000  # Max thrust of F-16 (N)
Cd0 = 0.03  # Zero-lift drag coefficient
k = 0.07  # Induced drag factor
CL0 = 0.2  # Lift coefficient at zero AoA
CL_alpha = 0.12  # Lift curve slope per degree
missile_weight = 85  # Missile weight (kg)
missile_velocity = 300  # Missile speed (m/s)

# Combat Variables
player_health = base_health + armor_bonus
missile_count = missile_settings.get("count", 50)
flare_count = progression["inventory"].get("flares", 10)
gun_ammo = 500
locked_target = None
target_index = 0
lock_progress = 0
lock_time_required = 2.0  # Seconds to achieve lock
is_locking = False
radar_range = 5000
lock_tone_playing = False
radar_enabled = True  # Toggle radar display

# Persistent progression tuning
upgrades = progression.get("upgrades", {})
radar_range += int(upgrades.get("radar_quality", 0)) * 400
missile_count += int(upgrades.get("missile_capacity", 0))
flare_count += int(upgrades.get("flare_capacity", 0))


def update_progression_on_win():
    global progression
    progression = load_json(PROGRESSION_FILE, default_progression())
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

    elapsed = time.time() - mission_start_time
    stars = 1
    if player_health >= 70:
        stars += 1
    bonus_time = mission.get("bonus_time")
    if bonus_time and elapsed <= bonus_time:
        stars += 1
    stars = min(stars, 3)

    if active_mission_type == "quest" and active_mission_id:
        if active_mission_id not in progression["completed_nodes"]:
            progression["completed_nodes"].append(active_mission_id)
        best = progression["node_stars"].get(active_mission_id, 0)
        progression["node_stars"][active_mission_id] = max(best, stars)
    elif active_mission_type == "challenge" and active_mission_id:
        best = progression["challenge_stars"].get(active_mission_id, 0)
        progression["challenge_stars"][active_mission_id] = max(best, stars)

    rewards = mission.get("rewards", {})
    
    # Currency rewards
    base_reward = rewards.get("currency", 50)  # Base reward of 50 AirBucks
    reward_scale = max(0.5, float(difficulty_scale)) if 'difficulty_scale' in globals() else 1.0
    currency_reward = int(round(base_reward * reward_scale))
    progression["currency"] += currency_reward
    
    for aircraft_id in rewards.get("aircraft_unlocks", []):
        if aircraft_id not in progression["unlocked_aircraft"]:
            progression["unlocked_aircraft"].append(aircraft_id)
        if aircraft_id not in progression["inventory"]["planes"]:
            progression["inventory"]["planes"].append(aircraft_id)

    for key, value in rewards.get("upgrades", {}).items():
        progression["upgrades"][key] = progression["upgrades"].get(key, 0) + value

    for cosmetic in rewards.get("cosmetics", []):
        if cosmetic not in progression["cosmetics"]:
            progression["cosmetics"].append(cosmetic)

    # Update stats
    progression["stats"]["missions_completed"] += 1
    progression["stats"]["time_flown"] += elapsed
    if elapsed > progression["stats"]["best_survival_time"]:
        progression["stats"]["best_survival_time"] = elapsed

    # Check for new badges
    new_badges = check_badges()
    
    progression["selected_aircraft"] = selected_aircraft_id
    save_json(PROGRESSION_FILE, progression)
    
    return currency_reward, new_badges
# Load Textures & Sounds
runway_texture = load_texture('models/runway.jpg')
cockpit_texture = load_texture('models/cockpit.png')
grass_texture = load_texture('models/terraiin.jpg')
wmap = load_texture('models/no-zoom.jpeg')
plane_engine = Audio('models/plane_engine.mp3', loop=True, volume=0.1, autoplay=True)
crash_sound = Audio('models/crash.mp3', autoplay=False)
terrain_warning = Audio('models/terrain.mp3', autoplay=False)
explosion = Audio('models/explosion.mp3', autoplay=False)
#check for mp3 files ending in "music"
matched_files = []
    # Loop through files in the directory
suffix = "music.mp3"
for filename in os.listdir("models"):

    if filename.lower().endswith(suffix.lower()):
        matched_files.append(os.path.join("/models", filename))
x = len(matched_files)
bgm = Audio(random.choice(matched_files), autoplay=True, loop=True)
