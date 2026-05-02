# Update Loop
y = 4
mission_complete = False

def update():
    
    global throttle, lift_force, speed, vertical_velocity, player_health, y, mission_complete, initial_enemy_count, game_paused, base_destroyed
    global mouse_pitch, mouse_yaw, completed_objectives, highest_altitude
    global last_badge_check_time

    mx = mouse.velocity[0]
    my = mouse.velocity[1]

    # Ignore tiny deltas to reduce micro-jitter from high polling mice.
    if abs(mx) < 0.001:
        mx = 0
    if abs(my) < 0.001:
        my = 0

    # Keep input feel stable across frame rates.
    input_scale = mouse_sensitivity * time.dt * 60
    mouse_yaw += mx * input_scale
    mouse_pitch -= my * input_scale

    # Clamp look range
    mouse_yaw = clamp(mouse_yaw, -max_look_angle, max_look_angle)
    mouse_pitch = clamp(mouse_pitch, -max_look_angle, max_look_angle)

    # Return to center only when the player isn't actively moving the mouse.
    if mx == 0:
        mouse_yaw = lerp(mouse_yaw, 0, time.dt * 0.8)
    if my == 0:
        mouse_pitch = lerp(mouse_pitch, 0, time.dt * 0.8)

    if displayed is not None:
        displayed.color = color.rgb(
            0,
            random.randint(230, 255),
            random.randint(80, 120)
        )

    if game_paused:
        return
    if held_keys['a']: plane.rotation_y -= 2.3
    if held_keys['d']: plane.rotation_y += 2.3
    if held_keys['w']: plane.rotation_x -= 2.3
    if held_keys['s']: plane.rotation_x += 2.3
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
            if hit_info.entity == enemy_base:
                enemy_base.health -= 200

                if enemy_base.health <= 0:
                    explosion_3d(enemy_base.position)
                    destroy(enemy_base)
                    base_destroyed = True

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

    if "last_badge_check_time" not in globals():
        last_badge_check_time = 0
    if time.time() - last_badge_check_time >= 0.5:
        last_badge_check_time = time.time()
        if 'check_badges' in globals() and 'show_badge_unlocked' in globals():
            new_badges = check_badges()
            if new_badges:
                show_badge_unlocked(new_badges)

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

    if held_keys['k']:
        try:
            runmissile()
        except IndexError:
            runcamera(y)
    
    # Check player death
    if player_health <= 0:
        explosion_3d(plane.position)
        
        trigger_game_over()

    if "initial_enemy_count" not in globals():
        initial_enemy_count = len(enemy_planes)

    if "completed_objectives" not in globals():
        completed_objectives = set()
    if "highest_altitude" not in globals():
        highest_altitude = plane.y
    highest_altitude = max(highest_altitude, plane.y)

    mission_constraints = {}


    for obj in mission.get("objectives", []):

        desc = obj.get("description", "Unnamed Objective")
        obj_type = obj.get("type")

        completed = desc in completed_objectives

        if not completed and obj_type == "destroy":
            target = obj.get("amount", 0)
            destroyed_count = initial_enemy_count - len(enemy_planes)
            completed = destroyed_count >= target

        elif not completed and obj_type == "survive":
            duration = obj.get("duration", 0)
            completed = (
                player_health > 0 and
                time.time() - mission_start_time >= duration
            )

        elif not completed and obj_type == "reach_altitude":
            required_altitude = obj.get("target", 0)
            completed = highest_altitude >= required_altitude

        elif not completed and obj_type == "destroy_base":
            completed = base_destroyed

        elif not completed and obj_type == "destroy_in_time":
            target = obj.get("amount", 0)
            time_limit = obj.get("time_limit", 0)

            destroyed_count = initial_enemy_count - len(enemy_planes)
            elapsed = time.time() - mission_start_time

            if elapsed > time_limit:
                mission_failed = True
                trigger_game_over()
            else:
                completed = destroyed_count >= target

        mission_constraints[desc] = completed

        if completed and desc not in completed_objectives:
            print(f"Objective completed: {desc}")
            completed_objectives.add(desc)

    if (
        mission_constraints and
        all(mission_constraints.values()) and
        not mission_complete
    ):
        mission_complete = True
        trigger_mission_complete()

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

