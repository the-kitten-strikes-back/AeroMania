from ursina import *
from ursina import Quat
import random, math, time
import os, sys
from ursina.prefabs.trail_renderer import TrailRenderer
import socket, json, threading, uuid
y = 4
print("Starting in 5 seconds...")
for i in range(5, 0, -1):
    print(i)
    time.sleep(1)
missiles = []
enemy_planes = []
flares = []
# Offscreen enemy arrows (HUD)
offscreen_arrows = {}
game_over = False

editor_mode = False
editor_cam = None

cockpit_view = False  # Toggle between external & cockpit view

# Initialize Ursina App
app = Ursina()
window.fullscreen = True
window.show_ursina_splash = True
window.borderless = True
window.vsync = True
window.color = color.rgb(0, 0, 0)
window.title = "Flight Simulator - Dogfight Mode"


def restart_game():
    os.execl(sys.executable, sys.executable, *sys.argv)



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
player_health = 100
missile_count = 50
flare_count = 10
gun_ammo = 500
locked_target = None
target_index = 0
lock_progress = 0
lock_time_required = 2.0  # Seconds to achieve lock
is_locking = False
radar_range = 5000
lock_tone_playing = False
radar_enabled = True  # Toggle radar display

# Load Textures & Sounds
runway_texture = load_texture('models/runway.jpg')
cockpit_texture = load_texture('models/cockpit.png')
grass_texture = load_texture('models/terraiin.jpg')
wmap = load_texture('models/no-zoom.jpeg')
plane_engine = Audio('models/plane_engine.mp3', loop=True, volume=0.1, autoplay=True)
crash_sound = Audio('models/crash.mp3', autoplay=False)
terrain_warning = Audio('models/terrain.mp3', autoplay=False)
explosion = Audio('models/explosion.mp3', autoplay=False)
if random.choice([1,2,3,4]) == 1:
    bgm = Audio('models/battle-music.mp3', autoplay=True, loop=True)
elif random.choice([1,2,3]) == 2:
    bgm = Audio('models/epic-music.mp3', autoplay=True, loop=True)
elif random.choice([1,2,3,4]) == 3:
    bgm = Audio('models/risk-music.mp3', autoplay=True, loop=True)
else:
    bgm = Audio('models/chase-music.mp3', autoplay=True, loop=True)

def create_explosion(position, num_particles=20, speed=5, lifetime=1):
    for _ in range(num_particles):
        particle = Entity(
            model='sphere',
            color=color.orange,
            scale=0.2,
            position=position
        )
        direction = Vec3(random.uniform(-1,1), random.uniform(0,1), random.uniform(-1,1)).normalized()
        particle.animate_position(position + direction * speed, duration=lifetime)
        destroy(particle, delay=lifetime)

def vec3_lerp(start, end, t):
    """Linear interpolation between two Vec3 vectors"""
    return start + (end - start) * t

def trigger_game_over():
    global game_over
    if game_over:
        return

    game_over = True

    # Update death stats
    if 'progression' in globals():
        progression["stats"]["total_deaths"] += 1

    # Freeze the world
    time.scale = 0

    # Stop sounds
    plane_engine.stop()
    bgm.stop()

    # Show UI
    game_over_bg.visible = True
    game_over_title.visible = True
    game_over_sub.visible = True
    restart_text.visible = True
    quit_text.visible = True

    mouse.locked = False


def explosion_3d(position, fireball_scale=4, debris_count=25, smoke_time=2):
    # --- Fireball (expanding sphere) ---
    fireball = Entity(
        model='sphere',
        color=color.orange,
        scale=0.1,
        position=position,
        emissive=True
    )
    fireball.animate_scale(fireball_scale, duration=0.3, curve=curve.out_expo)
    fireball.animate_color(color.rgba(0,0,0,0), duration=0.4, delay=0.3)
    destroy(fireball, delay=0.7)

    # --- Flash (instant bright light) ---
    flash = PointLight(position=position, color=color.rgb(255, 200, 100), shadows=False)
    flash.animate_color(color.rgba(0,0,0,0), duration=0.2)
    destroy(flash, delay=0.25)

    # --- Debris (chunks flying outward) ---
    for i in range(debris_count):
        debris = Entity(
            model='cube',
            scale=0.1,
            color=color.rgb(180, 80, 20),
            position=position,
        )
        direction = Vec3(
            random.uniform(-1,1),
            random.uniform(0,1),
            random.uniform(-1,1)
        ).normalized()

        speed = random.uniform(3, 10)
        debris.animate_position(position + direction * speed, duration=0.8, curve=curve.linear)
        debris.animate_color(color.rgba(0,0,0,0), duration=0.5, delay=0.4)
        destroy(debris, delay=1)

    # --- Smoke puff ---
    smoke = Entity(
        model='sphere',
        color=color.gray,
        scale=0.5,
        position=position
    )
    smoke.animate_scale(6, duration=smoke_time, curve=curve.out_expo)
    smoke.animate_color(color.rgba(20,20,20,0), duration=smoke_time, delay=0.2)
    destroy(smoke, delay=smoke_time)

class Flare(Entity):
    def __init__(self, position, **kwargs):
        super().__init__(
            model='sphere',
            color=color.rgb(255, 200, 100),
            scale=0.3,
            position=position,
            emissive=True,
            **kwargs
        )
        self.lifetime = 3
        self.velocity = Vec3(random.uniform(-2, 2), -5, random.uniform(-2, 2))
        invoke(self.cleanup, delay=self.lifetime)
    
    def update(self):
        self.position += self.velocity * time.dt
        self.velocity.y -= 9.8 * time.dt  # Gravity
    
    def cleanup(self):
        if self in flares:
            flares.remove(self)
        destroy(self)

class Missile(Entity):
    def __init__(self, position, forward_vector, velocity, target=None, is_enemy=False, lifetime=10, **kwargs):
        super().__init__(
            scale=0.1, 
            model='missile', 
            color=color.red if not is_enemy else color.orange, 
            rotationscale=0.02, 
            position=position, 
            collider='box', 
            **kwargs
        )
        self.rotation_x += 90
        self.velocity = velocity
        self.target = target
        self.is_enemy = is_enemy
        self.tracking = target is not None
        self.turn_rate = 3.5  # degrees per frame
        
        self.forward_vec = Vec3(forward_vector.x, forward_vector.y, forward_vector.z).normalized()
        self.trail = TrailRenderer(
            size=Vec3(1, 0.01, 1),
            segments=16,
            min_spacing=0.05,
            fade_speed=0,
            color_gradient=[color.red, color.orange, color.clear],
            parent=self
        )
        invoke(self.cleanup, delay=lifetime)

    def update(self):
        # Heat-seeking logic
        if self.tracking and self.target and hasattr(self.target, 'position'):
            # Check for flare distraction
            closest_flare = None
            min_flare_dist = 100
            for flare in flares:
                dist = distance(self.position, flare.position)
                if dist < min_flare_dist:
                    min_flare_dist = dist
                    closest_flare = flare
            
            # If flare is close, track it instead
            if closest_flare and min_flare_dist < 50:
                target_pos = closest_flare.position
            else:
                target_pos = self.target.position
            
            # Calculate direction to target
            direction = (target_pos - self.position).normalized()
            
            # Gradually turn towards target
            self.forward_vec = vec3_lerp(self.forward_vec, direction, self.turn_rate * time.dt)
            self.forward_vec = self.forward_vec.normalized()
            
            # Update rotation to match direction
            self.look_at(self.position + self.forward_vec)
        
        # Move forward
        self.position += self.forward_vec * self.velocity * time.dt

    def cleanup(self):
        if self in missiles:
            missiles.remove(self)
        destroy(self)

class EnemyPlane(Entity):
    def __init__(self, position, **kwargs):
        super().__init__(
            model='models/f167',
            scale=0.01,
            position=position,
            color=color.red,
            collider='mesh',
            **kwargs
        )
        self.health = 100
        self.speed = random.uniform(200, 300)  # Balanced speed
        self.target = None
        self.state = 'patrol'  # patrol, engage, circle, evade
        self.last_shot_time = 0
        self.shot_cooldown = random.uniform(5, 8)  # Longer cooldown - less spam
        self.ai_timer = 0
        
        # Initial patrol point relative to spawn
        angle = random.uniform(0, math.pi * 2)
        self.patrol_point = self.position + Vec3(
            math.sin(angle) * 2000,
            random.uniform(-200, 200),
            math.cos(angle) * 2000
        )
        
    def update(self):
        global plane
        self.ai_timer += time.dt
        
        # Check distance to player
        dist_to_player = distance(self.position, plane.position)
        
        # State machine with better distance thresholds
        if dist_to_player > 750:
            self.state = 'patrol'
        elif dist_to_player > 375:
            self.state = 'engage'
        elif dist_to_player > 150:
            self.state = 'circle'  # Circle around player to stay in view
        else:
            self.state = 'evade'  # Too close, break away
        
        # Behavior based on state
        if self.state == 'patrol':
            self.patrol_behavior()
        elif self.state == 'engage':
            self.engage_behavior()
        elif self.state == 'circle':
            self.circle_behavior()
        elif self.state == 'evade':
            self.evade_behavior()
        
        # Fire missiles at optimal range (not too close)
        if self.state in ['engage', 'circle'] and time.time() - self.last_shot_time > self.shot_cooldown:
            if 800 < dist_to_player < 2000:  # Optimal firing range
                # Check if player is roughly in front before firing
                to_player = (plane.position - self.position).normalized()
                yaw_rad = math.radians(self.rotation_y)
                my_forward = Vec3(math.sin(yaw_rad), 0, math.cos(yaw_rad)).normalized()
                
                if to_player.dot(my_forward) > 0.7:  # Player in front cone
                    self.fire_missile()
                    self.last_shot_time = time.time()
        
        # Keep altitude reasonable
        if self.y < 100:
            self.y = 100
        elif self.y > 3000:
            self.y = 3000
    
    def patrol_behavior(self):
        """Patrol in patterns that will cross player's field of view"""
        # Move towards patrol point
        direction = (self.patrol_point - self.position).normalized()
        self.position += direction * self.speed * time.dt
        
        # Look in movement direction
        self.look_at(self.position + direction)
        
        # Set new patrol point when reached
        if distance(self.position, self.patrol_point) < 200:
            # Create patrol points that cross in front of player
            # This makes enemies more visible
            angle_to_player = math.atan2(
                plane.position.x - self.position.x,
                plane.position.z - self.position.z
            )
            
            # Random offset from player direction
            offset_angle = angle_to_player + random.uniform(-math.pi/2, math.pi/2)
            patrol_distance = random.uniform(750, 1500)
            
            self.patrol_point = self.position + Vec3(
                math.sin(offset_angle) * patrol_distance,
                random.uniform(-200, 200),
                math.cos(offset_angle) * patrol_distance
            )
    
    def engage_behavior(self):
        """Approach player from angles that will cross their boresight"""
        if not self.target:
            self.target = plane
        
        # Get player's forward direction
        yaw_rad = math.radians(self.target.rotation_y)
        player_forward = Vec3(math.sin(yaw_rad), 0, math.cos(yaw_rad)).normalized()
        
        # Calculate vector from player to enemy
        to_enemy = (self.position - self.target.position).normalized()
        
        # Check if we're behind the player (dot product < 0 means behind)
        dot = to_enemy.dot(player_forward)
        
        if dot < -0.3:  # We're behind player - move to their side/front
            # Circle around to get in front of player
            # Calculate perpendicular direction (to move to side)
            perpendicular = Vec3(-player_forward.z, 0, player_forward.x).normalized()
            
            # Alternate sides based on AI timer
            if math.sin(self.ai_timer * 0.5) > 0:
                perpendicular = -perpendicular
            
            # Move in a circular arc to get ahead of player
            target_pos = self.target.position + player_forward * 750 + perpendicular * 400
            direction = (target_pos - self.position).normalized()
            
        else:  # We're in front or to the side - maintain position or approach
            # Stay at medium range in front of player
            target_pos = self.target.position + player_forward * 1200
            direction = (target_pos - self.position).normalized()
        
        # Move towards target position
        self.position += direction * self.speed * time.dt
        
        # Look at player
        self.look_at(self.target.position)
    
    def circle_behavior(self):
        """Circle around the player to stay visible and in engagement range"""
        # Calculate vector from player to this enemy
        to_enemy = self.position - plane.position
        distance_xz = math.sqrt(to_enemy.x**2 + to_enemy.z**2)
        
        # Desired orbit radius
        orbit_radius = 500
        
        # Calculate tangent direction (perpendicular to radius) for circular motion
        tangent = Vec3(-to_enemy.z, 0, to_enemy.x).normalized()
        
        # Add radial component to maintain distance
        radial = to_enemy.normalized()
        
        if distance_xz < orbit_radius:
            # Too close - move outward while circling
            move_direction = tangent * 0.7 + radial * 0.3
        elif distance_xz > orbit_radius + 200:
            # Too far - move inward while circling
            move_direction = tangent * 0.7 - radial * 0.3
        else:
            # Just right - pure circular motion
            move_direction = tangent
        
        move_direction = move_direction.normalized()
        
        # Move in circular pattern
        self.position += move_direction * self.speed * time.dt
        
        # Add slight altitude variation for more interesting patterns
        altitude_target = plane.y + math.sin(self.ai_timer * 0.3) * 200
        if abs(self.y - altitude_target) > 50:
            self.y += (altitude_target - self.y) * 0.02
        
        # Always face the player (good for firing position)
        self.look_at(plane.position)
    
    def evade_behavior(self):
        """Break away when too close to avoid collision"""
        # Move away from player aggressively
        away_direction = (self.position - plane.position).normalized()
        
        # Add vertical component to evade (go up or down)
        if self.y < plane.y:
            away_direction.y = -0.5  # Dive if below player
        else:
            away_direction.y = 0.5  # Climb if above player
        
        away_direction = away_direction.normalized()
        
        # Add evasive jinking
        jink = Vec3(
            math.sin(self.ai_timer * 8) * 30,
            math.cos(self.ai_timer * 4) * 20,
            math.cos(self.ai_timer * 6) * 30
        )
        
        # Move away at high speed
        self.position += away_direction * self.speed * 1.8 * time.dt
        self.position += jink * time.dt
        
        # Look where we're going
        self.look_at(self.position + away_direction * 100)
    
    def fire_missile(self):
        """Fire missile at player with lead calculation"""
        # Calculate firing direction with lead
        relative_pos = plane.position - self.position
        time_to_target = distance(self.position, plane.position) / missile_velocity  # Missile speed
        
        # Lead the target
        yaw_rad = math.radians(plane.rotation_y)
        player_velocity = Vec3(math.sin(yaw_rad), 0, math.cos(yaw_rad)) * speed
        predicted_pos = plane.position + player_velocity * time_to_target
        
        # Fire towards predicted position
        forward_vector = (predicted_pos - self.position).normalized()
        missile_pos = self.position + forward_vector * 5 + Vec3(0, 1, 0)
        
        missile = Missile(
            position=missile_pos,
            forward_vector=forward_vector,
            velocity=missile_velocity,
            target=plane,
            is_enemy=True,
            lifetime=20
        )
        missiles.append(missile)
    
    def take_damage(self, damage):
        self.health -= damage
        if self.health <= 0:
            self.destroy_plane()
    
    def destroy_plane(self):
        explosion_3d(self.position)
        explosion.play()
        if self in enemy_planes:
            enemy_planes.remove(self)
            # Update kill stats
            if 'progression' in globals():
                progression["stats"]["total_kills"] += 1
        destroy(self)

# Define Airports
airport_positions = [(10579.429, 1.1, 5094.8447), Vec3(15906.743, 1.1, 12849.584), Vec3(17547.707, 1.1, 12500.259)]
airport_codes = ['BLR', 'ICN', 'HND']

def create_airports(positions):
    airports, taxiways, terminals, towers, lights = [], [], [], [], []
    for pos in positions:
        x, y, z = pos
        airports.append(Entity(model='cube', texture=runway_texture, scale=(1000, 0.1, 50), position=(x, y, z), color=color.gray))
        taxiways.append(Entity(model='cube', color=color.light_gray, scale=(400, 0.1, 20), position=(x + 300, y, z + 40)))
        terminals.append(Entity(model='cube', color=color.blue, scale=(100, 30, 100), position=(x + 200, y + 15, z + 100)))
        towers.extend([Entity(model='cube', color=color.gray, scale=(10, 30, 10), position=(x + 300, y + 15, z + 120)),
                       Entity(model='cube', color=color.white, scale=(15, 10, 15), position=(x + 300, y + 35, z + 120))])
        for i in range(10):
            lights.append(Entity(model='sphere', color=color.yellow, scale=2, position=(x - 500 + i * 100, y + 5, z - 20)))

# Terrain
create_airports(airport_positions)
mountain = Entity(model='cube', scale=(500, 300, 500), position=(-2000, 150, 2000), color=color.brown, collider='box')
water = Entity(model='cube', scale=(2000, 1, 500), position=(0, 0.05, -3000), color=color.blue)
ground = Entity(model='plane', texture='models/rocks.jpg', texture_scale=(100, 100), scale=(100000, 100000, 100000), position=((10579.429, 1, 5094.8447)))

# Plane Setup
models = ['models/f16', 'models/tinker', 'models/ac130', 'models/f167', 'models/xwing']
plane = Entity(model=models[1], scale=0.01, rotation=(0, 0, 0), position=((10579.429, 1.2, 5094.8447)), collider='mesh')
camera_offset = Vec3(0, 3, 10)
cockpit_ui = Entity(parent=camera.ui, model='quad', texture=cockpit_texture, scale=(3, 2), position=plane.position, visible=False)

# HUD
speed_display = Text(text='Speed: 0', position=(-0.7, 0.45), scale=2, color=color.white)
altitude_display = Text(text='Altitude: 0', position=(-0.7, 0.4), scale=2, color=color.white)
throttle_display = Text(text='Throttle: 0%', position=(-0.7, 0.35), scale=2, color=color.white)
distance_display = Text(text='Distance from airport: 0', position=(-0.7, 0.3), scale=2, color=color.white)
stall_warning = Text(text='', position=(0, 0.4), scale=2, color=color.red)

game_over_bg = Entity(
    parent=camera.ui,
    model='quad',
    color=color.rgba(0, 0, 0, 180),
    scale=(2, 2),
    z=10,
    visible=False
)

game_over_title = Text(
    parent=camera.ui,
    text='GAME OVER',
    scale=4,
    color=color.red,
    origin=(0, 0),
    position=(0, 0.15),
    visible=False
)

game_over_sub = Text(
    parent=camera.ui,
    text='Your aircraft has been destroyed',
    scale=1.5,
    color=color.white,
    origin=(0, 0),
    position=(0, 0.05),
    visible=False
)

restart_text = Text(
    parent=camera.ui,
    text='Press [R] to Restart',
    scale=1.2,
    color=color.green,
    origin=(0, 0),
    position=(0, -0.1),
    visible=False
)

quit_text = Text(
    parent=camera.ui,
    text='Press [ESC] to Quit',
    scale=1.2,
    color=color.gray,
    origin=(0, 0),
    position=(0, -0.18),
    visible=False
)





# Combat HUD
health_display = Text(text='Health: 100', position=(0.5, 0.45), scale=2, color=color.green)
missile_display = Text(text='Missiles: 20', position=(0.5, 0.4), scale=2, color=color.white)
ammo_display = Text(text='Ammo: 500', position=(0.5, 0.35), scale=2, color=color.white)
flare_display = Text(text='Flares: 10', position=(0.5, 0.3), scale=2, color=color.white)
target_display = Text(text='', position=(0, 0.35), scale=2, color=color.red)
lock_indicator = Text(text='', position=(0, 0.25), scale=3, color=color.red)
warning_display = Text(text='', position=(0, 0.2), scale=2, color=color.orange)
enemy_count_display = Text(text='Enemies: 0', position=(0.5, 0.25), scale=2, color=color.red)

# Targeting reticle
reticle = Entity(parent=camera.ui, model='circle', color=color.green, scale=0.02, position=(0, 0))
lock_box = Entity(parent=camera.ui, model='quad', color=color.clear, scale=0.08, position=(0, 0), visible=False)

# Lock progress bar
lock_bar_bg = Entity(parent=camera.ui, model='quad', color=color.dark_gray, scale=(0.2, 0.02), position=(0, 0.15), visible=False)
lock_bar_fill = Entity(parent=camera.ui, model='quad', color=color.yellow, scale=(0, 0.02), position=(-0.1, 0.15), visible=False)

# Target info brackets (for locked enemy)
bracket_tl = Entity(parent=camera.ui, model='quad', color=color.red, scale=(0.02, 0.002), position=(-0.04, 0.04), visible=False)
bracket_tr = Entity(parent=camera.ui, model='quad', color=color.red, scale=(0.02, 0.002), position=(0.04, 0.04), visible=False)
bracket_bl = Entity(parent=camera.ui, model='quad', color=color.red, scale=(0.02, 0.002), position=(-0.04, -0.04), visible=False)
bracket_br = Entity(parent=camera.ui, model='quad', color=color.red, scale=(0.02, 0.002), position=(0.04, -0.04), visible=False)
bracket_tl2 = Entity(parent=camera.ui, model='quad', color=color.red, scale=(0.002, 0.02), position=(-0.04, 0.04), visible=False)
bracket_tr2 = Entity(parent=camera.ui, model='quad', color=color.red, scale=(0.002, 0.02), position=(0.04, 0.04), visible=False)
bracket_bl2 = Entity(parent=camera.ui, model='quad', color=color.red, scale=(0.002, 0.02), position=(-0.04, -0.04), visible=False)
bracket_br2 = Entity(parent=camera.ui, model='quad', color=color.red, scale=(0.002, 0.02), position=(0.04, -0.04), visible=False)

# Mini-map UI with enhanced radar
minimap = Entity(parent=camera.ui, model='quad', texture=wmap, scale=(0.3, 0.3), position=(0.65, -0.35), color=color.white)
minimap_border = Entity(parent=camera.ui, model='quad', color=color.dark_gray, scale=(0.32, 0.32), position=(0.65, -0.35), z=1)

# Radar overlay (circular radar screen)
radar_bg = Entity(parent=camera.ui, model='circle', color=color.rgba(0, 50, 0, 150), scale=0.25, position=(0.65, -0.35), z=-0.5)
radar_grid = Entity(parent=camera.ui, model='circle', color=color.rgba(0, 255, 0, 100), scale=0.25, position=(0.65, -0.35), z=-0.4)
radar_grid2 = Entity(parent=camera.ui, model='circle', color=color.red, scale=0.17, position=(0.65, -0.35), z=-0.4)
radar_grid3 = Entity(parent=camera.ui, model='circle', color=color.yellow, scale=0.09, position=(0.65, -0.35), z=-0.4)

# Radar range rings labels
radar_label = Text(parent=camera.ui, text='RADAR', position=(0.65, -0.13), scale=1.5, origin=(0, 0), color=color.green)
radar_range_text = Text(parent=camera.ui, text='5000m', position=(0.78, -0.35), scale=1, origin=(0, 0), color=color.green)

# Cardinal direction markers on radar
radar_n = Text(parent=camera.ui, text='N', position=(0.65, -0.10), scale=1.5, origin=(0, 0), color=color.green)
radar_s = Text(parent=camera.ui, text='S', position=(0.65, -0.60), scale=1.5, origin=(0, 0), color=color.green)
radar_e = Text(parent=camera.ui, text='E', position=(0.78, -0.35), scale=1.5, origin=(0, 0), color=color.green)
radar_w = Text(parent=camera.ui, text='W', position=(0.52, -0.35), scale=1.5, origin=(0, 0), color=color.green)

# Radar sweep line (rotating)
radar_sweep = Entity(parent=camera.ui, model='quad', color=color.blue, scale=(0.25, 0.002), position=(0.65, -0.35), z=-0.3, rotation_z=0)

# Player marker (center of radar - triangle pointing forward)
plane_marker = Entity(parent=camera.ui, model='circle', color=color.cyan, scale=0.015, position=(0.65, -0.35), z=-0.2)

# Enemy markers on radar (will be created dynamically)
enemy_markers = []
enemy_distance_texts = []

# Locked target indicator on radar
locked_marker = Entity(parent=camera.ui, model='circle', color=color.red, scale=0.02, position=(0.65, -0.35), z=-0.25, visible=False)
locked_marker_ring = Entity(parent=camera.ui, model='circle', color=color.rgba(255, 0, 0, 0), scale=0.03, position=(0.65, -0.35), z=-0.26, visible=False)

# Altitude meter
altitude_bar_bg = Entity(model='quad', color=color.dark_gray, scale=(0.02, 0.2), position=(-0.8, 0.1), parent=camera.ui)
altitude_bar = Entity(model='quad', color=color.green, scale=(0.02, 0.02), position=(-0.5, -0.1), parent=camera.ui)

# Artificial horizon
horizon_bg = Entity(model='quad', color=color.light_gray, scale=(0.2, 0.1), position=(0, -0.3), parent=camera.ui)
horizon = Entity(model='quad', color=color.blue, scale=(0.2, 0.05), position=(0, -0.3), parent=camera.ui)

# Flight Variables
throttle, max_speed, lift_force, gravity = 0.0, 50, 0.0, 0.21
models_index, autopilot, airport_index = 1, False, 0

def spawn_enemies(count=5):
    """Spawn enemy planes around the map at tactical distances"""
    for i in range(count):
        # Spawn at better engagement distances (2000-4000m away)
        angle = random.uniform(0, 360)
        distance_away = random.uniform(2000, 4000)
        
        spawn_pos = plane.position + Vec3(
            math.sin(math.radians(angle)) * distance_away,
            random.uniform(500, 2000),
            math.cos(math.radians(angle)) * distance_away
        )
        enemy = EnemyPlane(position=spawn_pos)
        enemy_planes.append(enemy)
        
        # Add marker to minimap
        marker = Entity(parent=minimap, model='circle', color=color.red, scale=0.015)
        enemy_markers.append(marker)

def get_targetable_enemies():
    """Get list of enemies within radar range, sorted by distance"""
    targetable = []
    for enemy in enemy_planes:
        dist = distance(plane.position, enemy.position)
        if dist <= radar_range:
            targetable.append((enemy, dist))
    
    # Sort by distance
    targetable.sort(key=lambda x: x[1])
    return [e[0] for e in targetable]

def cycle_target(direction=1):
    """Cycle through available targets"""
    global target_index, locked_target, is_locking, lock_progress
    
    targets = get_targetable_enemies()
    if not targets:
        locked_target = None
        target_index = 0
        is_locking = False
        lock_progress = 0
        return
    
    # Cycle through targets
    target_index = (target_index + direction) % len(targets)
    locked_target = targets[target_index]
    is_locking = True
    lock_progress = 0

def update_targeting():
    """Update targeting system with lock progression"""
    global locked_target, is_locking, lock_progress, target_index
    
    # Clear target if destroyed
    if locked_target and locked_target not in enemy_planes:
        locked_target = None
        is_locking = False
        lock_progress = 0
        target_index = 0
    
    # Update lock progress
    if is_locking and locked_target:
        dist = distance(plane.position, locked_target.position)
        
        # Check if still in range
        if dist > radar_range:
            locked_target = None
            is_locking = False
            lock_progress = 0
            lock_indicator.text = 'OUT OF RANGE'
            lock_indicator.color = color.gray
        else:
            # Check if target is in front of player (simplified FOV check)
            direction = (locked_target.position - plane.position).normalized()
            yaw_rad = math.radians(plane.rotation_y)
            forward = Vec3(math.sin(yaw_rad), 0, math.cos(yaw_rad)).normalized()
            
            dot_product = direction.dot(forward)
            
            # Target must be within ~60 degree cone in front
            if dot_product > 0.5:
                # Increase lock progress
                lock_progress += time.dt
                
                # Lock achieved
                if lock_progress >= lock_time_required:
                    lock_indicator.text = '** LOCKED **'
                    lock_indicator.color = color.red
                    reticle.color = color.red
                else:
                    # Still locking
                    lock_indicator.text = 'LOCKING...'
                    lock_indicator.color = color.yellow
                    reticle.color = color.yellow
                
                # Update lock progress bar
                lock_bar_bg.visible = True
                lock_bar_fill.visible = True
                progress_ratio = min(lock_progress / lock_time_required, 1.0)
                lock_bar_fill.scale_x = 0.2 * progress_ratio
                lock_bar_fill.x = -0.1 + (0.1 * progress_ratio)
                lock_bar_fill.color = color.red if progress_ratio >= 1.0 else color.yellow
                
                # Show target info
                target_display.text = f'Target: {dist:.0f}m | {locked_target.health}HP'
                
                # Show targeting brackets
                show_targeting_brackets(True)
            else:
                # Target not in FOV
                lock_progress = max(0, lock_progress - time.dt * 2)  # Decay faster
                lock_indicator.text = 'TARGET OFF BORESIGHT'
                lock_indicator.color = color.orange
                reticle.color = color.orange
                show_targeting_brackets(False)
    else:
        # No active lock
        lock_indicator.text = ''
        target_display.text = ''
        lock_bar_bg.visible = False
        lock_bar_fill.visible = False
        reticle.color = color.green
        show_targeting_brackets(False)
        
        # Show available targets
        targets = get_targetable_enemies()
        if targets:
            lock_indicator.text = f'[T] to lock | {len(targets)} targets'
            lock_indicator.color = color.white
            lock_indicator.scale = 1.5

def show_targeting_brackets(visible):
    """Show/hide targeting brackets around locked enemy"""
    bracket_tl.visible = visible
    bracket_tr.visible = visible
    bracket_bl.visible = visible
    bracket_br.visible = visible
    bracket_tl2.visible = visible
    bracket_tr2.visible = visible
    bracket_bl2.visible = visible
    bracket_br2.visible = visible
editor_cam = EditorCamera(enabled=False)
editor_cam.ignore_paused = True

# Controls
def input(key):
    global throttle, models_index, autopilot, gravity, cockpit_view, speed
    global missile_count, flare_count, gun_ammo, locked_target, is_locking, lock_progress
    global radar_enabled, camera_offset
    global editor_mode, game_over
    global y

    if game_over:
        if key == 'r':
            restart_game()
        if key == 'escape':
            application.quit()
        return
    if key == 'f1':
        editor_mode = not editor_mode

        if editor_mode:
            mouse.locked = False
            print("EditorCamera ENABLED")
        else:
            mouse.locked = True
            print("EditorCamera DISABLED")
    if key == 'escape': application.quit()
    if key == 'q' and throttle < 100.0: throttle += 1
    elif key == 'e' and throttle > 0.0: throttle -= 1
    elif key == 'left shift' or key == 'right shift':
        models_index = (models_index + (1 if key == 'left shift' else -1)) % len(models)
        plane.model = models[models_index]
    elif key == 'p':
        autopilot = not autopilot
        if autopilot:
            print("Autopilot ENGAGED")
            plane.rotation_y = get_bearing(plane.position, airport_positions[airport_index])
        else:
            print("Autopilot DISENGAGED")
    elif key == 'j':
        plane.position.y = enemy_planes[0].position.y if enemy_planes else plane.position.y
    elif key == 'space':
        print(f"Saving Airport at: {plane.position}")
    
    if key == 'c':
        cockpit_view = not cockpit_view
        cockpit_ui.visible = cockpit_view
        plane.visible = not cockpit_view
    
    # Fire missile (only if fully locked)
    if key == 'm' and missile_count > 0:
        if locked_target and lock_progress >= lock_time_required:
            yaw_rad = math.radians(plane.rotation_y)
            forward_vector = Vec3(math.sin(yaw_rad), 0, math.cos(yaw_rad)).normalized()
            missile_pos = plane.position + forward_vector * 5 + Vec3(0, 1, 0)
            
            missile = Missile(
                position=missile_pos,
                forward_vector=forward_vector,
                velocity=missile_velocity,
                target=locked_target
            )
            missile.net_id = uuid.uuid4().hex
            missiles.append(missile)
            missile_count -= 1
            
            # Add visual/audio feedback
            lock_indicator.text = 'MISSILE AWAY'
        else:
            # No lock warning
            lock_indicator.text = 'NO LOCK - CANNOT FIRE'
            lock_indicator.color = color.red
    
    # Deploy flare
    if key == 'f' and flare_count > 0:
        flare = Flare(position=plane.position + Vec3(0, -2, 0))
        flares.append(flare)
        flare_count -= 1
    
    # Lock next target (cycle forward)
    if key == 't':
        cycle_target(1)
    
    # Lock previous target (cycle backward)
    if key == 'r':
        cycle_target(-1)
    
    # Break lock
    if key == 'b':
        locked_target = None
        is_locking = False
        lock_progress = 0
        lock_indicator.text = 'LOCK BROKEN'
    
    # Gun fire (simplified - just damage nearest enemy in front)
    if key == 'g' and gun_ammo > 0:
        gun_ammo -= 1
        # Check if enemy in crosshairs
        for enemy in enemy_planes:
            if distance(plane.position, enemy.position) < 500:
                # Simple angle check
                direction = (enemy.position - plane.position).normalized()
                yaw_rad = math.radians(plane.rotation_y)
                forward = Vec3(math.sin(yaw_rad), 0, math.cos(yaw_rad)).normalized()
                
                if direction.dot(forward) > 0.95:  # Within ~18 degrees
                    enemy.take_damage(5)
                    break
    
    # Spawn enemies
    if key == 'n':
        spawn_enemies(3)
    
    # Toggle radar
    if key == 'h':
        radar_enabled = not radar_enabled
        radar_bg.visible = radar_enabled
        radar_grid.visible = radar_enabled
        radar_grid2.visible = radar_enabled
        radar_grid3.visible = radar_enabled
        radar_label.visible = radar_enabled
        radar_range_text.visible = radar_enabled
        radar_n.visible = radar_enabled
        radar_s.visible = radar_enabled
        radar_e.visible = radar_enabled
        radar_w.visible = radar_enabled
        radar_sweep.visible = radar_enabled
    
    # Camera zoom controls
    if key == 'z':
        camera_offset.z -= 2  # Zoom in
    if key == 'x' :
        camera_offset.z += 2  # Zoom out
    if key == 'v':
        camera_offset.z = 10  # Reset to default
        camera_offset.y = 3
    
    if key == 'l':
        explosion_3d(plane.position)
    if key == 'o':
        throttle = 0
        speed = 0
    if key == 'i':
        ground.position = plane.position - Vec3(0, 10, 0)
    if key == 'u':
        y += 1
    if key == 'y':
        y -= 1
# Bearing Calculation
def get_bearing(from_pos, to_pos):
    dx, dz = to_pos[0] - from_pos[0], to_pos[2] - from_pos[2]
    return math.degrees(math.atan2(dx, dz)) % 360

# Navigation Input
def navigate():
    global plane, airport_index
    loc = input_box.text.upper()
    if loc in airport_codes:
        airport_index = airport_codes.index(loc)
        plane.rotation_y = get_bearing(plane.position, airport_positions[airport_index])
    else:
        print("Invalid Airport Code!")
    input_box.visible = label.visible = submit_button.visible = False

def update_altitude_meter():
    alt_percentage = min(plane.y / 10000, 1)
    altitude_bar.position = (-0.8, -0.1 + (alt_percentage * 0.2))
    altitude_bar.scale_y = max(0.02, alt_percentage * 0.2)

def update_horizon():
    horizon.y = -0.3 + (plane.rotation_x / 90) * 0.05
    horizon.rotation_z = -(plane.rotation_y)

def update_radar():
    """Update radar display with enemies, sweep, and bearing information"""
    global enemy_markers, enemy_distance_texts
    
    if not radar_enabled:
        # Hide all radar elements
        for marker in enemy_markers:
            marker.visible = False
        for text in enemy_distance_texts:
            text.visible = False
        locked_marker.visible = False
        locked_marker_ring.visible = False
        return
    
    # Rotate radar sweep line
    radar_sweep.rotation_z += 120 * time.dt  # 2 rotations per second
    
    # Radar parameters
    radar_radius = 0.12  # Visual radius on screen
    radar_max_range = radar_range  # 5000m
    radar_center = Vec2(0.65, -0.35)
    
    # Clear old markers if count doesn't match
    if len(enemy_markers) != len(enemy_planes):
        for marker in enemy_markers:
            destroy(marker)
        for text in enemy_distance_texts:
            destroy(text)
        enemy_markers.clear()
        enemy_distance_texts.clear()
        
        # Create new markers
        for _ in enemy_planes:
            marker = Entity(
                parent=camera.ui, 
                model='circle', 
                color=color.red, 
                scale=0.012, 
                z=-0.22,
                visible=False
            )
            enemy_markers.append(marker)
            
            # Distance text for each enemy
            dist_text = Text(
                parent=camera.ui,
                text='',
                scale=0.8,
                color=color.red,
                origin=(0, 0),
                visible=False
            )
            enemy_distance_texts.append(dist_text)
    
    # Update enemy positions on radar
    for i, enemy in enumerate(enemy_planes):
        if i >= len(enemy_markers):
            continue
            
        # Calculate relative position
        relative_pos = enemy.position - plane.position
        distance_to_enemy = math.sqrt(relative_pos.x**2 + relative_pos.z**2)
        
        # Only show if within radar range
        if distance_to_enemy <= radar_max_range:
            # Calculate bearing (angle from north)
            angle = math.degrees(math.atan2(relative_pos.x, relative_pos.z))
            
            # Adjust for player's heading (rotate relative to player's facing)
            relative_angle = angle - plane.rotation_y
            angle_rad = math.radians(relative_angle)
            
            # Scale distance to radar display
            scaled_distance = (distance_to_enemy / radar_max_range) * radar_radius
            
            # Calculate screen position
            x_offset = scaled_distance * math.sin(angle_rad)
            y_offset = scaled_distance * math.cos(angle_rad)
            
            marker_pos = Vec2(
                radar_center.x + x_offset,
                radar_center.y + y_offset
            )
            
            # Update marker
            enemy_markers[i].position = (marker_pos.x, marker_pos.y, -0.22)
            enemy_markers[i].visible = True
            
            # Change color if this is the locked target
            if enemy == locked_target:
                enemy_markers[i].color = color.yellow
                enemy_markers[i].scale = 0.018
                
                # Update locked marker ring
                locked_marker.position = (marker_pos.x, marker_pos.y, -0.25)
                locked_marker.visible = True
                locked_marker_ring.position = (marker_pos.x, marker_pos.y, -0.26)
                locked_marker_ring.visible = True
                # Pulsing effect
                pulse = 0.03 + 0.01 * math.sin(time.time() * 5)
                locked_marker_ring.scale = pulse
                locked_marker_ring.color = color.rgba(255, 0, 0, 100 + 50 * math.sin(time.time() * 5))
            else:
                enemy_markers[i].color = color.red
                enemy_markers[i].scale = 0.012
            
            # Update distance text (show for closest 3 enemies or locked target)
            if i < 3 or enemy == locked_target:
                # Ensure text element exists
                while len(enemy_distance_texts) <= i:
                    dist_text = Text(
                        parent=minimap,
                        text='',
                        scale=0.8,
                        color=color.red,
                        position=(0, 0),
                        visible=False
                    )
                    enemy_distance_texts.append(dist_text)
                
                enemy_distance_texts[i].text = f'{int(distance_to_enemy)}m'
                enemy_distance_texts[i].position = (marker_pos.x + 0.02, marker_pos.y + 0.01)
                enemy_distance_texts[i].visible = True
                if enemy == locked_target:
                    enemy_distance_texts[i].color = color.yellow
                else:
                    enemy_distance_texts[i].color = color.red
            elif i < len(enemy_distance_texts):
                enemy_distance_texts[i].visible = False
        else:
            # Out of range
            enemy_markers[i].visible = False
            if i < len(enemy_distance_texts):
                enemy_distance_texts[i].visible = False
    
    # Hide locked marker if no lock
    if not locked_target:
        locked_marker.visible = False
        locked_marker_ring.visible = False

def update_offscreen_arrows():
    """Show arrows at screen edge pointing to offscreen enemies"""
    screen_edge = 0.9

    for enemy in enemy_planes:
        if enemy not in offscreen_arrows:
            offscreen_arrows[enemy] = Entity(
                parent=camera.ui,
                model='quad',
                color=color.red,
                scale=(0.04, 0.04),
                visible=False
            )


        arrow = offscreen_arrows[enemy]

        # Vector from player to enemy
        rel = enemy.position - plane.position
        dist = rel.length()

        # Ignore enemies in radar range
        if dist <= radar_range:
            arrow.visible = False
            continue

        # Angle relative to player heading
        angle = math.atan2(rel.x, rel.z) - math.radians(plane.rotation_y)
        angle = (angle + math.pi) % (2 * math.pi) - math.pi

        # Screen position
        x = math.sin(angle) * screen_edge
        y = math.cos(angle) * screen_edge
        arrow.position = (x, y)

        # Rotate arrow to point toward enemy
        arrow.rotation_z = -math.degrees(angle)
        arrow.visible = True

    # Cleanup arrows for destroyed enemies
    for enemy in list(offscreen_arrows.keys()):
        if enemy not in enemy_planes:
            destroy(offscreen_arrows[enemy])
            del offscreen_arrows[enemy]


def update_minimap():
    world_size = 50000
    minimap_size = 0.3
    
    norm_x = plane.x / world_size
    norm_z = plane.z / world_size
    
    plane_marker.x = norm_x * (minimap_size / 2)
    plane_marker.y = norm_z * (minimap_size / 2)
    
    # Update enemy markers
    for i, enemy in enumerate(enemy_planes):
        if i < len(enemy_markers):
            norm_ex = enemy.x / world_size
            norm_ez = enemy.z / world_size
            enemy_markers[i].x = norm_ex * (minimap_size / 2)
            enemy_markers[i].y = norm_ez * (minimap_size / 2)
            enemy_markers[i].visible = True
    
    # Hide unused markers
    for i in range(len(enemy_planes), len(enemy_markers)):
        enemy_markers[i].visible = False

def get_air_density(y):
    return rho0 * math.exp(-y / H)

def get_lift_coefficient(AoA):
    return CL0 + CL_alpha * AoA

def get_drag_coefficient(CL):
    return Cd0 + k * CL**2

def calculate_forces(AoA, velocity, altitude, throttle):
    rho = get_air_density(altitude)
    CL = get_lift_coefficient(AoA)
    CD = get_drag_coefficient(CL)
   
    Lift = 0.5 * rho * velocity**2 * S * CL
    Drag = 0.5 * rho * velocity**2 * S * CD
    Thrust = throttle * T_max * (1 - velocity / 900)
    Weight = mass * g
   
    return Lift, Drag, Thrust, Weight

input_box = InputField(position=(0, 0.3), scale=(0.4, 0.05))
label = Text(text='Type destination airport code (BLR, ICN, HND):', position=(input_box.position[0] - 0.2, input_box.position[1] + 0.1), color=color.black)
submit_button = Button(text='Submit', position=(0, 0.2), scale=(0.1, 0.05), on_click=navigate)

speed = 0

def runcamera(y=4):
    """Smooth lerp camera that stays behind the plane"""
    # Desired camera position (same math as before)
    desired_pos = plane.position - Vec3(
        math.sin(math.radians(plane.rotation_y)) * camera_offset.z,
        -camera_offset.y,
        math.cos(math.radians(plane.rotation_y)) * camera_offset.z
    )

    # Smooth position
    camera.position = lerp(
        camera.position,
        desired_pos,
        time.dt * y    # ← camera follow smoothness (increase = snappier)
    )

    # Smooth look-at (prevents jitter)
    look_target = lerp(
        camera.forward + camera.position,
        plane.position,
        time.dt * y
    )
    camera.look_at(look_target)


def runmissile():
    if missiles:
        camera.position = missiles[0].position - Vec3(
            math.sin(math.radians(plane.rotation_y)) * camera_offset.z,
            -camera_offset.y,
            math.cos(math.radians(plane.rotation_y)) * camera_offset.z
        )
        camera.look_at(missiles[0])

network_planes = {}
ghost_model = 'models/f167'
network_missiles = {}

# Update Loop
y = 4
def update():
    global throttle, lift_force, speed, vertical_velocity, player_health, y
   
    if held_keys['a']: plane.rotation_y -= 1
    if held_keys['d']: plane.rotation_y += 1
    if held_keys['w']: plane.rotation_x -= 1
    if held_keys['s']: plane.rotation_x += 1
    # Speed Calculation
    Lift, Drag, Thrust, Weight = calculate_forces(plane.rotation_x + 90, speed, plane.y, throttle)
    Lift = -Lift
    acceleration = (Thrust - Drag) / mass  
    speed += acceleration * time.dt

    # Move forward
    forward_vector = Vec3(math.sin(math.radians(plane.rotation_y)), 0, math.cos(math.radians(plane.rotation_y)))
    plane.position += forward_vector * speed * time.dt

    # Vertical movement
    vertical_acceleration = (Lift - Weight) / mass
    vertical_velocity += vertical_acceleration * time.dt  
    plane.y += vertical_velocity * time.dt
    
    # Update missiles
    for missile in missiles[:]:
        missile.update()
        hit_info = missile.intersects()
        
        if hit_info.hit and hit_info.entity != missile:
            # Check if hit an enemy
            if hit_info.entity in enemy_planes:
                hit_info.entity.take_damage(100)
            elif hit_info.entity == plane and missile.is_enemy:
                player_health -= 50
                health_display.color = color.red if player_health < 50 else color.green
            
            explosion_3d(hit_info.point)
            explosion.play()
            invoke(missile.cleanup)
    
    # Update enemy planes
    for enemy in enemy_planes[:]:
        enemy.update()
    
    # Update flares
    for flare in flares[:]:
        flare.update()
    
    # Check for incoming missiles
    incoming_missiles = [m for m in missiles if m.is_enemy and m.target == plane]
    if incoming_missiles:
        closest_missile_dist = min([distance(plane.position, m.position) for m in incoming_missiles])
        if closest_missile_dist < 500:
            warning_display.text = f'MISSILE WARNING! {closest_missile_dist:.0f}m'
        else:
            warning_display.text = ''
    else:
        warning_display.text = ''
    
    # Prevent sinking into ground
    if plane.y < 1:
        plane.y = 1
        vertical_velocity = 0
    
    # UI Updates
    speed_display.text = f'Speed: {speed:.2f}'
    altitude_display.text = f'Altitude: {plane.y:.2f}'
    throttle_display.text = f'Throttle: {throttle}%'
    health_display.text = f'Health: {player_health}'
    missile_display.text = f'Missiles: {missile_count}'
    ammo_display.text = f'Ammo: {gun_ammo}'
    flare_display.text = f'Flares: {flare_count}'
    enemy_count_display.text = f'Enemies: {len(enemy_planes)}'

    # Stall Mechanics
    angle_of_attack = -(plane.rotation_x + 90)
    lift_force = max(0, math.sin(math.radians(angle_of_attack))) * throttle * 0.005
    if angle_of_attack > 20 and speed < 50:
        lift_force *= 0.25
        stall_warning.text = "STALL!"
    elif angle_of_attack > 30:
        lift_force = -0.25
        stall_warning.text = "STALL DROP!"
    else:
        stall_warning.text = ""

    plane_engine.pitch = throttle / 100
    plane_engine.volume = throttle / 100
    
    # Terrain warning
    if plane.y < 50:
        terrain_warning.play()
    else:
        terrain_warning.stop()

    if plane.y < 1:
        if speed > 100: crash_sound.play()
        plane.y = 1
    
    # Update targeting
    update_targeting()
    
    # Update radar and minimap
    update_radar()
    update_offscreen_arrows()
    update_altitude_meter()
    update_horizon()
    if editor_mode:
        editor_cam.enabled = True
    else:
        editor_cam.enabled = False
        runcamera(y)

    if held_keys['p']:
        try:
            runmissile()
        except IndexError:
            runcamera(y)
    
    # Check player death
    if player_health <= 0:
        explosion_3d(plane.position)
        
        trigger_game_over()
    
    # Create/update other players
    for pid, d in other_players.items():
        if pid not in network_planes:
            network_planes[pid] = Entity(
                model=ghost_model,
                scale=0.01,
                color=color.blue,
            )

        p = d["pos"]
        r = d["rot"]

        ghost = network_planes[pid]
        ghost.position = Vec3(*p)
        ghost.rotation = Vec3(*r)

        # Update remote missiles
        remote_missiles = d.get('missiles', [])
        present_keys = set()
        for m in remote_missiles:
            key = f"{pid}:{m['id']}"
            present_keys.add(key)
            if key not in network_missiles:
                e = Entity(model='missile', scale=0.05, color=color.orange)
                network_missiles[key] = e
            network_missiles[key].position = Vec3(*m['pos'])
        
        to_remove = [k for k in network_missiles.keys() if k.startswith(f"{pid}:") and k not in present_keys]
        for k in to_remove:
            destroy(network_missiles[k])
            del network_missiles[k]

sun = Entity(
    model='sphere',
    color=color.yellow,
    scale=15,
    position=(10000, 10000, -300),
    emissive=True
)

sunlight = DirectionalLight(shadows=True)

# Spawn initial enemies
spawn_enemies(5)

SERVER_IP = "127.0.0.1"
SERVER_PORT = 5050

try:
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((SERVER_IP, SERVER_PORT))

    buf = ''
    while '\n' not in buf:
        buf += client.recv(4096).decode()
    player_id = json.loads(buf.split('\n', 1)[0])['id']
    print("Connected as player", player_id)
except:
    print("Could not connect to server, running offline")
    client = None
    player_id = "offline"

other_players = {}
net_recv_buffer = ''

def networking_loop():
    global other_players, net_recv_buffer
    if not client:
        return
    
    while True:
        missiles_payload = []
        for m in missiles:
            mid = getattr(m, 'net_id', None)
            if mid is None:
                continue
            missiles_payload.append({
                'id': mid,
                'pos': [m.x, m.y, m.z],
                'forward': [m.forward_vec.x, m.forward_vec.y, m.forward_vec.z],
                'vel': m.velocity,
            })
        
        send_data = {
            "pos": [plane.x, plane.y, plane.z],
            "rot": [plane.rotation_x, plane.rotation_y, plane.rotation_z],
            "missiles": missiles_payload,
        }
        try:
            client.sendall((json.dumps(send_data) + "\n").encode())
        except (BrokenPipeError, ConnectionResetError):
            break

        try:
            data = client.recv(4096)
            if not data:
                break
            net_recv_buffer += data.decode()
            while '\n' in net_recv_buffer:
                line, net_recv_buffer = net_recv_buffer.split('\n', 1)
                if not line:
                    continue
                try:
                    other_players = json.loads(line)
                except json.JSONDecodeError:
                    continue
        except (BrokenPipeError, ConnectionResetError):
            break

        time.sleep(0.066)

if client:
    net_thread = threading.Thread(target=networking_loop, daemon=True)
    net_thread.start()
Sky(texture='sky_sunset')
app.run()
