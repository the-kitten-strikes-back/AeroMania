def create_explosion(position, num_particles=20, speed=5, lifetime=1):
    for _ in range(num_particles):
        particle = Entity(
            model='sphere',
            color=color.orange,
            scale=10,
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
        scale=2.5,
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
            scale=2.5,
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
        scale=10,
        position=position
    )
    smoke.animate_scale(6, duration=smoke_time, curve=curve.out_expo)
    smoke.animate_color(color.rgba(20,20,20,0), duration=smoke_time, delay=0.2)
    destroy(smoke, delay=smoke_time)
