sun = Entity(
    model='sphere',
    color=color.yellow,
    scale=15,
    position=(10000, 10000, -300),
    emissive=True
)

sunlight = DirectionalLight(shadows=True)

# Spawn initial enemies (driven by selected quest/challenge when present)
spawn_count = 5
if 'initial_enemy_count_override' in globals() and initial_enemy_count_override:
    spawn_count = int(initial_enemy_count_override)
elif 'difficulty_scale' in globals():
    spawn_count = max(3, int(round(5 * difficulty_scale)))
spawn_enemies(spawn_count)

