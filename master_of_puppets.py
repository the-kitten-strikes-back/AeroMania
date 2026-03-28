
MODULE_ORDER = [
    'bootstrap.py',
    'physics.py',
    'effects.py',
    'entities.py',
    'map_setup.py',
    'combat_system.py',
    'controls.py',
    'hud_systems.py',
    'ui_navigation.py',
    'camera_system.py',
    'game_loop.py',
    'world_init.py',
    'networking.py',
    'app_entry.py',
]

for module_file in MODULE_ORDER:
    with open(module_file, 'r', encoding='utf-8') as f:
        code = compile(f.read(), module_file, 'exec')
        exec(code, globals(), globals())
