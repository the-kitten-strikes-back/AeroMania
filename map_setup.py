# Define Airports
Text.default_font = 'models/orbitron.ttf'

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
water = Entity(model='cube', scale=(2000, 1, 500), position=(0, 0.05, -3000), color=color.blue)
ground = Entity(model='plane', texture='models/rocks.jpg', texture_scale=(100, 100), scale=(100000, 100000, 100000), position=((10579.429, 1, 5094.8447)))

enemy_base = Entity(
    model='cube',
    scale=(200, 50, 200),
    position=(-2000, 150, 2000),
    color=color.gray
)

enemy_base.health = 1000
base_destroyed = False

# Plane Setup
models = ['models/f16', 'models/tinker', 'models/ac130', 'models/f167', 'models/xwing']
default_model = 'models/f167'
if 'selected_aircraft_model' in globals() and selected_aircraft_model in models:
    default_model = selected_aircraft_model
plane = Entity(model=default_model, scale=0.09, rotation=(0, 0, 0), position=((10579.429, 1.2, 5094.8447)), collider='mesh')
plane.look_at(enemy_base)
camera_offset = Vec3(0, 3, 10)
cockpit_ui = Entity(parent=camera.ui, model='quad', texture=cockpit_texture, scale=(3, 2), position=plane.position, visible=False)
cockpit_model = Entity(parent=camera, visible=False, enabled=False)

for cockpit_candidate in ('models/f16_cockpit', 'models/cockpit', 'models/f16'):
    if os.path.exists(f'{cockpit_candidate}.obj') or os.path.exists(f'{cockpit_candidate}.bam'):
        cockpit_model.model = cockpit_candidate
        cockpit_model.position = Vec3(0, -0.22, 0.62)
        cockpit_model.rotation = Vec3(0, 180, 0)
        cockpit_model.scale = 0.004 if cockpit_candidate == 'models/f16' else 0.35
        cockpit_model.double_sided = True
        cockpit_model.enabled = True
        break

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
points_display = Text(text='Points: 0', position=(0.5, 0.2), scale=2, color=color.yellow)
enemy_destroyed_display = Text(text='', position=(0, 0.15), scale=2, color=color.green)

# Targeting reticle and bounding boxes
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

def create_outline_box(thickness=0.003):
    box = Entity(parent=camera.ui, visible=False)

    box.top_edge = Entity(parent=box, model='quad', scale=(1, thickness))
    box.bottom_edge = Entity(parent=box, model='quad', scale=(1, thickness))
    box.left_edge = Entity(parent=box, model='quad', scale=(thickness, 1))
    box.right_edge = Entity(parent=box, model='quad', scale=(thickness, 1))

    for part in (
        box.top_edge,
        box.bottom_edge,
        box.left_edge,
        box.right_edge
    ):
        part.color = color.red

    return box


enemy_box = create_outline_box()


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
models_index = models.index(default_model)
autopilot, airport_index = False, 0

